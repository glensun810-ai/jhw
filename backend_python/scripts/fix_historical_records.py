"""
历史诊断记录修复脚本

用途:
1. 修复缺失 should_stop_polling 字段的记录
2. 修复状态不一致的记录
3. 补全缺失的 analysis 数据
4. 清理无效数据

执行方式:
    python scripts/fix_historical_records.py

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'backend_python' / 'wechat_backend' / 'database.db'


class HistoricalRecordsFixer:
    """历史记录修复器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化修复器
        
        参数:
            db_path: 数据库路径
        """
        self.db_path = db_path or DB_PATH
        self.stats = {
            'fixed_should_stop_polling': 0,
            'fixed_stage_status': 0,
            'marked_empty_reports': 0,
            'cleaned_invalid_records': 0,
            'errors': 0
        }
    
    def connect(self) -> sqlite3.Connection:
        """
        连接数据库
        
        返回:
            数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def fix_should_stop_polling(self) -> int:
        """
        修复缺失 should_stop_polling 字段的记录
        
        返回:
            修复的记录数
        """
        print("正在修复 should_stop_polling 字段...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 更新已完成/失败/超时的记录，设置 should_stop_polling=1
            cursor.execute('''
                UPDATE diagnosis_reports
                SET should_stop_polling = 1
                WHERE status IN ('completed', 'failed', 'timeout')
                AND (should_stop_polling = 0 OR should_stop_polling IS NULL)
            ''')
            
            fixed_count = cursor.rowcount
            self.stats['fixed_should_stop_polling'] = fixed_count
            
            conn.commit()
            
            print(f"✅ 修复 should_stop_polling 字段：{fixed_count} 条记录")
            return fixed_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 修复 should_stop_polling 字段失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def fix_stage_status_inconsistency(self) -> int:
        """
        修复 stage 和 status 字段不一致的记录
        
        返回:
            修复的记录数
        """
        print("正在修复 stage/status 不一致字段...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 更新 stage 使其与 status 一致
            cursor.execute('''
                UPDATE diagnosis_reports
                SET stage = status
                WHERE stage != status
                AND status IN ('initializing', 'ai_fetching', 'analyzing', 
                              'intelligence_analyzing', 'completed', 'failed', 'timeout')
            ''')
            
            fixed_count = cursor.rowcount
            self.stats['fixed_stage_status'] = fixed_count
            
            conn.commit()
            
            print(f"✅ 修复 stage/status 不一致：{fixed_count} 条记录")
            return fixed_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 修复 stage/status 不一致失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def mark_empty_reports(self) -> int:
        """
        标记空报告（没有对应结果的报告）
        
        返回:
            标记的记录数
        """
        print("正在标记空报告...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 标记没有对应结果的已完成报告
            cursor.execute('''
                UPDATE diagnosis_reports
                SET error_message = '历史数据：报告内容为空'
                WHERE execution_id NOT IN (
                    SELECT DISTINCT execution_id FROM diagnosis_results
                )
                AND status = 'completed'
                AND (error_message IS NULL OR error_message = '')
            ''')
            
            marked_count = cursor.rowcount
            self.stats['marked_empty_reports'] = marked_count
            
            conn.commit()
            
            print(f"✅ 标记空报告：{marked_count} 条记录")
            return marked_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 标记空报告失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def clean_invalid_records(self) -> int:
        """
        清理无效记录（超过 30 天的初始化状态记录）
        
        返回:
            清理的记录数
        """
        print("正在清理无效记录...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 删除超过 30 天且状态仍为 initializing 的记录
            cutoff_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            
            cursor.execute('''
                DELETE FROM diagnosis_reports
                WHERE status = 'initializing'
                AND created_at < ?
            ''', (cutoff_date,))
            
            cleaned_count = cursor.rowcount
            self.stats['cleaned_invalid_records'] = cleaned_count
            
            conn.commit()
            
            print(f"✅ 清理无效记录：{cleaned_count} 条记录")
            return cleaned_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 清理无效记录失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def add_data_schema_version(self) -> int:
        """
        添加数据 schema 版本标记
        
        返回:
            更新的记录数
        """
        print("正在添加数据 schema 版本标记...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 为没有 data_schema_version 的记录添加版本标记
            cursor.execute('''
                UPDATE diagnosis_reports
                SET data_schema_version = '1.0'
                WHERE data_schema_version IS NULL
            ''')
            
            updated_count = cursor.rowcount
            
            conn.commit()
            
            print(f"✅ 添加数据 schema 版本标记：{updated_count} 条记录")
            return updated_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 添加数据 schema 版本标记失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def run_all_fixes(self) -> Dict[str, Any]:
        """
        运行所有修复
        
        返回:
            修复统计信息
        """
        print("=" * 60)
        print("历史诊断记录修复脚本")
        print(f"数据库路径：{self.db_path}")
        print(f"开始时间：{datetime.now().isoformat()}")
        print("=" * 60)
        print()
        
        # 执行所有修复
        self.fix_should_stop_polling()
        self.fix_stage_status_inconsistency()
        self.mark_empty_reports()
        self.clean_invalid_records()
        self.add_data_schema_version()
        
        # 打印统计信息
        print()
        print("=" * 60)
        print("修复统计")
        print("=" * 60)
        print(f"修复 should_stop_polling 字段：{self.stats['fixed_should_stop_polling']} 条")
        print(f"修复 stage/status 不一致：{self.stats['fixed_stage_status']} 条")
        print(f"标记空报告：{self.stats['marked_empty_reports']} 条")
        print(f"清理无效记录：{self.stats['cleaned_invalid_records']} 条")
        print(f"错误数：{self.stats['errors']}")
        print("=" * 60)
        print()
        print(f"完成时间：{datetime.now().isoformat()}")
        
        return self.stats


def main():
    """主函数"""
    fixer = HistoricalRecordsFixer()
    stats = fixer.run_all_fixes()
    
    # 如果有错误，返回非零退出码
    if stats['errors'] > 0:
        exit(1)


if __name__ == '__main__':
    main()
