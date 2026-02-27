#!/usr/bin/env python3
"""
兼容性测试 - 验证新旧版本兼容性
确保 v1 和 v2 API 可以共存，旧数据可被读取
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Any


class CompatibilityTester:
    """兼容性测试器"""
    
    def __init__(self, base_url: str, admin_key: str = 'test-key'):
        self.base_url = base_url.rstrip('/')
        self.admin_key = admin_key
        self.results: List[Dict[str, str]] = []
    
    def run_all_tests(self) -> bool:
        """运行所有兼容性测试"""
        print("\n" + "="*60)
        print("兼容性测试")
        print("="*60)
        print(f"测试环境：{self.base_url}")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        self.test_v1_api_still_works()
        self.test_v2_api_response_format()
        self.test_old_data_can_be_read()
        self.test_feature_flag_toggle()
        self.test_data_migration()
        self.test_api_versioning()
        
        self.print_summary()
        return all(r['status'] == '✅' for r in self.results)
    
    def test_v1_api_still_works(self):
        """测试 v1 API 是否仍然可用"""
        test_name = 'v1 API 可用性'
        try:
            response = requests.post(
                f"{self.base_url}/api/perform-brand-test",
                json={
                    'brand_list': ['测试品牌'],
                    'selectedModels': [{'name': 'deepseek', 'checked': True}],
                    'custom_question': '兼容性测试',
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'report_id' in data or 'execution_id' in data:
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'v1 API 正常工作，HTTP {response.status_code}'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': f'v1 API 返回 200 但响应格式异常'
                    })
            elif response.status_code == 404:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': 'v1 API 已废弃 (404)'
                })
            elif response.status_code >= 500:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': f'v1 API 服务器错误：HTTP {response.status_code}'
                })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '✅',
                    'details': f'v1 API 返回 HTTP {response.status_code}'
                })
                
        except requests.exceptions.ConnectionError:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': '无法连接到 API'
            })
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_v2_api_response_format(self):
        """测试 v2 API 响应格式"""
        test_name = 'v2 响应格式'
        try:
            response = requests.post(
                f"{self.base_url}/api/v2/diagnostic/tasks",
                json={
                    'brand_list': ['测试品牌'],
                    'selectedModels': [{'name': 'deepseek', 'checked': True}],
                    'custom_question': '格式测试',
                    'userOpenid': 'compat_test'
                },
                timeout=10
            )
            
            assert response.status_code == 200, f"HTTP {response.status_code}"
            data = response.json()
            
            assert 'execution_id' in data, "缺少 execution_id"
            assert 'report_id' in data, "缺少 report_id"
            assert 'status' in data, "缺少 status"
            
            exec_id = data['execution_id']
            time.sleep(3)
            
            status_resp = requests.get(
                f"{self.base_url}/api/v2/diagnostic/tasks/{exec_id}/status",
                timeout=5
            )
            status_data = status_resp.json()
            
            assert 'status' in status_data, "状态响应缺少 status"
            assert 'progress' in status_data, "状态响应缺少 progress"
            assert 'should_stop_polling' in status_data, "状态响应缺少 should_stop_polling"
            
            self.results.append({
                'test': test_name,
                'status': '✅',
                'details': '格式验证通过'
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
    
    def test_old_data_can_be_read(self):
        """测试旧数据可被读取"""
        test_name = '旧数据读取'
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/history",
                params={'user_id': 'test_user', 'limit': 5},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                has_data = 'reports' in data or 'items' in data
                
                if has_data:
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'历史数据可读取，记录数：{len(data.get("reports", data.get("items", [])))}'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': '响应格式异常，缺少 reports 字段'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'HTTP {response.status_code}'
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
    
    def test_feature_flag_toggle(self):
        """测试特性开关切换"""
        test_name = '特性开关'
        try:
            response = requests.get(
                f"{self.base_url}/api/admin/feature-flags",
                headers={'X-Admin-Key': self.admin_key},
                timeout=5
            )
            
            if response.status_code != 200:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': '无法获取开关状态'
                })
                return
            
            original_flags = response.json()
            
            test_flag = 'diagnosis_v2_state_machine'
            if test_flag not in original_flags:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'测试开关 {test_flag} 不存在'
                })
                return
            
            original_value = original_flags[test_flag]
            new_value = not original_value
            
            update_resp = requests.put(
                f"{self.base_url}/api/admin/feature-flags",
                headers={'X-Admin-Key': self.admin_key},
                json={'key': test_flag, 'value': new_value},
                timeout=5
            )
            
            if update_resp.status_code == 200:
                verify_resp = requests.get(
                    f"{self.base_url}/api/admin/feature-flags",
                    headers={'X-Admin-Key': self.admin_key},
                    timeout=5
                )
                
                if verify_resp.status_code == 200:
                    updated_flags = verify_resp.json()
                    if updated_flags.get(test_flag) == new_value:
                        requests.put(
                            f"{self.base_url}/api/admin/feature-flags",
                            headers={'X-Admin-Key': self.admin_key},
                            json={'key': test_flag, 'value': original_value},
                            timeout=5
                        )
                        
                        self.results.append({
                            'test': test_name,
                            'status': '✅',
                            'details': '开关可正常切换和恢复'
                        })
                    else:
                        self.results.append({
                            'test': test_name,
                            'status': '⚠️',
                            'details': '开关切换后验证失败'
                        })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': '无法验证开关状态'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'开关切换失败：HTTP {update_resp.status_code}'
                })
            
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_data_migration(self):
        """测试数据迁移兼容性"""
        test_name = '数据迁移'
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/diagnostic/reports",
                params={'limit': 1},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                reports = data.get('reports', data.get('items', []))
                
                if reports:
                    report = reports[0]
                    required_fields = ['id', 'created_at', 'status']
                    missing_fields = [f for f in required_fields if f not in report]
                    
                    if missing_fields:
                        self.results.append({
                            'test': test_name,
                            'status': '⚠️',
                            'details': f'报告缺少字段：{missing_fields}'
                        })
                    else:
                        self.results.append({
                            'test': test_name,
                            'status': '✅',
                            'details': '数据格式兼容'
                        })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': '无报告数据可验证'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'HTTP {response.status_code}'
                })
            
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_api_versioning(self):
        """测试 API 版本控制"""
        test_name = 'API 版本控制'
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                version = data.get('version', 'unknown')
                
                if version and version != 'unknown':
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'当前版本：{version}'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': '版本信息格式异常'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': f'HTTP {response.status_code}'
                })
            
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def print_summary(self):
        """打印测试总结"""
        print("\n兼容性测试总结:")
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
    
    parser = argparse.ArgumentParser(description='兼容性测试')
    parser.add_argument('--url', default='http://localhost:5000',
                       help='API URL')
    parser.add_argument('--admin-key', default='test-key',
                       help='Admin API Key')
    
    args = parser.parse_args()
    
    tester = CompatibilityTester(args.url, args.admin_key)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
