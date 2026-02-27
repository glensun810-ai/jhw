#!/usr/bin/env python3
"""
回滚测试 - 验证回滚方案有效性
确保在出现问题时可以快速回滚到 v1.0.0 版本
"""

import requests
import time
import sys
import os
from datetime import datetime
from typing import List, Dict, Any


class RollbackTester:
    """回滚测试器"""
    
    def __init__(self, base_url: str, admin_key: str = 'test-key'):
        self.base_url = base_url.rstrip('/')
        self.admin_key = admin_key
        self.results: List[Dict[str, str]] = []
        self.original_flags: Dict[str, bool] = {}
    
    def run_all_tests(self) -> bool:
        """运行所有回滚测试"""
        print("\n" + "="*60)
        print("回滚测试")
        print("="*60)
        print(f"测试环境：{self.base_url}")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        self.test_feature_flag_rollback()
        self.test_database_rollback()
        self.test_full_system_rollback()
        self.test_rollback_documentation()
        self.test_v1_functionality_after_rollback()
        
        self.print_summary()
        return all(r['status'] == '✅' for r in self.results)
    
    def test_feature_flag_rollback(self):
        """测试特性开关回滚"""
        test_name = '特性开关回滚'
        try:
            response = requests.get(
                f"{self.base_url}/api/admin/feature-flags",
                headers={'X-Admin-Key': self.admin_key},
                timeout=5
            )
            
            if response.status_code != 200:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': f'无法获取开关状态：HTTP {response.status_code}'
                })
                return
            
            self.original_flags = response.json()
            
            v2_flags = [
                'diagnosis_v2_enabled',
                'diagnosis_v2_state_machine',
                'diagnosis_v2_timeout',
                'diagnosis_v2_retry',
                'diagnosis_v2_dead_letter'
            ]
            
            flags_to_toggle = [f for f in v2_flags if f in self.original_flags]
            
            if not flags_to_toggle:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': '无 v2 特性开关可测试'
                })
                return
            
            for flag in flags_to_toggle:
                requests.put(
                    f"{self.base_url}/api/admin/feature-flags",
                    headers={'X-Admin-Key': self.admin_key},
                    json={'key': flag, 'value': False},
                    timeout=5
                )
            
            time.sleep(1)
            
            verify_resp = requests.get(
                f"{self.base_url}/api/admin/feature-flags",
                headers={'X-Admin-Key': self.admin_key},
                timeout=5
            )
            
            if verify_resp.status_code == 200:
                current_flags = verify_resp.json()
                all_disabled = all(current_flags.get(f) is False for f in flags_to_toggle)
                
                if all_disabled:
                    for flag in flags_to_toggle:
                        original_value = self.original_flags.get(flag, True)
                        requests.put(
                            f"{self.base_url}/api/admin/feature-flags",
                            headers={'X-Admin-Key': self.admin_key},
                            json={'key': flag, 'value': original_value},
                            timeout=5
                        )
                    
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'成功关闭并恢复 {len(flags_to_toggle)} 个开关'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': '部分开关未能关闭'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': '无法验证开关状态'
                })
            
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_database_rollback(self):
        """测试数据库回滚"""
        test_name = '数据库回滚'
        try:
            rollback_script_paths = [
                'scripts/rollback/rollback_database.sh',
                'scripts/rollback_database.sh',
                'scripts/preproduction/rollback_database.sh'
            ]
            
            found_script = None
            for path in rollback_script_paths:
                if os.path.exists(path):
                    found_script = path
                    break
            
            if found_script:
                if os.access(found_script, os.X_OK):
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'回滚脚本存在且可执行：{found_script}'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': f'回滚脚本无执行权限：{found_script}'
                    })
            else:
                backup_dir = os.getenv('BACKUP_DIR', '/data/backups')
                if os.path.exists(backup_dir):
                    backup_files = [f for f in os.listdir(backup_dir) 
                                   if f.endswith('.db') or f.endswith('.sql')]
                    
                    if backup_files:
                        self.results.append({
                            'test': test_name,
                            'status': '✅',
                            'details': f'备份目录存在，备份文件数：{len(backup_files)}'
                        })
                    else:
                        self.results.append({
                            'test': test_name,
                            'status': '⚠️',
                            'details': '备份目录存在但无备份文件'
                        })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': '回滚脚本和备份目录均不存在'
                    })
                
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_full_system_rollback(self):
        """测试完整系统回滚"""
        test_name = '系统回滚文档'
        try:
            rollback_doc_paths = [
                'docs/rollback_plan.md',
                'docs/rollback.md',
                'ROLLBACK.md',
                'scripts/preproduction/../docs/rollback_plan.md'
            ]
            
            found_doc = None
            for path in rollback_doc_paths:
                if os.path.exists(path):
                    found_doc = path
                    break
            
            if found_doc:
                with open(found_doc, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                required_sections = [
                    '回滚',
                    '步骤',
                    '验证'
                ]
                
                missing = [s for s in required_sections if s not in content]
                
                if not missing:
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'回滚文档完整：{found_doc}'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': f'回滚文档缺少章节：{missing}'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': '回滚文档不存在'
                })
                
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_rollback_documentation(self):
        """测试回滚文档完整性"""
        test_name = '回滚文档完整性'
        try:
            doc_paths = [
                'docs/rollback_plan.md',
                'docs/rollback.md'
            ]
            
            found_doc = None
            for path in doc_paths:
                if os.path.exists(path):
                    found_doc = path
                    break
            
            if found_doc:
                with open(found_doc, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                required_keywords = [
                    '触发条件',
                    '回滚步骤',
                    '验证',
                    '联系人'
                ]
                
                found_keywords = [k for k in required_keywords if k in content]
                
                if len(found_keywords) >= 3:
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': f'文档包含 {len(found_keywords)}/{len(required_keywords)} 个关键部分'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': f'文档缺少关键部分：{set(required_keywords) - set(found_keywords)}'
                    })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': '未找到回滚文档'
                })
            
        except Exception as e:
            self.results.append({
                'test': test_name,
                'status': '❌',
                'details': f'异常：{str(e)}'
            })
    
    def test_v1_functionality_after_rollback(self):
        """测试回滚后 v1 功能可用性"""
        test_name = '回滚后 v1 功能'
        try:
            response = requests.post(
                f"{self.base_url}/api/perform-brand-test",
                json={
                    'brand_list': ['回滚测试品牌'],
                    'selectedModels': [{'name': 'deepseek', 'checked': True}],
                    'custom_question': '回滚测试',
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'report_id' in data or 'data' in data:
                    self.results.append({
                        'test': test_name,
                        'status': '✅',
                        'details': 'v1 功能在回滚后可用'
                    })
                else:
                    self.results.append({
                        'test': test_name,
                        'status': '⚠️',
                        'details': 'v1 响应格式异常'
                    })
            elif response.status_code == 404:
                self.results.append({
                    'test': test_name,
                    'status': '⚠️',
                    'details': 'v1 API 已废弃 (404)'
                })
            else:
                self.results.append({
                    'test': test_name,
                    'status': '❌',
                    'details': f'v1 功能不可用：HTTP {response.status_code}'
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
    
    def print_summary(self):
        """打印测试总结"""
        print("\n回滚测试总结:")
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
        
        if failed > 0:
            print("\n⚠️ 警告：回滚方案存在风险，请修复后重试")
        elif warnings > 0:
            print("\n⚠️ 注意：回滚方案存在警告项，请确认是否可接受")
        else:
            print("\n✅ 回滚方案验证通过")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='回滚测试')
    parser.add_argument('--url', default='http://localhost:5000',
                       help='API URL')
    parser.add_argument('--admin-key', default='test-key',
                       help='Admin API Key')
    
    args = parser.parse_args()
    
    tester = RollbackTester(args.url, args.admin_key)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
