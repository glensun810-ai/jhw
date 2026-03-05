#!/usr/bin/env python3
"""
数据库迁移脚本：005_add_sentiment_column

添加 diagnosis_results.sentiment 字段

使用方法:
    cd /Users/sgl/PycharmProjects/PythonProject/backend_python
    python3 migrations/005_add_sentiment_column.py
"""

import sqlite3
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / 'database.db'


def migrate():
    """执行迁移"""
    print(f"[Migration 005] 开始迁移：{DB_PATH}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute('''
            PRAGMA table_info(diagnosis_results)
        ''')
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"[Migration 005] 当前字段列表：{columns}")
        
        if 'sentiment' in columns:
            print("[Migration 005] sentiment 字段已存在，跳过迁移")
            return True
        
        # 添加 sentiment 字段
        print("[Migration 005] 添加 sentiment 字段到 diagnosis_results 表")
        cursor.execute('''
            ALTER TABLE diagnosis_results 
            ADD COLUMN sentiment TEXT DEFAULT 'neutral'
        ''')
        
        conn.commit()
        
        # 验证字段已添加
        cursor.execute('''
            PRAGMA table_info(diagnosis_results)
        ''')
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'sentiment' in columns:
            print("[Migration 005] ✅ 迁移成功：sentiment 字段已添加")
            print(f"[Migration 005] 当前字段列表：{columns}")
            return True
        else:
            print("[Migration 005] ❌ 迁移失败：字段未添加成功")
            return False
            
    except Exception as e:
        print(f"[Migration 005] ❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
