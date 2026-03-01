"""
API 调用日志仓库

用于存储和查询 API 调用日志。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.v2.models.api_call_log import APICallLog
from wechat_backend.v2.utils.sanitizer import DataSanitizer
from wechat_backend.v2.exceptions import RepositoryError

logger = logging.getLogger(__name__)


class APICallLogRepository:
    """
    API 调用日志仓库
    
    职责：
    1. 存储 API 调用日志
    2. 查询日志（按 execution_id, 时间范围等）
    3. 统计和分析日志数据
    4. 清理旧日志
    
    使用示例:
        >>> repo = APICallLogRepository()
        >>> repo.create(log)
        >>> logs = repo.get_by_execution_id('exec-123')
    """
    
    # 默认数据库路径
    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'data', 'api_call_logs.db'
    )
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化仓库
        
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
            "api_call_log_repository_initialized",
            extra={
                'event': 'api_call_log_repository_initialized',
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
            
            # 创建 api_call_logs 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- 任务关联
                    execution_id TEXT NOT NULL,
                    report_id INTEGER,
                    
                    -- 调用基本信息
                    brand TEXT NOT NULL,
                    question TEXT NOT NULL,
                    model TEXT NOT NULL,
                    
                    -- 请求信息
                    request_data TEXT NOT NULL,
                    request_headers TEXT,
                    request_timestamp TIMESTAMP NOT NULL,
                    
                    -- 响应信息
                    response_data TEXT,
                    response_headers TEXT,
                    response_timestamp TIMESTAMP,
                    
                    -- 状态信息
                    status_code INTEGER,
                    success BOOLEAN DEFAULT 0,
                    error_message TEXT,
                    error_stack TEXT,
                    
                    -- 性能指标
                    latency_ms INTEGER,
                    retry_count INTEGER DEFAULT 0,
                    
                    -- 元数据
                    api_version TEXT,
                    request_id TEXT,
                    
                    -- 敏感信息标记
                    has_sensitive_data BOOLEAN DEFAULT 0,
                    
                    -- 审计字段
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            self._create_index_if_not_exists(
                cursor, 'idx_api_logs_execution',
                'api_call_logs(execution_id)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_api_logs_report',
                'api_call_logs(report_id)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_api_logs_model',
                'api_call_logs(model)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_api_logs_success',
                'api_call_logs(success)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_api_logs_timestamp',
                'api_call_logs(request_timestamp)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_api_logs_execution_model',
                'api_call_logs(execution_id, model)'
            )
            
            db_logger.info("api_call_logs_table_initialized")
    
    def _create_index_if_not_exists(
        self,
        cursor: sqlite3.Cursor,
        index_name: str,
        index_def: str
    ) -> None:
        """
        创建索引（如果不存在）

        Args:
            cursor: 数据库游标
            index_name: 索引名称
            index_def: 索引定义

        Note:
            索引名称和定义必须是预定义的，不允许动态拼接
        """
        # 白名单验证索引名称
        allowed_indexes = {
            'idx_api_call_logs_execution_id': 'api_call_logs(execution_id)',
            'idx_api_call_logs_report_id': 'api_call_logs(report_id)',
            'idx_api_call_logs_timestamp': 'api_call_logs(request_timestamp)',
            'idx_api_call_logs_model': 'api_call_logs(model)',
        }
        
        if index_name not in allowed_indexes:
            raise ValueError(f"不允许的索引名称：{index_name}")
        
        if allowed_indexes[index_name] != index_def:
            raise ValueError(f"索引定义不匹配：{index_def}")
        
        try:
            # 使用参数化查询（索引名称无法参数化，已通过白名单验证）
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}')
        except sqlite3.OperationalError:
            # 索引已存在
            pass
    
    def create(self, log: APICallLog) -> int:
        """
        创建新的日志记录
        
        Args:
            log: API 调用日志对象
        
        Returns:
            int: 新记录的 ID
        
        Raises:
            RepositoryError: 存储失败
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO api_call_logs (
                        execution_id, report_id, brand, question, model,
                        request_data, request_headers, request_timestamp,
                        response_data, response_headers, response_timestamp,
                        status_code, success, error_message, error_stack,
                        latency_ms, retry_count, api_version, request_id,
                        has_sensitive_data, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log.execution_id,
                    log.report_id,
                    log.brand,
                    log.question,
                    log.model,
                    json.dumps(log.request_data, ensure_ascii=False),
                    json.dumps(log.request_headers) if log.request_headers else None,
                    log.request_timestamp.isoformat(),
                    json.dumps(log.response_data, ensure_ascii=False) if log.response_data else None,
                    json.dumps(log.response_headers) if log.response_headers else None,
                    log.response_timestamp.isoformat() if log.response_timestamp else None,
                    log.status_code,
                    1 if log.success else 0,
                    log.error_message,
                    log.error_stack,
                    log.latency_ms,
                    log.retry_count,
                    log.api_version,
                    log.request_id,
                    1 if log.has_sensitive_data else 0,
                    now,
                    now,
                ))
                
                log_id = cursor.lastrowid
                
                # 同时写入文件备份（双重保险）
                self._write_to_file_backup(log)
                
                api_logger.info(
                    "api_call_log_created",
                    extra={
                        'event': 'api_call_log_created',
                        'log_id': log_id,
                        'execution_id': log.execution_id,
                        'model': log.model,
                        'success': log.success,
                        'latency_ms': log.latency_ms,
                    }
                )
                
                return log_id
                
        except Exception as e:
            db_logger.error(
                "api_call_log_create_failed",
                extra={
                    'event': 'api_call_log_create_failed',
                    'execution_id': log.execution_id if hasattr(log, 'execution_id') else 'unknown',
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise RepositoryError(f"创建 API 调用日志失败：{e}") from e
    
    def get_by_id(self, log_id: int) -> Optional[APICallLog]:
        """
        根据 ID 获取日志
        
        Args:
            log_id: 日志 ID
        
        Returns:
            Optional[APICallLog]: 日志对象，不存在返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM api_call_logs WHERE id = ?', (log_id,))
                row = cursor.fetchone()
                
                if row:
                    return APICallLog.from_db_row(dict(row))
                return None
        except Exception as e:
            db_logger.error(
                "api_call_log_get_failed",
                extra={
                    'event': 'api_call_log_get_failed',
                    'log_id': log_id,
                    'error': str(e),
                }
            )
            return None
    
    def get_by_execution_id(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[APICallLog]:
        """
        获取某次诊断的所有 API 调用
        
        Args:
            execution_id: 执行 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[APICallLog]: 日志列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM api_call_logs
                    WHERE execution_id = ?
                    ORDER BY request_timestamp ASC
                    LIMIT ? OFFSET ?
                ''', (execution_id, limit, offset))
                
                return [APICallLog.from_db_row(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            db_logger.error(
                "api_call_log_get_by_execution_failed",
                extra={
                    'event': 'api_call_log_get_by_execution_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                }
            )
            return []
    
    def get_by_report_id(
        self,
        report_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[APICallLog]:
        """
        获取某份报告关联的所有 API 调用
        
        Args:
            report_id: 报告 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[APICallLog]: 日志列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM api_call_logs
                    WHERE report_id = ?
                    ORDER BY request_timestamp ASC
                    LIMIT ? OFFSET ?
                ''', (report_id, limit, offset))
                
                return [APICallLog.from_db_row(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            return []
    
    def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        model: Optional[str] = None,
        success_only: bool = False,
        limit: int = 1000,
    ) -> List[APICallLog]:
        """
        获取时间范围内的日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            model: 模型过滤
            success_only: 只返回成功的
            limit: 限制数量
        
        Returns:
            List[APICallLog]: 日志列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM api_call_logs
                    WHERE request_timestamp BETWEEN ? AND ?
                '''
                params = [start_time.isoformat(), end_time.isoformat()]
                
                if model:
                    query += ' AND model = ?'
                    params.append(model)
                
                if success_only:
                    query += ' AND success = 1'
                
                query += ' ORDER BY request_timestamp DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                return [APICallLog.from_db_row(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            return []
    
    def get_statistics(
        self,
        execution_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取调用统计信息
        
        Args:
            execution_id: 执行 ID
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建 WHERE 条件
                where_clauses = []
                params = []
                
                if execution_id:
                    where_clauses.append("execution_id = ?")
                    params.append(execution_id)
                
                if start_time:
                    where_clauses.append("request_timestamp >= ?")
                    params.append(start_time.isoformat())
                
                if end_time:
                    where_clauses.append("request_timestamp <= ?")
                    params.append(end_time.isoformat())
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # 总调用次数
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                        AVG(latency_ms) as avg_latency,
                        MAX(latency_ms) as max_latency
                    FROM api_call_logs
                    WHERE {where_sql}
                ''', params)
                
                stats = dict(cursor.fetchone())
                
                # 按模型统计
                cursor.execute(f'''
                    SELECT 
                        model,
                        COUNT(*) as count,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                        AVG(latency_ms) as avg_latency
                    FROM api_call_logs
                    WHERE {where_sql}
                    GROUP BY model
                ''', params)
                
                stats['by_model'] = [dict(row) for row in cursor.fetchall()]
                
                # 错误统计
                cursor.execute(f'''
                    SELECT 
                        error_message, 
                        COUNT(*) as count
                    FROM api_call_logs
                    WHERE success = 0 AND {where_sql}
                    GROUP BY error_message
                    ORDER BY count DESC
                    LIMIT 10
                ''', params)
                
                stats['top_errors'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
                
        except Exception as e:
            db_logger.error(
                "api_call_log_statistics_failed",
                extra={
                    'event': 'api_call_log_statistics_failed',
                    'error': str(e),
                }
            )
            return {
                'total': 0,
                'success_count': 0,
                'avg_latency': 0,
                'max_latency': 0,
                'by_model': [],
                'top_errors': [],
            }
    
    def delete_old_logs(self, days: int = 90) -> int:
        """
        删除指定天数前的日志
        
        Args:
            days: 保留天数（默认 90 天）
        
        Returns:
            int: 删除的记录数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM api_call_logs
                    WHERE request_timestamp < datetime('now', ?)
                ''', (f'-{days} days',))
                
                deleted = cursor.rowcount
                
                if deleted > 0:
                    api_logger.info(
                        "api_logs_cleanup",
                        extra={
                            'event': 'api_logs_cleanup',
                            'deleted_count': deleted,
                            'older_than_days': days,
                        }
                    )
                
                return deleted
                
        except Exception as e:
            db_logger.error(
                "api_logs_cleanup_failed",
                extra={
                    'event': 'api_logs_cleanup_failed',
                    'error': str(e),
                }
            )
            return 0
    
    def _write_to_file_backup(self, log: APICallLog) -> None:
        """
        写入文件备份（双重保险）
        
        将日志同时写入文件系统，防止数据库损坏导致数据丢失。
        
        Args:
            log: API 调用日志对象
        """
        try:
            # 按日期组织目录
            date_str = log.request_timestamp.strftime('%Y/%m/%d')
            log_dir = os.path.join(os.path.dirname(self.db_path), '..', 'api_logs', date_str)
            os.makedirs(log_dir, exist_ok=True)
            
            # 文件名格式：execution_id_model_timestamp.json
            timestamp = log.request_timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"{log.execution_id}_{log.model}_{timestamp}.json"
            filepath = os.path.join(log_dir, filename)
            
            # 写入文件（只写脱敏后的数据）
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log.to_dict(), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            # 文件备份失败不影响主流程，只记录警告
            api_logger.warning(
                "api_log_file_backup_failed",
                extra={
                    'event': 'api_log_file_backup_failed',
                    'error': str(e),
                }
            )
