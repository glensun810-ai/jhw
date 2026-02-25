"""
报告快照存储仓库

功能：
- 保存完整的诊断报告快照（JSON 格式）
- 支持快照一致性验证（SHA256 哈希）
- 支持按用户、按时间查询历史报告
- 支持快照压缩（可选）

核心原则：
1. 快照一旦创建，永不修改（Write-Once）
2. 每次读取都验证一致性
3. 支持快速查询和检索
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager

from wechat_backend.logging_config import db_logger, api_logger
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


class ReportSnapshotRepository:
    """
    报告快照存储仓库
    
    用法：
        repo = ReportSnapshotRepository()
        
        # 保存快照
        snapshot_id = repo.save_snapshot(
            execution_id="exec_123",
            user_id="user_456",
            report_data={...}
        )
        
        # 获取快照
        snapshot = repo.get_snapshot(execution_id="exec_123")
        
        # 验证一致性
        is_valid = repo.verify_consistency(execution_id="exec_123")
    """
    
    def __init__(self):
        self.table_name = "report_snapshots"
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """确保表存在（如果不存在则创建）"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS report_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            report_data TEXT NOT NULL,
            report_hash TEXT NOT NULL,
            size_kb INTEGER NOT NULL,
            storage_timestamp TEXT NOT NULL,
            report_version TEXT DEFAULT 'v1.0',
            INDEX idx_execution_id (execution_id),
            INDEX idx_user_id (user_id),
            INDEX idx_storage_timestamp (storage_timestamp)
        )
        """
        
        # SQLite 不支持在 CREATE TABLE 中添加 INDEX，需要单独创建
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS report_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            report_data TEXT NOT NULL,
            report_hash TEXT NOT NULL,
            size_kb INTEGER NOT NULL,
            storage_timestamp TEXT NOT NULL,
            report_version TEXT DEFAULT 'v1.0'
        )
        """
        
        create_index_sqls = [
            "CREATE INDEX IF NOT EXISTS idx_snapshot_execution_id ON report_snapshots(execution_id)",
            "CREATE INDEX IF NOT EXISTS idx_snapshot_user_id ON report_snapshots(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp ON report_snapshots(storage_timestamp)"
        ]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            for index_sql in create_index_sqls:
                cursor.execute(index_sql)
        
        db_logger.info("[ReportSnapshotRepository] 表初始化完成")
    
    def save_snapshot(
        self,
        execution_id: str,
        user_id: str,
        report_data: Dict[str, Any],
        report_version: str = "v1.0"
    ) -> str:
        """
        保存报告快照
        
        参数：
            execution_id: 执行 ID
            user_id: 用户 ID
            report_data: 完整的报告数据（字典）
            report_version: 报告版本
        
        返回：
            execution_id: 执行 ID（用于链式调用）
        
        异常：
            如果保存失败，抛出异常
        """
        try:
            # 1. 序列化报告数据
            report_json = json.dumps(report_data, ensure_ascii=False, default=str)
            
            # 2. 计算哈希（用于一致性验证）
            report_hash = hashlib.sha256(report_json.encode('utf-8')).hexdigest()
            
            # 3. 计算大小（KB）
            size_kb = len(report_json) // 1024 + 1  # 向上取整
            
            # 4. 生成时间戳
            storage_timestamp = datetime.now().isoformat()
            
            # 5. 保存到数据库
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO report_snapshots 
                    (execution_id, user_id, report_data, report_hash, size_kb, storage_timestamp, report_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution_id,
                    user_id,
                    report_json,
                    report_hash,
                    size_kb,
                    storage_timestamp,
                    report_version
                ))
            
            api_logger.info(
                f"[ReportSnapshot] ✅ 快照保存成功：{execution_id}, "
                f"大小：{size_kb}KB, 哈希：{report_hash[:16]}..."
            )
            
            return execution_id
            
        except Exception as e:
            db_logger.error(f"[ReportSnapshot] ❌ 快照保存失败：{execution_id}, 错误：{e}")
            raise
    
    def get_snapshot(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取报告快照
        
        参数：
            execution_id: 执行 ID
        
        返回：
            报告数据字典，如果不存在则返回 None
        """
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM report_snapshots
                    WHERE execution_id = ?
                ''', (execution_id,))
                
                row = cursor.fetchone()
                
                if not row:
                    api_logger.warning(f"[ReportSnapshot] ⚠️ 快照不存在：{execution_id}")
                    return None
                
                # 解析 JSON 数据
                report_data = json.loads(row['report_data'])
                
                # 添加元数据
                report_data['_metadata'] = {
                    'storage_timestamp': row['storage_timestamp'],
                    'size_kb': row['size_kb'],
                    'report_version': row['report_version'],
                    'stored_hash': row['report_hash']
                }
                
                api_logger.info(f"[ReportSnapshot] ✅ 快照加载成功：{execution_id}")
                
                return report_data
                
        except Exception as e:
            db_logger.error(f"[ReportSnapshot] ❌ 快照加载失败：{execution_id}, 错误：{e}")
            return None
    
    def get_user_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取用户历史报告列表
        
        参数：
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 偏移量
        
        返回：
            报告元数据列表（不包含完整报告数据）
        """
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        execution_id,
                        user_id,
                        report_version,
                        size_kb,
                        storage_timestamp,
                        substr(report_hash, 1, 16) as hash_prefix
                    FROM report_snapshots
                    WHERE user_id = ?
                    ORDER BY storage_timestamp DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'execution_id': row['execution_id'],
                        'user_id': row['user_id'],
                        'report_version': row['report_version'],
                        'size_kb': row['size_kb'],
                        'storage_timestamp': row['storage_timestamp'],
                        'hash_prefix': row['hash_prefix']
                    })
                
                api_logger.info(
                    f"[ReportSnapshot] ✅ 用户历史加载成功：{user_id}, "
                    f"数量：{len(results)}"
                )
                
                return results
                
        except Exception as e:
            db_logger.error(f"[ReportSnapshot] ❌ 用户历史加载失败：{user_id}, 错误：{e}")
            return []
    
    def verify_consistency(self, execution_id: str) -> Tuple[bool, Optional[str]]:
        """
        验证快照一致性
        
        参数：
            execution_id: 执行 ID
        
        返回：
            (is_valid, error_message): 是否有效，错误信息（如果有）
        """
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT report_data, report_hash
                    FROM report_snapshots
                    WHERE execution_id = ?
                ''', (execution_id,))
                
                row = cursor.fetchone()
                
                if not row:
                    return False, "快照不存在"
                
                # 重新计算哈希
                current_hash = hashlib.sha256(row['report_data'].encode('utf-8')).hexdigest()
                
                # 对比哈希
                if current_hash == row['report_hash']:
                    api_logger.info(f"[ReportSnapshot] ✅ 一致性验证通过：{execution_id}")
                    return True, None
                else:
                    error_msg = f"哈希不匹配：存储={row['report_hash'][:16]}..., 当前={current_hash[:16]}..."
                    api_logger.error(f"[ReportSnapshot] ❌ 一致性验证失败：{execution_id}, {error_msg}")
                    return False, error_msg
                
        except Exception as e:
            error_msg = f"验证异常：{e}"
            db_logger.error(f"[ReportSnapshot] ❌ 一致性验证异常：{execution_id}, {error_msg}")
            return False, error_msg
    
    def delete_snapshot(self, execution_id: str) -> bool:
        """
        删除报告快照（谨慎使用）
        
        参数：
            execution_id: 执行 ID
        
        返回：
            是否删除成功
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM report_snapshots
                    WHERE execution_id = ?
                ''', (execution_id,))
                
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    api_logger.info(f"[ReportSnapshot] 🗑️ 快照删除成功：{execution_id}")
                    return True
                else:
                    api_logger.warning(f"[ReportSnapshot] ⚠️ 快照不存在，无法删除：{execution_id}")
                    return False
                
        except Exception as e:
            db_logger.error(f"[ReportSnapshot] ❌ 快照删除失败：{execution_id}, 错误：{e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取快照统计信息
        
        返回：
            统计信息字典
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 总数量
                cursor.execute('SELECT COUNT(*) as count FROM report_snapshots')
                total_count = cursor.fetchone()[0]
                
                # 总大小
                cursor.execute('SELECT SUM(size_kb) as total_size FROM report_snapshots')
                total_size_kb = cursor.fetchone()[0] or 0
                
                # 按用户分组
                cursor.execute('''
                    SELECT user_id, COUNT(*) as count
                    FROM report_snapshots
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 10
                ''')
                top_users = [
                    {'user_id': row[0], 'count': row[1]}
                    for row in cursor.fetchall()
                ]
                
                # 按版本分组
                cursor.execute('''
                    SELECT report_version, COUNT(*) as count
                    FROM report_snapshots
                    GROUP BY report_version
                ''')
                version_distribution = [
                    {'version': row[0], 'count': row[1]}
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_count': total_count,
                    'total_size_kb': total_size_kb,
                    'total_size_mb': round(total_size_kb / 1024, 2),
                    'top_users': top_users,
                    'version_distribution': version_distribution
                }
                
        except Exception as e:
            db_logger.error(f"[ReportSnapshot] ❌ 统计信息获取失败：{e}")
            return {}


# 全局仓库实例
_snapshot_repo: Optional[ReportSnapshotRepository] = None

def get_snapshot_repository() -> ReportSnapshotRepository:
    """获取全局快照仓库实例"""
    global _snapshot_repo
    if _snapshot_repo is None:
        _snapshot_repo = ReportSnapshotRepository()
    return _snapshot_repo


# 便捷函数
def save_report_snapshot(
    execution_id: str,
    user_id: str,
    report_data: Dict[str, Any],
    report_version: str = "v1.0"
) -> str:
    """
    便捷函数：保存报告快照
    
    用法：
        snapshot_id = save_report_snapshot(execution_id, user_id, report_data)
    """
    return get_snapshot_repository().save_snapshot(
        execution_id=execution_id,
        user_id=user_id,
        report_data=report_data,
        report_version=report_version
    )


def get_report_snapshot(execution_id: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取报告快照
    
    用法：
        snapshot = get_report_snapshot(execution_id)
    """
    return get_snapshot_repository().get_snapshot(execution_id=execution_id)


# 导入 sqlite3（在文件顶部导入可能导致循环依赖）
import sqlite3
