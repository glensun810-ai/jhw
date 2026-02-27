#!/usr/bin/env python3
"""
数据库 Schema 验证脚本

验证数据库表结构完整性，确保所有必要的表和索引都存在。
"""

import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / 'backend_python' / 'database.db'

# 期望的表列表
EXPECTED_TABLES = [
    'diagnosis_reports',
    'diagnosis_results',
    'diagnosis_snapshots',
    'task_statuses',
    'users',
    'user_roles',
    'roles',
    'permissions',
    'role_permissions',
    'user_preferences',
    'verification_codes',
    'refresh_tokens',
    'test_records',
    'brand_test_results',
    'brands',
    'diagnosis_analysis',
    'dimension_results',
    'sync_results',
    'sync_metadata',
    'report_snapshots',
    'permission_change_log',
    'deep_intelligence_results',
    'apscheduler_jobs',
    # 问题 2 和 3 的表
    'cache_entries',
    'audit_logs',
]

# 期望的索引列表
EXPECTED_INDEXES = [
    # diagnosis_reports
    ('idx_diagnosis_reports_execution_id', 'diagnosis_reports'),
    # cache_entries
    ('idx_cache_entries_cache_key', 'cache_entries'),
    ('idx_cache_entries_expires_at', 'cache_entries'),
    ('idx_cache_entries_created_at', 'cache_entries'),
    # audit_logs
    ('idx_audit_logs_user_id', 'audit_logs'),
    ('idx_audit_logs_action', 'audit_logs'),
    ('idx_audit_logs_timestamp', 'audit_logs'),
]

# 诊断 reports 表期望的列
DIAGNOSIS_REPORTS_COLUMNS = [
    'id',
    'execution_id',
    'user_id',
    'brand_name',
    'competitor_brands',
    'selected_models',
    'custom_questions',
    'status',
    'progress',
    'stage',
    'is_completed',
    'created_at',
    'updated_at',
    'completed_at',
    'data_schema_version',
    'server_version',
    'checksum',
    'should_stop_polling',  # 问题 1 修复的字段
]


def verify_database():
    """验证数据库结构"""
    print(f"📊 数据库路径：{DB_PATH}")
    print(f"数据库存在：{DB_PATH.exists()}\n")
    
    if not DB_PATH.exists():
        print("❌ 数据库文件不存在！")
        return False
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 验证表是否存在
    print("=" * 60)
    print("📋 验证表结构")
    print("=" * 60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    existing_tables = {row['name'] for row in cursor.fetchall()}
    
    missing_tables = []
    for table in EXPECTED_TABLES:
        if table in existing_tables:
            print(f"✅ 表 {table} 存在")
        else:
            print(f"❌ 表 {table} 缺失")
            missing_tables.append(table)
    
    # 2. 验证索引是否存在
    print("\n" + "=" * 60)
    print("📋 验证索引结构")
    print("=" * 60)
    
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
    existing_indexes = {(row['name'], row['tbl_name']) for row in cursor.fetchall()}
    
    missing_indexes = []
    for index_name, table_name in EXPECTED_INDEXES:
        if (index_name, table_name) in existing_indexes:
            print(f"✅ 索引 {index_name} 存在 (表：{table_name})")
        else:
            print(f"❌ 索引 {index_name} 缺失 (表：{table_name})")
            missing_indexes.append((index_name, table_name))
    
    # 3. 验证 diagnosis_reports 表结构
    print("\n" + "=" * 60)
    print("📋 验证 diagnosis_reports 表结构")
    print("=" * 60)
    
    cursor.execute(f"PRAGMA table_info(diagnosis_reports)")
    existing_columns = {row['name'] for row in cursor.fetchall()}
    
    missing_columns = []
    for column in DIAGNOSIS_REPORTS_COLUMNS:
        if column in existing_columns:
            print(f"✅ 列 {column} 存在")
        else:
            print(f"❌ 列 {column} 缺失")
            missing_columns.append(column)
    
    conn.close()
    
    # 4. 总结报告
    print("\n" + "=" * 60)
    print("📊 验证总结")
    print("=" * 60)
    
    issues = []
    
    if missing_tables:
        issues.append(f"缺失表：{', '.join(missing_tables)}")
    
    if missing_indexes:
        issues.append(f"缺失索引：{', '.join([f'{idx}({tbl})' for idx, tbl in missing_indexes])}")
    
    if missing_columns:
        issues.append(f"缺失列：{', '.join(missing_columns)}")
    
    if issues:
        print("\n❌ 发现问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ 数据库结构完整，所有表和索引都存在！")
        return True


def create_missing_indexes():
    """创建缺失的索引"""
    print("\n" + "=" * 60)
    print("🔧 创建缺失的索引")
    print("=" * 60)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 为 audit_logs 添加 action 索引（如果缺失）
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_audit_logs_action'")
    if not cursor.fetchone():
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
            print("✅ 创建索引 idx_audit_logs_action")
            conn.commit()
        except Exception as e:
            print(f"❌ 创建索引失败：{e}")
    else:
        print("✅ 索引 idx_audit_logs_action 已存在")
    
    conn.close()


if __name__ == '__main__':
    success = verify_database()
    
    if not success:
        create_missing_indexes()
        print("\n💡 请重新运行此脚本验证数据库结构")
    else:
        print("\n🎉 数据库验证通过！")
