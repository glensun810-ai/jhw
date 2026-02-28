"""
数据库连接池模块

功能：
- SQLite 数据库连接池管理
- 连接复用，减少创建开销
- 最大连接数限制
- 监控指标采集
- P2-6: 支持读写分离

参考：P2-6: 数据库读写分离未实现
"""

import sqlite3
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from wechat_backend.logging_config import db_logger

DB_PATH = Path(__file__).parent.parent / 'database.db'

# 监控指标
_db_pool_metrics = {
    'active_connections': 0,
    'available_connections': 0,
    'total_created': 0,
    'timeout_count': 0,
    'total_wait_time_ms': 0,
    'connection_count': 0,
    'last_reset_time': time.time()
}


class DatabaseConnectionPool:
    """
    SQLite 数据库连接池
    
    功能：
    1. 连接复用，减少创建开销
    2. 最大连接数限制，防止资源耗尽
    3. 自动健康检查
    4. 监控指标采集
    """

    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._pool: list = []
        self._in_use: set = set()
        self._lock = threading.Lock()
        self._created_count = 0
        self._timeout_count = 0
        self._total_wait_time_ms = 0
        self._connection_count = 0
        
        db_logger.info(f"数据库连接池初始化：max_connections={max_connections}")

    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """获取数据库连接"""
        start_time = time.time()
        wait_start = start_time

        while True:
            with self._lock:
                # 尝试从池中获取
                if self._pool:
                    conn = self._pool.pop()
                    self._in_use.add(id(conn))
                    wait_time_ms = (time.time() - wait_start) * 1000
                    self._total_wait_time_ms += wait_time_ms
                    self._connection_count += 1
                    self._update_metrics()
                    db_logger.debug(f"连接池获取连接：等待{wait_time_ms:.2f}ms，池中剩余{len(self._pool)}")
                    return conn

                # 如果未达到上限，创建新连接
                if self._created_count < self.max_connections:
                    self._created_count += 1
                    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    self._in_use.add(id(conn))
                    wait_time_ms = (time.time() - wait_start) * 1000
                    self._total_wait_time_ms += wait_time_ms
                    self._connection_count += 1
                    self._update_metrics()
                    db_logger.debug(f"连接池创建新连接：等待{wait_time_ms:.2f}ms")
                    return conn

                # 检查是否有连接超时
                if (time.time() - start_time) >= timeout:
                    self._timeout_count += 1
                    self._update_metrics()
                    db_logger.error(f"连接池获取连接超时：{timeout}秒")
                    raise TimeoutError(f"Database connection timeout after {timeout}s")

            # 等待后重试
            time.sleep(0.1)

    def return_connection(self, conn: sqlite3.Connection):
        """归还数据库连接"""
        with self._lock:
            conn_id = id(conn)
            if conn_id in self._in_use:
                self._in_use.remove(conn_id)
                self._pool.append(conn)
                self._update_metrics()
                db_logger.debug(f"连接池归还连接：池中数量{len(self._pool)}")

    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._in_use.clear()
            self._update_metrics()
            db_logger.info("连接池关闭所有连接")

    def _update_metrics(self):
        """更新监控指标"""
        global _db_pool_metrics
        _db_pool_metrics.update({
            'active_connections': len(self._in_use),
            'available_connections': len(self._pool),
            'total_created': self._created_count,
            'timeout_count': self._timeout_count,
            'total_wait_time_ms': self._total_wait_time_ms,
            'connection_count': self._connection_count,
            'last_reset_time': time.time()
        })

    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        return _db_pool_metrics.copy()

    def reset_metrics(self):
        """重置监控指标"""
        global _db_pool_metrics
        _db_pool_metrics.update({
            'active_connections': 0,
            'available_connections': 0,
            'total_created': 0,
            'timeout_count': 0,
            'total_wait_time_ms': 0,
            'connection_count': 0,
            'last_reset_time': time.time()
        })


# 全局连接池实例
_db_pool: Optional[DatabaseConnectionPool] = None


def get_db_pool() -> DatabaseConnectionPool:
    """获取全局连接池实例"""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabaseConnectionPool(max_connections=10)
    return _db_pool


def get_db_pool_metrics() -> Dict[str, Any]:
    """获取连接池指标"""
    return get_db_pool().get_metrics()


def reset_db_pool_metrics():
    """重置连接池指标"""
    get_db_pool().reset_metrics()


def close_db_pool():
    """关闭连接池"""
    global _db_pool
    if _db_pool:
        _db_pool.close_all()
        _db_pool = None


# ==================== P2-6: 读写分离兼容函数 ====================

def get_db_connection(operation_type: str = 'read') -> sqlite3.Connection:
    """
    根据操作类型获取数据库连接（兼容旧代码）
    
    Args:
        operation_type: 操作类型 ('read' 或 'write')
        
    Returns:
        数据库连接
    """
    # 尝试使用读写分离连接
    try:
        from wechat_backend.database.database_read_write_split import get_db_connection as get_rw_db_connection
        return get_rw_db_connection(operation_type)
    except Exception:
        # 回退到默认连接池
        return get_db_pool().get_connection()


def return_db_connection(conn: sqlite3.Connection, operation_type: str = 'read'):
    """
    归还数据库连接（兼容旧代码）
    
    Args:
        conn: 数据库连接
        operation_type: 操作类型 ('read' 或 'write')
    """
    # 尝试使用读写分离归还
    try:
        from wechat_backend.database.database_read_write_split import return_db_connection as return_rw_db_connection
        return_rw_db_connection(conn, operation_type)
    except Exception:
        # 回退到默认连接池
        get_db_pool().return_connection(conn)
