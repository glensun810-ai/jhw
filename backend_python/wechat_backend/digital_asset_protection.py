"""
数字资产保护模块

核心原则：
1. AI 响应返回后 1 秒内持久化
2. 至少两份数据副本
3. 事务保护确保一致性
4. 定期备份确保可恢复

存储层级：
1. 内存层 - execution_store（实时访问）
2. 数据库层 - SQLite（主存储）
3. 文件层 - JSON 日志（审计追踪）
4. 备份层 - 定时备份（灾难恢复）
"""

import json
import os
import shutil
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.database_connection_pool import get_db_pool


# ==================== 配置 ====================

# 备份目录
BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data_backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

# 审计日志目录
AUDIT_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'audit_logs')
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)

# 保留天数
BACKUP_RETENTION_DAYS = 30
AUDIT_LOG_RETENTION_DAYS = 90


# ==================== 核心函数 ====================

@contextmanager
def transaction_context():
    """事务上下文管理器"""
    conn = get_db_pool().get_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')  # 立即获取写锁
        yield conn
        conn.execute('COMMIT')
    except Exception as e:
        conn.execute('ROLLBACK')
        db_logger.error(f"事务失败：{e}")
        raise
    finally:
        get_db_pool().return_connection(conn)


def calculate_checksum(data: Dict[str, Any]) -> str:
    """计算数据校验和"""
    # 排序键以确保一致性
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]


def save_diagnosis_result_to_db(
    execution_id: str,
    user_id: str,
    brand_name: str,
    results: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    保存诊断结果到数据库（带事务保护）
    
    参数:
    - execution_id: 执行 ID
    - user_id: 用户 ID
    - brand_name: 品牌名称
    - results: 结果列表
    - metadata: 元数据
    
    返回:
    - 记录 ID
    """
    try:
        # 计算校验和
        checksum = calculate_checksum({
            'execution_id': execution_id,
            'results': results
        })
        
        # 序列化数据
        results_json = json.dumps(results, ensure_ascii=False)
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        
        with transaction_context() as conn:
            cursor = conn.cursor()
            
            # 1. 保存到主表
            cursor.execute('''
                INSERT OR REPLACE INTO diagnosis_results (
                    execution_id, user_id, brand_name, results,
                    metadata, checksum, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_id,
                user_id,
                brand_name,
                results_json,
                metadata_json,
                checksum,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            record_id = cursor.lastrowid
            
            # 2. 保存到备份表（双重保护）
            cursor.execute('''
                INSERT INTO diagnosis_results_backup (
                    execution_id, user_id, brand_name, results,
                    checksum, backup_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                execution_id,
                user_id,
                brand_name,
                results_json,
                checksum,
                datetime.now().isoformat()
            ))
            
            db_logger.info(f"✅ 诊断结果已保存到数据库：{execution_id}, 记录 ID: {record_id}")
            return record_id
            
    except Exception as e:
        db_logger.error(f"❌ 数据库保存失败：{execution_id}, 错误：{e}")
        # 降级：保存到文件
        save_to_emergency_log(execution_id, results, metadata)
        raise


def save_to_emergency_log(
    execution_id: str,
    results: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    紧急日志保存（降级方案）
    
    当数据库不可用时，保存到文件
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"emergency_{execution_id}_{timestamp}.json"
        filepath = os.path.join(AUDIT_LOG_DIR, filename)
        
        data = {
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'metadata': metadata or {},
            'checksum': calculate_checksum({'execution_id': execution_id, 'results': results})
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        api_logger.warning(f"⚠️ 紧急日志已保存：{filepath}")
        return filepath
        
    except Exception as e:
        api_logger.error(f"❌ 紧急日志保存失败：{e}")
        return None


def get_diagnosis_result_by_execution_id(execution_id: str) -> Optional[Dict[str, Any]]:
    """
    根据执行 ID 获取诊断结果
    
    优先级：
    1. 主数据库
    2. 备份表
    3. 紧急日志文件
    """
    try:
        conn = get_db_pool().get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 尝试主表
        cursor.execute('''
            SELECT * FROM diagnosis_results
            WHERE execution_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (execution_id,))
        
        row = cursor.fetchone()
        get_db_pool().return_connection(conn)
        
        if row:
            result = dict(row)
            result['results'] = json.loads(result['results'])
            result['metadata'] = json.loads(result['metadata'])
            db_logger.info(f"✅ 从主表获取结果：{execution_id}")
            return result
        
        # 2. 尝试备份表
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM diagnosis_results_backup
            WHERE execution_id = ?
            ORDER BY backup_at DESC
            LIMIT 1
        ''', (execution_id,))
        
        row = cursor.fetchone()
        get_db_pool().return_connection(conn)
        
        if row:
            result = dict(row)
            result['results'] = json.loads(result['results'])
            db_logger.info(f"✅ 从备份表获取结果：{execution_id}")
            return result
        
        # 3. 尝试紧急日志
        for filename in os.listdir(AUDIT_LOG_DIR):
            if execution_id in filename and filename.endswith('.json'):
                filepath = os.path.join(AUDIT_LOG_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        db_logger.info(f"✅ 从紧急日志获取结果：{execution_id}")
                        return data
                except Exception:
                    continue
        
        db_logger.warning(f"⚠️ 未找到结果：{execution_id}")
        return None
        
    except Exception as e:
        db_logger.error(f"❌ 获取结果失败：{execution_id}, 错误：{e}")
        return None


def verify_data_integrity(execution_id: str, results: List[Dict[str, Any]]) -> bool:
    """
    验证数据完整性
    
    通过校验和验证数据是否被篡改
    """
    stored_result = get_diagnosis_result_by_execution_id(execution_id)
    
    if not stored_result:
        return False
    
    stored_checksum = stored_result.get('checksum', '')
    current_checksum = calculate_checksum({
        'execution_id': execution_id,
        'results': results
    })
    
    is_valid = stored_checksum == current_checksum
    
    if not is_valid:
        db_logger.error(f"❌ 数据完整性验证失败：{execution_id}")
        db_logger.error(f"   存储校验和：{stored_checksum}")
        db_logger.error(f"   当前校验和：{current_checksum}")
    
    return is_valid


# ==================== 备份机制 ====================

def create_daily_backup() -> Dict[str, Any]:
    """
    创建每日备份
    
    返回:
    - 备份统计信息
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    backup_stats = {
        'timestamp': timestamp,
        'database_backup': None,
        'json_export': None,
        'records_count': 0,
        'size_bytes': 0
    }
    
    try:
        # 1. SQLite 数据库备份
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'diagnosis.db')
        if os.path.exists(db_path):
            backup_db_path = os.path.join(BACKUP_DIR, f'db_{timestamp}.db')
            shutil.copy2(db_path, backup_db_path)
            backup_stats['database_backup'] = backup_db_path
            db_logger.info(f"✅ 数据库备份完成：{backup_db_path}")
        
        # 2. 导出所有结果为 JSON
        conn = get_db_pool().get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM diagnosis_results ORDER BY created_at DESC')
        rows = cursor.fetchall()
        get_db_pool().return_connection(conn)
        
        results = []
        for row in rows:
            item = dict(row)
            item['results'] = json.loads(item['results'])
            item['metadata'] = json.loads(item['metadata'])
            results.append(item)
        
        backup_stats['records_count'] = len(results)
        
        # 保存 JSON 导出
        json_path = os.path.join(BACKUP_DIR, f'results_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        backup_stats['json_export'] = json_path
        backup_stats['size_bytes'] = os.path.getsize(json_path)
        
        db_logger.info(f"✅ JSON 导出完成：{json_path}, 记录数：{len(results)}")
        
    except Exception as e:
        db_logger.error(f"❌ 备份失败：{e}")
        backup_stats['error'] = str(e)
    
    return backup_stats


def cleanup_old_backups(days: int = BACKUP_RETENTION_DAYS) -> Dict[str, Any]:
    """
    清理旧备份
    
    保留最近 N 天的备份
    """
    cleanup_stats = {
        'deleted_files': 0,
        'freed_bytes': 0,
        'errors': []
    }
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_filename = cutoff_date.strftime('%Y%m%d')
        
        for filename in os.listdir(BACKUP_DIR):
            # 从文件名提取日期
            if filename.startswith('db_') or filename.startswith('results_'):
                file_date = filename.split('_')[1].split('.')[0]
                if file_date < cutoff_filename:
                    filepath = os.path.join(BACKUP_DIR, filename)
                    try:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleanup_stats['deleted_files'] += 1
                        cleanup_stats['freed_bytes'] += file_size
                        db_logger.info(f"🗑️ 已删除旧备份：{filename}")
                    except Exception as e:
                        cleanup_stats['errors'].append(f"{filename}: {e}")
                        db_logger.error(f"❌ 删除备份失败：{filename}, 错误：{e}")
        
        db_logger.info(f"✅ 清理完成：删除 {cleanup_stats['deleted_files']} 个文件，释放 {cleanup_stats['freed_bytes']} 字节")
        
    except Exception as e:
        db_logger.error(f"❌ 清理失败：{e}")
        cleanup_stats['errors'].append(f"cleanup: {e}")
    
    return cleanup_stats


# ==================== 初始化 ====================

def init_database_tables():
    """初始化数据库表"""
    with transaction_context() as conn:
        cursor = conn.cursor()
        
        # 主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                results TEXT NOT NULL,
                metadata TEXT,
                checksum TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 备份表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_results_backup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                results TEXT NOT NULL,
                checksum TEXT NOT NULL,
                backup_at TEXT NOT NULL
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_execution_id
            ON diagnosis_results(execution_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON diagnosis_results(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_backup_execution_id
            ON diagnosis_results_backup(execution_id)
        ''')
        
        db_logger.info("✅ 数据库表初始化完成")


# 模块加载时初始化
try:
    init_database_tables()
except Exception as e:
    db_logger.error(f"⚠️ 数据库表初始化失败：{e}")
