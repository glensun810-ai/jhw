"""
任务队列数据模型

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from enum import Enum

from wechat_backend.logging_config import db_logger

DB_PATH = Path(__file__).parent.parent.parent / 'database.db'


class TaskQueueStatus(Enum):
    """任务队列状态枚举"""
    PENDING = "pending"           # 等待执行
    QUEUED = "queued"             # 已入队
    RUNNING = "running"           # 执行中
    SUCCESS = "success"           # 成功
    FAILED = "failed"             # 失败
    RETRY = "retry"               # 重试中
    TIMEOUT = "timeout"           # 超时
    CANCELLED = "cancelled"       # 已取消


class TaskQueueModel:
    """任务队列数据模型"""

    def __init__(self, execution_id, task_type, priority=0,
                 status=None, payload=None,
                 result=None, error_message=None,
                 retry_count=0, max_retries=3,
                 celery_task_id=None, worker_name=None,
                 created_at=None, started_at=None,
                 completed_at=None):
        self.execution_id = execution_id
        self.task_type = task_type
        self.priority = priority
        self.status = status if status else TaskQueueStatus.PENDING
        self.payload = payload or {}
        self.result = result or {}
        self.error_message = error_message
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.celery_task_id = celery_task_id
        self.worker_name = worker_name
        self.created_at = created_at or datetime.now().isoformat()
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self):
        """转换为字典格式"""
        return {
            'execution_id': self.execution_id,
            'task_type': self.task_type,
            'priority': self.priority,
            'status': self.status.value,
            'payload': self.payload,
            'result': self.result,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        status = TaskQueueStatus(data.get('status', 'pending'))
        return cls(
            execution_id=data['execution_id'],
            task_type=data['task_type'],
            priority=data.get('priority', 0),
            status=status,
            payload=data.get('payload', {}),
            result=data.get('result', {}),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            created_at=data.get('created_at'),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at')
        )


def init_task_queue_db():
    """初始化任务队列数据库表"""
    db_logger.info(f"Initializing task queue database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建任务队列表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            payload TEXT, -- JSON string
            result TEXT, -- JSON string
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            celery_task_id TEXT,
            worker_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db_logger.debug("Task queue table created or verified")

    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_status
        ON task_queue (status)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_execution_id
        ON task_queue (execution_id)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_task_type
        ON task_queue (task_type)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_created_at
        ON task_queue (created_at DESC)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_priority
        ON task_queue (priority DESC)
    ''')

    db_logger.debug("Task queue indexes created or verified")

    conn.commit()
    conn.close()
    db_logger.info("Task queue database initialization completed")


def save_task_queue(task_queue: TaskQueueModel) -> bool:
    """
    保存任务队列记录

    参数:
        task_queue: TaskQueueModel 对象

    返回:
        是否成功
    """
    db_logger.info(f"Saving task queue for execution: {task_queue.execution_id}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 检查记录是否存在
        cursor.execute(
            'SELECT execution_id FROM task_queue WHERE execution_id = ?',
            (task_queue.execution_id,)
        )
        exists = cursor.fetchone() is not None

        if exists:
            # 更新现有记录
            cursor.execute('''
                UPDATE task_queue
                SET status = ?, payload = ?, result = ?, error_message = ?,
                    retry_count = ?, celery_task_id = ?, worker_name = ?,
                    started_at = ?, completed_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE execution_id = ?
            ''', (
                task_queue.status.value,
                json.dumps(task_queue.payload),
                json.dumps(task_queue.result),
                task_queue.error_message,
                task_queue.retry_count,
                task_queue.celery_task_id,
                task_queue.worker_name,
                task_queue.started_at,
                task_queue.completed_at,
                task_queue.execution_id
            ))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO task_queue
                (execution_id, task_type, priority, status, payload, result,
                 error_message, retry_count, max_retries, celery_task_id,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_queue.execution_id,
                task_queue.task_type,
                task_queue.priority,
                task_queue.status.value,
                json.dumps(task_queue.payload),
                json.dumps(task_queue.result),
                task_queue.error_message,
                task_queue.retry_count,
                task_queue.max_retries,
                task_queue.celery_task_id,
                task_queue.created_at
            ))

        conn.commit()
        db_logger.info(f"Task queue saved successfully for execution: {task_queue.execution_id}")
        return True

    except Exception as e:
        conn.rollback()
        db_logger.error(f"Failed to save task queue: {e}")
        return False

    finally:
        conn.close()


def get_task_queue(execution_id: str) -> TaskQueueModel:
    """
    获取任务队列记录

    参数:
        execution_id: 执行 ID

    返回:
        TaskQueueModel 对象，不存在返回 None
    """
    db_logger.info(f"Retrieving task queue for execution: {execution_id}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT execution_id, task_type, priority, status, payload, result,
                   error_message, retry_count, max_retries, celery_task_id,
                   worker_name, created_at, started_at, completed_at
            FROM task_queue
            WHERE execution_id = ?
        ''', (execution_id,))

        row = cursor.fetchone()

        if row:
            task_queue = TaskQueueModel(
                execution_id=row[0],
                task_type=row[1],
                priority=row[2],
                status=TaskQueueStatus(row[3]),
                payload=json.loads(row[4]) if row[4] else {},
                result=json.loads(row[5]) if row[5] else {},
                error_message=row[6],
                retry_count=row[7],
                max_retries=row[8],
                celery_task_id=row[9],
                worker_name=row[10],
                created_at=row[11],
                started_at=row[12],
                completed_at=row[13]
            )
            db_logger.info(f"Successfully retrieved task queue for execution: {execution_id}")
            return task_queue
        else:
            db_logger.warning(f"No task queue found for execution: {execution_id}")
            return None

    except Exception as e:
        db_logger.error(f"Failed to retrieve task queue: {e}")
        return None

    finally:
        conn.close()


def update_task_queue_status(
    execution_id: str,
    status: TaskQueueStatus,
    result: dict = None,
    error_message: str = None,
    celery_task_id: str = None,
    worker_name: str = None
) -> bool:
    """
    更新任务队列状态

    参数:
        execution_id: 执行 ID
        status: 新状态
        result: 结果数据
        error_message: 错误信息
        celery_task_id: Celery 任务 ID
        worker_name: Worker 名称

    返回:
        是否成功
    """
    db_logger.info(f"Updating task queue status for execution: {execution_id} to {status.value}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        updates = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
        params = [status.value]

        if result is not None:
            updates.append('result = ?')
            params.append(json.dumps(result))

        if error_message is not None:
            updates.append('error_message = ?')
            params.append(error_message)

        if celery_task_id is not None:
            updates.append('celery_task_id = ?')
            params.append(celery_task_id)

        if worker_name is not None:
            updates.append('worker_name = ?')
            params.append(worker_name)

        if status == TaskQueueStatus.RUNNING:
            updates.append('started_at = CURRENT_TIMESTAMP')
        elif status in [TaskQueueStatus.SUCCESS, TaskQueueStatus.FAILED,
                        TaskQueueStatus.TIMEOUT, TaskQueueStatus.CANCELLED]:
            updates.append('completed_at = CURRENT_TIMESTAMP')

        params.append(execution_id)

        cursor.execute(f'''
            UPDATE task_queue
            SET {', '.join(updates)}
            WHERE execution_id = ?
        ''', params)

        conn.commit()
        db_logger.info(f"Task queue status updated successfully for execution: {execution_id}")
        return True

    except Exception as e:
        conn.rollback()
        db_logger.error(f"Failed to update task queue status: {e}")
        return False

    finally:
        conn.close()


def get_pending_tasks(limit: int = 10) -> list:
    """
    获取待执行的任务

    参数:
        limit: 返回数量限制

    返回:
        TaskQueueModel 列表
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT execution_id, task_type, priority, status, payload, result,
                   error_message, retry_count, max_retries, celery_task_id,
                   worker_name, created_at, started_at, completed_at
            FROM task_queue
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        ''', (limit,))

        tasks = []
        for row in cursor.fetchall():
            task_queue = TaskQueueModel(
                execution_id=row[0],
                task_type=row[1],
                priority=row[2],
                status=TaskQueueStatus(row[3]),
                payload=json.loads(row[4]) if row[4] else {},
                result=json.loads(row[5]) if row[5] else {},
                error_message=row[6],
                retry_count=row[7],
                max_retries=row[8],
                celery_task_id=row[9],
                worker_name=row[10],
                created_at=row[11],
                started_at=row[12],
                completed_at=row[13]
            )
            tasks.append(task_queue)

        return tasks

    finally:
        conn.close()


def get_task_statistics(days: int = 7) -> dict:
    """
    获取任务统计信息

    参数:
        days: 统计天数

    返回:
        统计信息字典
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        stats = {}

        # 总任务数
        cursor.execute('''
            SELECT COUNT(*) FROM task_queue WHERE created_at > ?
        ''', (cutoff_date,))
        stats['total_tasks'] = cursor.fetchone()[0]

        # 按状态统计
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM task_queue
            WHERE created_at > ?
            GROUP BY status
        ''', (cutoff_date,))
        stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 按任务类型统计
        cursor.execute('''
            SELECT task_type, COUNT(*) as count
            FROM task_queue
            WHERE created_at > ?
            GROUP BY task_type
        ''', (cutoff_date,))
        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 平均执行时间
        cursor.execute('''
            SELECT AVG(
                (julianday(completed_at) - julianday(started_at)) * 86400
            ) as avg_duration
            FROM task_queue
            WHERE status IN ('success', 'failed')
            AND started_at IS NOT NULL
            AND completed_at IS NOT NULL
            AND created_at > ?
        ''', (cutoff_date,))
        stats['avg_duration_seconds'] = cursor.fetchone()[0] or 0

        # 成功率
        cursor.execute('''
            SELECT
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
            FROM task_queue
            WHERE created_at > ?
        ''', (cutoff_date,))
        stats['success_rate'] = cursor.fetchone()[0] or 0

        return stats

    finally:
        conn.close()
