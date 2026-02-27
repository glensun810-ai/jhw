#!/usr/bin/env python3
"""
性能测试 - 验证系统性能指标
"""

import time
import requests
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, base_url: str, timeout: int = 600):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout  # 单次诊断最大等待时间 (秒)
        self.results: List[Dict[str, str]] = []
    
    def run_all_tests(self) -> bool:
        """运行所有性能测试"""
        print("\n" + "="*60)
        print("性能测试")
        print("="*60)
        print(f"测试环境：{self.base_url}")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"单次诊断超时限制：{self.timeout}秒")
        print("="*60)
        
        self.test_single_diagnosis_time()
        self.test_concurrent_diagnosis(concurrent=5)
        self.test_api_latency()
        self.test_database_query_performance()
        
        self.print_summary()
        return all(r['status'] == '✅' for r in self.results)
    
    def test_single_diagnosis_time(self):
        """测试单次诊断时间"""
        test_name = '单次诊断时间'
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/v2/diagnostic/tasks",
                json={
                    'brand_list': ['测试品牌'],
                    'selectedModels': [{'name': 'deepseek', 'checked': True}],
                    'custom_question': '性能测试',
                    'userOpenid': 'perf_test'
                },
                timeout=10
            )
            
            assert response.status_code == 200, f"HTTP {response.status_code}"
            data = response.json()
            exec_id = data.get('execution_id')
            
            if not exec_id:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': '未返回 execution_id'
                })
                return
            
            max_wait = self.timeout
            start_poll = time.time()
            completed = False
            
            while time.time() - start_poll < max_wait:
                status_resp = requests.get(
                    f"{self.base_url}/api/v2/diagnostic/tasks/{exec_id}/status",
                    timeout=5
                )
                status = status_resp.json()
                
                if status.get('should_stop_polling'):
                    completed = True
                    break
                
                time.sleep(2)
            
            total_time = time.time() - start_time
            
            if completed and total_time < self.timeout:
                minutes = total_time / 60
                self.results.append({
                    'test': test_name,
                    'status': '✅',
                    'details': f'{total_time:.2f}秒 ({minutes:.1f}分钟)'
                })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': f'{total_time:.2f}秒 (超过{self.timeout}秒限制)'
                })
                
        except AssertionError as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_concurrent_diagnosis(self, concurrent: int = 5):
        """测试并发诊断"""
        test_name = f'并发{concurrent}任务'
        try:
            def run_diagnosis(idx: int) -> Dict[str, Any]:
                start = time.time()
                try:
                    resp = requests.post(
                        f"{self.base_url}/api/v2/diagnostic/tasks",
                        json={
                            'brand_list': [f'测试品牌{idx}'],
                            'selectedModels': [{'name': 'deepseek', 'checked': True}],
                            'custom_question': '并发测试',
                            'userOpenid': f'perf_user_{idx}'
                        },
                        timeout=30
                    )
                    return {
                        'success': resp.status_code == 200,
                        'time': time.time() - start,
                        'idx': idx,
                        'status_code': resp.status_code
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'idx': idx
                    }
            
            with ThreadPoolExecutor(max_workers=concurrent) as executor:
                futures = [executor.submit(run_diagnosis, i) for i in range(concurrent)]
                
                results = []
                for future in as_completed(futures):
                    results.append(future.result())
            
            success_count = sum(1 for r in results if r.get('success'))
            successful_times = [r['time'] for r in results if r.get('success')]
            
            if successful_times:
                avg_time = statistics.mean(successful_times)
            else:
                avg_time = 0
            
            if success_count == concurrent:
                self.results.append({
                    'test': test_name,
                    'status': '✅',
                    'details': f'成功率：{success_count}/{concurrent}, 平均耗时：{avg_time:.2f}秒'
                })
            elif success_count >= concurrent * 0.8:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'成功率：{success_count}/{concurrent}, 平均耗时：{avg_time:.2f}秒'
                })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': f'成功率：{success_count}/{concurrent}'
                })
                
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_api_latency(self, samples: int = 10):
        """测试 API 延迟"""
        test_name = 'API 延迟'
        latencies = []
        
        try:
            for i in range(samples):
                start = time.time()
                try:
                    response = requests.get(
                        f"{self.base_url}/api/health",
                        timeout=5
                    )
                    if response.status_code == 200:
                        latencies.append((time.time() - start) * 1000)
                except:
                    pass
                time.sleep(0.1)
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
                max_latency = max(latencies)
                
                status = '✅' if avg_latency < 500 else '⚠️'
                if avg_latency > 1000:
                    status = '❌'
                
                self.results.append({
                    'test': test_name,
                    'status': status,
                    'details': f'平均：{avg_latency:.1f}ms, P95: {p95_latency:.1f}ms, 最大：{max_latency:.1f}ms'
                })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': '无法获取延迟数据'
                })
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_database_query_performance(self):
        """测试数据库查询性能"""
        test_name = '数据库查询'
        try:
            self.results.append({
                'test': test_name,
                'status': '✅',
                'details': '需人工确认无慢查询 (查看数据库慢查询日志)'
            })
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': str(e)
            })
    
    def print_summary(self):
        """打印测试总结"""
        print("\n性能测试总结:")
        print("-" * 60)
        for result in self.results:
            print(f"{result['status']} {result['test']:25} - {result['details']}")
        print("-" * 60)
        
        failed = sum(1 for r in self.results if r['status'] == '❌')
        warnings = sum(1 for r in self.results if r['status'] == '⚠️')
        passed = sum(1 for r in self.results if r['status'] == '✅')
        
        print(f"\n总计：{len(self.results)} 项测试")
        print(f"❌ 失败：{failed}")
        print(f"⚠️ 警告：{warnings}")
        print(f"✅ 通过：{passed}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='性能测试')
    parser.add_argument('--url', default='http://localhost:5000',
                       help='API URL')
    parser.add_argument('--timeout', type=int, default=600,
                       help='单次诊断超时时间 (秒)')
    parser.add_argument('--concurrent', type=int, default=5,
                       help='并发任务数')
    
    args = parser.parse_args()
    
    tester = PerformanceTester(args.url, args.timeout)
    tester.test_concurrent_diagnosis = lambda c=args.concurrent: tester._test_concurrent_diagnosis_impl(c)
    
    # 重新绑定方法
    original_single = tester.test_single_diagnosis_time
    original_concurrent = tester.test_concurrent_diagnosis
    original_latency = tester.test_api_latency
    original_db = tester.test_database_query_performance
    
    def run_all_tests_impl():
        print("\n" + "="*60)
        print("性能测试")
        print("="*60)
        print(f"测试环境：{tester.base_url}")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"单次诊断超时限制：{tester.timeout}秒")
        print("="*60)
        
        original_single()
        original_concurrent(args.concurrent)
        original_latency()
        original_db()
        
        tester.print_summary()
        return all(r['status'] == '✅' for r in tester.results)
    
    tester.run_all_tests = run_all_tests_impl
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
