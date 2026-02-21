"""
Database schema for GEO Content Quality Validator

修复记录:
- 2026-02-20: 使用上下文管理器确保连接关闭
- 2026-02-20: 添加数据加密支持 (P0-3)

P1 修复：使用绝对路径引用，避免相对路径越界错误
"""

import sqlite3
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, Any

from wechat_backend.logging_config import db_logger
from wechat_backend.security.sql_protection import SafeDatabaseQuery, sql_protector
from wechat_backend.security.data_encryption import (
    encrypt_field,
    decrypt_field,
    encrypt_sensitive_data,
    decrypt_sensitive_data,
    SENSITIVE_FIELDS
)

DB_PATH = Path(__file__).parent.parent / 'database.db'

# 加密开关 (可通过环境变量控制)
ENCRYPTION_ENABLED = os.environ.get('ENCRYPTION_ENABLED', 'false').lower() == 'true'

# ==================== 连接池配置 ====================

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
    
    功能:
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
        import time
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
                    conn.execute('PRAGMA journal_mode=WAL')  # WAL 模式提升并发
                    conn.execute('PRAGMA synchronous=NORMAL')  # 平衡性能和安全性
                    self._in_use.add(id(conn))
                    wait_time_ms = (time.time() - wait_start) * 1000
                    self._total_wait_time_ms += wait_time_ms
                    self._connection_count += 1
                    self._update_metrics()
                    db_logger.debug(f"连接池创建新连接：等待{wait_time_ms:.2f}ms，总连接数{self._created_count}")
                    return conn
            
            # 等待超时检查
            if time.time() - start_time > timeout:
                self._timeout_count += 1
                self._update_metrics()
                db_logger.error(f"获取数据库连接超时（{timeout}秒），活跃={len(self._in_use)}, 可用={len(self._pool)}")
                raise TimeoutError(f"获取数据库连接超时（{timeout}秒）")
            
            # 等待 10ms 后重试
            time.sleep(0.01)
    
    def return_connection(self, conn: sqlite3.Connection):
        """归还数据库连接"""
        with self._lock:
            conn_id = id(conn)
            if conn_id in self._in_use:
                self._in_use.discard(conn_id)
                # 健康检查
                try:
                    conn.execute('SELECT 1')
                    self._pool.append(conn)
                    db_logger.debug(f"连接归还池：池中数量{len(self._pool)}")
                except Exception:
                    # 连接损坏，创建新连接替换
                    self._created_count -= 1
                    conn.close()
                    new_conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
                    new_conn.execute('PRAGMA journal_mode=WAL')
                    new_conn.execute('PRAGMA synchronous=NORMAL')
                    self._pool.append(new_conn)
                    db_logger.warning(f"连接损坏已替换：池中数量{len(self._pool)}")
            self._update_metrics()
    
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
            'avg_wait_time_ms': self._total_wait_time_ms / max(self._connection_count, 1)
        })
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._in_use.clear()
            self._created_count = 0
            self._update_metrics()
            db_logger.info("数据库连接池已关闭")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取连接池监控指标"""
        with self._lock:
            return {
                'active_connections': len(self._in_use),
                'available_connections': len(self._pool),
                'total_created': self._created_count,
                'timeout_count': self._timeout_count,
                'total_wait_time_ms': round(self._total_wait_time_ms, 2),
                'connection_count': self._connection_count,
                'avg_wait_time_ms': round(self._total_wait_time_ms / max(self._connection_count, 1), 2),
                'utilization': f"{len(self._in_use) / self.max_connections * 100:.1f}%"
            }


# 全局连接池实例
_db_pool = None


def get_db_pool() -> DatabaseConnectionPool:
    """获取全局数据库连接池"""
    global _db_pool
    if _db_pool is None:
        import threading
        _db_pool = DatabaseConnectionPool(max_connections=10)
    return _db_pool


def get_db_pool_metrics() -> Dict[str, Any]:
    """获取数据库连接池监控指标"""
    pool = get_db_pool()
    return pool.get_metrics()


def reset_db_pool_metrics():
    """重置数据库连接池指标"""
    global _db_pool_metrics
    pool = get_db_pool()
    with pool._lock:
        pool._timeout_count = 0
        pool._total_wait_time_ms = 0
        pool._connection_count = 0
        pool._update_metrics()
    db_logger.info("数据库连接池指标已重置")


# ==================== 慢查询日志配置 ====================

SLOW_QUERY_THRESHOLD = 1.0  # 1 秒
_slow_query_count = 0
_total_query_time = 0.0
_query_count = 0

# ==================== 压缩率统计配置 ====================

_compression_metrics = {
    'total_compressed': 0,
    'total_uncompressed': 0,
    'original_size_bytes': 0,
    'compressed_size_bytes': 0,
    'space_saved_bytes': 0
}


def record_compression_stats(original_size: int, compressed_size: int):
    """记录压缩统计"""
    global _compression_metrics
    _compression_metrics['total_compressed'] += 1
    _compression_metrics['original_size_bytes'] += original_size
    _compression_metrics['compressed_size_bytes'] += compressed_size
    _compression_metrics['space_saved_bytes'] += (original_size - compressed_size)
    
    compression_ratio = compressed_size / max(original_size, 1)
    db_logger.debug(
        f"压缩统计：原始={original_size}字节，压缩后={compressed_size}字节，" +
        f"压缩率={compression_ratio*100:.1f}%，节省={(1-compression_ratio)*100:.1f}%"
    )


def get_compression_metrics() -> Dict[str, Any]:
    """获取压缩统计指标"""
    original_size = _compression_metrics['original_size_bytes']
    compressed_size = _compression_metrics['compressed_size_bytes']
    space_saved = _compression_metrics['space_saved_bytes']
    
    return {
        'total_compressed': _compression_metrics['total_compressed'],
        'total_uncompressed': _compression_metrics['total_uncompressed'],
        'original_size_kb': round(original_size / 1024, 2),
        'compressed_size_kb': round(compressed_size / 1024, 2),
        'space_saved_kb': round(space_saved / 1024, 2),
        'space_saved_mb': round(space_saved / 1024 / 1024, 2),
        'avg_compression_ratio': f"{compressed_size / max(original_size, 1) * 100:.1f}%",
        'space_savings': f"{(1 - compressed_size / max(original_size, 1)) * 100:.1f}%"
    }


def reset_compression_metrics():
    """重置压缩统计指标"""
    global _compression_metrics
    _compression_metrics = {
        'total_compressed': 0,
        'total_uncompressed': 0,
        'original_size_bytes': 0,
        'compressed_size_bytes': 0,
        'space_saved_bytes': 0
    }
    db_logger.info("压缩统计指标已重置")


@contextmanager
def monitored_query(description: str = "数据库查询"):
    """
    慢查询监控上下文管理器
    
    使用示例:
    with monitored_query("用户查询"):
        cursor.execute(...)
    
    自动记录慢查询并统计
    """
    global _slow_query_count, _total_query_time, _query_count
    
    import time
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        _total_query_time += duration
        _query_count += 1
        
        if duration > SLOW_QUERY_THRESHOLD:
            _slow_query_count += 1
            db_logger.warning(
                f"慢查询检测 [{description}]: {duration:.3f}秒 " +
                f"(阈值：{SLOW_QUERY_THRESHOLD}秒，累计慢查询：{_slow_query_count})"
            )


def get_query_metrics() -> Dict[str, Any]:
    """获取查询监控指标"""
    return {
        'slow_query_count': _slow_query_count,
        'total_query_time': round(_total_query_time, 3),
        'query_count': _query_count,
        'avg_query_time_ms': round((_total_query_time / max(_query_count, 1)) * 1000, 2),
        'slow_query_threshold': SLOW_QUERY_THRESHOLD,
        'slow_query_ratio': f"{_slow_query_count / max(_query_count, 1) * 100:.2f}%"
    }


def reset_query_metrics():
    """重置查询监控指标"""
    global _slow_query_count, _total_query_time, _query_count
    _slow_query_count = 0
    _total_query_time = 0.0
    _query_count = 0
    db_logger.info("查询监控指标已重置")


@contextmanager
def get_connection():
    """
    获取数据库连接（上下文管理器版本）
    
    使用示例:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(...)
    
    自动确保连接关闭和归还
    """
    conn = None
    try:
        conn = get_db_pool().get_connection()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            get_db_pool().return_connection(conn)


def get_or_create_user_by_unionid(union_id: str, openid: str) -> tuple:
    """
    Get or create user by UnionID

    Args:
        union_id: WeChat UnionID (or openid if unionid not available)
        openid: WeChat OpenID

    Returns:
        tuple: (user_dict, is_new_user)
    """
    from wechat_backend.logging_config import db_logger

    db_logger.info(f"Get or create user by union_id: {union_id[:10]}...")

    # 【性能修复】使用连接池获取连接
    with get_connection() as conn:
        cursor = conn.cursor()

        try:
            # Query existing user
            cursor.execute('''
                SELECT id, union_id, membership_plan, diagnostic_limit
                FROM users
                WHERE union_id = ? OR openid = ?
            ''', (union_id, openid))

            row = cursor.fetchone()

            if row:
                # Existing user, update info
                cursor.execute('''
                    UPDATE users
                    SET union_id = ?, openid = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (union_id, openid, row[0]))

                user = {
                    'id': row[0],
                    'union_id': row[1],
                    'membership_plan': row[2] or 'free',
                    'diagnostic_limit': row[3] or 2
                }
                is_new_user = False
                db_logger.info(f"Existing user found: {union_id[:10]}...")
            else:
                # New user, create record
                cursor.execute('''
                    INSERT INTO users (union_id, openid, membership_plan, diagnostic_limit, created_at)
                    VALUES (?, ?, 'free', 2, CURRENT_TIMESTAMP)
                ''', (union_id, openid))

                user = {
                    'id': cursor.lastrowid,
                    'union_id': union_id,
                    'membership_plan': 'free',
                    'diagnostic_limit': 2
                }
                is_new_user = True
                db_logger.info(f"New user created: {union_id[:10]}...")

            return user, is_new_user

        except Exception as e:
            db_logger.error(f"Error in get_or_create_user_by_unionid: {e}")
            # Return default user on error
            return {'id': 0, 'union_id': union_id, 'membership_plan': 'free', 'diagnostic_limit': 2}, True


def init_db():
    """Initialize the database with required tables"""
    db_logger.info(f"Initializing database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE,
            phone TEXT UNIQUE,
            password_hash TEXT,
            nickname TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db_logger.debug("Users table created or verified")

    # Create brands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db_logger.debug("Brands table created or verified")

    # Create test_records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_name TEXT NOT NULL,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_models_used TEXT, -- JSON string
            questions_used TEXT, -- JSON string
            overall_score REAL,
            total_tests INTEGER,
            results_summary BLOB, -- JSON string or compressed BLOB
            detailed_results BLOB, -- Full JSON results or compressed BLOB
            is_summary_compressed INTEGER DEFAULT 0,
            is_detailed_compressed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db_logger.debug("Test records table created or verified")

    # Create user_preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preference_key TEXT NOT NULL,
            preference_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, preference_key)
        )
    ''')
    db_logger.debug("User preferences table created or verified")

    # Create task statuses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            progress INTEGER DEFAULT 0,
            stage TEXT NOT NULL,
            status_text TEXT,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db_logger.debug("Task statuses table created or verified")

    # Create deep intelligence results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deep_intelligence_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            exposure_analysis TEXT, -- JSON string
            source_intelligence TEXT, -- JSON string
            evidence_chain TEXT, -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES task_statuses (task_id)
        )
    ''')
    db_logger.debug("Deep intelligence results table created or verified")

    conn.commit()
    conn.close()
    db_logger.info("Database initialization completed")

def save_test_record(user_openid, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results):
    """
    Save a test record to the database (修复版 + 加密支持 + 压缩优化)

    修复内容:
    1. ✅ 使用上下文管理器确保连接关闭
    2. ✅ 添加输入验证
    3. ✅ 使用 SafeDatabaseQuery 统一处理
    4. ✅ P0-3: 添加敏感数据加密支持
    5. ✅ P1: 大对象压缩存储（节省 70-80% 空间）
    """
    from .security.input_validator import validate_execution_id, validate_brand_name
    import gzip

    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(brand_name):
        raise ValueError("Invalid brand_name")

    db_logger.info(f"Saving test record for user: {user_openid}, brand: {brand_name}")

    # 使用上下文管理器确保连接关闭
    with get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Get user ID or create new user
            cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
            row = cursor.fetchone()

            if row:
                user_id = row[0]
                db_logger.debug(f"Found existing user with ID: {user_id}")
            else:
                # Create new user
                cursor.execute('INSERT INTO users (openid) VALUES (?)', (user_openid,))
                user_id = cursor.lastrowid
                db_logger.debug(f"Created new user with ID: {user_id}")

            # Convert lists/dicts to JSON strings
            ai_models_json = json.dumps(ai_models_used)
            questions_json = json.dumps(questions_used)
            results_summary_json = json.dumps(results_summary)
            detailed_results_json = json.dumps(detailed_results)

            # 【性能优化】大对象压缩存储
            compression_threshold = 10 * 1024  # 10KB
            is_detailed_compressed = 0
            is_summary_compressed = 0
            
            # 压缩 detailed_results
            detailed_results_bytes = detailed_results_json.encode('utf-8')
            original_detailed_size = len(detailed_results_bytes)
            if len(detailed_results_bytes) > compression_threshold:
                detailed_results_bytes = gzip.compress(detailed_results_bytes, compresslevel=6)
                is_detailed_compressed = 1
                record_compression_stats(original_detailed_size, len(detailed_results_bytes))
                db_logger.debug(f"detailed_results 压缩：{original_detailed_size} → {len(detailed_results_bytes)} 字节 ({(1 - len(detailed_results_bytes)/original_detailed_size)*100:.1f}% 压缩率)")
            else:
                _compression_metrics['total_uncompressed'] += 1

            # 压缩 results_summary
            results_summary_bytes = results_summary_json.encode('utf-8')
            original_summary_size = len(results_summary_bytes)
            if len(results_summary_bytes) > compression_threshold:
                results_summary_bytes = gzip.compress(results_summary_bytes, compresslevel=6)
                is_summary_compressed = 1
                record_compression_stats(original_summary_size, len(results_summary_bytes))
                db_logger.debug(f"results_summary 压缩：{original_summary_size} → {len(results_summary_bytes)} 字节 ({(1 - len(results_summary_bytes)/original_summary_size)*100:.1f}% 压缩率)")
            else:
                _compression_metrics['total_uncompressed'] += 1

            # P0-3: 加密敏感数据（在压缩后加密）
            if ENCRYPTION_ENABLED:
                try:
                    detailed_results_bytes = encrypt_field(detailed_results_bytes.decode('latin1'))
                    db_logger.debug("Encrypted detailed_results")
                except Exception as e:
                    db_logger.warning(f"Failed to encrypt detailed_results: {e}, saving unencrypted")

            # Insert test record
            cursor.execute('''
                INSERT INTO test_records
                (user_id, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results, is_summary_compressed, is_detailed_compressed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, brand_name, ai_models_json, questions_json, overall_score, total_tests, 
                  results_summary_bytes, detailed_results_bytes, is_summary_compressed, is_detailed_compressed))

            record_id = cursor.lastrowid
            conn.commit()
            
            db_logger.info(f"Test record saved successfully with ID: {record_id}, " +
                          f"detailed_compressed={is_detailed_compressed}, summary_compressed={is_summary_compressed}")

            return record_id
            
        except Exception as e:
            db_logger.error(f"Error saving test record: {e}")
            raise

def get_user_test_history(user_openid, limit=20, offset=0):
    """Get test history for a specific user (修复版 + 解压缩支持)"""
    import gzip
    
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")

    # Validate numeric inputs
    if not isinstance(limit, int) or not isinstance(offset, int) or limit < 0 or offset < 0:
        raise ValueError("Limit and offset must be non-negative integers")

    db_logger.info(f"Retrieving test history for user: {user_openid}, limit: {limit}, offset: {offset}")

    # 使用上下文管理器确保连接关闭
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get user ID
        cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
        row = cursor.fetchone()

        if not row:
            db_logger.debug(f"No user found with openid: {user_openid}")
            return []

        user_id = row[0]
        db_logger.debug(f"Found user with ID: {user_id}")

        # Get test records for this user
        cursor.execute('''
            SELECT id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, is_summary_compressed
            FROM test_records
            WHERE user_id = ?
            ORDER BY test_date DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))

        records_data = cursor.fetchall()

        records = []
        for row in records_data:
            # 【解压缩】处理 results_summary
            results_summary_bytes = row[7]
            is_compressed = row[8]
            
            if results_summary_bytes:
                try:
                    # 解压缩
                    if is_compressed:
                        results_summary_bytes = gzip.decompress(results_summary_bytes)
                        db_logger.debug(f"results_summary 解压缩：{len(row[7])} → {len(results_summary_bytes)} 字节")
                    
                    # 解密（如果启用了加密）
                    if ENCRYPTION_ENABLED and isinstance(results_summary_bytes, bytes):
                        try:
                            results_summary_bytes = decrypt_field(results_summary_bytes.decode('latin1'))
                        except Exception:
                            pass  # 可能未加密
                    
                    results_summary = json.loads(results_summary_bytes.decode('utf-8') if isinstance(results_summary_bytes, bytes) else results_summary_bytes)
                except Exception as e:
                    db_logger.warning(f"Failed to decompress/decrypt results_summary: {e}")
                    results_summary = {}
            else:
                results_summary = {}
            
            record = {
                'id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': results_summary
            }
            records.append(record)

    db_logger.info(f"Retrieved {len(records)} test records for user: {user_openid}")
    return records

def get_test_record_by_id(record_id):
    """
    Get a specific test record by ID (修复版 + 加密支持)
    
    P0-3: 添加敏感数据解密支持
    """
    # Validate inputs to prevent SQL injection
    if not isinstance(record_id, int) or record_id < 0:
        raise ValueError("Record ID must be a non-negative integer")

    db_logger.info(f"Retrieving test record with ID: {record_id}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        rows = safe_query.execute_query('''
            SELECT id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, detailed_results
            FROM test_records
            WHERE id = ?
        ''', (record_id,))

        if rows:
            row = rows[0]  # Get first row
            record = {
                'id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {},
                'detailed_results': json.loads(row[8]) if row[8] else []
            }
            
            # P0-3: 解密敏感数据
            if ENCRYPTION_ENABLED and record.get('detailed_results'):
                try:
                    # 尝试解密
                    record['detailed_results'] = decrypt_field(record['detailed_results'])
                    record['detailed_results'] = json.loads(record['detailed_results'])
                    db_logger.debug("Decrypted detailed_results")
                except Exception as e:
                    db_logger.warning(f"Failed to decrypt detailed_results: {e}, keeping original")
            
            db_logger.info(f"Successfully retrieved test record with ID: {record_id}")
        else:
            record = None
            db_logger.warning(f"No test record found with ID: {record_id}")

    return record


def save_user_preference(user_openid, preference_key, preference_value):
    """
    Save a user preference (修复版 + 加密支持)
    
    P0-3: 加密用户偏好数据
    """
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(preference_key):
        raise ValueError("Invalid preference_key")

    db_logger.info(f"Saving user preference for user {user_openid}, key: {preference_key}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # First, get or create user ID based on openid
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if user_rows:
            user_id = user_rows[0][0]
        else:
            # Create new user if not exists
            safe_query.execute_query('INSERT INTO users (openid) VALUES (?)', (user_openid,))
            # Get the new user ID
            user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))
            user_id = user_rows[0][0]

        # Convert preference value to JSON string if it's a dict/list
        if isinstance(preference_value, (dict, list)):
            pref_value_str = json.dumps(preference_value)
        else:
            pref_value_str = str(preference_value)
        
        # P0-3: 加密敏感数据
        if ENCRYPTION_ENABLED:
            try:
                pref_value_str = encrypt_field(pref_value_str)
                db_logger.debug(f"Encrypted preference value for key: {preference_key}")
            except Exception as e:
                db_logger.warning(f"Failed to encrypt preference {preference_key}: {e}")

        try:
            safe_query.execute_query('''
                INSERT OR REPLACE INTO user_preferences
                (user_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, preference_key, pref_value_str))

            db_logger.info(f"User preference saved successfully: {preference_key}")
        except Exception as e:
            db_logger.error(f"Error saving user preference: {e}")
            raise


def get_user_preference(user_openid, preference_key, default_value=None):
    """
    Get a user preference (修复版 + 加密支持)
    
    P0-3: 解密用户偏好数据
    """
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(preference_key):
        raise ValueError("Invalid preference_key")

    db_logger.info(f"Retrieving user preference for user {user_openid}, key: {preference_key}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # Get user ID based on openid
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if not user_rows:
            return default_value

        user_id = user_rows[0][0]

        rows = safe_query.execute_query('''
            SELECT preference_value
            FROM user_preferences
            WHERE user_id = ? AND preference_key = ?
        ''', (user_id, preference_key))

        if rows:
            pref_value_str = rows[0][0]
            # P0-3: 尝试解密
            if ENCRYPTION_ENABLED:
                try:
                    pref_value_str = decrypt_field(pref_value_str)
                    db_logger.debug(f"Decrypted preference value for key: {preference_key}")
                except Exception as e:
                    db_logger.warning(f"Failed to decrypt preference {preference_key}: {e}, keeping original")
            
            # Try to parse as JSON, if it fails return as string
            try:
                return json.loads(pref_value_str)
            except (json.JSONDecodeError, TypeError):
                return pref_value_str
        else:
            return default_value


def get_all_user_preferences(user_openid):
    """Get all preferences for a user (修复版)"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")

    db_logger.info(f"Retrieving all preferences for user {user_openid}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # Get user ID based on openid
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if not user_rows:
            return {}

        user_id = user_rows[0][0]

        rows = safe_query.execute_query('''
            SELECT preference_key, preference_value
            FROM user_preferences
            WHERE user_id = ?
        ''', (user_id,))

        preferences = {}
        for row in rows:
            key, value_str = row
            # Try to parse as JSON, if it fails return as string
            try:
                preferences[key] = json.loads(value_str)
            except (json.JSONDecodeError, TypeError):
                preferences[key] = value_str

    return preferences


# Verification code storage (in-memory for mock, should use Redis in production)
_verification_codes = {}


def save_verification_code(phone: str, code: str):
    """
    Save verification code for phone number
    
    Args:
        phone: Phone number
        code: Verification code
    """
    from datetime import timedelta
    from wechat_backend.logging_config import db_logger
    
    expiration_time = datetime.now() + timedelta(minutes=5)  # 5 minutes validity
    _verification_codes[phone] = {
        'code': code,
        'expires_at': expiration_time,
        'attempts': 0
    }
    db_logger.debug(f"Verification code saved for {phone}")


def verify_code(phone: str, code: str) -> bool:
    """
    Verify the code for a phone number
    
    Args:
        phone: Phone number
        code: Code to verify
        
    Returns:
        bool: True if code is valid, False otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    if phone not in _verification_codes:
        db_logger.warning(f"No verification code found for {phone}")
        return False
    
    stored = _verification_codes[phone]
    
    # Check expiration
    if datetime.now() > stored['expires_at']:
        del _verification_codes[phone]
        db_logger.warning(f"Verification code expired for {phone}")
        return False
    
    # Check attempts
    if stored['attempts'] >= 5:
        del _verification_codes[phone]
        db_logger.warning(f"Too many verification attempts for {phone}")
        return False
    
    # Verify code
    if stored['code'] != code:
        stored['attempts'] += 1
        db_logger.warning(f"Invalid verification code for {phone}, attempt {stored['attempts']}")
        return False
    
    # Code is valid, remove it
    del _verification_codes[phone]
    db_logger.info(f"Verification code validated for {phone}")
    return True


def create_user_with_phone(phone: str, password_hash: str, nickname: str = None) -> int:
    """
    Create a new user with phone and password
    
    Args:
        phone: Phone number
        password_hash: Hashed password
        nickname: Optional nickname
        
    Returns:
        int: User ID if successful, -1 if failed
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.security.sql_protection import SafeDatabaseQuery
    
    db_logger.info(f"Creating user with phone: {phone}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if phone already exists
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        existing = cursor.fetchone()
        if existing:
            db_logger.error(f"Phone number {phone} already registered")
            return -1
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (phone, password_hash, nickname, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (phone, password_hash, nickname))
        
        conn.commit()
        user_id = cursor.lastrowid
        db_logger.info(f"User created with ID: {user_id}")
        return user_id
        
    except Exception as e:
        db_logger.error(f"Error creating user: {e}")
        return -1
    finally:
        if conn:
            conn.close()


def get_user_by_phone(phone: str) -> dict:
    """
    Get user by phone number
    
    Args:
        phone: Phone number
        
    Returns:
        dict: User data or None if not found
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.security.sql_protection import SafeDatabaseQuery
    
    db_logger.info(f"Looking up user by phone: {phone}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, phone, password_hash, nickname, avatar_url, created_at
            FROM users
            WHERE phone = ?
        ''', (phone,))
        
        row = cursor.fetchone()
        if not row:
            db_logger.info(f"No user found for phone: {phone}")
            return None
        
        return {
            'id': row[0],
            'phone': row[1],
            'password_hash': row[2],
            'nickname': row[3],
            'avatar_url': row[4],
            'created_at': row[5]
        }
        
    except Exception as e:
        db_logger.error(f"Error getting user by phone: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int) -> dict:
    """
    Get user by ID
    
    Args:
        user_id: User ID
        
    Returns:
        dict: User data or None if not found
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info(f"Looking up user by ID: {user_id}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, phone, nickname, avatar_url, created_at, updated_at
            FROM users
            WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row:
            db_logger.info(f"No user found for ID: {user_id}")
            return None
        
        return {
            'id': row[0],
            'phone': row[1],
            'nickname': row[2],
            'avatar_url': row[3],
            'created_at': row[4],
            'updated_at': row[5]
        }
        
    except Exception as e:
        db_logger.error(f"Error getting user by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_user_profile(user_id: int, data: dict) -> bool:
    """
    Update user profile information
    
    Args:
        user_id: User ID
        data: Dictionary containing fields to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info(f"Updating profile for user {user_id}")
    
    # Allowed fields that can be updated
    allowed_fields = ['nickname', 'avatar_url']
    
    # Filter only allowed fields
    update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
    
    if not update_data:
        db_logger.warning("No valid fields to update")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build dynamic UPDATE statement
        fields = ', '.join([f"{field} = ?" for field in update_data.keys()])
        values = list(update_data.values())
        values.append(user_id)  # For WHERE clause
        
        query = f'''
            UPDATE users 
            SET {fields}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        
        cursor.execute(query, values)
        conn.commit()
        
        if cursor.rowcount > 0:
            db_logger.info(f"Updated {cursor.rowcount} row(s) for user {user_id}")
            return True
        else:
            db_logger.warning(f"No rows updated for user {user_id}")
            return False
            
    except Exception as e:
        db_logger.error(f"Error updating user profile: {e}")
        return False
    finally:
        if conn:
            conn.close()


# ============================================================================
# Data Sync Tables and Functions
# ============================================================================

def init_sync_db():
    """
    Initialize database tables for data sync
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info("Initializing sync database tables")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create user_data table for storing synced test results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            result_id TEXT UNIQUE NOT NULL,
            brand_name TEXT NOT NULL,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_models_used TEXT,  -- JSON string
            questions_used TEXT,  -- JSON string
            overall_score REAL,
            total_tests INTEGER,
            results_summary TEXT,  -- JSON string
            detailed_results TEXT,  -- Full JSON results
            sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db_logger.debug("user_data table created or verified")
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_user_id 
        ON user_data(user_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_result_id 
        ON user_data(result_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_sync_timestamp 
        ON user_data(sync_timestamp)
    ''')
    db_logger.debug("Indexes created for user_data table")
    
    conn.commit()
    conn.close()
    db_logger.info("Sync database initialization completed")


def save_user_data(user_id: int, data: dict) -> str:
    """
    Save or update user data (test result)
    
    Args:
        user_id: User ID
        data: Dictionary containing test result data
        
    Returns:
        str: Result ID if successful, None otherwise
    """
    from wechat_backend.logging_config import db_logger
    import json
    
    db_logger.info(f"Saving user data for user {user_id}")
    
    # Generate result ID if not provided
    result_id = data.get('result_id') or f"result_{user_id}_{int(datetime.now().timestamp())}"
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if result already exists
        cursor.execute('SELECT id FROM user_data WHERE result_id = ?', (result_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute('''
                UPDATE user_data 
                SET brand_name = ?,
                    ai_models_used = ?,
                    questions_used = ?,
                    overall_score = ?,
                    total_tests = ?,
                    results_summary = ?,
                    detailed_results = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    is_deleted = 0
                WHERE result_id = ?
            ''', (
                data.get('brand_name', ''),
                json.dumps(data.get('ai_models_used', [])),
                json.dumps(data.get('questions_used', [])),
                data.get('overall_score', 0),
                data.get('total_tests', 0),
                json.dumps(data.get('results_summary', {})),
                json.dumps(data.get('detailed_results', {})),
                result_id
            ))
            db_logger.info(f"Updated existing result {result_id} for user {user_id}")
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO user_data (
                    user_id, result_id, brand_name, ai_models_used, 
                    questions_used, overall_score, total_tests, 
                    results_summary, detailed_results
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                result_id,
                data.get('brand_name', ''),
                json.dumps(data.get('ai_models_used', [])),
                json.dumps(data.get('questions_used', [])),
                data.get('overall_score', 0),
                data.get('total_tests', 0),
                json.dumps(data.get('results_summary', {})),
                json.dumps(data.get('detailed_results', {}))
            ))
            db_logger.info(f"Inserted new result {result_id} for user {user_id}")
        
        conn.commit()
        return result_id
        
    except Exception as e:
        db_logger.error(f"Error saving user data: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_data(user_id: int, since_timestamp: str = None) -> list:
    """
    Get user data for sync (incremental sync support)
    
    Args:
        user_id: User ID
        since_timestamp: Only return data synced after this timestamp (for incremental sync)
        
    Returns:
        list: List of user data records
    """
    from wechat_backend.logging_config import db_logger
    import json
    
    db_logger.info(f"Getting user data for user {user_id} since {since_timestamp or 'beginning'}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if since_timestamp:
            cursor.execute('''
                SELECT result_id, brand_name, test_date, ai_models_used,
                       questions_used, overall_score, total_tests,
                       results_summary, detailed_results, sync_timestamp,
                       is_deleted
                FROM user_data
                WHERE user_id = ? 
                  AND sync_timestamp > ?
                  AND is_deleted = 0
                ORDER BY sync_timestamp ASC
            ''', (user_id, since_timestamp))
        else:
            cursor.execute('''
                SELECT result_id, brand_name, test_date, ai_models_used,
                       questions_used, overall_score, total_tests,
                       results_summary, detailed_results, sync_timestamp,
                       is_deleted
                FROM user_data
                WHERE user_id = ?
                  AND is_deleted = 0
                ORDER BY sync_timestamp ASC
            ''', (user_id,))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'result_id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {},
                'detailed_results': json.loads(row[8]) if row[8] else {},
                'sync_timestamp': row[9],
                'is_deleted': bool(row[10])
            })
        
        db_logger.info(f"Retrieved {len(results)} records for user {user_id}")
        return results
        
    except Exception as e:
        db_logger.error(f"Error getting user data: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_user_data(user_id: int, result_id: str) -> bool:
    """
    Soft delete user data (mark as deleted)
    
    Args:
        user_id: User ID
        result_id: Result ID to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info(f"Deleting result {result_id} for user {user_id}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_data 
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND result_id = ? AND is_deleted = 0
        ''', (user_id, result_id))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            db_logger.info(f"Deleted result {result_id} for user {user_id}")
            return True
        else:
            db_logger.warning(f"Result {result_id} not found for user {user_id}")
            return False
        
    except Exception as e:
        db_logger.error(f"Error deleting user data: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Refresh token storage (in-memory for mock, should use Redis in production)
_refresh_tokens = {}


def save_refresh_token(user_id: str, refresh_token: str):
    """
    Save refresh token for user
    
    Args:
        user_id: User ID
        refresh_token: Refresh token string
    """
    from datetime import timedelta
    from wechat_backend.logging_config import db_logger
    
    expiration_time = datetime.now() + timedelta(days=7)  # 7 days validity
    _refresh_tokens[refresh_token] = {
        'user_id': user_id,
        'expires_at': expiration_time,
        'created_at': datetime.now()
    }
    db_logger.debug(f"Refresh token saved for user {user_id}")


def verify_refresh_token(refresh_token: str) -> str:
    """
    Verify refresh token and return user_id if valid
    
    Args:
        refresh_token: Refresh token to verify
        
    Returns:
        str: User ID if valid, None otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    if refresh_token not in _refresh_tokens:
        db_logger.warning(f"Refresh token not found")
        return None
    
    stored = _refresh_tokens[refresh_token]
    
    # Check expiration
    if datetime.now() > stored['expires_at']:
        del _refresh_tokens[refresh_token]
        db_logger.warning(f"Refresh token expired for user {stored['user_id']}")
        return None
    
    db_logger.info(f"Refresh token validated for user {stored['user_id']}")
    return stored['user_id']


def revoke_refresh_token(refresh_token: str):
    """
    Revoke (logout) a refresh token
    
    Args:
        refresh_token: Refresh token to revoke
    """
    from wechat_backend.logging_config import db_logger
    
    if refresh_token in _refresh_tokens:
        del _refresh_tokens[refresh_token]
        db_logger.debug(f"Refresh token revoked")


def revoke_all_user_tokens(user_id: str):
    """
    Revoke all refresh tokens for a user (logout from all devices)
    
    Args:
        user_id: User ID
    """
    from wechat_backend.logging_config import db_logger
    
    tokens_to_revoke = [token for token, data in _refresh_tokens.items() 
                       if data['user_id'] == user_id]
    
    for token in tokens_to_revoke:
        del _refresh_tokens[token]
    
    db_logger.info(f"Revoked {len(tokens_to_revoke)} tokens for user {user_id}")


if __name__ == '__main__':
    # Initialize the database when this module is run directly
    init_db()
    print(f"Database initialized at {DB_PATH}")