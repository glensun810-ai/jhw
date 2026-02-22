"""
数据库索引优化脚本

功能：
- 添加缺失的索引
- 优化查询性能
- 索引维护

根据技术重构方案 6.1 索引优化清单执行
"""

import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from wechat_backend.logging_config import db_logger
except ImportError:
    # 如果导入失败，使用简单的 logging
    import logging
    db_logger = logging.getLogger('db_logger')
    db_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[DB Index] %(message)s'))
    db_logger.addHandler(handler)

# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'database.db'


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')  # WAL 模式提升并发
    return conn


def create_index_if_not_exists(conn, index_name, table_name, columns, unique=False):
    """
    如果索引不存在则创建
    
    参数：
    - conn: 数据库连接
    - index_name: 索引名称
    - table_name: 表名
    - columns: 列名（可以是列表或逗号分隔的字符串）
    - unique: 是否唯一索引
    """
    if isinstance(columns, list):
        columns_str = ', '.join(columns)
    else:
        columns_str = columns
    
    unique_str = 'UNIQUE' if unique else ''
    
    sql = f"""
    CREATE {unique_str} INDEX IF NOT EXISTS {index_name}
    ON {table_name} ({columns_str})
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        db_logger.info(f'[DB Index] 索引创建成功：{index_name} on {table_name}({columns_str})')
        return True
    except Exception as e:
        db_logger.error(f'[DB Index] 索引创建失败：{index_name}, 错误：{e}')
        return False


def analyze_indexes():
    """
    分析并优化索引
    
    根据重构方案 6.1 索引优化清单：
    1. test_records: brand_name, created_at
    2. task_statuses: status, updated_at
    3. brand_test_results: brand_name, platform
    """
    conn = get_db_connection()
    
    db_logger.info('[DB Index] 开始索引优化...')
    
    created_count = 0
    total_count = 0
    
    # 1. test_records 表索引优化
    db_logger.info('[DB Index] 优化 test_records 表索引...')
    
    # 已有索引检查
    existing_indexes = get_existing_indexes(conn, 'test_records')
    
    # 添加 brand_name 索引（如果不存在）
    total_count += 1
    if 'idx_test_records_brand_name' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_test_records_brand_name', 'test_records', 'brand_name'):
            created_count += 1
    
    # 添加 created_at 索引（如果不存在）
    total_count += 1
    if 'idx_test_records_created_at' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_test_records_created_at', 'test_records', 'created_at'):
            created_count += 1
    
    # 添加组合索引 (brand_name, test_date) - 用于按品牌查询历史记录
    total_count += 1
    if 'idx_test_records_brand_date' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_test_records_brand_date', 'test_records', ['brand_name', 'test_date']):
            created_count += 1
    
    # 2. task_statuses 表索引优化
    db_logger.info('[DB Index] 优化 task_statuses 表索引...')
    
    existing_indexes = get_existing_indexes(conn, 'task_statuses')
    
    # 添加 status 索引
    total_count += 1
    if 'idx_task_statuses_status' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_task_statuses_status', 'task_statuses', 'status'):
            created_count += 1
    
    # 添加 updated_at 索引（用于轮询排序）
    total_count += 1
    if 'idx_task_statuses_updated_at' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_task_statuses_updated_at', 'task_statuses', 'updated_at'):
            created_count += 1
    
    # 添加组合索引 (is_completed, updated_at) - 用于查询未完成的任务
    total_count += 1
    if 'idx_task_statuses_completed_updated' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_task_statuses_completed_updated', 'task_statuses', ['is_completed', 'updated_at']):
            created_count += 1
    
    # 3. brand_test_results 表索引优化
    db_logger.info('[DB Index] 优化 brand_test_results 表索引...')
    
    existing_indexes = get_existing_indexes(conn, 'brand_test_results')
    
    # 添加 brand_name 索引（如果不存在）
    total_count += 1
    if 'idx_brand_test_results_brand_name' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_brand_test_results_brand_name', 'brand_test_results', 'brand_name'):
            created_count += 1
    
    # 添加 platform 相关索引（如果有 platform 字段）
    # 注意：需要检查字段是否存在
    
    # 4. users 表索引优化
    db_logger.info('[DB Index] 优化 users 表索引...')
    
    existing_indexes = get_existing_indexes(conn, 'users')
    
    # 添加 phone 索引（用于手机号登录）
    total_count += 1
    if 'idx_users_phone' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_users_phone', 'users', 'phone'):
            created_count += 1
    
    # 5. audit_logs 表索引优化
    db_logger.info('[DB Index] 优化 audit_logs 表索引...')
    
    existing_indexes = get_existing_indexes(conn, 'audit_logs')
    
    # 添加 user_id 索引（用于用户活动追踪）
    total_count += 1
    if 'idx_audit_logs_user_id' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_audit_logs_user_id', 'audit_logs', 'user_id'):
            created_count += 1
    
    # 添加组合索引 (created_at, action) - 用于按时间查询审计日志
    total_count += 1
    if 'idx_audit_logs_date_action' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_audit_logs_date_action', 'audit_logs', ['created_at', 'action']):
            created_count += 1
    
    # 6. sync_results 表索引优化
    db_logger.info('[DB Index] 优化 sync_results 表索引...')
    
    existing_indexes = get_existing_indexes(conn, 'sync_results')
    
    # 添加 brand_name 索引
    total_count += 1
    if 'idx_sync_results_brand_name' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_sync_results_brand_name', 'sync_results', 'brand_name'):
            created_count += 1
    
    # 添加组合索引 (user_id, sync_timestamp) - 用于增量同步
    total_count += 1
    if 'idx_sync_results_user_timestamp' not in existing_indexes:
        if create_index_if_not_exists(conn, 'idx_sync_results_user_timestamp', 'sync_results', ['user_id', 'sync_timestamp']):
            created_count += 1
    
    conn.close()
    
    db_logger.info(f'[DB Index] 索引优化完成：新增 {created_count}/{total_count} 个索引')
    
    return {
        'success': True,
        'created_count': created_count,
        'total_count': total_count
    }


def get_existing_indexes(conn, table_name):
    """
    获取表的所有现有索引
    
    参数：
    - conn: 数据库连接
    - table_name: 表名
    
    返回：
    - indexes: 索引名称列表
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}'")
    indexes = cursor.fetchall()
    return [idx[0] for idx in indexes]


def analyze_query_performance(conn, query):
    """
    分析查询性能
    
    参数：
    - conn: 数据库连接
    - query: SQL 查询
    
    返回：
    - plan: 查询计划
    """
    cursor = conn.cursor()
    cursor.execute(f'EXPLAIN QUERY PLAN {query}')
    plan = cursor.fetchall()
    return plan


def run_analyze():
    """
    运行 ANALYZE 命令更新统计信息
    """
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute('ANALYZE')
        conn.commit()
        db_logger.info('[DB Index] 统计信息已更新')
        return True
    except Exception as e:
        db_logger.error(f'[DB Index] 统计信息更新失败：{e}')
        return False
    finally:
        conn.close()


def get_index_usage_stats():
    """
    获取索引使用统计
    
    返回：
    - stats: 索引使用统计
    """
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # 获取所有索引的使用情况
        cursor.execute("""
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type='index'
            AND name NOT LIKE 'sqlite_%'
        """)
        
        indexes = cursor.fetchall()
        
        stats = []
        for idx in indexes:
            stats.append({
                'name': idx[0],
                'table': idx[1],
                'sql': idx[2]
            })
        
        return stats
    finally:
        conn.close()


# 主函数
if __name__ == '__main__':
    print('=== 数据库索引优化 ===')
    print('根据技术重构方案 6.1 索引优化清单执行...')
    
    result = analyze_indexes()
    
    print(f"\n索引优化结果:")
    print(f"  - 新增索引：{result['created_count']} 个")
    print(f"  - 总检查：{result['total_count']} 个")
    
    # 更新统计信息
    print('\n更新统计信息...')
    run_analyze()
    
    print('\n优化完成！')
