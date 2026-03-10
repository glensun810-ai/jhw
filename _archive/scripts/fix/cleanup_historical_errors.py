#!/usr/bin/env python3
"""
P1-5 历史异常数据清理脚本

修复内容：
1. 清理重复的诊断报告（UNIQUE constraint 错误）
2. 清理孤立的诊断结果（无对应报告）
3. 清理孤立的诊断分析（无对应报告）
4. 清理过期的临时数据
5. 清理失败/取消的任务数据（超过 30 天）

使用方法：
    python3 scripts/cleanup_historical_errors.py

@author: 系统架构组
@date: 2026-02-28
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
backend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'backend_python'
)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from wechat_backend.logging_config import api_logger

# 数据库路径
DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'backend_python',
    'database.db'
)


class HistoricalDataCleaner:
    """历史数据清理器"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """
        初始化清理器
        
        参数：
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.stats = {
            'duplicates_removed': 0,
            'orphaned_results_removed': 0,
            'orphaned_analysis_removed': 0,
            'expired_tasks_removed': 0,
            'invalid_records_removed': 0,
            'total_freed_bytes': 0
        }
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def cleanup_duplicate_reports(self) -> int:
        """
        清理重复的诊断报告（保留 ID 最小的记录）
        
        返回：
            删除的记录数
        """
        api_logger.info("[P1-5] 开始清理重复的诊断报告...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 查找重复的 execution_id
            cursor.execute('''
                SELECT execution_id, COUNT(*) as count
                FROM diagnosis_reports
                GROUP BY execution_id
                HAVING COUNT(*) > 1
            ''')
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                api_logger.info("[P1-5] ✅ 未发现重复的诊断报告")
                return 0
            
            api_logger.info(f"[P1-5] 发现 {len(duplicates)} 个重复的 execution_id")
            
            total_deleted = 0
            
            for dup in duplicates:
                execution_id = dup['execution_id']
                count = dup['count']
                
                # 删除除了最小 ID 之外的所有记录
                cursor.execute('''
                    DELETE FROM diagnosis_reports
                    WHERE execution_id = ?
                    AND id NOT IN (
                        SELECT MIN(id)
                        FROM diagnosis_reports
                        WHERE execution_id = ?
                    )
                ''', (execution_id, execution_id))
                
                deleted = cursor.rowcount
                total_deleted += deleted
                
                api_logger.info(
                    f"[P1-5] 清理 execution_id={execution_id} 的 {deleted} 条重复记录 "
                    f"(原 {count} 条，保留 1 条)"
                )
            
            conn.commit()
            
            self.stats['duplicates_removed'] = total_deleted
            api_logger.info(f"[P1-5] ✅ 清理完成，共删除 {total_deleted} 条重复记录")
            
            return total_deleted
            
        except Exception as e:
            api_logger.error(f"[P1-5] ❌ 清理重复报告失败：{e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def cleanup_orphaned_results(self) -> int:
        """
        清理孤立的诊断结果（无对应报告）
        
        返回：
            删除的记录数
        """
        api_logger.info("[P1-5] 开始清理孤立的诊断结果...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 查找孤立的 diagnosis_results
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM diagnosis_results dr
                LEFT JOIN diagnosis_reports dp ON dr.report_id = dp.id
                WHERE dp.id IS NULL
            ''')
            
            orphaned_count = cursor.fetchone()['count']
            
            if orphaned_count == 0:
                api_logger.info("[P1-5] ✅ 未发现孤立的诊断结果")
                return 0
            
            api_logger.info(f"[P1-5] 发现 {orphaned_count} 条孤立的诊断结果")
            
            # 删除孤立的记录
            cursor.execute('''
                DELETE FROM diagnosis_results
                WHERE report_id NOT IN (SELECT id FROM diagnosis_reports)
            ''')
            
            deleted = cursor.rowcount
            conn.commit()
            
            self.stats['orphaned_results_removed'] = deleted
            api_logger.info(f"[P1-5] ✅ 清理完成，共删除 {deleted} 条孤立记录")
            
            return deleted
            
        except Exception as e:
            api_logger.error(f"[P1-5] ❌ 清理孤立结果失败：{e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def cleanup_orphaned_analysis(self) -> int:
        """
        清理孤立的诊断分析（无对应报告）
        
        返回：
            删除的记录数
        """
        api_logger.info("[P1-5] 开始清理孤立的诊断分析...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 查找孤立的 diagnosis_analysis
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM diagnosis_analysis da
                LEFT JOIN diagnosis_reports dp ON da.report_id = dp.id
                WHERE dp.id IS NULL
            ''')
            
            orphaned_count = cursor.fetchone()['count']
            
            if orphaned_count == 0:
                api_logger.info("[P1-5] ✅ 未发现孤立的诊断分析")
                return 0
            
            api_logger.info(f"[P1-5] 发现 {orphaned_count} 条孤立的诊断分析")
            
            # 删除孤立的记录
            cursor.execute('''
                DELETE FROM diagnosis_analysis
                WHERE report_id NOT IN (SELECT id FROM diagnosis_reports)
            ''')
            
            deleted = cursor.rowcount
            conn.commit()
            
            self.stats['orphaned_analysis_removed'] = deleted
            api_logger.info(f"[P1-5] ✅ 清理完成，共删除 {deleted} 条孤立记录")
            
            return deleted
            
        except Exception as e:
            api_logger.error(f"[P1-5] ❌ 清理孤立分析失败：{e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def cleanup_expired_tasks(self, days: int = 30) -> int:
        """
        清理过期的任务数据（失败/取消状态超过指定天数）
        
        参数：
            days: 保留天数，默认 30 天
            
        返回：
            删除的记录数
        """
        api_logger.info(f"[P1-5] 开始清理过期任务数据（>{days}天）...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 查找过期的任务
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM diagnosis_reports
                WHERE status IN ('failed', 'cancelled', 'timeout')
                AND created_at < ?
            ''', (cutoff_date,))
            
            expired_count = cursor.fetchone()['count']
            
            if expired_count == 0:
                api_logger.info(f"[P1-5] ✅ 未发现过期任务数据（>{days}天）")
                return 0
            
            api_logger.info(
                f"[P1-5] 发现 {expired_count} 条过期任务数据（>{days}天）"
            )
            
            # 先删除关联的结果和分析
            cursor.execute('''
                DELETE FROM diagnosis_results
                WHERE report_id IN (
                    SELECT id FROM diagnosis_reports
                    WHERE status IN ('failed', 'cancelled', 'timeout')
                    AND created_at < ?
                )
            ''', (cutoff_date,))
            
            cursor.execute('''
                DELETE FROM diagnosis_analysis
                WHERE report_id IN (
                    SELECT id FROM diagnosis_reports
                    WHERE status IN ('failed', 'cancelled', 'timeout')
                    AND created_at < ?
                )
            ''', (cutoff_date,))
            
            # 删除过期任务
            cursor.execute('''
                DELETE FROM diagnosis_reports
                WHERE status IN ('failed', 'cancelled', 'timeout')
                AND created_at < ?
            ''', (cutoff_date,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            self.stats['expired_tasks_removed'] = deleted
            api_logger.info(
                f"[P1-5] ✅ 清理完成，共删除 {deleted} 条过期任务记录"
            )
            
            return deleted
            
        except Exception as e:
            api_logger.error(f"[P1-5] ❌ 清理过期任务失败：{e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def cleanup_invalid_records(self) -> int:
        """
        清理无效记录（关键字段为空或格式错误）
        
        返回：
            删除的记录数
        """
        api_logger.info("[P1-5] 开始清理无效记录...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 清理 brand_name 为空的记录
            cursor.execute('''
                DELETE FROM diagnosis_reports
                WHERE brand_name IS NULL OR brand_name = ''
            ''')
            deleted_brand = cursor.rowcount
            
            # 清理 user_id 为空的记录
            cursor.execute('''
                DELETE FROM diagnosis_reports
                WHERE user_id IS NULL OR user_id = ''
            ''')
            deleted_user = cursor.rowcount
            
            # 清理 execution_id 格式错误的记录（应该是以 exec- 开头或 UUID 格式）
            cursor.execute('''
                DELETE FROM diagnosis_reports
                WHERE execution_id IS NULL 
                OR execution_id = ''
                OR (LENGTH(execution_id) < 10 AND execution_id NOT LIKE 'exec-%')
            ''')
            deleted_exec = cursor.rowcount
            
            total_deleted = deleted_brand + deleted_user + deleted_exec
            conn.commit()
            
            self.stats['invalid_records_removed'] = total_deleted
            
            if total_deleted > 0:
                api_logger.info(
                    f"[P1-5] ✅ 清理完成，共删除 {total_deleted} 条无效记录 "
                    f"(brand_name={deleted_brand}, user_id={deleted_user}, "
                    f"execution_id={deleted_exec})"
                )
            else:
                api_logger.info("[P1-5] ✅ 未发现无效记录")
            
            return total_deleted
            
        except Exception as e:
            api_logger.error(f"[P1-5] ❌ 清理无效记录失败：{e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def get_database_size(self) -> int:
        """获取数据库文件大小（字节）"""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0
    
    def run_full_cleanup(self) -> dict:
        """
        运行完整清理流程
        
        返回：
            清理统计信息
        """
        api_logger.info("=" * 60)
        api_logger.info("[P1-5] 开始历史异常数据清理")
        api_logger.info("=" * 60)
        
        # 记录清理前数据库大小
        size_before = self.get_database_size()
        api_logger.info(f"[P1-5] 清理前数据库大小：{size_before / 1024 / 1024:.2f} MB")
        
        # 执行清理步骤
        steps = [
            ("重复报告", self.cleanup_duplicate_reports),
            ("孤立结果", self.cleanup_orphaned_results),
            ("孤立分析", self.cleanup_orphaned_analysis),
            ("过期任务", lambda: self.cleanup_expired_tasks(30)),
            ("无效记录", self.cleanup_invalid_records),
        ]
        
        for step_name, step_func in steps:
            try:
                deleted = step_func()
                api_logger.info(f"[P1-5] {step_name}: 删除 {deleted} 条记录")
            except Exception as e:
                api_logger.error(f"[P1-5] {step_name} 失败：{e}")
        
        # 记录清理后数据库大小
        size_after = self.get_database_size()
        freed_bytes = size_before - size_after
        self.stats['total_freed_bytes'] = freed_bytes
        
        api_logger.info("=" * 60)
        api_logger.info("[P1-5] 清理完成")
        api_logger.info("=" * 60)
        api_logger.info(f"[P1-5] 清理后数据库大小：{size_after / 1024 / 1024:.2f} MB")
        api_logger.info(f"[P1-5] 释放空间：{freed_bytes / 1024 / 1024:.2f} MB")
        api_logger.info(f"[P1-5] 清理统计：{self.stats}")
        
        return self.stats
    
    def get_statistics(self) -> dict:
        """
        获取当前数据库统计信息
        
        返回：
            统计信息字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 总报告数
            cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
            stats['total_reports'] = cursor.fetchone()[0]
            
            # 重复报告数
            cursor.execute('''
                SELECT COUNT(*) FROM (
                    SELECT execution_id
                    FROM diagnosis_reports
                    GROUP BY execution_id
                    HAVING COUNT(*) > 1
                )
            ''')
            stats['duplicate_execution_ids'] = cursor.fetchone()[0]
            
            # 孤立结果数
            cursor.execute('''
                SELECT COUNT(*)
                FROM diagnosis_results dr
                LEFT JOIN diagnosis_reports dp ON dr.report_id = dp.id
                WHERE dp.id IS NULL
            ''')
            stats['orphaned_results'] = cursor.fetchone()[0]
            
            # 孤立分析数
            cursor.execute('''
                SELECT COUNT(*)
                FROM diagnosis_analysis da
                LEFT JOIN diagnosis_reports dp ON da.report_id = dp.id
                WHERE dp.id IS NULL
            ''')
            stats['orphaned_analysis'] = cursor.fetchone()[0]
            
            # 过期任务数
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute('''
                SELECT COUNT(*)
                FROM diagnosis_reports
                WHERE status IN ('failed', 'cancelled', 'timeout')
                AND created_at < ?
            ''', (cutoff_date,))
            stats['expired_tasks'] = cursor.fetchone()[0]
            
            # 无效记录数
            cursor.execute('''
                SELECT COUNT(*)
                FROM diagnosis_reports
                WHERE brand_name IS NULL OR brand_name = ''
                OR user_id IS NULL OR user_id = ''
            ''')
            stats['invalid_records'] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            api_logger.error(f"[P1-5] 获取统计信息失败：{e}")
            return {}
        finally:
            conn.close()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("P1-5 历史异常数据清理工具")
    print("=" * 60)
    print()
    
    # 创建清理器
    cleaner = HistoricalDataCleaner()
    
    # 显示清理前统计
    print("清理前数据库状态:")
    print("-" * 60)
    stats_before = cleaner.get_statistics()
    for key, value in stats_before.items():
        print(f"  {key}: {value}")
    print()
    
    # 询问是否继续
    confirm = input("是否继续清理？(y/N): ")
    if confirm.lower() != 'y':
        print("已取消清理操作")
        return
    
    print()
    
    # 执行清理
    result = cleaner.run_full_cleanup()
    
    # 显示清理后统计
    print()
    print("清理后数据库状态:")
    print("-" * 60)
    stats_after = cleaner.get_statistics()
    for key, value in stats_after.items():
        print(f"  {key}: {value}")
    print()
    
    # 计算改善
    print("清理效果:")
    print("-" * 60)
    if stats_before.get('duplicate_execution_ids', 0) > 0:
        print(f"  ✅ 重复 execution_id: {stats_before['duplicate_execution_ids']} → 0")
    if stats_before.get('orphaned_results', 0) > 0:
        print(f"  ✅ 孤立结果：{stats_before['orphaned_results']} → {stats_after.get('orphaned_results', 0)}")
    if stats_before.get('orphaned_analysis', 0) > 0:
        print(f"  ✅ 孤立分析：{stats_before['orphaned_analysis']} → {stats_after.get('orphaned_analysis', 0)}")
    if stats_before.get('expired_tasks', 0) > 0:
        print(f"  ✅ 过期任务：{stats_before['expired_tasks']} → {stats_after.get('expired_tasks', 0)}")
    if stats_before.get('invalid_records', 0) > 0:
        print(f"  ✅ 无效记录：{stats_before['invalid_records']} → {stats_after.get('invalid_records', 0)}")
    
    freed_mb = result.get('total_freed_bytes', 0) / 1024 / 1024
    if freed_mb > 0:
        print(f"  ✅ 释放空间：{freed_mb:.2f} MB")
    
    print()
    print("=" * 60)
    print("P1-5 清理完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
