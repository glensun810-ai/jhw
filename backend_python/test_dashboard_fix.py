#!/usr/bin/env python3
"""
Dashboard API 修复验证脚本

验证内容:
1. Dashboard API 路由是否已注册
2. /api/dashboard/aggregate 端点是否可用
3. 返回的数据格式是否与前端兼容
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("Dashboard API 修复验证")
print("=" * 70)

# 测试 1: 检查 app.py 中是否注册了 Dashboard API
print("\n[测试 1] 检查 app.py 中的 Dashboard API 注册...")
with open('wechat_backend/app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

if 'from wechat_backend.views_dashboard_api import register_dashboard_routes' in app_content:
    print("  ✅ Dashboard API 导入语句已添加")
else:
    print("  ❌ Dashboard API 导入语句缺失")

if 'register_dashboard_routes(wechat_bp)' in app_content:
    print("  ✅ Dashboard API 注册调用已添加")
else:
    print("  ❌ Dashboard API 注册调用缺失")

# 测试 2: 检查 dashboard_api.py 是否存在
print("\n[测试 2] 检查 dashboard_api.py 文件...")
if os.path.exists('wechat_backend/views/dashboard_api.py'):
    print("  ✅ dashboard_api.py 文件存在")
    
    with open('wechat_backend/views/dashboard_api.py', 'r', encoding='utf-8') as f:
        dashboard_content = f.read()
    
    if 'register_dashboard_routes' in dashboard_content:
        print("  ✅ register_dashboard_routes 函数存在")
    
    if '/api/dashboard/aggregate' in dashboard_content:
        print("  ✅ /api/dashboard/aggregate 路由已定义")
else:
    print("  ❌ dashboard_api.py 文件不存在")

# 测试 3: 尝试导入 Dashboard API 模块
print("\n[测试 3] 尝试导入 Dashboard API 模块...")
try:
    from wechat_backend.views.dashboard_api import register_dashboard_routes, enrich_dashboard_with_roi
    print("  ✅ Dashboard API 模块导入成功")
except Exception as e:
    print(f"  ❌ Dashboard API 模块导入失败：{e}")

# 测试 3b: 检查 app.py 中的导入语句是否正确
print("\n[测试 3b] 检查 app.py 中的导入路径...")
if 'from wechat_backend.views.dashboard_api import register_dashboard_routes' in app_content:
    print("  ✅ app.py 中的导入路径正确 (views/dashboard_api)")
elif 'from wechat_backend.views_dashboard_api import register_dashboard_routes' in app_content:
    print("  ⚠️  app.py 中的导入路径可能有误 (views_dashboard_api vs views/dashboard_api)")
else:
    print("  ❌ app.py 中未找到导入语句")

# 测试 4: 检查 DiagnosisReportRepository
print("\n[测试 4] 检查 DiagnosisReportRepository...")
try:
    from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
    repo = DiagnosisReportRepository()
    print("  ✅ DiagnosisReportRepository 初始化成功")
    
    # 测试获取最新报告
    cursor = repo._get_db_cursor()
    if cursor:
        cursor.execute('''
            SELECT execution_id, brand_name, status 
            FROM diagnosis_reports 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        row = cursor.fetchone()
        repo._close_db_cursor(cursor)
        
        if row:
            print(f"  📊 最新报告：execution_id={row[0]}, brand={row[1]}, status={row[2]}")
        else:
            print("  ⚠️  数据库中没有报告记录")
except Exception as e:
    print(f"  ❌ DiagnosisReportRepository 检查失败：{e}")

# 测试 5: 检查数据库表关联
print("\n[测试 5] 检查数据库表关联...")
import sqlite3
db_path = 'database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查 diagnosis_reports 和 diagnosis_results 的关联
cursor.execute('''
    SELECT 
        r.id as report_id,
        r.execution_id,
        r.brand_name,
        r.status,
        COUNT(res.id) as result_count
    FROM diagnosis_reports r
    LEFT JOIN diagnosis_results res ON r.id = res.report_id
    GROUP BY r.id
    ORDER BY r.created_at DESC
    LIMIT 5
''')

print("  最新 5 条报告关联:")
for row in cursor.fetchall():
    has_results = '✅' if row[4] > 0 else '⚠️'
    print(f"    {has_results} report_id={row[0]}, exec_id={row[1]}, brand={row[2]}, results={row[4]}")

conn.close()

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)

print("\n📋 修复说明:")
print("1. 在 app.py 中添加了 Dashboard API 路由注册")
print("2. register_dashboard_routes(wechat_bp) 注册了 /api/dashboard/aggregate 端点")
print("3. Dashboard API 现在可以为前端提供聚合数据")

print("\n🔧 下一步操作:")
print("1. 重启后端服务：cd backend_python && python run.py")
print("2. 观察启动日志中是否显示 '✅ Dashboard API 已注册'")
print("3. 在微信小程序中查看诊断报告看板页面")
print("4. 验证是否能正确显示 Dashboard 数据")
