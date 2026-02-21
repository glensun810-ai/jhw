#!/usr/bin/env python3
"""
数据同步持久化模块
将同步数据存储到 SQLite 数据库，避免服务重启数据丢失

功能:
1. 同步结果存储 (Sync Result Storage)
2. 增量同步支持 (Incremental Sync)
3. 数据合并冲突解决 (Conflict Resolution)
4. 自动清理过期数据 (Auto Cleanup)
"""

import sqlite3
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from wechat_backend.logging_config import api_logger

# ==================== 数据库配置 ====================

# 从配置管理器获取数据库路径（优先使用环境变量）
DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'database.db'
DATABASE_DIR = os.environ.get('DATABASE_DIR') or ''

# 如果设置了 DATABASE_DIR，则使用完整路径
if DATABASE_DIR:
    DATABASE_PATH = os.path.join(DATABASE_DIR, 'database.db')

# 同步数据保留天数配置
SYNC_RETENTION_DAYS = int(os.environ.get('SYNC_RETENTION_DAYS', '90'))

# ==================== 数据库表结构 ====================

CREATE_SYNC_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS sync_results (
    result_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    brand_name TEXT,
    ai_models_used TEXT,
    questions_used TEXT,
    overall_score REAL,
    total_tests INTEGER,
    results_summary TEXT,
    detailed_results TEXT,
    test_date TEXT,
    sync_timestamp TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
)
"""

CREATE_SYNC_RESULTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_user_id ON sync_results(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_timestamp ON sync_results(sync_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_test_date ON sync_results(test_date)",
    "CREATE INDEX IF NOT EXISTS idx_brand_name ON sync_results(brand_name)",
]

CREATE_SYNC_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS sync_metadata (
    user_id TEXT PRIMARY KEY,
    last_sync_timestamp TEXT,
    total_results INTEGER DEFAULT 0,
    storage_used_kb REAL DEFAULT 0,
    last_cleanup TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

# ==================== 同步存储管理器 ====================

class SyncStorageManager:
    """同步数据存储管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        self._init_tables()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_tables(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_SYNC_RESULTS_TABLE)
            cursor.execute(CREATE_SYNC_METADATA_TABLE)
            for index_sql in CREATE_SYNC_RESULTS_INDEXES:
                cursor.execute(index_sql)
            api_logger.info('同步数据存储表初始化完成')
    
    def save_result(self, user_id: str, result: Dict[str, Any]) -> bool:
        """
        保存同步结果
        
        Args:
            user_id: 用户 ID
            result: 结果数据
        
        Returns:
            是否保存成功
        """
        result_id = result.get('result_id')
        if not result_id:
            api_logger.error('保存失败：缺少 result_id')
            return False
        
        sync_timestamp = datetime.now().isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否已存在
                cursor.execute(
                    "SELECT result_id FROM sync_results WHERE result_id = ?",
                    (result_id,)
                )
                exists = cursor.fetchone() is not None
                
                if exists:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE sync_results SET
                            user_id = ?,
                            brand_name = ?,
                            ai_models_used = ?,
                            questions_used = ?,
                            overall_score = ?,
                            total_tests = ?,
                            results_summary = ?,
                            detailed_results = ?,
                            test_date = ?,
                            sync_timestamp = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE result_id = ?
                    """, (
                        user_id,
                        result.get('brand_name', ''),
                        json.dumps(result.get('ai_models_used', [])),
                        json.dumps(result.get('questions_used', [])),
                        result.get('overall_score', 0),
                        result.get('total_tests', 0),
                        json.dumps(result.get('results_summary', {})),
                        json.dumps(result.get('detailed_results', [])),
                        result.get('test_date', sync_timestamp),
                        sync_timestamp,
                        result_id
                    ))
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO sync_results (
                            result_id, user_id, brand_name, ai_models_used,
                            questions_used, overall_score, total_tests,
                            results_summary, detailed_results, test_date,
                            sync_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result_id,
                        user_id,
                        result.get('brand_name', ''),
                        json.dumps(result.get('ai_models_used', [])),
                        json.dumps(result.get('questions_used', [])),
                        result.get('overall_score', 0),
                        result.get('total_tests', 0),
                        json.dumps(result.get('results_summary', {})),
                        json.dumps(result.get('detailed_results', [])),
                        result.get('test_date', sync_timestamp),
                        sync_timestamp
                    ))
                
                # 更新元数据
                self._update_user_metadata(conn, user_id)
                
                api_logger.debug(f'同步结果已保存：result_id={result_id}, user_id={user_id}')
                return True
                
        except Exception as e:
            api_logger.error(f'保存同步结果失败：{e}', exc_info=True)
            return False
    
    def get_results(self, user_id: str, 
                    last_sync_timestamp: Optional[str] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户同步结果
        
        Args:
            user_id: 用户 ID
            last_sync_timestamp: 上次同步时间戳（增量获取）
            limit: 返回数量限制
        
        Returns:
            结果列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if last_sync_timestamp:
                    cursor.execute("""
                        SELECT * FROM sync_results
                        WHERE user_id = ? 
                          AND sync_timestamp > ?
                          AND is_deleted = 0
                        ORDER BY sync_timestamp DESC
                        LIMIT ?
                    """, (user_id, last_sync_timestamp, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM sync_results
                        WHERE user_id = ? 
                          AND is_deleted = 0
                        ORDER BY sync_timestamp DESC
                        LIMIT ?
                    """, (user_id, limit))
                
                rows = cursor.fetchall()
                results = []
                
                for row in rows:
                    result = dict(row)
                    # 解析 JSON 字段
                    for field in ['ai_models_used', 'questions_used', 'results_summary', 'detailed_results']:
                        try:
                            if result.get(field):
                                result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            result[field] = [] if field in ['ai_models_used', 'questions_used'] else {}
                    
                    results.append(result)
                
                return results
                
        except Exception as e:
            api_logger.error(f'获取同步结果失败：{e}', exc_info=True)
            return []
    
    def delete_result(self, user_id: str, result_id: str) -> bool:
        """
        删除同步结果（软删除）
        
        Args:
            user_id: 用户 ID
            result_id: 结果 ID
        
        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE sync_results
                    SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE result_id = ? AND user_id = ?
                """, (result_id, user_id))
                
                # 更新元数据
                self._update_user_metadata(conn, user_id)
                
                if cursor.rowcount > 0:
                    api_logger.debug(f'同步结果已删除：result_id={result_id}')
                    return True
                else:
                    api_logger.warning(f'未找到要删除的结果：result_id={result_id}')
                    return False
                    
        except Exception as e:
            api_logger.error(f'删除同步结果失败：{e}', exc_info=True)
            return False
    
    def _update_user_metadata(self, conn, user_id: str):
        """更新用户元数据"""
        cursor = conn.cursor()
        
        # 统计用户数据
        cursor.execute("""
            SELECT 
                COUNT(*) as total_results,
                SUM(LENGTH(detailed_results)) as total_size
            FROM sync_results
            WHERE user_id = ? AND is_deleted = 0
        """, (user_id,))
        
        stats = cursor.fetchone()
        total_results = stats['total_results'] or 0
        storage_used_kb = (stats['total_size'] or 0) / 1024
        
        # 更新或插入元数据
        cursor.execute("""
            INSERT OR REPLACE INTO sync_metadata (
                user_id, last_sync_timestamp, total_results, 
                storage_used_kb, updated_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id,
            datetime.now().isoformat(),
            total_results,
            storage_used_kb
        ))
    
    def get_user_metadata(self, user_id: str) -> Dict[str, Any]:
        """获取用户元数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM sync_metadata WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                else:
                    return {
                        'user_id': user_id,
                        'last_sync_timestamp': None,
                        'total_results': 0,
                        'storage_used_kb': 0,
                        'last_cleanup': None
                    }
        except Exception as e:
            api_logger.error(f'获取用户元数据失败：{e}', exc_info=True)
            return {}
    
    def cleanup_old_results(self, user_id: str, days: int = None) -> int:
        """
        清理过期结果
        
        Args:
            user_id: 用户 ID
            days: 保留天数（默认使用配置值）
        
        Returns:
            清理数量
        """
        try:
            retention_days = days or SYNC_RETENTION_DAYS
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM sync_results
                    WHERE user_id = ? 
                      AND test_date < ?
                      AND is_deleted = 0
                """, (user_id, cutoff_date))
                
                deleted_count = cursor.rowcount
                
                # 更新元数据
                self._update_user_metadata(conn, user_id)
                
                if deleted_count > 0:
                    api_logger.info(f'清理 {deleted_count} 条过期同步结果：user_id={user_id}')
                
                return deleted_count
                
        except Exception as e:
            api_logger.error(f'清理过期结果失败：{e}', exc_info=True)
            return 0
    
    def get_all_results_count(self) -> int:
        """获取所有结果数量"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM sync_results WHERE is_deleted = 0")
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            api_logger.error(f'获取结果数量失败：{e}', exc_info=True)
            return 0


# ==================== 全局实例 ====================

_sync_storage: Optional[SyncStorageManager] = None


def get_sync_storage() -> SyncStorageManager:
    """获取同步存储实例"""
    global _sync_storage
    if _sync_storage is None:
        _sync_storage = SyncStorageManager()
    return _sync_storage


def init_sync_storage() -> SyncStorageManager:
    """初始化同步存储"""
    global _sync_storage
    _sync_storage = SyncStorageManager()
    api_logger.info('同步存储初始化完成')
    return _sync_storage
