#!/usr/bin/env python3
"""
P0 修复：数据库迁移脚本
添加 execution_id 列到 test_records 表
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'database.db'

def migrate():
    """执行数据库迁移"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    
    print("📋 检查数据库结构...")
    
    # 检查 execution_id 列是否存在
    cursor.execute('PRAGMA table_info(test_records)')
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'execution_id' in columns:
        print("✅ execution_id 列已存在")
    else:
        print("🔧 添加 execution_id 列...")
        try:
            cursor.execute('ALTER TABLE test_records ADD COLUMN execution_id TEXT')
            conn.commit()
            print("✅ execution_id 列添加成功")
        except Exception as e:
            print(f"❌ 添加列失败：{e}")
            return False
    
    # 检查索引是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_test_records_execution_id'")
    result = cursor.fetchone()
    
    if result:
        print("✅ idx_test_records_execution_id 索引已存在")
    else:
        print("🔧 创建 execution_id 索引...")
        try:
            cursor.execute('CREATE INDEX idx_test_records_execution_id ON test_records(execution_id)')
            conn.commit()
            print("✅ idx_test_records_execution_id 索引创建成功")
        except Exception as e:
            print(f"❌ 创建索引失败：{e}")
            return False
    
    # 验证查询性能
    print("\n📊 验证查询性能...")
    cursor.execute('''
    EXPLAIN QUERY PLAN
    SELECT results_summary, is_summary_compressed
    FROM test_records
    WHERE execution_id = ?
    ORDER BY id DESC
    LIMIT 1
    ''', ('test-123',))
    
    plan = cursor.fetchall()
    print("查询计划:")
    for row in plan:
        print(f"  {row}")
    
    # 检查是否使用了索引
    plan_str = str(plan)
    if 'USING INDEX' in plan_str or 'SEARCH' in plan_str:
        print("\n✅ 查询使用了索引，性能优化成功")
    else:
        print("\n⚠️  查询可能未使用索引，需要进一步分析")
    
    conn.close()
    print("\n✅ 迁移完成")
    return True

if __name__ == '__main__':
    print("="*60)
    print("P0 修复：数据库迁移")
    print("="*60)
    print()
    migrate()
