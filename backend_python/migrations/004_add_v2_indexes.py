"""
数据库迁移脚本：004_add_v2_indexes

添加 v2 重构所需的索引

执行方式：
    python migrations/004_add_v2_indexes.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'database.db'

# 索引定义白名单（与安全规范保持一致）
INDEXES = {
    'idx_diagnosis_reports_execution_id': 
        'diagnosis_reports(execution_id)',
    'idx_diagnosis_reports_status': 
        'diagnosis_reports(status)',
    'idx_diagnosis_reports_user_id': 
        'diagnosis_reports(user_id)',
    'idx_diagnosis_reports_created_at': 
        'diagnosis_reports(created_at)',
    'idx_diagnosis_results_execution_id': 
        'diagnosis_results(execution_id)',
    'idx_api_call_logs_execution_id': 
        'api_call_logs(execution_id)',
    'idx_api_call_logs_request_timestamp': 
        'api_call_logs(request_timestamp)',
}


def upgrade():
    """
    执行迁移：添加索引
    
    这些索引用于优化 v2 重构后的查询性能
    """
    print("执行迁移：添加 v2 索引")
    print(f"数据库路径：{DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    indexes_created = 0
    indexes_skipped = 0

    try:
        for index_name, index_def in INDEXES.items():
            try:
                cursor.execute(
                    f'CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}'
                )
                indexes_created += 1
                print(f"  ✅ {index_name}")
            except sqlite3.OperationalError as e:
                if 'already exists' in str(e):
                    indexes_skipped += 1
                    print(f"  ℹ️  {index_name} (已存在)")
                else:
                    raise

        conn.commit()
        print(
            f"\n✅ 迁移执行完成！"
            f"新建：{indexes_created} 个索引，"
            f"跳过：{indexes_skipped} 个索引"
        )

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败：{e}")
        raise
    finally:
        conn.close()


def downgrade():
    """
    回滚迁移：删除索引
    
    注意：删除索引可能会影响查询性能
    """
    print("执行回滚：删除 v2 索引")
    print(f"数据库路径：{DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    indexes_dropped = 0

    try:
        for index_name in INDEXES.keys():
            try:
                cursor.execute(f'DROP INDEX IF EXISTS {index_name}')
                indexes_dropped += 1
                print(f"  ✅ {index_name}")
            except sqlite3.OperationalError as e:
                print(f"  ⚠️  {index_name}: {e}")

        conn.commit()
        print(f"\n✅ 回滚完成！删除：{indexes_dropped} 个索引")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 回滚失败：{e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    upgrade()
