#!/usr/bin/env python3
"""
差距 8 修复：性能压测脚本

功能:
1. 负载测试
2. 并发测试
3. 压力测试
4. 性能基准测试

使用方法:
    python3 tests/performance/load_test.py
    python3 tests/performance/load_test.py --concurrent 100
    python3 tests/performance/load_test.py --duration 60
"""

import time
import argparse
import statistics
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import json


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, base_url: str = 'http://127.0.0.1:5000'):
        self.base_url = base_url
        self.results = []
    
    def make_single_request(self, endpoint: str, method: str = 'GET', 
                           data: Dict = None) -> Tuple[float, int, bool]:
        """
        发起单个请求
        
        Returns:
            (响应时间，状态码，成功标志)
        """
        start_time = time.time()
        try:
            if method == 'GET':
                response = requests.get(f"{self.base_url}{endpoint}", timeout=30)
            elif method == 'POST':
                response = requests.post(f"{self.base_url}{endpoint}", 
                                       json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = time.time() - start_time
            success = response.status_code == 200
            
            return elapsed, response.status_code, success
            
        except Exception as e:
            elapsed = time.time() - start_time
            return elapsed, 0, False
    
    def health_check(self) -> bool:
        """健康检查"""
        print("📊 执行健康检查...")
        elapsed, status, success = self.make_single_request('/api/test')
        
        if success:
            print(f"✅ 健康检查通过 (响应时间：{elapsed:.2f}秒)")
            return True
        else:
            print(f"❌ 健康检查失败 (状态码：{status})")
            return False
    
    def load_test(self, endpoint: str, concurrent_users: int = 10, 
                 total_requests: int = 100, method: str = 'GET',
                 data: Dict = None) -> Dict:
        """
        负载测试
        
        Args:
            endpoint: API 端点
            concurrent_users: 并发用户数
            total_requests: 总请求数
            method: 请求方法
            data: 请求数据
        
        Returns:
            测试结果统计
        """
        print(f"\n🚀 开始负载测试")
        print(f"   端点：{endpoint}")
        print(f"   并发用户数：{concurrent_users}")
        print(f"   总请求数：{total_requests}")
        print()
        
        start_time = time.time()
        results = []
        
        def worker():
            return self.make_single_request(endpoint, method, data)
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(total_requests)]
            
            for future in as_completed(futures):
                elapsed, status, success = future.result()
                results.append({
                    'elapsed': elapsed,
                    'status': status,
                    'success': success
                })
        
        total_time = time.time() - start_time
        
        # 统计分析
        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) * 100 if results else 0
        
        elapsed_times = [r['elapsed'] for r in results if r['success']]
        avg_elapsed = statistics.mean(elapsed_times) if elapsed_times else 0
        p50_elapsed = statistics.median(elapsed_times) if elapsed_times else 0
        p95_elapsed = sorted(elapsed_times)[int(len(elapsed_times) * 0.95)] if len(elapsed_times) > 1 else 0
        p99_elapsed = sorted(elapsed_times)[int(len(elapsed_times) * 0.99)] if len(elapsed_times) > 1 else 0
        
        # 吞吐量
        requests_per_second = total_requests / total_time if total_time > 0 else 0
        
        stats = {
            'total_requests': total_requests,
            'success_count': success_count,
            'fail_count': total_requests - success_count,
            'success_rate': f"{success_rate:.1f}%",
            'total_time': f"{total_time:.2f}秒",
            'requests_per_second': f"{requests_per_second:.1f} RPS",
            'avg_response_time': f"{avg_elapsed:.3f}秒",
            'p50_response_time': f"{p50_elapsed:.3f}秒",
            'p95_response_time': f"{p95_elapsed:.3f}秒",
            'p99_response_time': f"{p99_elapsed:.3f}秒"
        }
        
        return stats
    
    def stress_test(self, duration_seconds: int = 60, 
                   max_concurrent: int = 100) -> Dict:
        """
        压力测试
        
        Args:
            duration_seconds: 测试持续时间（秒）
            max_concurrent: 最大并发数
        
        Returns:
            测试结果
        """
        print(f"\n💥 开始压力测试")
        print(f"   持续时间：{duration_seconds}秒")
        print(f"   最大并发数：{max_concurrent}")
        print()
        
        start_time = time.time()
        request_count = 0
        success_count = 0
        error_count = 0
        
        def worker():
            nonlocal request_count, success_count, error_count
            while time.time() - start_time < duration_seconds:
                request_count += 1
                elapsed, status, success = self.make_single_request('/api/test')
                if success:
                    success_count += 1
                else:
                    error_count += 1
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(worker) for _ in range(max_concurrent)]
            for future in as_completed(futures):
                future.result()
        
        total_time = time.time() - start_time
        
        stats = {
            'duration': f"{total_time:.2f}秒",
            'total_requests': request_count,
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': f"{success_count/request_count*100:.1f}%" if request_count > 0 else "0%",
            'requests_per_second': f"{request_count/total_time:.1f} RPS" if total_time > 0 else "0 RPS"
        }
        
        return stats
    
    def print_stats(self, stats: Dict, title: str = "测试结果"):
        """打印统计结果"""
        print(f"\n{'='*60}")
        print(f"📊 {title}")
        print(f"{'='*60}")
        
        for key, value in stats.items():
            # 格式化键名
            key_name = key.replace('_', ' ').title()
            print(f"   {key_name:25s}: {value}")
        
        print(f"{'='*60}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='性能压测工具')
    parser.add_argument('--base-url', default='http://127.0.0.1:5000',
                       help='基础 URL')
    parser.add_argument('--concurrent', type=int, default=10,
                       help='并发用户数')
    parser.add_argument('--requests', type=int, default=100,
                       help='总请求数')
    parser.add_argument('--duration', type=int, default=60,
                       help='压力测试持续时间（秒）')
    parser.add_argument('--max-concurrent', type=int, default=100,
                       help='压力测试最大并发数')
    
    args = parser.parse_args()
    
    print("="*60)
    print("差距 8 修复：性能压测")
    print("="*60)
    print()
    
    tester = PerformanceTester(args.base_url)
    
    # 1. 健康检查
    if not tester.health_check():
        print("\n❌ 服务不可用，请确保后端服务已启动")
        return
    
    # 2. 负载测试
    print("\n" + "="*60)
    print("阶段 1: 负载测试")
    print("="*60)
    
    load_stats = tester.load_test(
        endpoint='/api/test',
        concurrent_users=args.concurrent,
        total_requests=args.requests,
        method='GET'
    )
    tester.print_stats(load_stats, "负载测试结果")
    
    # 3. 压力测试
    print("\n" + "="*60)
    print("阶段 2: 压力测试")
    print("="*60)
    
    stress_stats = tester.stress_test(
        duration_seconds=args.duration,
        max_concurrent=args.max_concurrent
    )
    tester.print_stats(stress_stats, "压力测试结果")
    
    # 4. 总结
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)
    print(f"✅ 负载测试完成：{load_stats['total_requests']} 个请求")
    print(f"✅ 压力测试完成：{stress_stats['total_requests']} 个请求")
    print(f"✅ 平均吞吐量：{load_stats['requests_per_second']}")
    print()
    print("💡 建议:")
    print("   - 如果成功率 < 95%，检查服务器配置")
    print("   - 如果 P95 响应时间 > 2 秒，优化数据库查询")
    print("   - 如果 RPS < 10，考虑增加服务器或使用缓存")
    print("="*60)


if __name__ == '__main__':
    main()
