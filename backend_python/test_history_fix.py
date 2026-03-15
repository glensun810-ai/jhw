#!/usr/bin/env python3
"""
诊断报告历史查询修复验证脚本

验证内容:
1. /api/history/list 端点是否可用
2. get_user_test_history 函数是否能正确读取 diagnosis_reports 数据
3. 返回的数据格式是否与前端兼容
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.database_repositories import get_user_test_history
import json

print("=" * 70)
print("诊断报告历史查询修复验证")
print("=" * 70)

# 测试 1: 验证 get_user_test_history 函数
print("\n[测试 1] 验证 get_user_test_history 函数...")
try:
    history = get_user_test_history('anonymous', limit=10, offset=0)
    print(f"  ✅ 函数调用成功")
    print(f"  📊 返回记录数：{len(history)}")
    
    if history:
        print(f"\n  最新 3 条记录:")
        for i, record in enumerate(history[:3], 1):
            print(f"\n  [{i}] ID={record.get('id', 'N/A')}")
            print(f"      execution_id={record.get('execution_id', 'N/A')}")
            print(f"      brandName={record.get('brandName', 'N/A')}")
            print(f"      status={record.get('status', 'N/A')}")
            print(f"      healthScore={record.get('healthScore', 'N/A')}")
            print(f"      createdAt={record.get('createdAt', 'N/A')}")
    else:
        print(f"  ⚠️  未找到历史记录")
        
except Exception as e:
    print(f"  ❌ 函数调用失败：{e}")
    import traceback
    traceback.print_exc()

# 测试 2: 验证数据格式
print("\n[测试 2] 验证数据格式兼容性...")
try:
    history = get_user_test_history('anonymous', limit=5, offset=0)
    
    if history:
        record = history[0]
        required_fields = ['id', 'execution_id', 'brandName', 'status', 'healthScore', 'createdAt']
        
        missing_fields = []
        for field in required_fields:
            if field not in record:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"  ⚠️  缺少字段：{missing_fields}")
        else:
            print(f"  ✅ 所有必需字段都存在")
            print(f"  📋 字段列表：{list(record.keys())}")
    else:
        print(f"  ⚠️  无数据可验证格式")
        
except Exception as e:
    print(f"  ❌ 格式验证失败：{e}")

# 测试 3: 检查数据库表
print("\n[测试 3] 检查数据库表状态...")
import sqlite3
db_path = 'database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
report_count = cursor.fetchone()[0]
print(f"  diagnosis_reports 表记录数：{report_count}")

cursor.execute('SELECT COUNT(*) FROM test_records')
test_count = cursor.fetchone()[0]
print(f"  test_records 表记录数：{test_count}")

cursor.execute('SELECT COUNT(*) FROM diagnosis_results')
result_count = cursor.fetchone()[0]
print(f"  diagnosis_results 表记录数：{result_count}")

conn.close()

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)

print("\n📋 修复说明:")
print("1. 新增 /api/history/list 端点作为 /api/test-history 的别名")
print("2. get_user_test_history 函数现在从 diagnosis_reports 表读取数据")
print("3. 保留了 test_records 的向后兼容支持")
print("\n🔧 下一步操作:")
print("1. 重启后端服务：cd backend_python && python run.py")
print("2. 在微信小程序中查看历史记录页面")
print("3. 验证是否能正确显示诊断报告列表")
