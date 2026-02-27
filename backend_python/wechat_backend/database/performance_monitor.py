"""
数据库性能监控模块

功能：
1. 慢查询日志记录
2. 连接池等待时间监控
3. 查询性能统计
4. 数据库连接健康检查

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import time
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager
from collections import defaultdict
import json

from wechat_backend.logging_config import db_logger


# ==================== 配置常量 ====================

class DatabasePerformanceConfig:
    """数据库性能配置"""
    # 慢查询阈值（秒）
    SLOW_QUERY_THRESHOLD = 1.0
    # 极慢查询阈值（秒）
    VERY_SLOW_QUERY_THRESHOLD = 5.0
    # 连接超时阈值（秒）
    CONNECTION_TIMEOUT_THRESHOLD = 5.0
    # 统计窗口大小（秒）
    STATS_WINDOW_SECONDS = 60
    # 最大统计记录数
    MAX_STATS_RECORDS = 1000


# ==================== 查询统计数据结构 ====================

class QueryStats:
    """查询统计数据"""
    
    def __init__(self):
        self.total_queries = 0
        self.slow_queries = 0
        self.very_slow_queries = 0
        self.total_time = 0.0
        self.max_time = 0.0
        self.min_time = float('inf')
        self.errors = 0
        self.last_query_time = None
        self.query_types = defaultdict(int)
        
    def record_query(
        self, 
        duration: float, 
        query_type: str = 'unknown',
        is_error: bool = False
    ):
        """记录一次查询"""
        self.total_queries += 1
        self.total_time += duration
        self.max_time = max(self.max_time, duration)
        self.min_time = min(self.min_time, duration)
        self.last_query_time = datetime.now()
        self.query_types[query_type] += 1
        
        if duration >= DatabasePerformanceConfig.VERY_SLOW_QUERY_THRESHOLD:
            self.very_slow_queries += 1
        elif duration >= DatabasePerformanceConfig.SLOW_QUERY_THRESHOLD:
            self.slow_queries += 1
            
        if is_error:
            self.errors += 1
    
    def get_average_time(self) -> float:
        """获取平均查询时间"""
        if self.total_queries == 0:
            return 0.0
        return self.total_time / self.total_queries
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_queries': self.total_queries,
            'slow_queries': self.slow_queries,
            'very_slow_queries': self.very_slow_queries,
            'total_time_ms': round(self.total_time * 1000, 2),
            'average_time_ms': round(self.get_average_time() * 1000, 2),
            'max_time_ms': round(self.max_time * 1000, 2),
            'min_time_ms': round(self.min_time * 1000, 2) if self.min_time != float('inf') else 0,
            'errors': self.errors,
            'query_types': dict(self.query_types),
            'last_query_time': self.last_query_time.isoformat() if self.last_query_time else None
        }


# ==================== 数据库性能监控器 ====================

class DatabasePerformanceMonitor:
    """
    数据库性能监控器
    
    单例模式，全局访问
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.stats = QueryStats()
        self.slow_queries_log: List[Dict[str, Any]] = []
        self.connection_wait_times: List[float] = []
        self._callbacks: List[Callable] = []
        
        db_logger.info("DatabasePerformanceMonitor initialized")
    
    def record_query(
        self,
        query: str,
        duration: float,
        query_type: str = 'unknown',
        params: Optional[tuple] = None,
        is_error: bool = False,
        error_message: Optional[str] = None
    ):
        """
        记录查询性能
        
        Args:
            query: SQL 查询语句
            duration: 执行时间（秒）
            query_type: 查询类型（SELECT, INSERT, UPDATE, DELETE）
            params: 查询参数
            is_error: 是否出错
            error_message: 错误消息
        """
        # 记录统计
        self.stats.record_query(duration, query_type, is_error)
        
        # 记录慢查询
        if duration >= DatabasePerformanceConfig.SLOW_QUERY_THRESHOLD:
            self._log_slow_query(query, duration, query_type, params, is_error, error_message)
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(query, duration, query_type, is_error)
            except Exception as e:
                db_logger.error(f"Performance callback error: {e}")
    
    def _log_slow_query(
        self,
        query: str,
        duration: float,
        query_type: str,
        params: Optional[tuple],
        is_error: bool,
        error_message: Optional[str]
    ):
        """记录慢查询日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': self._truncate_query(query),
            'duration_ms': round(duration * 1000, 2),
            'query_type': query_type,
            'has_params': params is not None,
            'param_count': len(params) if params else 0,
            'is_error': is_error,
            'error_message': error_message
        }
        
        self.slow_queries_log.append(log_entry)
        
        # 限制日志数量
        if len(self.slow_queries_log) > DatabasePerformanceConfig.MAX_STATS_RECORDS:
            self.slow_queries_log = self.slow_queries_log[-DatabasePerformanceConfig.MAX_STATS_RECORDS:]
        
        # 记录日志
        if is_error:
            db_logger.error(
                f"Slow query error ({log_entry['duration_ms']}ms): {log_entry['query'][:200]}"
            )
        elif duration >= DatabasePerformanceConfig.VERY_SLOW_QUERY_THRESHOLD:
            db_logger.warning(
                f"Very slow query ({log_entry['duration_ms']}ms): {log_entry['query'][:200]}"
            )
        else:
            db_logger.warning(
                f"Slow query ({log_entry['duration_ms']}ms): {log_entry['query'][:200]}"
            )
    
    def _truncate_query(self, query: str, max_length: int = 500) -> str:
        """截断超长查询"""
        query = ' '.join(query.split())  # 规范化空格
        if len(query) <= max_length:
            return query
        return query[:max_length] + '... [truncated]'
    
    def record_connection_wait(self, wait_time: float):
        """
        记录连接池等待时间
        
        Args:
            wait_time: 等待时间（秒）
        """
        self.connection_wait_times.append(wait_time)
        
        # 限制记录数量
        if len(self.connection_wait_times) > 100:
            self.connection_wait_times = self.connection_wait_times[-100:]
        
        # 记录慢连接
        if wait_time >= DatabasePerformanceConfig.CONNECTION_TIMEOUT_THRESHOLD:
            db_logger.warning(
                f"Slow database connection: {round(wait_time * 1000, 2)}ms"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            'overall': self.stats.to_dict(),
            'connection_wait': {
                'count': len(self.connection_wait_times),
                'total_ms': round(sum(self.connection_wait_times) * 1000, 2),
                'average_ms': round(
                    (sum(self.connection_wait_times) / len(self.connection_wait_times) * 1000)
                    if self.connection_wait_times else 0, 2
                ),
                'max_ms': round(max(self.connection_wait_times) * 1000, 2) if self.connection_wait_times else 0
            },
            'slow_queries_count': len(self.slow_queries_log),
            'recent_slow_queries': self.slow_queries_log[-10:]  # 最近 10 条
        }
    
    def reset_stats(self):
        """重置统计"""
        self.stats = QueryStats()
        self.slow_queries_log = []
        self.connection_wait_times = []
        db_logger.info("Database performance stats reset")
    
    def register_callback(self, callback: Callable):
        """
        注册性能回调
        
        Args:
            callback: 回调函数 (query, duration, query_type, is_error)
        """
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """注销性能回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# ==================== 性能监控装饰器 ====================

def monitor_database_performance(query_type: str = 'unknown'):
    """
    数据库性能监控装饰器
    
    用法:
        @monitor_database_performance(query_type='SELECT')
        def get_user(user_id):
            cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
            return cursor.fetchone()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 记录成功查询
                monitor = DatabasePerformanceMonitor()
                monitor.record_query(
                    query=func.__name__,
                    duration=duration,
                    query_type=query_type,
                    is_error=False
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # 记录错误查询
                monitor = DatabasePerformanceMonitor()
                monitor.record_query(
                    query=func.__name__,
                    duration=duration,
                    query_type=query_type,
                    is_error=True,
                    error_message=str(e)
                )
                
                raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# ==================== 性能监控 SQLite 连接 ====================

class MonitoredSQLiteConnection:
    """
    带性能监控的 SQLite 连接包装器
    """
    
    def __init__(self, db_path: str, **kwargs):
        self.db_path = db_path
        self.connection = None
        self.monitor = DatabasePerformanceMonitor()
        self.connection_kwargs = kwargs
        
    def connect(self) -> sqlite3.Connection:
        """建立连接"""
        start_time = time.time()
        
        # 记录连接等待时间
        self.connection = sqlite3.connect(self.db_path, **self.connection_kwargs)
        
        wait_time = time.time() - start_time
        self.monitor.record_connection_wait(wait_time)
        
        # 启用查询追踪
        self.connection.row_factory = sqlite3.Row
        
        db_logger.debug(f"Database connected: {self.db_path} (wait: {round(wait_time * 1000, 2)}ms)")
        
        return self.connection
    
    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            db_logger.debug(f"Database disconnected: {self.db_path}")
    
    def __enter__(self):
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        query_type: str = 'unknown'
    ) -> sqlite3.Cursor:
        """
        执行查询（带性能监控）
        
        Args:
            query: SQL 查询
            params: 查询参数
            query_type: 查询类型
            
        Returns:
            sqlite3.Cursor: 游标对象
        """
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        start_time = time.time()
        is_error = False
        error_message = None
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            return cursor
            
        except Exception as e:
            is_error = True
            error_message = str(e)
            raise
            
        finally:
            duration = time.time() - start_time
            self.monitor.record_query(
                query=query,
                duration=duration,
                query_type=query_type,
                params=params,
                is_error=is_error,
                error_message=error_message
            )
    
    def commit(self):
        """提交事务"""
        if self.connection:
            self.connection.commit()
    
    def rollback(self):
        """回滚事务"""
        if self.connection:
            self.connection.rollback()


# ==================== 便捷函数 ====================

def get_db_performance_monitor() -> DatabasePerformanceMonitor:
    """获取数据库性能监控器实例"""
    return DatabasePerformanceMonitor()

def get_monitored_connection(db_path: str, **kwargs) -> MonitoredSQLiteConnection:
    """获取带监控的数据库连接"""
    return MonitoredSQLiteConnection(db_path, **kwargs)

@contextmanager
def monitored_database_connection(db_path: str, **kwargs):
    """
    带性能监控的数据库连接上下文管理器
    
    用法:
        with monitored_database_connection('data.db') as conn:
            cursor = conn.execute("SELECT * FROM users")
            results = cursor.fetchall()
    """
    conn_wrapper = get_monitored_connection(db_path, **kwargs)
    try:
        conn = conn_wrapper.connect()
        yield conn_wrapper
    finally:
        conn_wrapper.close()


# ==================== 全局实例 ====================

# 全局性能监控器实例
db_performance_monitor = DatabasePerformanceMonitor()
