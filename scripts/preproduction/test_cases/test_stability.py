#!/usr/bin/env python3
"""
稳定性测试 - 长时间运行测试
验证系统在持续负载下的稳定性
"""

import time
import requests
import threading
import random
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class StabilityTester:
    """稳定性测试器"""
    
    def __init__(self, base_url: str, duration_minutes: int = 30):
        self.base_url = base_url.rstrip('/')
        self.duration_minutes = duration_minutes
        self.results: List[Dict[str, str]] = []
        self.errors: List[Dict[str, Any]] = []
        self.running = False
        self.last_exec_id: Optional[str] = None
        self.metrics_history: List[Dict[str, Any]] = []
    
    def run_all_tests(self) -> bool:
        """运行稳定性测试"""
        print(f"\n{'='*60}")
        print(f"稳定性测试 - 持续运行 {self.duration_minutes} 分钟")
        print(f"{'='*60}")
        print(f"测试环境：{self.base_url}")
        print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"预计结束：{(datetime.now() + timedelta(minutes=self.duration_minutes)).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        self.running = True
        
        monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        monitor_thread.start()
        
        self._run_load_test()
        
        self.running = False
        monitor_thread.join(timeout=10)
        
        self._analyze_results()
        self.print_summary()
        
        return len(self.errors) == 0
    
    def _monitor_system(self):
        """监控系统指标"""
        check_interval = 30
        
        while self.running:
            try:
                health = requests.get(
                    f"{self.base_url}/api/health",
                    timeout=5
                )
                
                if health.status_code != 200:
                    self.errors.append({
                        'time': datetime.now(),
                        'type': 'health_check_failed',
                        'details': f'HTTP {health.status_code}'
                    })
                
                try:
                    metrics = requests.get(
                        f"{self.base_url}/api/monitoring/metrics",
                        timeout=5
                    )
                    
                    if metrics.status_code == 200:
                        data = metrics.json()
                        memory_usage = data.get('memory_usage', 0)
                        cpu_usage = data.get('cpu_usage', 0)
                        
                        self.metrics_history.append({
                            'time': datetime.now(),
                            'memory': memory_usage,
                            'cpu': cpu_usage
                        })
                        
                        if memory_usage > 80:
                            self.errors.append({
                                'time': datetime.now(),
                                'type': 'high_memory',
                                'details': f"内存使用率：{memory_usage}%"
                            })
                        
                        if cpu_usage > 90:
                            self.errors.append({
                                'time': datetime.now(),
                                'type': 'high_cpu',
                                'details': f"CPU 使用率：{cpu_usage}%"
                            })
                except:
                    pass
                
            except Exception as e:
                self.errors.append({
                    'time': datetime.now(),
                    'type': 'monitor_error',
                    'details': str(e)
                })
            
            time.sleep(check_interval)
    
    def _run_load_test(self):
        """运行持续负载"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=self.duration_minutes)
        
        iteration = 0
        
        while self.running and datetime.now() < end_time:
            iteration += 1
            
            try:
                action = random.choice(['diagnosis', 'status', 'report', 'history'])
                
                if action == 'diagnosis' or self.last_exec_id is None:
                    try:
                        response = requests.post(
                            f"{self.base_url}/api/v2/diagnostic/tasks",
                            json={
                                'brand_list': [f'测试品牌{random.randint(1,100)}'],
                                'selectedModels': [{'name': 'deepseek', 'checked': True}],
                                'custom_question': f'稳定性测试-{iteration}',
                                'userOpenid': f'stress_user_{random.randint(1,10)}'
                            },
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            self.last_exec_id = data.get('execution_id')
                        else:
                            self.errors.append({
                                'time': datetime.now(),
                                'type': 'diagnosis_failed',
                                'details': f'HTTP {response.status_code}'
                            })
                    except Exception as e:
                        self.errors.append({
                            'time': datetime.now(),
                            'type': 'diagnosis_error',
                            'details': str(e)
                        })
                
                elif action == 'status' and self.last_exec_id:
                    try:
                        requests.get(
                            f"{self.base_url}/api/v2/diagnostic/tasks/{self.last_exec_id}/status",
                            timeout=5
                        )
                    except Exception as e:
                        self.errors.append({
                            'time': datetime.now(),
                            'type': 'status_error',
                            'details': str(e)
                        })
                
                elif action == 'report' and self.last_exec_id:
                    try:
                        requests.get(
                            f"{self.base_url}/api/v2/diagnostic/tasks/{self.last_exec_id}/report",
                            timeout=10
                        )
                    except Exception as e:
                        self.errors.append({
                            'time': datetime.now(),
                            'type': 'report_error',
                            'details': str(e)
                        })
                
                elif action == 'history':
                    try:
                        requests.get(
                            f"{self.base_url}/api/v2/diagnostic/history",
                            params={'user_id': f'stress_user_{random.randint(1,10)}', 'limit': 5},
                            timeout=5
                        )
                    except Exception as e:
                        self.errors.append({
                            'time': datetime.now(),
                            'type': 'history_error',
                            'details': str(e)
                        })
                
                elapsed = (datetime.now() - start_time).total_seconds() / 60
                progress = (elapsed / self.duration_minutes) * 100
                print(f"\r进度：{progress:.1f}% | 迭代：{iteration} | 错误：{len(self.errors)}", end='', flush=True)
                
                time.sleep(random.uniform(2, 5))
                
            except KeyboardInterrupt:
                print("\n用户中断测试")
                self.running = False
                break
            except Exception as e:
                self.errors.append({
                    'time': datetime.now(),
                    'type': 'load_test_error',
                    'details': str(e)
                })
                time.sleep(5)
        
        print()
    
    def _analyze_results(self):
        """分析测试结果"""
        total_tests = len(self.errors)
        error_types = {}
        
        for error in self.errors:
            error_type = error.get('type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if self.metrics_history:
            memory_values = [m['memory'] for m in self.metrics_history if 'memory' in m]
            cpu_values = [m['cpu'] for m in self.metrics_history if 'cpu' in m]
            
            if memory_values:
                avg_memory = sum(memory_values) / len(memory_values)
                max_memory = max(memory_values)
                
                self.results.append({
                    'test': '内存稳定性',
                    'status': '✅' if max_memory < 80 else '⚠️',
                    'details': f'平均：{avg_memory:.1f}%, 最大：{max_memory:.1f}%'
                })
            
            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)
                max_cpu = max(cpu_values)
                
                self.results.append({
                    'test': 'CPU 稳定性',
                    'status': '✅' if max_cpu < 90 else '⚠️',
                    'details': f'平均：{avg_cpu:.1f}%, 最大：{max_cpu:.1f}%'
                })
        
        self.results.append({
            'test': f'{self.duration_minutes}分钟持续运行',
            'status': '✅' if len(self.errors) == 0 else '❌',
            'details': f'错误数：{len(self.errors)}'
        })
        
        if error_types:
            error_details = ', '.join([f"{k}: {v}" for k, v in error_types.items()])
            self.results.append({
                'test': '错误分布',
                'status': 'ℹ️',
                'details': error_details
            })
    
    def print_summary(self):
        """打印测试总结"""
        print("\n稳定性测试总结:")
        print("-" * 60)
        
        for result in self.results:
            print(f"{result['status']} {result['test']:25} - {result['details']}")
        
        print("-" * 60)
        print(f"测试时长：{self.duration_minutes} 分钟")
        print(f"总错误数：{len(self.errors)}")
        
        if self.errors:
            print("\n错误详情 (前 10 个):")
            for error in self.errors[:10]:
                time_str = error['time'].strftime('%H:%M:%S')
                print(f"  [{time_str}] {error['type']}: {error['details']}")
            
            if len(self.errors) > 10:
                print(f"  ... 还有 {len(self.errors) - 10} 个错误未显示")
        
        print("-" * 60)
        
        if len(self.errors) == 0:
            print("✅ 稳定性测试通过")
        else:
            print(f"❌ 稳定性测试失败，发现 {len(self.errors)} 个错误")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='稳定性测试')
    parser.add_argument('--url', default='http://localhost:5000',
                       help='API URL')
    parser.add_argument('--duration', type=int, default=30,
                       help='测试时长 (分钟)')
    
    args = parser.parse_args()
    
    tester = StabilityTester(args.url, args.duration)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
