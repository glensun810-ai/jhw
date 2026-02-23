#!/usr/bin/env python3
"""
DS-P1-1 修复：数据清理和归档机制

功能：
1. 定期清理过期数据
2. 软删除标记数据处理
3. 数据归档到历史表
4. 自动调度执行

配置：
- DATA_RETENTION_DAYS: 数据保留天数（默认 90 天）
- CLEANUP_SCHEDULE_HOUR: 清理执行时间（默认凌晨 3 点）
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple

from wechat_backend.logging_config import api_logger
from wechat_backend.database.transaction import database_transaction

# 数据保留策略配置
DATA_RETENTION_DAYS = 90  # 保留 90 天数据
SOFT_DELETE_RETENTION_DAYS = 30  # 软删除数据保留 30 天
ARCHIVE_THRESHOLD_DAYS = 180  # 超过 180 天的数据归档

# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'database.db'


def cleanup_expired_data(dry_run: bool = False) -> dict:
    """
    清理过期数据
    
    Args:
        dry_run: 如果为 True，只统计不删除
    
    Returns:
        清理统计信息
    
    Example:
        stats = cleanup_expired_data()
        print(f"删除了 {stats['deleted_count']} 条记录")
    """
    stats = {
        'start_time': datetime.now(),
        'deleted_count': 0,
        'archived_count': 0,
        'tables_processed': [],
        'errors': []
    }
    
    cutoff_date = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
    soft_delete_cutoff = datetime.now() - timedelta(days=SOFT_DELETE_RETENTION_DAYS)
    
    api_logger.info(
        f"[DataCleanup] 开始清理过期数据 "
        f"(保留{DATA_RETENTION_DAYS}天，软删除{SOFT_DELETE_RETENTION_DAYS}天)"
    )
    
    try:
        with database_transaction("清理过期数据") as conn:
            cursor = conn.cursor()
            
            # 1. 清理 sync_results 中的软删除记录
            api_logger.info(f"[DataCleanup] 清理 sync_results 软删除记录...")
            if dry_run:
                cursor.execute("""
                    SELECT COUNT(*) FROM sync_results
                    WHERE is_deleted = 1
                    AND updated_at < ?
                """, (soft_delete_cutoff.isoformat(),))
                count = cursor.fetchone()[0]
                api_logger.info(f"[DataCleanup] [DRY RUN] 将删除 {count} 条 sync_results 记录")
            else:
                cursor.execute("""
                    DELETE FROM sync_results
                    WHERE is_deleted = 1
                    AND updated_at < ?
                """, (soft_delete_cutoff.isoformat(),))
                count = cursor.rowcount
                api_logger.info(f"[DataCleanup] 已删除 {count} 条 sync_results 记录")
            
            stats['deleted_count'] += count
            stats['tables_processed'].append('sync_results')
            
            # 2. 清理 task_statuses 中的已完成任务（超过保留期）
            api_logger.info(f"[DataCleanup] 清理 task_statuses 已完成任务...")
            if dry_run:
                cursor.execute("""
                    SELECT COUNT(*) FROM task_statuses
                    WHERE is_completed = 1
                    AND updated_at < ?
                """, (cutoff_date.isoformat(),))
                count = cursor.fetchone()[0]
                api_logger.info(f"[DataCleanup] [DRY RUN] 将删除 {count} 条 task_statuses 记录")
            else:
                cursor.execute("""
                    DELETE FROM task_statuses
                    WHERE is_completed = 1
                    AND updated_at < ?
                """, (cutoff_date.isoformat(),))
                count = cursor.rowcount
                api_logger.info(f"[DataCleanup] 已删除 {count} 条 task_statuses 记录")
            
            stats['deleted_count'] += count
            stats['tables_processed'].append('task_statuses')
            
            # 3. 清理 verification_codes 中的过期验证码
            api_logger.info(f"[DataCleanup] 清理 verification_codes 过期验证码...")
            if dry_run:
                cursor.execute("""
                    SELECT COUNT(*) FROM verification_codes
                    WHERE expires_at < ?
                    OR (created_at < ? AND used = 0)
                """, (datetime.now().isoformat(), cutoff_date.isoformat()))
                count = cursor.fetchone()[0]
                api_logger.info(f"[DataCleanup] [DRY RUN] 将删除 {count} 条 verification_codes 记录")
            else:
                cursor.execute("""
                    DELETE FROM verification_codes
                    WHERE expires_at < ?
                    OR (created_at < ? AND used = 0)
                """, (datetime.now().isoformat(), cutoff_date.isoformat()))
                count = cursor.rowcount
                api_logger.info(f"[DataCleanup] 已删除 {count} 条 verification_codes 记录")
            
            stats['deleted_count'] += count
            stats['tables_processed'].append('verification_codes')
            
            # 4. 清理 audit_logs 中的过期日志（保留 180 天）
            audit_cutoff = datetime.now() - timedelta(days=180)
            api_logger.info(f"[DataCleanup] 清理 audit_logs 过期日志...")
            if dry_run:
                cursor.execute("""
                    SELECT COUNT(*) FROM audit_logs
                    WHERE created_at < ?
                """, (audit_cutoff.isoformat(),))
                count = cursor.fetchone()[0]
                api_logger.info(f"[DataCleanup] [DRY RUN] 将删除 {count} 条 audit_logs 记录")
            else:
                cursor.execute("""
                    DELETE FROM audit_logs
                    WHERE created_at < ?
                """, (audit_cutoff.isoformat(),))
                count = cursor.rowcount
                api_logger.info(f"[DataCleanup] 已删除 {count} 条 audit_logs 记录")
            
            stats['deleted_count'] += count
            stats['tables_processed'].append('audit_logs')
            
            # 5. 统计数据库大小变化
            cursor.execute("PRAGMA database_size")
            db_size = cursor.fetchone()[0] * 1024  # 转换为字节
            stats['database_size_bytes'] = db_size
            stats['database_size_mb'] = round(db_size / 1024 / 1024, 2)
    
    except Exception as e:
        error_msg = f"[DataCleanup] 清理失败：{e}"
        api_logger.error(error_msg)
        stats['errors'].append(error_msg)
    
    # 计算执行时间
    stats['end_time'] = datetime.now()
    stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()
    
    # 记录总结
    api_logger.info(
        f"[DataCleanup] 清理完成：删除 {stats['deleted_count']} 条记录，"
        f"归档 {stats['archived_count']} 条记录，"
        f"耗时 {stats['duration_seconds']:.2f}秒，"
        f"数据库大小 {stats['database_size_mb']}MB"
    )
    
    return stats


def archive_old_data(dry_run: bool = False) -> dict:
    """
    归档历史数据
    
    Args:
        dry_run: 如果为 True，只统计不删除
    
    Returns:
        归档统计信息
    """
    stats = {
        'start_time': datetime.now(),
        'archived_count': 0,
        'errors': []
    }
    
    archive_date = datetime.now() - timedelta(days=ARCHIVE_THRESHOLD_DAYS)
    
    api_logger.info(f"[DataArchive] 开始归档 {ARCHIVE_THRESHOLD_DAYS} 天前的历史数据...")
    
    try:
        with database_transaction("归档历史数据") as conn:
            cursor = conn.cursor()
            
            # 检查是否有归档表
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='test_records_archive'
            """)
            has_archive_table = cursor.fetchone() is not None
            
            if not has_archive_table:
                api_logger.info("[DataArchive] 归档表不存在，跳过归档")
                return stats
            
            # 归档 test_records
            api_logger.info(f"[DataArchive] 归档 test_records...")
            if dry_run:
                cursor.execute("""
                    SELECT COUNT(*) FROM test_records
                    WHERE test_date < ?
                    AND id NOT IN (SELECT id FROM test_records_archive)
                """, (archive_date.isoformat(),))
                count = cursor.fetchone()[0]
                api_logger.info(f"[DataArchive] [DRY RUN] 将归档 {count} 条 test_records 记录")
            else:
                cursor.execute("""
                    INSERT INTO test_records_archive
                    SELECT * FROM test_records
                    WHERE test_date < ?
                    AND id NOT IN (SELECT id FROM test_records_archive)
                """, (archive_date.isoformat(),))
                count = cursor.rowcount
                api_logger.info(f"[DataArchive] 已归档 {count} 条 test_records 记录")
            
            stats['archived_count'] += count
    
    except Exception as e:
        error_msg = f"[DataArchive] 归档失败：{e}"
        api_logger.error(error_msg)
        stats['errors'].append(error_msg)
    
    stats['end_time'] = datetime.now()
    stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()
    
    api_logger.info(
        f"[DataArchive] 归档完成：归档 {stats['archived_count']} 条记录，"
        f"耗时 {stats['duration_seconds']:.2f}秒"
    )
    
    return stats


def get_storage_stats() -> dict:
    """
    获取存储统计信息
    
    Returns:
        存储统计信息字典
    """
    stats = {}
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 数据库大小
            cursor.execute("PRAGMA database_size")
            db_size = cursor.fetchone()[0] * 1024
            stats['database_size_bytes'] = db_size
            stats['database_size_mb'] = round(db_size / 1024 / 1024, 2)
            
            # 各表记录数
            tables = ['test_records', 'sync_results', 'task_statuses', 'users', 'audit_logs']
            table_stats = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_stats[table] = count
            
            stats['table_counts'] = table_stats
            
            # 软删除记录数
            cursor.execute("""
                SELECT COUNT(*) FROM sync_results WHERE is_deleted = 1
            """)
            stats['soft_deleted_count'] = cursor.fetchone()[0]
            
            # 过期数据估算
            cutoff_date = (datetime.now() - timedelta(days=DATA_RETENTION_DAYS)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM task_statuses
                WHERE is_completed = 1 AND updated_at < ?
            """, (cutoff_date,))
            stats['expired_task_count'] = cursor.fetchone()[0]
    
    except Exception as e:
        stats['error'] = str(e)
    
    return stats


def schedule_daily_cleanup():
    """
    调度每日清理任务
    
    使用 APScheduler 每天凌晨 3 点执行清理
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        
        # 添加每日清理任务
        scheduler.add_job(
            cleanup_expired_data,
            'cron',
            hour=3,
            minute=0,
            id='daily_data_cleanup',
            name='每日数据清理',
            replace_existing=True
        )
        
        # 添加每周归档任务（每周日凌晨 2 点）
        scheduler.add_job(
            archive_old_data,
            'cron',
            day_of_week='sun',
            hour=2,
            minute=0,
            id='weekly_data_archive',
            name='每周数据归档',
            replace_existing=True
        )
        
        scheduler.start()
        api_logger.info("[DataCleanup] 定时清理任务已启动")
        
        return scheduler
    
    except ImportError:
        api_logger.warning("[DataCleanup] APScheduler 未安装，无法启动定时任务")
        return None


if __name__ == '__main__':
    print("="*60)
    print("DS-P1-1: 数据清理和归档机制")
    print("="*60)
    print()
    
    # 显示存储统计
    print("📊 当前存储统计:")
    stats = get_storage_stats()
    print(f"  数据库大小：{stats.get('database_size_mb', 'N/A')} MB")
    if 'table_counts' in stats:
        print("  各表记录数:")
        for table, count in stats['table_counts'].items():
            print(f"    {table}: {count}")
    if 'soft_deleted_count' in stats:
        print(f"  软删除记录：{stats['soft_deleted_count']}")
    if 'expired_task_count' in stats:
        print(f"  过期任务：{stats['expired_task_count']}")
    
    print()
    
    # 执行清理（dry run 模式）
    print("📋 执行清理（预览模式）...")
    cleanup_stats = cleanup_expired_data(dry_run=True)
    print(f"  预计删除：{cleanup_stats['deleted_count']} 条记录")
    print(f"  处理表：{', '.join(cleanup_stats['tables_processed'])}")
    print(f"  耗时：{cleanup_stats['duration_seconds']:.2f}秒")
    
    print()
    print("="*60)
    print("提示：生产环境请移除 dry_run=True 参数执行实际清理")
    print("="*60)
