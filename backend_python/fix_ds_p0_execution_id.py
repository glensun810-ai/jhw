#!/usr/bin/env python3
"""
DS-P0 修复：execution_id 索引修复和数据迁移

修复内容:
1. 删除旧的 json_extract 索引
2. 创建新的 execution_id 列索引
3. 为旧数据生成 execution_id
"""

import sqlite3
import uuid
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / 'database.db'

def fix_execution_id_index():
    """修复 execution_id 索引"""
    print("="*60)
    print("DS-P0-1: 修复 execution_id 索引")
    print("="*60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 删除旧索引
    print("📋 步骤 1: 删除旧索引...")
    cursor.execute("DROP INDEX IF EXISTS idx_test_records_execution_id")
    conn.commit()
    print("✅ 旧索引已删除")
    
    # 2. 创建新索引
    print("\n📋 步骤 2: 创建新索引...")
    cursor.execute("""
        CREATE INDEX idx_test_records_execution_id 
        ON test_records (execution_id)
    """)
    conn.commit()
    print("✅ 新索引已创建")
    
    # 3. 验证索引
    print("\n📋 步骤 3: 验证索引...")
    cursor.execute("""
        SELECT name, sql FROM sqlite_master 
        WHERE type='index' AND name='idx_test_records_execution_id'
    """)
    result = cursor.fetchone()
    if result:
        print(f"✅ 索引验证成功:")
        print(f"   名称：{result[0]}")
        print(f"   定义：{result[1]}")
        
        if 'execution_id' in result[1] and 'json_extract' not in result[1]:
            print("✅ 索引定义正确（直接使用 execution_id 列）")
        else:
            print("❌ 索引定义错误（仍使用 json_extract）")
    else:
        print("❌ 索引验证失败")
    
    # 4. 验证查询计划
    print("\n📋 步骤 4: 验证查询计划...")
    cursor.execute("""
        EXPLAIN QUERY PLAN 
        SELECT results_summary, is_summary_compressed
        FROM test_records
        WHERE execution_id = 'test-123'
    """)
    plan = cursor.fetchall()
    print("查询计划:")
    for row in plan:
        print(f"   {row}")
        
        if 'USING INDEX' in str(row) or 'SEARCH' in str(row):
            print("✅ 查询使用索引，性能优化成功")
        else:
            print("⚠️  查询可能未使用索引")
    
    conn.close()
    print("\n✅ DS-P0-1 修复完成")

def fix_old_data():
    """为旧数据生成 execution_id"""
    print("\n" + "="*60)
    print("DS-P0-2: 为旧数据生成 execution_id")
    print("="*60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 统计旧数据
    print("📋 步骤 1: 统计旧数据...")
    cursor.execute("""
        SELECT COUNT(*) FROM test_records 
        WHERE execution_id IS NULL
    """)
    null_count = cursor.fetchone()[0]
    print(f"   execution_id 为 NULL 的记录数：{null_count}")
    
    if null_count == 0:
        print("✅ 无需修复，所有记录已有 execution_id")
        conn.close()
        return
    
    # 2. 生成 execution_id
    print(f"\n📋 步骤 2: 为 {null_count} 条记录生成 execution_id...")
    cursor.execute("""
        SELECT id, brand_name, test_date 
        FROM test_records 
        WHERE execution_id IS NULL
    """)
    records = cursor.fetchall()
    
    updated_count = 0
    for record in records:
        # 基于 test_date 和品牌名称生成可重现的 execution_id
        timestamp = record[2] or datetime.now().isoformat()
        unique_id = f"{record[1]}-{timestamp}-{record[0]}"
        execution_id = f"migrated-{uuid.uuid5(uuid.NAMESPACE_DNS, unique_id)}"
        
        cursor.execute("""
            UPDATE test_records 
            SET execution_id = ? 
            WHERE id = ?
        """, (execution_id, record[0]))
        updated_count += 1
        
        if updated_count <= 5:  # 只显示前 5 条
            print(f"   ✅ Record {record[0]} ({record[1]}): {execution_id[:40]}...")
    
    conn.commit()
    print(f"\n✅ 已更新 {updated_count} 条记录")
    
    # 3. 验证修复
    print("\n📋 步骤 3: 验证修复...")
    cursor.execute("""
        SELECT COUNT(*) FROM test_records 
        WHERE execution_id IS NULL
    """)
    remaining_null = cursor.fetchone()[0]
    
    if remaining_null == 0:
        print("✅ 所有记录已有 execution_id")
    else:
        print(f"❌ 仍有 {remaining_null} 条记录 execution_id 为 NULL")
    
    # 4. 统计
    print("\n📋 步骤 4: 统计...")
    cursor.execute("SELECT COUNT(*) FROM test_records")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT execution_id, COUNT(*) as count
        FROM test_records
        GROUP BY execution_id
        ORDER BY count DESC
        LIMIT 5
    """)
    top_execution_ids = cursor.fetchall()
    
    print(f"   总记录数：{total}")
    print(f"   有 execution_id 的记录：{total - remaining_null} ({(total - remaining_null)/total*100:.1f}%)")
    print(f"   无 execution_id 的记录：{remaining_null} ({remaining_null/total*100:.1f}%)")
    
    if top_execution_ids:
        print(f"\n   Top 5 execution_id:")
        for row in top_execution_ids:
            print(f"     {row[0][:40]}...: {row[1]} 条")
    
    conn.close()
    print("\n✅ DS-P0-2 修复完成")

if __name__ == '__main__':
    print("="*60)
    print("DS-P0 修复：execution_id 索引和数据迁移")
    print("="*60)
    print()
    
    # 修复索引
    fix_execution_id_index()
    
    # 修复旧数据
    fix_old_data()
    
    print("\n" + "="*60)
    print("所有修复完成！")
    print("="*60)
    print("\n请执行以下验证命令:")
    print("  cd backend_python")
    print("  python3 -c \"import sqlite3; conn=sqlite3.connect('database.db'); print(conn.execute('SELECT sql FROM sqlite_master WHERE name=\"idx_test_records_execution_id\"').fetchone()[0])\"")
