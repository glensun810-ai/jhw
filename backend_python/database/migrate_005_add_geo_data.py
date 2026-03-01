#!/usr/bin/env python3
"""
迁移脚本执行器：添加 geo_data 字段到 diagnosis_results 表
日期：2026-03-01
"""

import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'database.db'
MIGRATION_SQL = Path(__file__).parent / 'migrations' / '005_add_geo_data_field.sql'


def run_migration():
    """执行迁移脚本"""
    print(f"🔍 连接到数据库：{DB_PATH}")
    
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在：{DB_PATH}")
        return False
    
    if not MIGRATION_SQL.exists():
        print(f"❌ 迁移脚本不存在：{MIGRATION_SQL}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查 geo_data 字段是否已存在
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM PRAGMA_TABLE_INFO('diagnosis_results')
        WHERE name = 'geo_data'
    """)
    result = cursor.fetchone()
    
    if result['cnt'] > 0:
        print("✅ geo_data 字段已存在，无需迁移")
        conn.close()
        return True
    
    print("📝 开始执行迁移脚本...")
    
    # 读取并执行 SQL 脚本
    with open(MIGRATION_SQL, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 分割 SQL 语句并执行（跳过注释和空行）
    statements = []
    for line in sql_script.split(';'):
        line = line.strip()
        if line and not line.startswith('--'):
            statements.append(line)
    
    success = True
    for stmt in statements:
        try:
            # 跳过纯注释或验证查询
            if stmt.startswith('SELECT') and 'PRAGMA_TABLE_INFO' in stmt:
                continue
            if stmt.startswith('--'):
                continue
                
            cursor.execute(stmt)
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print(f"⚠️  字段已存在，跳过：{e}")
            else:
                print(f"❌ 执行失败：{e}")
                success = False
                break
    
    if success:
        conn.commit()
        print("✅ 迁移成功完成")
        
        # 验证
        cursor.execute("""
            SELECT name, type FROM PRAGMA_TABLE_INFO('diagnosis_results')
            WHERE name = 'geo_data'
        """)
        result = cursor.fetchone()
        if result:
            print(f"✅ 验证成功：geo_data ({result['type']}) 已添加")
    
    conn.close()
    return success


if __name__ == '__main__':
    success = run_migration()
    if success:
        print("\n✅ 迁移完成！")
    else:
        print("\n❌ 迁移失败，请检查日志")
        exit(1)
