#!/usr/bin/env python3
"""
数据库迁移脚本 - 诊断表结构增强

迁移内容：
1. diagnosis_reports 表添加 error_message 列
2. diagnosis_reports 表添加 should_stop_polling 列
3. diagnosis_reports 表添加 is_completed 列
4. 创建 task_status 表（如果不存在）

用法：
    python3 backend_python/scripts/migrations/005_add_diagnosis_columns.py
"""

import sqlite3
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / 'backend_python'
sys.path.insert(0, str(backend_path))

# 使用绝对路径
DB_PATH = Path('/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db')


def get_connection():
    """获取数据库连接"""
    return sqlite3.connect(str(DB_PATH))


def column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def add_column_if_not_exists(cursor, table_name, column_name, column_def, default=None):
    """如果列不存在则添加"""
    if column_exists(cursor, table_name, column_name):
        print(f"  ⚠️  列 {table_name}.{column_name} 已存在，跳过")
        return False
    
    if default is not None:
        if isinstance(default, str):
            default_value = f"'{default}'"
        elif isinstance(default, bool):
            default_value = str(int(default))
        else:
            default_value = str(default)
        
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def} DEFAULT {default_value}"
    else:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
    
    cursor.execute(sql)
    print(f"  ✅ 添加列 {table_name}.{column_name}")
    return True


def migrate():
    """执行迁移"""
    print("\n" + "=" * 60)
    print("  数据库迁移 - 诊断表结构增强")
    print("=" * 60)
    print(f"\n数据库路径：{DB_PATH}")
    print(f"数据库文件存在：{DB_PATH.exists()}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    changes_made = 0
    
    try:
        # 启用外键
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # ========== 迁移 diagnosis_reports 表 ==========
        print("\n📋 迁移 diagnosis_reports 表...")
        
        # 添加 error_message 列
        if add_column_if_not_exists(
            cursor, 'diagnosis_reports', 'error_message',
            'TEXT', default=None
        ):
            changes_made += 1
        
        # 添加 should_stop_polling 列
        if add_column_if_not_exists(
            cursor, 'diagnosis_reports', 'should_stop_polling',
            'BOOLEAN DEFAULT 0',
            default=False
        ):
            changes_made += 1
        
        # 添加 is_completed 列
        if add_column_if_not_exists(
            cursor, 'diagnosis_reports', 'is_completed',
            'BOOLEAN DEFAULT 0',
            default=False
        ):
            changes_made += 1
        
        # 添加 updated_at 列
        if add_column_if_not_exists(
            cursor, 'diagnosis_reports', 'updated_at',
            'DATETIME', default=None
        ):
            changes_made += 1
        
        # ========== 创建 task_status 表 ==========
        print("\n📋 检查 task_status 表...")
        
        if not table_exists(cursor, 'task_status'):
            print("  📝 创建 task_status 表...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'initializing',
                    stage TEXT NOT NULL DEFAULT 'init',
                    progress INTEGER NOT NULL DEFAULT 0,
                    is_completed BOOLEAN DEFAULT 0,
                    should_stop_polling BOOLEAN DEFAULT 0,
                    error_message TEXT,
                    error_code TEXT,
                    results_summary TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("  ✅ task_status 表已创建")
            changes_made += 1
        else:
            print("  ⚠️  task_status 表已存在，跳过")
        
        # 为 task_status 表添加索引
        print("\n📋 创建索引...")
        
        indexes_to_create = [
            ("idx_task_status_execution", "task_status", "execution_id"),
            ("idx_task_status_user", "task_status", "user_id"),
            ("idx_task_status_created", "task_status", "created_at"),
        ]
        
        for index_name, table_name, column in indexes_to_create:
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column})')
                print(f"  ✅ 索引 {index_name} 已创建/存在")
            except Exception as e:
                print(f"  ⚠️  索引 {index_name} 创建失败：{e}")
        
        # ========== 提交更改 ==========
        conn.commit()
        
        print("\n" + "=" * 60)
        print(f"  迁移完成！共 {changes_made} 项更改")
        print("=" * 60)
        
        # 验证迁移结果
        print("\n📋 验证迁移结果...")
        
        cursor.execute("PRAGMA table_info(diagnosis_reports)")
        diag_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_columns = [
            'error_message',
            'should_stop_polling',
            'is_completed',
            'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in diag_columns]
        
        if missing_columns:
            print(f"  ❌ 验证失败：缺少列 {missing_columns}")
            return False
        else:
            print(f"  ✅ diagnosis_reports 表结构验证通过")
        
        # 验证 task_status 表
        if table_exists(cursor, 'task_status'):
            print(f"  ✅ task_status 表存在")
        else:
            print(f"  ❌ task_status 表不存在")
            return False
        
        print("\n✅ 所有迁移验证通过！")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
