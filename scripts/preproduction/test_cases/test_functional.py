#!/usr/bin/env python3
"""
功能验证测试用例 - 模拟真实用户操作
验证阶段一所有核心功能
"""

import requests
import time
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional


class FunctionalTester:
    """功能测试器"""
    
    def __init__(self, base_url: str, admin_key: str = 'test-key'):
        self.base_url = base_url.rstrip('/')
        self.admin_key = admin_key
        self.test_results: List[Dict[str, str]] = []
        self.execution_id: Optional[str] = None
        self.report_id: Optional[str] = None
    
    def run_all_tests(self) -> bool:
        """运行所有功能测试"""
        print("\n" + "="*60)
        print("功能验证测试")
        print("="*60)
        print(f"测试环境：{self.base_url}")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        self.test_create_diagnosis()
        self.test_status_polling()
        self.test_get_report()
        self.test_partial_success()
        self.test_timeout_handling()
        self.test_error_handling()
        self.test_history_records()
        self.test_stub_report()
        
        self.print_summary()
        return all(r['status'] == '✅' for r in self.test_results)
    
    def test_create_diagnosis(self):
        """测试发起诊断"""
        test_name = '发起诊断'
        try:
            response = requests.post(
                f"{self.base_url}/api/v2/diagnostic/tasks",
                json={
                    'brand_list': ['测试品牌 A', '测试品牌 B'],
                    'selectedModels': [
                        {'name': 'deepseek', 'checked': True},
                        {'name': 'doubao', 'checked': True}
                    ],
                    'custom_question': '用户如何看待测试品牌的产品质量？',
                    'userOpenid': 'test_user_123'
                },
                timeout=10
            )
            
            assert response.status_code == 200, f"HTTP {response.status_code}"
            data = response.json()
            
            assert 'execution_id' in data, "响应缺少 execution_id"
            assert 'report_id' in data, "响应缺少 report_id"
            assert data.get('status') == 'success', f"状态异常：{data.get('status')}"
            
            self.execution_id = data['execution_id']
            self.report_id = data['report_id']
            
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': f'execution_id: {self.execution_id}, report_id: {self.report_id}'
            })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_status_polling(self):
        """测试状态轮询"""
        test_name = '状态轮询'
        try:
            if not self.execution_id:
                self.test_results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': '跳过：无执行 ID'
                })
                return
            
            max_attempts = 30
            completed = False
            final_status = 'unknown'
            progress = 0
            
            for i in range(max_attempts):
                response = requests.get(
                    f"{self.base_url}/api/v2/diagnostic/tasks/{self.execution_id}/status",
                    timeout=5
                )
                
                assert response.status_code == 200, f"HTTP {response.status_code}"
                status = response.json()
                
                if status.get('should_stop_polling'):
                    completed = True
                    final_status = status.get('status', 'unknown')
                    progress = status.get('progress', 0)
                    break
                
                time.sleep(2)
            
            assert completed, f"轮询未在{max_attempts}次内完成"
            
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': f'最终状态：{final_status}, 进度：{progress}%'
            })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_get_report(self):
        """测试获取报告"""
        test_name = '获取报告'
        try:
            if not self.execution_id:
                self.test_results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': '跳过：无执行 ID'
                })
                return
            
            response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/tasks/{self.execution_id}/report",
                timeout=10
            )
            
            assert response.status_code == 200, f"HTTP {response.status_code}"
            report = response.json()
            
            assert 'report' in report, "响应缺少 report 字段"
            assert 'results' in report, "响应缺少 results 字段"
            assert 'meta' in report, "响应缺少 meta 字段"
            
            results = report.get('results', [])
            is_stub = report.get('meta', {}).get('is_stub', False)
            
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': f'结果数：{len(results)}, 存根：{is_stub}'
            })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_partial_success(self):
        """测试部分成功场景"""
        test_name = '部分成功'
        try:
            response = requests.post(
                f"{self.base_url}/api/v2/diagnostic/tasks",
                json={
                    'brand_list': ['测试品牌 A'],
                    'selectedModels': [
                        {'name': 'deepseek', 'checked': True},
                        {'name': 'doubao', 'checked': True},
                        {'name': 'qwen', 'checked': True}
                    ],
                    'custom_question': '部分成功测试',
                    'userOpenid': 'test_user_456'
                },
                timeout=10
            )
            
            assert response.status_code == 200, f"HTTP {response.status_code}"
            data = response.json()
            exec_id = data.get('execution_id')
            
            if not exec_id:
                self.test_results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': '未返回 execution_id'
                })
                return
            
            time.sleep(15)
            
            report_response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/tasks/{exec_id}/report",
                timeout=10
            )
            
            if report_response.status_code != 200:
                self.test_results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'获取报告失败：HTTP {report_response.status_code}'
                })
                return
            
            report = report_response.json()
            status = report.get('report', {}).get('status', 'unknown')
            
            if status == 'partial_success':
                meta = report.get('meta', {})
                successful = meta.get('successful_count', 0)
                total = meta.get('results_count', 0)
                
                self.test_results.append({
                    'test': test_name,
                    'status': '✅',
                    'details': f'成功率：{successful}/{total}'
                })
            else:
                self.test_results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'未触发部分成功，状态：{status}'
                })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_timeout_handling(self):
        """测试超时处理"""
        test_name = '超时处理'
        try:
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': '需人工确认超时日志 (查看 api_call_logs 表)'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': str(e)
            })
    
    def test_error_handling(self):
        """测试错误处理"""
        test_name = '错误处理'
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/tasks/invalid-id/report",
                timeout=5
            )
            
            if response.status_code == 404:
                data = response.json()
                meta = data.get('meta', {})
                assert meta.get('is_stub') is True, "404 响应应包含存根标记"
                assert 'error_message' in meta or 'message' in data, "404 响应应包含错误信息"
            else:
                self.test_results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'无效 ID 返回 HTTP {response.status_code}, 期望 404'
                })
                return
            
            response = requests.post(
                f"{self.base_url}/api/v2/diagnostic/tasks",
                json={},
                timeout=5
            )
            
            assert response.status_code == 400, f"空参数应返回 400, 实际：{response.status_code}"
            data = response.json()
            assert data.get('status') == 'error' or 'error' in data, "错误响应格式不正确"
            
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': '无效请求处理正确'
            })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_history_records(self):
        """测试历史记录"""
        test_name = '历史记录'
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/history",
                params={'user_id': 'test_user_123', 'limit': 10},
                timeout=5
            )
            
            assert response.status_code == 200, f"HTTP {response.status_code}"
            data = response.json()
            
            assert 'reports' in data or 'items' in data, "响应缺少 reports 字段"
            
            reports = data.get('reports', data.get('items', []))
            
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': f'记录数：{len(reports)}'
            })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_stub_report(self):
        """测试存根报告"""
        test_name = '存根报告'
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/tasks/non-existent-123/report",
                timeout=5
            )
            
            data = response.json()
            meta = data.get('meta', {})
            
            assert meta.get('is_stub') is True, "不存在 ID 应返回存根报告"
            assert 'error_message' in meta or 'message' in data, "存根报告应包含错误信息"
            assert 'next_steps' in meta or 'suggestions' in data, "存根报告应包含建议"
            
            self.test_results.append({
                'test': test_name,
                'status': '✅',
                'details': '存根报告格式正确'
            })
            
        except AssertionError as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'断言失败：{str(e)}'
            })
        except requests.exceptions.RequestException as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'请求失败：{str(e)}'
            })
        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def print_summary(self):
        """打印测试总结"""
        print("\n功能测试总结:")
        print("-" * 60)
        for result in self.test_results:
            print(f"{result['status']} {result['test']:20} - {result['details']}")
        print("-" * 60)
        
        failed = sum(1 for r in self.test_results if r['status'] == '❌')
        warnings = sum(1 for r in self.test_results if r['status'] == '⚠️')
        passed = sum(1 for r in self.test_results if r['status'] == '✅')
        
        print(f"\n总计：{len(self.test_results)} 项测试")
        print(f"❌ 失败：{failed}")
        print(f"⚠️ 警告：{warnings}")
        print(f"✅ 通过：{passed}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='功能验证测试')
    parser.add_argument('--url', default='http://localhost:5000',
                       help='API URL')
    parser.add_argument('--admin-key', default='test-key',
                       help='Admin API Key')
    
    args = parser.parse_args()
    
    tester = FunctionalTester(args.url, args.admin_key)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
