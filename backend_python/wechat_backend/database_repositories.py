"""
数据库仓库层模块

功能：
- 测试记录仓库
- 用户数据仓库
- 验证码仓库
- 同步数据仓库
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
from wechat_backend.logging_config import db_logger
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


# ==================== 测试记录仓库 ====================

def save_test_record(
    user_openid: str,
    brand_name: str,
    ai_models_used: str,
    questions_used: str,
    overall_score: float,
    total_tests: int,
    results_summary: str,
    detailed_results: str
) -> int:
    """保存测试记录"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO test_records (
                user_openid, brand_name, ai_models_used, questions_used,
                overall_score, total_tests, results_summary, detailed_results,
                test_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_openid, brand_name, ai_models_used, questions_used,
            overall_score, total_tests, results_summary, detailed_results,
            datetime.now().isoformat()
        ))
        return cursor.lastrowid


def get_user_test_history(
    user_openid: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """获取用户测试历史"""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM test_records
            WHERE user_openid = ?
            ORDER BY test_date DESC
            LIMIT ? OFFSET ?
        ''', (user_openid, limit, offset))
        return [dict(row) for row in cursor.fetchall()]


def get_test_record_by_id(record_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取测试记录"""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test_records WHERE id = ?', (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ==================== 用户数据仓库 ====================

def save_user_data(user_id: int, data: Dict[str, Any]) -> str:
    """保存用户数据"""
    result_id = f"user_{user_id}_{datetime.now().timestamp()}"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sync_results (user_id, result_id, data_type, data, sync_timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            result_id,
            'user_data',
            json.dumps(data, ensure_ascii=False),
            datetime.now().isoformat()
        ))
    
    return result_id


def get_user_data(
    user_id: int,
    since_timestamp: Optional[str] = None
) -> List[Dict[str, Any]]:
    """获取用户数据"""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if since_timestamp:
            cursor.execute('''
                SELECT * FROM sync_results
                WHERE user_id = ? AND sync_timestamp > ?
                ORDER BY sync_timestamp ASC
            ''', (user_id, since_timestamp))
        else:
            cursor.execute('''
                SELECT * FROM sync_results
                WHERE user_id = ?
                ORDER BY sync_timestamp ASC
            ''', (user_id,))
        
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item['data'] = json.loads(item['data'])
            results.append(item)
        
        return results


def delete_user_data(user_id: int, result_id: str) -> bool:
    """删除用户数据"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM sync_results
            WHERE user_id = ? AND result_id = ?
        ''', (user_id, result_id))
        return cursor.rowcount > 0


# ==================== 验证码仓库 ====================

def save_verification_code(phone: str, code: str):
    """保存验证码"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO verification_codes (phone, code, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (
            phone,
            code,
            datetime.now().isoformat(),
            (datetime.now().replace(minute=datetime.now().minute + 5)).isoformat()
        ))


def verify_code(phone: str, code: str) -> bool:
    """验证验证码"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM verification_codes
            WHERE phone = ? AND code = ? AND expires_at > ?
        ''', (phone, code, datetime.now().isoformat()))
        return cursor.fetchone() is not None


# ==================== Token 仓库 ====================

def save_refresh_token(user_id: str, refresh_token: str):
    """保存刷新令牌"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO refresh_tokens (user_id, refresh_token, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, refresh_token, datetime.now().isoformat()))


def verify_refresh_token(refresh_token: str) -> Optional[str]:
    """验证刷新令牌"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id FROM refresh_tokens
            WHERE refresh_token = ?
        ''', (refresh_token,))
        row = cursor.fetchone()
        return row['user_id'] if row else None


def revoke_refresh_token(refresh_token: str):
    """撤销刷新令牌"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM refresh_tokens
            WHERE refresh_token = ?
        ''', (refresh_token,))


def revoke_all_user_tokens(user_id: str):
    """撤销用户所有令牌"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM refresh_tokens
            WHERE user_id = ?
        ''', (user_id,))
