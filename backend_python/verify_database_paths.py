#!/usr/bin/env python3
"""
数据库路径一致性验证脚本

验证所有模块使用的数据库路径是否一致
"""

import sys
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).resolve().parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

print("=" * 70)
print("数据库路径一致性验证")
print("=" * 70)

# 1. database_core.py 的路径
from wechat_backend.database_core import DB_PATH as CORE_DB_PATH
print(f"\n1. database_core.py:")
print(f"   路径：{CORE_DB_PATH}")
print(f"   解析：{CORE_DB_PATH.resolve()}")
print(f"   存在：{CORE_DB_PATH.exists()}")

# 2. database_connection_pool.py 的路径
from wechat_backend.database_connection_pool import DB_PATH as POOL_DB_PATH
print(f"\n2. database_connection_pool.py:")
print(f"   路径：{POOL_DB_PATH}")
print(f"   解析：{POOL_DB_PATH.resolve()}")
print(f"   存在：{POOL_DB_PATH.exists()}")

# 3. query_optimizer.py 的路径
from wechat_backend.database.query_optimizer import DATABASE_PATH as OPTIMIZER_DB_PATH
print(f"\n3. query_optimizer.py:")
print(f"   路径：{OPTIMIZER_DB_PATH}")
print(f"   解析：{OPTIMIZER_DB_PATH.resolve()}")
print(f"   存在：{OPTIMIZER_DB_PATH.exists()}")

# 4. 验证一致性
print("\n" + "=" * 70)
print("路径一致性验证")
print("=" * 70)

core_resolved = str(CORE_DB_PATH.resolve())
pool_resolved = str(POOL_DB_PATH.resolve())
optimizer_resolved = str(OPTIMIZER_DB_PATH.resolve())

all_consistent = (core_resolved == pool_resolved == optimizer_resolved)

if all_consistent:
    print("✅ 所有模块的数据库路径一致！")
    print(f"   统一路径：{core_resolved}")
else:
    print("❌ 数据库路径不一致！")
    print(f"   database_core.py:        {core_resolved}")
    print(f"   database_connection_pool: {pool_resolved}")
    print(f"   query_optimizer.py:       {optimizer_resolved}")
    
    if core_resolved != pool_resolved:
        print("   ⚠️  database_core.py ≠ database_connection_pool.py")
    if core_resolved != optimizer_resolved:
        print("   ⚠️  database_core.py ≠ query_optimizer.py")
    if pool_resolved != optimizer_resolved:
        print("   ⚠️  database_connection_pool.py ≠ query_optimizer.py")

# 5. 文件状态
print("\n" + "=" * 70)
print("数据库文件状态")
print("=" * 70)

if CORE_DB_PATH.exists():
    stat = CORE_DB_PATH.stat()
    import time
    print(f"   文件大小：{stat.st_size} bytes")
    print(f"   最后修改：{time.ctime(stat.st_mtime)}")
    
    # 检查 WAL 文件
    wal_path = Path(str(CORE_DB_PATH) + '-wal')
    shm_path = Path(str(CORE_DB_PATH) + '-shm')
    
    if wal_path.exists():
        print(f"   WAL 文件：存在 ({wal_path.stat().st_size} bytes)")
    else:
        print(f"   WAL 文件：不存在")
        
    if shm_path.exists():
        print(f"   SHM 文件：存在 ({shm_path.stat().st_size} bytes)")
    else:
        print(f"   SHM 文件：不存在")
else:
    print("   ⚠️  数据库文件不存在，将在首次连接时创建")

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)

# 返回退出码
sys.exit(0 if all_consistent else 1)
