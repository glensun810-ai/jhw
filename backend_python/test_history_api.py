#!/usr/bin/env python3
"""
P21 历史列表 API 测试脚本

测试整个 API 链路：
1. 后端 API 是否正常返回数据
2. 数据格式是否正确
3. 前端是否能正确解析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("P21 历史列表 API 测试")
print("=" * 70)

# 测试 1: 检查数据库
print("\n[测试 1] 检查数据库记录...")
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
total = cursor.fetchone()[0]
print(f"  数据库总记录数：{total}")

cursor.execute('SELECT DISTINCT user_id FROM diagnosis_reports')
user_ids = [row[0] for row in cursor.fetchall()]
print(f"  不同的 user_id: {user_ids}")

cursor.execute('''
    SELECT id, user_id, brand_name, status, created_at 
    FROM diagnosis_reports 
    ORDER BY created_at DESC 
    LIMIT 3
''')
rows = cursor.fetchall()
print(f"  最新 3 条记录:")
for row in rows:
    print(f"    ID={row[0]}, user_id='{row[1]}', brand='{row[2]}', status={row[3]}")

conn.close()

# 测试 2: 测试 Repository
print("\n[测试 2] 测试 Repository 查询...")
from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository

repo = DiagnosisReportRepository()
results = repo.get_user_history('anonymous', 100, 0)
print(f"  Repository 返回数量：{len(results)}")
if results:
    print(f"  第 1 条数据:")
    print(f"    id: {results[0].get('id')}")
    print(f"    brand_name: {results[0].get('brand_name')}")
    print(f"    execution_id: {results[0].get('execution_id')}")

# 测试 3: 测试 Service
print("\n[测试 3] 测试 Service 层...")
from wechat_backend.diagnosis_report_service import get_report_service

service = get_report_service()
result = service.get_user_history('anonymous', 1, 100)
print(f"  Service 返回 reports 数量：{len(result.get('reports', []))}")
print(f"  Service 返回 pagination: {result.get('pagination', {})}")

if result.get('reports'):
    print(f"  第 1 条报告:")
    report = result['reports'][0]
    for key in ['id', 'brand_name', 'execution_id', 'status']:
        print(f"    {key}: {report.get(key)}")

# 测试 4: 检查 API 路由注册
print("\n[测试 4] 检查 API 路由注册...")
with open('wechat_backend/views/diagnosis_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

if "@diagnosis_bp.route('/history'" in content:
    print("  ✅ /api/diagnosis/history 路由已定义")
else:
    print("  ❌ /api/diagnosis/history 路由未定义")

# 测试 5: 模拟前端请求格式
print("\n[测试 5] 模拟前端请求格式...")
print("  前端请求 URL: http://127.0.0.1:5001/api/diagnosis/history?user_id=anonymous&page=1&limit=100")
print("  预期返回格式:")
print("    {")
print("      'reports': [...],")
print("      'pagination': {...}")
print("    }")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n📋 下一步操作:")
print("1. 确保后端服务运行：cd backend_python && python run.py")
print("2. 在微信开发者工具中设置'不校验合法域名'")
print("3. 检查前端 API 地址是否正确（http://127.0.0.1:5001）")
print("4. 在小程序控制台查看网络请求日志")
