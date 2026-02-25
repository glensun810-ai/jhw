#!/usr/bin/env python3
"""
数据库健康检查脚本
"""

import sqlite3

print('='*60)
print('数据库健康检查')
print('='*60)

# 连接数据库
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# 获取所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f'\n数据库表数量：{len(tables)}')
print('数据库表列表:')
for table in tables:
    print(f'  - {table[0]}')

# 检查关键表是否存在
critical_tables = [
    'test_records',
    'task_statuses',
    'deep_intelligence_results',
    'brand_test_results',
    'users',
    'sync_results'
]

print('\n关键表检查:')
for table in critical_tables:
    exists = any(t[0] == table for t in tables)
    if exists:
        print(f'  ✅ {table}')
    else:
        print(f'  ❌ {table} (缺失)')

# 获取所有索引
cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name")
indexes = cursor.fetchall()

print(f'\n索引数量：{len(indexes)}')
print('索引列表:')
for index in indexes:
    print(f'  - {index[0]} on {index[1]}')

# 检查缺失的索引（这些表可能不存在，是预期的）
print('\n缺失索引检查 (非关键):')
for table in ['audit_logs', 'cache_entries']:
    exists = any(t[0] == table for t in tables)
    if not exists:
        print(f'  ℹ️  {table} 表不存在 (非关键，可忽略)')

conn.close()

print('\n' + '='*60)
print('数据库检查完成')
print('='*60)
