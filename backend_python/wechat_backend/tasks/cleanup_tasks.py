"""
清理相关 Celery 异步任务

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from wechat_backend.celery_app import celery_app
from wechat_backend.logging_config import api_logger


@celery_app.task(
    name='wechat_backend.tasks.cleanup_tasks.cleanup_old_tasks',
    time_limit=600
)
def cleanup_old_tasks(days: int = 30) -> Dict[str, Any]:
    """
    清理过期任务记录

    参数:
        days: 保留天数

    返回:
        清理结果
    """
    api_logger.info(f"[Celery] 开始清理过期任务记录（保留{days}天）")

    try:
        import sqlite3
        from pathlib import Path

        db_path = Path(__file__).parent.parent.parent / 'database.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # 删除过期的任务队列记录
        cursor.execute('''
            DELETE FROM task_queue
            WHERE created_at < ?
            AND status IN ('success', 'failed', 'cancelled', 'timeout')
        ''', (cutoff_date,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        api_logger.info(f"[Celery] 清理完成，删除 {deleted_count} 条记录")

        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date
        }

    except Exception as e:
        api_logger.error(f"[Celery] 清理过期任务失败：{e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


@celery_app.task(
    name='wechat_backend.tasks.cleanup_tasks.cleanup_expired_cache',
    time_limit=300
)
def cleanup_expired_cache(days: int = 7) -> Dict[str, Any]:
    """
    清理过期缓存

    参数:
        days: 保留天数

    返回:
        清理结果
    """
    api_logger.info(f"[Celery] 开始清理过期缓存（保留{days}天）")

    try:
        import sqlite3
        from pathlib import Path

        db_path = Path(__file__).parent.parent.parent / 'database.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff_timestamp = (datetime.now() - timedelta(days=days)).timestamp()

        # 删除过期的缓存记录
        cursor.execute('''
            DELETE FROM cache_entries
            WHERE created_at < ?
        ''', (cutoff_timestamp,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        api_logger.info(f"[Celery] 清理完成，删除 {deleted_count} 条缓存记录")

        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_timestamp
        }

    except Exception as e:
        api_logger.error(f"[Celery] 清理过期缓存失败：{e}")
        return {
            'status': 'failed',
            'error': str(e)
        }
