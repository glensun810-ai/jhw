#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试脚本
验证 P0-P1 优化后的性能指标

测试场景：
1. SSE 连接性能
2. 配置热更新性能
3. API 响应时间
4. 并发连接测试
"""

import sys
import time
import json
import requests
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = 'http://127.0.0.1:5001'

class TestColors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{TestColors.BOLD}{TestColors.BLUE}{'='*70}{TestColors.END}")
    print(f"{TestColors.BOLD}{TestColors.BLUE}  {text}{TestColors.END}")
    print(f"{TestColors.BOLD}{TestColors.BLUE}{'='*70}{TestColors.END}\n")

def print_metric(name, value, unit, target=None, success=True):
    status = f"{TestColors.GREEN}✅{TestColors.END}" if success else f"{TestColors.RED}❌{TestColors.END}"
    target_text = f" (目标：{target}{unit})" if target else ""
    print(f"{status} {name}: {value}{unit}{target_text}")

class PerformanceBenchmarkTester:
    """性能基准测试器"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'metrics': [],
            'passed': 0,
            'failed': 0
        }
    
    def test_health_endpoint_latency(self):
        """测试健康检查端点延迟"""
        print_header("1. 健康检查端点延迟测试")
        
        latencies = []
        iterations = 10
        
        print(f"执行 {iterations} 次请求测试...")
        
        for i in range(iterations):
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}/health", timeout=5)
                latency = (time.time() - start) * 1000  # 转换为毫秒
                
                if response.status_code == 200:
                    latencies.append(latency)
            except Exception as e:
                print(f"请求失败：{e}")
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print_metric("平均延迟", f"{avg_latency:.2f}", "ms", target="50ms", success=avg_latency < 50)
            print_metric("P95 延迟", f"{p95_latency:.2f}", "ms", target="100ms", success=p95_latency < 100)
            print_metric("最小延迟", f"{min_latency:.2f}", "ms")
            print_metric("最大延迟", f"{max_latency:.2f}", "ms")
            
            self.results['metrics'].append({
                'name': '健康检查延迟',
                'avg_ms': avg_latency,
                'p95_ms': p95_latency,
                'min_ms': min_latency,
                'max_ms': max_latency,
                'iterations': iterations,
                'passed': avg_latency < 50 and p95_latency < 100
            })
            
            if avg_latency < 50 and p95_latency < 100:
                self.results['passed'] += 1
                return True
            else:
                self.results['failed'] += 1
                return False
        else:
            print_metric("测试", "失败", "", success=False)
            self.results['failed'] += 1
            return False
    
    def test_sse_connection(self):
        """测试 SSE 连接性能"""
        print_header("2. SSE 连接性能测试")
        
        try:
            # 测试 SSE 统计端点响应时间
            start = time.time()
            response = self.session.get(f"{self.base_url}/sse/stats", timeout=5)
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                print_metric("SSE 统计端点延迟", f"{latency:.2f}", "ms", target="50ms", success=latency < 50)
                print_metric("当前连接数", data.get('total_connections', 0), "")
                print_metric("已发送消息", data.get('messages_sent', 0), "")
                
                self.results['metrics'].append({
                    'name': 'SSE 连接性能',
                    'latency_ms': latency,
                    'connections': data.get('total_connections', 0),
                    'messages_sent': data.get('messages_sent', 0),
                    'passed': latency < 50
                })
                
                if latency < 50:
                    self.results['passed'] += 1
                    return True
                else:
                    self.results['failed'] += 1
                    return False
            else:
                print_metric("SSE 统计端点", f"HTTP {response.status_code}", "", success=False)
                self.results['failed'] += 1
                return False
                
        except Exception as e:
            print_metric("SSE 连接测试", str(e), "", success=False)
            self.results['failed'] += 1
            return False
    
    def test_concurrent_connections(self):
        """测试并发连接性能"""
        print_header("3. 并发连接测试")
        
        def make_request(i):
            try:
                start = time.time()
                response = requests.get(f"{self.base_url}/health", timeout=10)
                latency = (time.time() - start) * 1000
                return {
                    'success': response.status_code == 200,
                    'latency': latency,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        concurrent_users = 10
        print(f"模拟 {concurrent_users} 个并发用户...")
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_users)]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        successful = sum(1 for r in results if r.get('success'))
        latencies = [r['latency'] for r in results if r.get('success') and 'latency' in r]
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            
            print_metric("成功请求", successful, f"/{concurrent_users}", success=successful == concurrent_users)
            print_metric("平均延迟", f"{avg_latency:.2f}", "ms", target="100ms", success=avg_latency < 100)
            
            self.results['metrics'].append({
                'name': '并发连接测试',
                'concurrent_users': concurrent_users,
                'successful': successful,
                'total': concurrent_users,
                'avg_latency_ms': avg_latency,
                'passed': successful == concurrent_users and avg_latency < 100
            })
            
            if successful == concurrent_users and avg_latency < 100:
                self.results['passed'] += 1
                return True
            else:
                self.results['failed'] += 1
                return False
        else:
            print_metric("并发测试", "失败", "", success=False)
            self.results['failed'] += 1
            return False
    
    def test_api_response_time(self):
        """测试 API 响应时间"""
        print_header("4. API 响应时间测试")
        
        endpoints = [
            '/health',
            '/sse/stats',
            '/api/config'
        ]
        
        all_passed = True
        
        for endpoint in endpoints:
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                latency = (time.time() - start) * 1000
                
                success = response.status_code == 200 and latency < 100
                print_metric(f"{endpoint}", f"{latency:.2f}", "ms", target="100ms", success=success)
                
                self.results['metrics'].append({
                    'name': f'API 响应时间：{endpoint}',
                    'latency_ms': latency,
                    'status_code': response.status_code,
                    'passed': success
                })
                
                if not success:
                    all_passed = False
                    
            except Exception as e:
                print_metric(f"{endpoint}", str(e), "", success=False)
                all_passed = False
        
        if all_passed:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
        
        return all_passed
    
    def run_all_tests(self):
        """运行所有性能测试"""
        print_header("⚡ 性能基准测试套件")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"服务器地址：{self.base_url}")
        
        # 首先检查服务器是否可用
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print(f"{TestColors.RED}服务器未响应或返回错误状态码{TestColors.END}")
                return False
        except Exception as e:
            print(f"{TestColors.RED}无法连接到服务器：{e}{TestColors.END}")
            return False
        
        # 执行测试
        self.test_health_endpoint_latency()
        self.test_sse_connection()
        self.test_concurrent_connections()
        self.test_api_response_time()
        
        # 打印汇总
        self.print_summary()
        
        return self.results['failed'] == 0
    
    def print_summary(self):
        """打印测试汇总"""
        print_header("📊 性能测试汇总报告")
        
        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0
        
        print(f"总测试数：{total}")
        print(f"{TestColors.GREEN}通过：{self.results['passed']}{TestColors.END}")
        print(f"{TestColors.RED}失败：{self.results['failed']}{TestColors.END}")
        print(f"通过率：{pass_rate:.1f}%")
        
        # 性能指标汇总
        print(f"\n{TestColors.BOLD}性能指标汇总:{TestColors.END}")
        
        for metric in self.results['metrics']:
            if 'avg_latency_ms' in metric or 'latency_ms' in metric:
                latency = metric.get('avg_latency_ms') or metric.get('latency_ms')
                name = metric['name']
                status = "✅" if metric.get('passed') else "❌"
                print(f"  {status} {name}: {latency:.2f}ms")
        
        if self.results['failed'] == 0:
            print(f"\n{TestColors.GREEN}{TestColors.BOLD}🎉 所有性能测试通过！系统性能优秀。{TestColors.END}")
        else:
            print(f"\n{TestColors.RED}{TestColors.BOLD}⚠️  有 {self.results['failed']} 个测试失败，请优化系统性能。{TestColors.END}")
        
        # 保存测试结果
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'summary': {
                'total': total,
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'pass_rate': pass_rate
            },
            'metrics': self.results['metrics']
        }
        
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试报告已保存到：{report_file}")


if __name__ == '__main__':
    tester = PerformanceBenchmarkTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
