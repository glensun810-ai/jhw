"""
数据库索引修复脚本
问题：P0-002 数据库表缺少索引，导致查询性能慢
修复：添加关键查询字段的索引

使用方法:
    python3 apply_indexes.py
"""

import sqlite3
import os
from datetime import datetime

# 数据库路径（按优先级检查多个位置）
DB_PATHS = [
    os.path.join(os.path.dirname(__file__), 'database.db'),
    os.path.join(os.path.dirname(__file__), 'wechat_backend', 'database.db'),
    os.path.join(os.path.dirname(__file__), 'data', 'database.db'),
]

# 选择第一个存在的数据库路径
DB_PATH = None
for path in DB_PATHS:
    if os.path.exists(path):
        DB_PATH = path
        break

# 索引定义（根据实际表结构调整）
INDEXES = [
    # deep_intelligence_results 表索引 - 使用 task_id 而非 execution_id
    ("idx_deep_intelligence_task_id", "deep_intelligence_results", "task_id"),
    
    # task_statuses 表索引 - 使用 stage 而非 status
    ("idx_task_statuses_task_id", "task_statuses", "task_id"),
    ("idx_task_statuses_stage", "task_statuses", "stage"),
    ("idx_task_statuses_is_completed", "task_statuses", "is_completed"),
    ("idx_task_statuses_task_stage", "task_statuses", "task_id, stage"),
    
    # test_records 表索引
    ("idx_test_records_execution_id", "test_records", "execution_id"),
    ("idx_test_records_brand_name", "test_records", "brand_name"),
    ("idx_test_records_test_date", "test_records", "test_date DESC"),
]

def create_index(cursor, index_name, table_name, columns):
    """创建索引（如果不存在）"""
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
    try:
        cursor.execute(sql)
        print(f"✅ 索引创建成功：{index_name}")
        return True
    except Exception as e:
        print(f"❌ 索引创建失败：{index_name} - {e}")
        return False

def verify_indexes(cursor):
    """验证索引创建结果"""
    cursor.execute("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type='index' 
        AND tbl_name IN ('deep_intelligence_results', 'task_statuses', 'test_records')
        ORDER BY tbl_name, name
    """)
    
    indexes = cursor.fetchall()
    print(f"\n📊 数据库索引统计：共 {len(indexes)} 个索引")
    print("\n索引列表:")
    for name, tbl_name, sql in indexes:
        print(f"  - {tbl_name}.{name}")
    
    return len(indexes)

def main():
    """主函数"""
    print("=" * 60)
    print("数据库索引修复脚本")
    print("=" * 60)
    print(f"数据库路径：{DB_PATH}")
    print(f"开始时间：{datetime.now().isoformat()}")
    print()
    
    # 检查数据库文件是否存在
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在：{DB_PATH}")
        return
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建索引
    success_count = 0
    for index_name, table_name, columns in INDEXES:
        if create_index(cursor, index_name, table_name, columns):
            success_count += 1
    
    # 提交事务
    conn.commit()
    
    # 验证索引
    total_indexes = verify_indexes(cursor)
    
    # 关闭连接
    conn.close()
    
    # 输出总结
    print()
    print("=" * 60)
    print(f"修复完成!")
    print(f"  - 成功创建：{success_count}/{len(INDEXES)} 个索引")
    print(f"  - 总索引数：{total_indexes} 个")
    print(f"  - 结束时间：{datetime.now().isoformat()}")
    print("=" * 60)

if __name__ == '__main__':
    main()
