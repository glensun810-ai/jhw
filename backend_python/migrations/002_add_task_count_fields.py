"""
数据库迁移脚本：002_add_task_count_fields

添加 completed_count 和 total_count 字段到 task_statuses 表

执行方式：
    python migrations/002_add_task_count_fields.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'database.db'


def init_db_if_not_exists():
    """如果数据库不存在，先初始化"""
    if not DB_PATH.exists():
        print(f"数据库不存在，正在初始化：{DB_PATH}")
        
        # 导入初始化函数
        import sys
        sys.path.append(str(Path(__file__).parent.parent / 'wechat_backend'))
        from models import init_task_status_db
        
        init_task_status_db()
        print("✅ 数据库初始化完成")


def upgrade():
    """执行迁移"""
    print(f"执行迁移：添加 completed_count 和 total_count 字段")
    print(f"数据库路径：{DB_PATH}")
    
    # 先确保数据库已初始化
    init_db_if_not_exists()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(task_statuses)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'completed_count' not in columns:
            print("添加 completed_count 字段...")
            cursor.execute('''
                ALTER TABLE task_statuses 
                ADD COLUMN completed_count INTEGER DEFAULT 0
            ''')
            print("✅ completed_count 字段添加成功")
        else:
            print("ℹ️  completed_count 字段已存在，跳过")
        
        if 'total_count' not in columns:
            print("添加 total_count 字段...")
            cursor.execute('''
                ALTER TABLE task_statuses 
                ADD COLUMN total_count INTEGER DEFAULT 0
            ''')
            print("✅ total_count 字段添加成功")
        else:
            print("ℹ️  total_count 字段已存在，跳过")
        
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
    print("执行回滚：删除 completed_count 和 total_count 字段")
    print(f"数据库路径：{DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # SQLite 不支持直接删除列，需要重建表
        # 这里仅作为记录，实际使用时请谨慎
        print("⚠️  SQLite 不支持直接删除列，如需回滚请手动处理")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 回滚失败：{e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    upgrade()
