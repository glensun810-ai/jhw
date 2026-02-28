"""
任务结果跟踪服务

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import sqlite3

from wechat_backend.logging_config import api_logger
from wechat_backend.models_pkg.task_queue import (
    TaskQueueModel,
    TaskQueueStatus,
    save_task_queue,
    get_task_queue,
    update_task_queue_status,
    get_task_statistics
)


class TaskResultTracker:
    """任务结果跟踪器"""

    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / 'database.db'

    def create_task_record(
        self,
        execution_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        user_id: str = None
    ) -> TaskQueueModel:
        """
        创建任务记录

        参数:
            execution_id: 执行 ID
            task_type: 任务类型
            payload: 任务参数
            priority: 优先级
            user_id: 用户 ID

        返回:
            TaskQueueModel 对象
        """
        task_queue = TaskQueueModel(
            execution_id=execution_id,
            task_type=task_type,
            priority=priority,
            status=TaskQueueStatus.PENDING,
            payload=payload,
            created_at=datetime.now().isoformat()
        )

        if save_task_queue(task_queue):
            api_logger.info(f"创建任务记录：{execution_id}")
            return task_queue
        else:
            api_logger.error(f"创建任务记录失败：{execution_id}")
            return None

    def get_task_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        参数:
            execution_id: 执行 ID

        返回:
            任务状态字典
        """
        task_queue = get_task_queue(execution_id)

        if not task_queue:
            return None

        # 计算进度
        progress = self._calculate_progress(task_queue)

        return {
            'execution_id': task_queue.execution_id,
            'status': task_queue.status.value,
            'progress': progress,
            'task_type': task_queue.task_type,
            'priority': task_queue.priority,
            'retry_count': task_queue.retry_count,
            'created_at': task_queue.created_at,
            'started_at': task_queue.started_at,
            'completed_at': task_queue.completed_at,
            'result': task_queue.result,
            'error_message': task_queue.error_message
        }

    def _calculate_progress(self, task_queue: TaskQueueModel) -> int:
        """
        计算任务进度

        参数:
            task_queue: 任务队列对象

        返回:
            进度百分比 (0-100)
        """
        status_progress_map = {
            TaskQueueStatus.PENDING: 0,
            TaskQueueStatus.QUEUED: 10,
            TaskQueueStatus.RUNNING: 50,
            TaskQueueStatus.RETRY: 30,
            TaskQueueStatus.SUCCESS: 100,
            TaskQueueStatus.FAILED: 100,
            TaskQueueStatus.TIMEOUT: 100,
            TaskQueueStatus.CANCELLED: 100
        }

        return status_progress_map.get(task_queue.status, 0)

    def get_task_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取任务统计信息

        参数:
            days: 统计天数

        返回:
            统计信息字典
        """
        return get_task_statistics(days)

    def get_user_tasks(
        self,
        user_id: str,
        limit: int = 10,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户任务列表

        参数:
            user_id: 用户 ID
            limit: 返回数量限制
            status: 状态过滤

        返回:
            任务列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = '''
                SELECT execution_id, task_type, priority, status, payload,
                       result, error_message, retry_count, created_at,
                       started_at, completed_at
                FROM task_queue
                WHERE payload LIKE ?
            '''
            params = [f'%{user_id}%']

            if status:
                query += ' AND status = ?'
                params.append(status)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            tasks = []
            for row in rows:
                task = {
                    'execution_id': row['execution_id'],
                    'task_type': row['task_type'],
                    'priority': row['priority'],
                    'status': row['status'],
                    'result': json.loads(row['result']) if row['result'] else {},
                    'error_message': row['error_message'],
                    'retry_count': row['retry_count'],
                    'created_at': row['created_at'],
                    'started_at': row['started_at'],
                    'completed_at': row['completed_at']
                }
                tasks.append(task)

            return tasks

        finally:
            conn.close()

    def cancel_task(self, execution_id: str) -> bool:
        """
        取消任务

        参数:
            execution_id: 执行 ID

        返回:
            是否成功
        """
        task_queue = get_task_queue(execution_id)

        if not task_queue:
            api_logger.warning(f"任务不存在：{execution_id}")
            return False

        if task_queue.status in [
            TaskQueueStatus.SUCCESS,
            TaskQueueStatus.FAILED,
            TaskQueueStatus.TIMEOUT,
            TaskQueueStatus.CANCELLED
        ]:
            api_logger.warning(f"任务已完成，无法取消：{execution_id}")
            return False

        # 更新状态为取消
        return update_task_queue_status(
            execution_id=execution_id,
            status=TaskQueueStatus.CANCELLED,
            error_message="用户取消任务"
        )


# 全局跟踪器实例
task_tracker = TaskResultTracker()


def get_task_tracker() -> TaskResultTracker:
    """获取任务跟踪器实例"""
    return task_tracker
