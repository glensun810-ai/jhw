#!/usr/bin/env python3
"""快速验证数据库状态"""

import sqlite3
from pathlib import Path

DB_PATH = Path('backend_python/database.db')

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# 验证 should_stop_polling 字段
cursor.execute('PRAGMA table_info(diagnosis_reports)')
columns = [row[1] for row in cursor.fetchall()]
print('diagnosis_reports 表字段:', columns)
print()
print('should_stop_polling 字段存在:', 'should_stop_polling' in columns)
print()

# 验证 cache_entries 表
cursor.execute('SELECT COUNT(*) FROM cache_entries')
cache_count = cursor.fetchone()[0]
print('cache_entries 表记录数:', cache_count)
print()

# 验证 audit_logs 表
cursor.execute('SELECT COUNT(*) FROM audit_logs')
audit_count = cursor.fetchone()[0]
print('audit_logs 表记录数:', audit_count)
print()

conn.close()
print('✅ 数据库验证成功！')
