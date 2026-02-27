"""
死信队列服务

用于存储和处理无法自动恢复的失败任务。

功能：
1. 添加失败任务到死信队列
2. 查询死信任务（支持分页、过滤）
3. 重试死信任务
4. 标记死信任务为已解决/忽略
5. 统计死信任务
6. 定期清理旧记录

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import sqlite3
import json
import traceback
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import os

from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.v2.models.dead_letter import DeadLetter
from wechat_backend.v2.exceptions import DeadLetterQueueError

logger = logging.getLogger(__name__)


class DeadLetterQueue:
    """
    死信队列服务
    
    使用示例:
        >>> dlq = DeadLetterQueue()
        >>> dlq.add_to_dead_letter(
        ...     execution_id='exec-123',
        ...     task_type='ai_call',
        ...     error=TimeoutError('Timeout'),
        ...     task_context={'brand': '品牌 A'}
        ... )
        >>> stats = dlq.get_statistics()
    """
    
    # 默认数据库路径
    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'data', 'dead_letter_queue.db'
    )
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化死信队列
        
        Args:
            db_path: 数据库路径，默认使用 DEFAULT_DB_PATH
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        # 初始化数据库表
        self._init_db()
        
        api_logger.info(
            "dead_letter_queue_initialized",
            extra={
                'event': 'dead_letter_queue_initialized',
                'db_path': self.db_path,
            }
        )
    
    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        Yields:
            sqlite3.Connection: 数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            db_logger.error(
                "database_operation_failed",
                extra={
                    'event': 'database_operation_failed',
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建死信队列表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    
                    -- 失败信息
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    error_stack TEXT,
                    
                    -- 任务上下文
                    task_context TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    
                    -- 时间信息
                    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_retry_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    
                    -- 处理信息
                    handled_by TEXT,
                    resolution_notes TEXT,
                    
                    -- 索引字段
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_dead_letter_status 
                ON dead_letter_queue(status)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_dead_letter_execution 
                ON dead_letter_queue(execution_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_dead_letter_failed_at 
                ON dead_letter_queue(failed_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_dead_letter_priority 
                ON dead_letter_queue(priority DESC, failed_at ASC)
            ''')
            
            db_logger.info("dead_letter_queue_table_initialized")
    
    def add_to_dead_letter(
        self,
        execution_id: str,
        task_type: str,
        error: Exception,
        task_context: Dict[str, Any],
        retry_count: int = 0,
        max_retries: int = 3,
        priority: int = 0,
    ) -> int:
        """
        添加失败任务到死信队列
        
        Args:
            execution_id: 任务执行 ID
            task_type: 任务类型（ai_call, analysis, report_generation）
            error: 捕获的异常
            task_context: 任务上下文（JSON 可序列化）
            retry_count: 已重试次数
            max_retries: 最大重试次数
            priority: 优先级（0-10）
        
        Returns:
            int: 死信记录 ID
        
        Raises:
            DeadLetterQueueError: 添加失败
        """
        try:
            # 获取堆栈信息
            error_stack = ''.join(traceback.format_tb(error.__traceback__))
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO dead_letter_queue (
                        execution_id, task_type, status,
                        error_type, error_message, error_stack,
                        task_context, retry_count, max_retries, priority,
                        failed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution_id,
                    task_type,
                    'pending',
                    type(error).__name__,
                    str(error),
                    error_stack,
                    json.dumps(task_context, ensure_ascii=False),
                    retry_count,
                    max_retries,
                    priority,
                    now,
                    now,
                    now,
                ))
                
                dead_letter_id = cursor.lastrowid
                
                api_logger.info(
                    "dead_letter_added",
                    extra={
                        'event': 'dead_letter_added',
                        'dead_letter_id': dead_letter_id,
                        'execution_id': execution_id,
                        'task_type': task_type,
                        'error_type': type(error).__name__,
                        'error_message': str(error),
                        'retry_count': retry_count,
                        'priority': priority,
                    }
                )
                
                return dead_letter_id
                
        except Exception as e:
            db_logger.error(
                "dead_letter_add_failed",
                extra={
                    'event': 'dead_letter_add_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DeadLetterQueueError(f"添加死信失败：{e}") from e
    
    def get_dead_letter(self, dead_letter_id: int) -> Optional[Dict[str, Any]]:
        """
        获取单个死信记录
        
        Args:
            dead_letter_id: 死信记录 ID
        
        Returns:
            Optional[Dict[str, Any]]: 死信记录字典，不存在返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM dead_letter_queue WHERE id = ?
                ''', (dead_letter_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            db_logger.error(
                "dead_letter_get_failed",
                extra={
                    'event': 'dead_letter_get_failed',
                    'dead_letter_id': dead_letter_id,
                    'error': str(e),
                }
            )
            return None
    
    def list_dead_letters(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = 'priority DESC, failed_at ASC',
    ) -> List[Dict[str, Any]]:
        """
        查询死信记录（支持分页和过滤）
        
        Args:
            status: 过滤状态（pending/processing/resolved/ignored）
            task_type: 过滤任务类型
            limit: 每页数量
            offset: 偏移量
            sort_by: 排序方式
        
        Returns:
            List[Dict[str, Any]]: 死信记录列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM dead_letter_queue"
                params = []
                
                where_clauses = []
                if status:
                    where_clauses.append("status = ?")
                    params.append(status)
                if task_type:
                    where_clauses.append("task_type = ?")
                    params.append(task_type)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                
                query += f" ORDER BY {sort_by} LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            db_logger.error(
                "dead_letter_list_failed",
                extra={
                    'event': 'dead_letter_list_failed',
                    'error': str(e),
                }
            )
            return []
    
    def count_dead_letters(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> int:
        """
        统计死信数量
        
        Args:
            status: 过滤状态
            task_type: 过滤任务类型
        
        Returns:
            int: 死信数量
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT COUNT(*) FROM dead_letter_queue"
                params = []
                
                where_clauses = []
                if status:
                    where_clauses.append("status = ?")
                    params.append(status)
                if task_type:
                    where_clauses.append("task_type = ?")
                    params.append(task_type)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                
                cursor.execute(query, params)
                return cursor.fetchone()[0]
                
        except Exception as e:
            db_logger.error(
                "dead_letter_count_failed",
                extra={
                    'event': 'dead_letter_count_failed',
                    'error': str(e),
                }
            )
            return 0
    
    def mark_as_resolved(
        self,
        dead_letter_id: int,
        handled_by: str = 'system',
        resolution_notes: str = '',
    ) -> bool:
        """
        标记死信为已解决
        
        Args:
            dead_letter_id: 死信记录 ID
            handled_by: 处理人（system 或 username）
            resolution_notes: 处理说明
        
        Returns:
            bool: 是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE dead_letter_queue
                    SET status = 'resolved',
                        handled_by = ?,
                        resolution_notes = ?,
                        resolved_at = ?,
                        updated_at = ?
                    WHERE id = ? AND status = 'pending'
                ''', (
                    handled_by,
                    resolution_notes,
                    now,
                    now,
                    dead_letter_id,
                ))
                
                affected = cursor.rowcount > 0
                
                if affected:
                    api_logger.info(
                        "dead_letter_resolved",
                        extra={
                            'event': 'dead_letter_resolved',
                            'dead_letter_id': dead_letter_id,
                            'handled_by': handled_by,
                        }
                    )
                
                return affected
                
        except Exception as e:
            db_logger.error(
                "dead_letter_resolve_failed",
                extra={
                    'event': 'dead_letter_resolve_failed',
                    'dead_letter_id': dead_letter_id,
                    'error': str(e),
                }
            )
            return False
    
    def mark_as_ignored(
        self,
        dead_letter_id: int,
        handled_by: str = 'system',
        resolution_notes: str = '',
    ) -> bool:
        """
        标记死信为忽略
        
        Args:
            dead_letter_id: 死信记录 ID
            handled_by: 处理人
            resolution_notes: 处理说明
        
        Returns:
            bool: 是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE dead_letter_queue
                    SET status = 'ignored',
                        handled_by = ?,
                        resolution_notes = ?,
                        resolved_at = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    handled_by,
                    resolution_notes,
                    now,
                    now,
                    dead_letter_id,
                ))
                
                affected = cursor.rowcount > 0
                
                if affected:
                    api_logger.info(
                        "dead_letter_ignored",
                        extra={
                            'event': 'dead_letter_ignored',
                            'dead_letter_id': dead_letter_id,
                            'handled_by': handled_by,
                        }
                    )
                
                return affected
                
        except Exception as e:
            db_logger.error(
                "dead_letter_ignore_failed",
                extra={
                    'event': 'dead_letter_ignore_failed',
                    'dead_letter_id': dead_letter_id,
                    'error': str(e),
                }
            )
            return False
    
    def retry_dead_letter(
        self,
        dead_letter_id: int,
        handled_by: str = 'system',
    ) -> bool:
        """
        重试死信任务
        
        注意：此方法只更新状态为 'processing'，实际重试逻辑由调用方实现
        
        Args:
            dead_letter_id: 死信记录 ID
            handled_by: 处理人
        
        Returns:
            bool: 是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE dead_letter_queue
                    SET status = 'processing',
                        last_retry_at = ?,
                        handled_by = ?,
                        updated_at = ?
                    WHERE id = ? AND status = 'pending'
                ''', (
                    now,
                    handled_by,
                    now,
                    dead_letter_id,
                ))
                
                affected = cursor.rowcount > 0
                
                if affected:
                    api_logger.info(
                        "dead_letter_retry_marked",
                        extra={
                            'event': 'dead_letter_retry_marked',
                            'dead_letter_id': dead_letter_id,
                            'handled_by': handled_by,
                        }
                    )
                
                return affected
                
        except Exception as e:
            db_logger.error(
                "dead_letter_retry_failed",
                extra={
                    'event': 'dead_letter_retry_failed',
                    'dead_letter_id': dead_letter_id,
                    'error': str(e),
                }
            )
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取死信队列统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 按状态统计
                cursor.execute('''
                    SELECT status, COUNT(*) as count
                    FROM dead_letter_queue
                    GROUP BY status
                ''')
                status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
                
                # 按任务类型统计
                cursor.execute('''
                    SELECT task_type, COUNT(*) as count
                    FROM dead_letter_queue
                    WHERE status = 'pending'
                    GROUP BY task_type
                ''')
                type_stats = {row['task_type']: row['count'] for row in cursor.fetchall()}
                
                # 最近 24 小时新增
                cursor.execute('''
                    SELECT COUNT(*) FROM dead_letter_queue
                    WHERE failed_at > datetime('now', '-1 day')
                ''')
                last_24h = cursor.fetchone()[0]
                
                # 最早的 pending 任务时间
                oldest_pending = self._get_oldest_pending()
                
                return {
                    'total': sum(status_stats.values()),
                    'by_status': status_stats,
                    'by_task_type': type_stats,
                    'last_24h': last_24h,
                    'oldest_pending': oldest_pending,
                }
                
        except Exception as e:
            db_logger.error(
                "dead_letter_statistics_failed",
                extra={
                    'event': 'dead_letter_statistics_failed',
                    'error': str(e),
                }
            )
            return {
                'total': 0,
                'by_status': {},
                'by_task_type': {},
                'last_24h': 0,
                'oldest_pending': None,
            }
    
    def _get_oldest_pending(self) -> Optional[str]:
        """获取最早的 pending 任务时间"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT failed_at FROM dead_letter_queue
                    WHERE status = 'pending'
                    ORDER BY failed_at ASC
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                return row['failed_at'] if row else None
        except Exception:
            return None
    
    def cleanup_resolved(self, days: int = 30) -> int:
        """
        清理已解决超过指定天数的记录
        
        Args:
            days: 保留天数
        
        Returns:
            int: 清理的记录数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM dead_letter_queue
                    WHERE status IN ('resolved', 'ignored')
                    AND resolved_at < datetime('now', ?)
                ''', (f'-{days} days',))
                
                deleted = cursor.rowcount
                
                if deleted > 0:
                    api_logger.info(
                        "dead_letter_cleanup",
                        extra={
                            'event': 'dead_letter_cleanup',
                            'deleted_count': deleted,
                            'older_than_days': days,
                        }
                    )
                
                return deleted
                
        except Exception as e:
            db_logger.error(
                "dead_letter_cleanup_failed",
                extra={
                    'event': 'dead_letter_cleanup_failed',
                    'error': str(e),
                }
            )
            return 0
