"""
任务状态存储仓库

功能：
- 保存任务进度状态
- 支持按任务 ID 查询
- 支持实时更新
"""

import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager

from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.database_connection_pool import get_db_pool


@contextmanager
def get_db_connection():
    """获取数据库连接上下文管理器"""
    conn = get_db_pool().get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        db_logger.error(f"数据库操作失败：{e}")
        raise
    finally:
        get_db_pool().return_connection(conn)


def save_task_status(
    task_id: str,
    stage: str = 'init',
    progress: int = 0,
    status_text: str = None,
    completed_count: int = 0,
    total_count: int = 0,
    is_completed: bool = False
) -> int:
    """
    保存任务状态（如果不存在则创建，存在则更新）
    
    参数：
        task_id: 任务 ID
        stage: 阶段（init, ai_fetching, intelligence_analyzing, completed, failed）
        progress: 进度（0-100）
        status_text: 状态文本（用户友好提示）
        completed_count: 已完成任务数
        total_count: 总任务数
        is_completed: 是否完成
    
    返回：
        记录 ID
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute('SELECT id FROM task_statuses WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        
        if row:
            # 更新现有记录
            cursor.execute('''
                UPDATE task_statuses
                SET stage = ?, progress = ?, status_text = ?,
                    completed_count = ?, total_count = ?,
                    is_completed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (
                stage, progress, status_text,
                completed_count, total_count,
                is_completed, task_id
            ))
            record_id = row[0]
            api_logger.info(f"[TaskStatus] ✅ 任务状态更新成功：{task_id}, 阶段：{stage}, 进度：{progress}%")
        else:
            # 创建新记录
            cursor.execute('''
                INSERT INTO task_statuses
                (task_id, stage, progress, status_text, completed_count, total_count, is_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id, stage, progress, status_text,
                completed_count, total_count, is_completed
            ))
            record_id = cursor.lastrowid
            api_logger.info(f"[TaskStatus] ✅ 任务状态创建成功：{task_id}, 阶段：{stage}, 进度：{progress}%")
        
        return record_id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取任务状态
    
    参数：
        task_id: 任务 ID
    
    返回：
        任务状态字典，如果不存在则返回 None
    """
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM task_statuses
            WHERE task_id = ?
        ''', (task_id,))
        
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        else:
            api_logger.warning(f"[TaskStatus] ⚠️ 任务状态不存在：{task_id}")
            return None


def update_task_progress(
    task_id: str,
    progress: int,
    completed_count: int = None,
    total_count: int = None,
    stage: str = None
) -> bool:
    """
    更新任务进度（便捷函数）
    
    参数：
        task_id: 任务 ID
        progress: 进度（0-100）
        completed_count: 已完成任务数（可选）
        total_count: 总任务数（可选）
        stage: 阶段（可选）
    
    返回：
        是否更新成功
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 动态构建更新语句
        updates = ['progress = ?', 'updated_at = CURRENT_TIMESTAMP']
        values = [progress]
        
        if completed_count is not None:
            updates.append('completed_count = ?')
            values.append(completed_count)
        
        if total_count is not None:
            updates.append('total_count = ?')
            values.append(total_count)
        
        if stage is not None:
            updates.append('stage = ?')
            values.append(stage)
        
        values.append(task_id)
        
        cursor.execute(f'''
            UPDATE task_statuses
            SET {', '.join(updates)}
            WHERE task_id = ?
        ''', values)
        
        updated_count = cursor.rowcount
        
        if updated_count > 0:
            api_logger.info(f"[TaskStatus] ✅ 任务进度更新成功：{task_id}, 进度：{progress}%")
            return True
        else:
            api_logger.warning(f"[TaskStatus] ⚠️ 任务不存在，无法更新：{task_id}")
            return False


# 全局仓库实例
_task_status_repo = None

def get_task_status_repository():
    """获取全局任务状态仓库实例"""
    global _task_status_repo
    if _task_status_repo is None:
        from wechat_backend.repositories.task_status_repository import TaskStatusRepository
        _task_status_repo = TaskStatusRepository()
    return _task_status_repo


__all__ = [
    'save_task_status',
    'get_task_status',
    'update_task_progress'
]
