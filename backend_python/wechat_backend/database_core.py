"""
数据库核心模块 - 重构简化版

重构说明:
- 连接池管理 → database_connection_pool.py
- 数据仓库层 → database_repositories.py
- P2-6: 读写分离支持 → database_read_write_split.py

本文件保留:
- 数据库初始化
- 表结构定义
- 核心连接函数（支持读写分离）
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from wechat_backend.logging_config import db_logger
from wechat_backend.database_connection_pool import (
    get_db_pool,
    get_db_pool_metrics,
    reset_db_pool_metrics,
    close_db_pool,
    get_db_connection,
    return_db_connection,
)

DB_PATH = Path(__file__).parent.parent / 'database.db'

# ==================== 加密配置 ====================
# 默认关闭加密，确保系统能先跑起来
ENCRYPTION_ENABLED = False  # 数据库加密开关
ENCRYPTION_KEY = None       # 加密密钥（未启用）

# 增加别名兼容
DATABASE_ENCRYPTION = ENCRYPTION_ENABLED


# ==================== 数据库连接 ====================

def get_connection(operation_type: str = 'read') -> sqlite3.Connection:
    """
    获取数据库连接（从连接池，支持读写分离）
    
    Args:
        operation_type: 操作类型 ('read' 或 'write')
        
    Returns:
        数据库连接
    """
    return get_db_connection(operation_type)


def return_connection(conn: sqlite3.Connection, operation_type: str = 'read'):
    """
    归还数据库连接
    
    Args:
        conn: 数据库连接
        operation_type: 操作类型 ('read' 或 'write')
    """
    return_db_connection(conn, operation_type)


def close_db_connection():
    """关闭数据库连接池"""
    close_db_pool()


# ==================== 数据库初始化 ====================

def init_db():
    """初始化数据库表结构"""
    db_logger.info(f"初始化数据库于 {DB_PATH}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openid TEXT UNIQUE,
                unionid TEXT,
                phone TEXT,
                nickname TEXT,
                avatar_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 测试记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_openid TEXT,
                brand_name TEXT,
                ai_models_used TEXT,
                questions_used TEXT,
                overall_score REAL,
                total_tests INTEGER,
                results_summary TEXT,
                detailed_results TEXT,
                test_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 验证码表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                code TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                used INTEGER DEFAULT 0
            )
        ''')
        
        # 刷新令牌表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                refresh_token TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 同步结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                result_id TEXT UNIQUE,
                data_type TEXT,
                data TEXT,
                sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 品牌测试结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brand_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                brand_name TEXT,
                model_name TEXT,
                question TEXT,
                response TEXT,
                geo_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 审计日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # P2-2: 添加缺失的 cache_entries 表（缓存条目）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,
                cache_value TEXT,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        db_logger.info("数据库表结构初始化完成")
        
    except Exception as e:
        db_logger.error(f"数据库初始化失败：{e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def init_sync_db():
    """初始化同步数据库表（兼容旧接口）"""
    # sync_results 表已在 init_db 中创建
    db_logger.info("同步数据库表已存在")


# ==================== 监控指标 ====================

def get_database_metrics() -> Dict[str, Any]:
    """获取数据库监控指标"""
    return {
        'pool_metrics': get_db_pool_metrics(),
        'db_path': str(DB_PATH),
        'db_exists': DB_PATH.exists()
    }


def reset_database_metrics():
    """重置数据库监控指标"""
    reset_db_pool_metrics()


# ==================== 用户相关函数（兼容层） ====================

def get_or_create_user_by_unionid(
    union_id: str,
    openid: str
) -> Tuple[Optional[int], bool]:
    """
    根据 unionid 获取或创建用户
    
    返回：(user_id, is_new_user)
    """
    from wechat_backend.database_repositories import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 尝试获取现有用户
        cursor.execute('SELECT id FROM users WHERE unionid = ? OR openid = ?', (union_id, openid))
        row = cursor.fetchone()
        
        if row:
            return row['id'], False
        
        # 创建新用户
        cursor.execute('''
            INSERT INTO users (openid, unionid) VALUES (?, ?)
        ''', (openid, union_id))
        conn.commit()
        
        return cursor.lastrowid, True
