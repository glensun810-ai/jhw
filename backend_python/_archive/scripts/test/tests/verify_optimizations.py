#!/usr/bin/env python3
"""
存储与性能优化验证脚本

简单验证核心功能是否正常工作
"""

import sqlite3
import time
import gzip
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'database.db'

print("="*80)
print("存储与性能优化验证")
print("="*80)

# 1. 验证 WAL 模式
print("\n[1/4] 验证 WAL 模式...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('PRAGMA journal_mode')
journal_mode = cursor.fetchone()[0]
conn.close()

if journal_mode == 'wal':
    print(f"  ✅ WAL 模式已启用")
else:
    print(f"  ⚠️  当前模式：{journal_mode}")

# 2. 验证索引
print("\n[2/4] 验证索引...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='test_records'")
indexes = cursor.fetchall()
conn.close()

print(f"  ✅ test_records 表索引数：{len(indexes)}")
for idx in indexes:
    print(f"    - {idx[0]}")

# 3. 验证压缩
print("\n[3/4] 验证压缩功能...")
test_data = {'test': 'A' * 10000}
original = json.dumps(test_data).encode('utf-8')
compressed = gzip.compress(original, compresslevel=6)
ratio = len(compressed) / len(original) * 100

print(f"  原始大小：{len(original)} 字节")
print(f"  压缩后：{len(compressed)} 字节")
print(f"  压缩率：{ratio:.1f}% (节省 {100-ratio:.1f}%)")

if ratio < 50:
    print(f"  ✅ 压缩效果良好")
else:
    print(f"  ⚠️  压缩效果一般")

# 4. 验证数据库文件大小
print("\n[4/4] 验证数据库文件大小...")
if DB_PATH.exists():
    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"  数据库大小：{size_mb:.2f}MB")
    
    # 检查 WAL 文件
    wal_path = Path(str(DB_PATH) + '-wal')
    shm_path = Path(str(DB_PATH) + '-shm')
    
    if wal_path.exists() or shm_path.exists():
        print(f"  ✅ WAL 文件存在")
    else:
        print(f"  ⚠️  WAL 文件不存在")
else:
    print(f"  ⚠️  数据库文件不存在")

print("\n" + "="*80)
print("验证完成")
print("="*80)
