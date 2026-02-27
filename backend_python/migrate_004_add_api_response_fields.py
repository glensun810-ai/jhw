#!/usr/bin/env python3
"""
数据库迁移脚本：添加完整的 API 响应字段

执行 Migration 004，为 diagnosis_results 表添加完整的 API 响应存储字段。

符合重构规范：
- 规则 7.1.1: 向后兼容
- 规则 7.2.1: 提供迁移脚本
- 规则 7.3.1: 添加必要索引

使用方法:
    python3 migrate_004_add_api_response_fields.py

作者：系统架构组
日期：2026-02-27
版本：v2.0.0
"""

import sqlite3
import os
import sys
from datetime import datetime

# 数据库路径
DB_PATH = os.path.join(
    os.path.dirname(__file__),
    'database.db'
)

# 迁移 SQL 文件路径
MIGRATION_SQL = os.path.join(
    os.path.dirname(__file__),
    'wechat_backend',
    'database',
    'migrations',
    '004_add_complete_api_response_fields.sql'
)


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_migration_status():
    """检查迁移状态"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查 migration 记录表
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='migration_history'
    ''')
    
    if not cursor.fetchone():
        print("⚠️  migration_history 表不存在，创建中...")
        cursor.execute('''
            CREATE TABLE migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL
            )
        ''')
        conn.commit()
    
    # 检查是否已执行此迁移
    cursor.execute('''
        SELECT * FROM migration_history 
        WHERE migration_name = '004_add_complete_api_response_fields'
        ORDER BY applied_at DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    if row:
        if row['success']:
            print(f"✅ 迁移已执行：{row['applied_at']}")
            return True
        else:
            print(f"⚠️  迁移曾失败：{row['applied_at']}")
            return False
    
    conn.close()
    return False


def execute_migration():
    """执行迁移"""
    print("=" * 60)
    print("开始执行 Migration 004: 添加完整的 API 响应字段")
    print("=" * 60)
    print()
    
    # 检查是否已执行
    if check_migration_status():
        print("✅ 迁移已完成，无需重复执行")
        return True
    
    # 读取 SQL 文件
    if not os.path.exists(MIGRATION_SQL):
        print(f"❌ SQL 文件不存在：{MIGRATION_SQL}")
        return False
    
    with open(MIGRATION_SQL, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 分割 SQL 语句（按分号分隔，忽略注释）
        statements = []
        for line in sql_content.split(';'):
            line = line.strip()
            if line and not line.startswith('--'):
                statements.append(line)
        
        print(f"📋 检测到 {len(statements)} 个 SQL 语句")
        print()
        
        # 执行每个语句
        for i, stmt in enumerate(statements, 1):
            if stmt.strip().startswith('--'):
                continue
                
            print(f"[{i}/{len(statements)}] 执行：{stmt[:60]}...")
            cursor.execute(stmt)
        
        # 记录迁移历史
        cursor.execute('''
            INSERT INTO migration_history (migration_name, success)
            VALUES (?, ?)
        ''', ('004_add_complete_api_response_fields', True))
        
        conn.commit()
        
        print()
        print("=" * 60)
        print("✅ 迁移成功完成！")
        print("=" * 60)
        
        # 验证迁移结果
        verify_migration(conn)
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print()
        print("=" * 60)
        print(f"❌ 迁移失败：{e}")
        print("=" * 60)
        
        # 记录失败
        try:
            cursor.execute('''
                INSERT INTO migration_history (migration_name, success)
                VALUES (?, ?)
            ''', ('004_add_complete_api_response_fields', False))
            conn.commit()
        except:
            pass
        
        conn.close()
        return False


def verify_migration(conn):
    """验证迁移结果"""
    print()
    print("📋 验证迁移结果...")
    print()
    
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("PRAGMA table_info(diagnosis_results)")
    columns = cursor.fetchall()
    
    print("✅ diagnosis_results 表结构:")
    new_columns = [
        'raw_response', 'response_metadata',
        'tokens_used', 'prompt_tokens', 'completion_tokens', 'cached_tokens',
        'finish_reason', 'request_id', 'model_version', 'reasoning_content',
        'api_endpoint', 'service_tier', 'retry_count', 'is_fallback',
        'updated_at'
    ]
    
    existing_columns = [col['name'] for col in columns]
    
    for col in new_columns:
        if col in existing_columns:
            print(f"   ✅ {col}")
        else:
            print(f"   ❌ {col} (缺失)")
    
    # 检查索引
    cursor.execute("PRAGMA index_list(diagnosis_results)")
    indexes = cursor.fetchall()
    index_names = [idx['name'] for idx in indexes]
    
    print()
    print("✅ 索引检查:")
    new_indexes = [
        'idx_results_created_at',
        'idx_results_model',
        'idx_results_status',
        'idx_results_execution_status'
    ]
    
    for idx in new_indexes:
        if idx in index_names:
            print(f"   ✅ {idx}")
        else:
            print(f"   ⚠️  {idx} (未找到，可能已存在同名索引)")
    
    # 统计记录数
    cursor.execute("SELECT COUNT(*) as count FROM diagnosis_results")
    count = cursor.fetchone()['count']
    print()
    print(f"📊 当前诊断结果记录数：{count}")


def rollback_migration():
    """回滚迁移（警告：会丢失数据）"""
    print()
    print("⚠️  警告：回滚迁移会丢失新字段的数据！")
    print("是否继续？(y/N): ", end='')
    
    response = input().strip().lower()
    if response != 'y':
        print("已取消回滚")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # SQLite 不支持 DROP COLUMN，需要重建表
        print("正在备份数据...")
        cursor.execute("CREATE TABLE diagnosis_results_backup AS SELECT * FROM diagnosis_results")
        
        print("正在重建表结构...")
        # 这里需要手动编写原表结构的 CREATE TABLE
        # 为安全起见，建议手动执行回滚
        
        print("✅ 数据已备份到 diagnosis_results_backup")
        print("⚠️  完整回滚需要手动执行，请参考 migration SQL 文件中的降级说明")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ 回滚失败：{e}")
        conn.close()


def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'rollback':
            rollback_migration()
            return
        elif sys.argv[1] == 'verify':
            conn = get_connection()
            verify_migration(conn)
            conn.close()
            return
    
    # 执行迁移
    success = execute_migration()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
