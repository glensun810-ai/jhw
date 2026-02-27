#!/usr/bin/env python3
"""
预发布环境检查脚本
检查预发布环境的配置、连通性和必要组件
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Any

try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class EnvironmentChecker:
    """预发布环境检查器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.env_config = config or {
            'staging_api': os.getenv('STAGING_API_URL', 'http://localhost:5000'),
            'staging_db': os.getenv('STAGING_DB_PATH', '/data/staging/diagnosis.db'),
            'staging_redis': os.getenv('STAGING_REDIS_URL', 'localhost:6379'),
            'feature_flags': {
                'diagnosis_v2_state_machine': True,
                'diagnosis_v2_timeout': True,
                'diagnosis_v2_retry': True,
                'diagnosis_v2_dead_letter': True,
                'diagnosis_v2_api_logging': True,
                'diagnosis_v2_data_persistence': True,
                'diagnosis_v2_report_stub': True,
            }
        }
        self.check_results: List[Dict[str, str]] = []
        self.admin_key = os.getenv('ADMIN_API_KEY', 'test-key')
    
    def run_all_checks(self) -> bool:
        """运行所有环境检查"""
        print("\n" + "="*60)
        print("预发布环境检查")
        print("="*60)
        print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        self.check_api_connectivity()
        self.check_database()
        self.check_redis()
        self.check_feature_flags()
        self.check_disk_space()
        self.check_memory()
        self.check_version()
        self.check_log_directory()
        self.check_backup_directory()
        
        self.print_report()
        return all(r['status'] == '✅' for r in self.check_results)
    
    def check_api_connectivity(self):
        """检查 API 连通性"""
        try:
            base_url = self.env_config['staging_api']
            response = requests.get(
                f"{base_url}/api/health",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                self.check_results.append({
                    'check': 'API 连通性',
                    'status': '✅',
                    'details': f'响应时间：{response.elapsed.total_seconds():.2f}s, 状态：{status}'
                })
            else:
                self.check_results.append({
                    'check': 'API 连通性',
                    'status': '❌',
                    'details': f'HTTP {response.status_code}'
                })
        except requests.exceptions.ConnectionError as e:
            self.check_results.append({
                'check': 'API 连通性',
                'status': '❌',
                'details': f'无法连接到 API: {str(e)}'
            })
        except requests.exceptions.Timeout:
            self.check_results.append({
                'check': 'API 连通性',
                'status': '❌',
                'details': '请求超时 (5 秒)'
            })
        except Exception as e:
            self.check_results.append({
                'check': 'API 连通性',
                'status': '❌',
                'details': f'错误：{str(e)}'
            })
    
    def check_database(self):
        """检查数据库"""
        db_path = self.env_config['staging_db']
        
        if not HAS_SQLITE:
            self.check_results.append({
                'check': '数据库',
                'status': '⚠️',
                'details': 'sqlite3 模块不可用'
            })
            return
        
        if os.path.exists(db_path):
            try:
                size_mb = os.path.getsize(db_path) / (1024 * 1024)
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = [
                    'diagnosis_reports', 'diagnosis_results', 
                    'api_call_logs', 'dead_letter_queue',
                    'diagnosis_execution'
                ]
                
                missing = [t for t in required_tables if t not in tables]
                conn.close()
                
                if missing:
                    self.check_results.append({
                        'check': '数据库',
                        'status': '⚠️',
                        'details': f'存在，大小：{size_mb:.2f}MB, 缺少表：{missing}'
                    })
                else:
                    self.check_results.append({
                        'check': '数据库',
                        'status': '✅',
                        'details': f'存在，大小：{size_mb:.2f}MB, 所有必要表已创建'
                    })
            except Exception as e:
                self.check_results.append({
                    'check': '数据库',
                    'status': '❌',
                    'details': f'数据库文件存在但无法访问：{str(e)}'
                })
        else:
            self.check_results.append({
                'check': '数据库',
                'status': '❌',
                'details': f'数据库文件不存在：{db_path}'
            })
    
    def check_redis(self):
        """检查 Redis 连接"""
        redis_url = self.env_config['staging_redis']
        
        try:
            import redis
            redis_client = redis.from_url(f"redis://{redis_url}")
            redis_client.ping()
            
            info = redis_client.info('memory')
            used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
            
            self.check_results.append({
                'check': 'Redis',
                'status': '✅',
                'details': f'连接成功，内存使用：{used_memory_mb:.2f}MB'
            })
        except ImportError:
            self.check_results.append({
                'check': 'Redis',
                'status': '⚠️',
                'details': 'redis 模块未安装，跳过检查'
            })
        except Exception as e:
            self.check_results.append({
                'check': 'Redis',
                'status': '⚠️',
                'details': f'无法连接 Redis: {str(e)}'
            })
    
    def check_feature_flags(self):
        """检查特性开关配置"""
        try:
            base_url = self.env_config['staging_api']
            response = requests.get(
                f"{base_url}/api/admin/feature-flags",
                headers={'X-Admin-Key': self.admin_key},
                timeout=5
            )
            
            if response.status_code == 200:
                flags = response.json()
                mismatches = []
                
                for key, expected in self.env_config['feature_flags'].items():
                    actual = flags.get(key)
                    if actual != expected:
                        mismatches.append(f"{key}: 期望{expected}, 实际{actual}")
                
                if mismatches:
                    self.check_results.append({
                        'check': '特性开关',
                        'status': '⚠️',
                        'details': '; '.join(mismatches)
                    })
                else:
                    self.check_results.append({
                        'check': '特性开关',
                        'status': '✅',
                        'details': '所有开关配置正确'
                    })
            else:
                self.check_results.append({
                    'check': '特性开关',
                    'status': '⚠️',
                    'details': f'无法获取开关状态：HTTP {response.status_code}'
                })
        except Exception as e:
            self.check_results.append({
                'check': '特性开关',
                'status': '⚠️',
                'details': f'检查失败：{str(e)}'
            })
    
    def check_disk_space(self):
        """检查磁盘空间"""
        try:
            stat = os.statvfs('/')
            free_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
            
            if free_gb > 10:
                self.check_results.append({
                    'check': '磁盘空间',
                    'status': '✅',
                    'details': f'剩余：{free_gb:.2f}GB'
                })
            elif free_gb > 5:
                self.check_results.append({
                    'check': '磁盘空间',
                    'status': '⚠️',
                    'details': f'剩余：{free_gb:.2f}GB (建议>10GB)'
                })
            else:
                self.check_results.append({
                    'check': '磁盘空间',
                    'status': '❌',
                    'details': f'剩余：{free_gb:.2f}GB (严重不足)'
                })
        except Exception as e:
            self.check_results.append({
                'check': '磁盘空间',
                'status': '⚠️',
                'details': f'无法检查：{str(e)}'
            })
    
    def check_memory(self):
        """检查内存"""
        if not HAS_PSUTIL:
            self.check_results.append({
                'check': '内存',
                'status': '⚠️',
                'details': 'psutil 模块未安装，跳过检查'
            })
            return
        
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            if available_gb > 2:
                self.check_results.append({
                    'check': '内存',
                    'status': '✅',
                    'details': f'可用：{available_gb:.2f}GB'
                })
            elif available_gb > 1:
                self.check_results.append({
                    'check': '内存',
                    'status': '⚠️',
                    'details': f'可用：{available_gb:.2f}GB (建议>2GB)'
                })
            else:
                self.check_results.append({
                    'check': '内存',
                    'status': '❌',
                    'details': f'可用：{available_gb:.2f}GB (严重不足)'
                })
        except Exception as e:
            self.check_results.append({
                'check': '内存',
                'status': '⚠️',
                'details': f'无法检查：{str(e)}'
            })
    
    def check_version(self):
        """检查版本信息"""
        try:
            base_url = self.env_config['staging_api']
            response = requests.get(
                f"{base_url}/api/version",
                timeout=5
            )
            if response.status_code == 200:
                version = response.json().get('version', 'unknown')
                commit = response.json().get('commit', 'unknown')[:7]
                self.check_results.append({
                    'check': '版本',
                    'status': '✅',
                    'details': f'版本：{version}, 提交：{commit}'
                })
            else:
                self.check_results.append({
                    'check': '版本',
                    'status': '⚠️',
                    'details': '无法获取版本信息'
                })
        except Exception as e:
            self.check_results.append({
                'check': '版本',
                'status': '⚠️',
                'details': f'检查失败：{str(e)}'
            })
    
    def check_log_directory(self):
        """检查日志目录"""
        log_dir = os.getenv('LOG_DIR', '/var/log/wechat-backend')
        
        if os.path.exists(log_dir):
            if os.access(log_dir, os.W_OK):
                self.check_results.append({
                    'check': '日志目录',
                    'status': '✅',
                    'details': f'{log_dir} 可写'
                })
            else:
                self.check_results.append({
                    'check': '日志目录',
                    'status': '⚠️',
                    'details': f'{log_dir} 存在但不可写'
                })
        else:
            self.check_results.append({
                'check': '日志目录',
                'status': '⚠️',
                'details': f'{log_dir} 不存在'
            })
    
    def check_backup_directory(self):
        """检查备份目录"""
        backup_dir = os.getenv('BACKUP_DIR', '/data/backups')
        
        if os.path.exists(backup_dir):
            files = os.listdir(backup_dir)
            recent_backups = [f for f in files if f.endswith('.db') or f.endswith('.sql')]
            
            if recent_backups:
                self.check_results.append({
                    'check': '备份目录',
                    'status': '✅',
                    'details': f'存在，备份文件数：{len(recent_backups)}'
                })
            else:
                self.check_results.append({
                    'check': '备份目录',
                    'status': '⚠️',
                    'details': '存在但无备份文件'
                })
        else:
            self.check_results.append({
                'check': '备份目录',
                'status': '⚠️',
                'details': f'{backup_dir} 不存在'
            })
    
    def print_report(self):
        """打印检查报告"""
        print("\n环境检查报告:")
        print("-" * 60)
        for result in self.check_results:
            print(f"{result['status']} {result['check']:20} - {result['details']}")
        print("-" * 60)
        
        failed = sum(1 for r in self.check_results if r['status'] == '❌')
        warnings = sum(1 for r in self.check_results if r['status'] == '⚠️')
        passed = sum(1 for r in self.check_results if r['status'] == '✅')
        
        print(f"\n总计：{len(self.check_results)} 项检查")
        print(f"❌ 失败：{failed}")
        print(f"⚠️ 警告：{warnings}")
        print(f"✅ 通过：{passed}")
        
        if failed > 0:
            print("\n❌ 存在失败项，请修复后重试")
        elif warnings > 0:
            print("\n⚠️ 存在警告项，请确认是否可接受")
        else:
            print("\n✅ 所有检查通过")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='预发布环境检查')
    parser.add_argument('--api-url', default=os.getenv('STAGING_API_URL', 'http://localhost:5000'),
                       help='预发布 API URL')
    parser.add_argument('--db-path', default=os.getenv('STAGING_DB_PATH', '/data/staging/diagnosis.db'),
                       help='数据库路径')
    parser.add_argument('--redis-url', default=os.getenv('STAGING_REDIS_URL', 'localhost:6379'),
                       help='Redis URL')
    
    args = parser.parse_args()
    
    config = {
        'staging_api': args.api_url,
        'staging_db': args.db_path,
        'staging_redis': args.redis_url,
        'feature_flags': {
            'diagnosis_v2_state_machine': True,
            'diagnosis_v2_timeout': True,
            'diagnosis_v2_retry': True,
            'diagnosis_v2_dead_letter': True,
            'diagnosis_v2_api_logging': True,
            'diagnosis_v2_data_persistence': True,
            'diagnosis_v2_report_stub': True,
        }
    }
    
    checker = EnvironmentChecker(config)
    success = checker.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
