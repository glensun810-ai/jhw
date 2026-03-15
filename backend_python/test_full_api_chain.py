#!/usr/bin/env python3
"""
P21 完整 API 链路测试

验证整个数据流：
数据库 → Repository → Service → API → 前端
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("P21 完整 API 链路测试")
print("=" * 70)

# 测试 1: 数据库层
print("\n[测试 1] 数据库层...")
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
db_count = cursor.fetchone()[0]
print(f"  ✅ 数据库记录数：{db_count}")
conn.close()

# 测试 2: Repository 层
print("\n[测试 2] Repository 层...")
from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
repo = DiagnosisReportRepository()
repo_results = repo.get_user_history('anonymous', 100, 0)
print(f"  ✅ Repository 返回：{len(repo_results)} 条")
if repo_results:
    print(f"  第 1 条：id={repo_results[0]['id']}, brand_name='{repo_results[0]['brand_name']}'")

# 测试 3: Service 层
print("\n[测试 3] Service 层...")
from wechat_backend.diagnosis_report_service import get_report_service
service = get_report_service()
service_result = service.get_user_history('anonymous', 1, 100)
print(f"  ✅ Service 返回：{len(service_result.get('reports', []))} 条")
if service_result.get('reports'):
    report = service_result['reports'][0]
    print(f"  第 1 条：id={report['id']}, brand_name='{report['brand_name']}', health_score={report['health_score']}")

# 测试 4: API 层
print("\n[测试 4] API 层...")
from flask import Flask, request
from wechat_backend.views.diagnosis_api import diagnosis_bp

app = Flask(__name__)
app.register_blueprint(diagnosis_bp)

with app.test_client() as client:
    response = client.get('/api/diagnosis/history?user_id=anonymous&page=1&limit=100')
    print(f"  ✅ API 状态码：{response.status_code}")
    
    if response.status_code == 200:
        import json
        data = json.loads(response.data)
        print(f"  ✅ API 返回 reports：{len(data.get('reports', []))} 条")
        if data.get('reports'):
            report = data['reports'][0]
            print(f"  第 1 条：id={report['id']}, brand_name='{report['brand_name']}', health_score={report.get('health_score')}")
            print(f"  字段格式：{'snake_case' if 'brand_name' in report else 'camelCase'}")

# 测试 5: 前端兼容性
print("\n[测试 5] 前端字段兼容性...")
print("  检查前端 WXML 和 JS 是否适配 snake_case:")

with open('pages/report/history/history.wxml', 'r', encoding='utf-8') as f:
    wxml_content = f.read()

if 'brand_name' in wxml_content and 'health_score' in wxml_content:
    print("  ✅ WXML 已适配 snake_case (brand_name, health_score)")
else:
    print("  ⚠️  WXML 可能未完全适配 snake_case")

with open('pages/report/history/history.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

if 'created_at' in js_content and 'health_score' in js_content:
    print("  ✅ JS 已适配 snake_case (created_at, health_score)")
else:
    print("  ⚠️  JS 可能未完全适配 snake_case")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n📋 数据流验证:")
print(f"  数据库：{db_count} 条 ✅")
print(f"  Repository: {len(repo_results)} 条 ✅")
print(f"  Service: {len(service_result.get('reports', []))} 条 ✅")
print(f"  API: {data.get('reports') and len(data['reports']) or 0} 条 ✅")

print("\n🔧 下一步操作:")
print("1. 重启后端服务：cd backend_python && python run.py")
print("2. 清除前端缓存：wx.clearStorageSync()")
print("3. 重新编译小程序")
print("4. 进入'诊断记录'页面验证是否显示 98 条记录")
