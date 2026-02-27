"""
数据库迁移脚本：003_add_should_stop_polling

添加 should_stop_polling 字段到 diagnosis_reports 表

执行方式：
    python migrations/003_add_should_stop_polling.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'database.db'


def upgrade():
    """执行迁移"""
    print(f"执行迁移：添加 should_stop_polling 字段")
    print(f"数据库路径：{DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(diagnosis_reports)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'should_stop_polling' not in columns:
            print("添加 should_stop_polling 字段...")
            cursor.execute('''
                ALTER TABLE diagnosis_reports 
                ADD COLUMN should_stop_polling BOOLEAN DEFAULT 0
            ''')
            print("✅ should_stop_polling 字段添加成功")
        else:
            print("ℹ️  should_stop_polling 字段已存在，跳过")
        
        conn.commit()
        print("\n✅ 迁移执行完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败：{e}")
        raise
    finally:
        conn.close()


def downgrade():
    """回滚迁移（可选）"""
    print("执行回滚：删除 should_stop_polling 字段")
    print(f"数据库路径：{DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # SQLite 不支持直接删除列，需要重建表
        print("⚠️  SQLite 不支持直接删除列，如需回滚请手动处理")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 回滚失败：{e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    upgrade()
