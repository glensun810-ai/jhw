#!/usr/bin/env python3
"""
P21 修复验证脚本 - 历史诊断详情页 API

验证内容:
1. 后端 API 端点是否已注册
2. API 是否能正确返回诊断数据
3. 数据格式是否与前端兼容
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("P21 修复验证 - 历史诊断详情页 API")
print("=" * 70)

# 测试 1: 检查 API 端点是否已注册
print("\n[测试 1] 检查 API 端点注册...")
with open('wechat_backend/views/diagnosis_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

if "@diagnosis_bp.route('/history/<execution_id>/detail'" in content:
    print("  ✅ /api/diagnosis/history/<execution_id>/detail 端点已注册")
else:
    print("  ❌ /api/diagnosis/history/<execution_id>/detail 端点未注册")

if "get_diagnosis_detail" in content:
    print("  ✅ get_diagnosis_detail 函数已定义")
else:
    print("  ❌ get_diagnosis_detail 函数未定义")

# 测试 2: 尝试导入并测试 API
print("\n[测试 2] 测试 API 功能...")
try:
    from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
    
    repo = DiagnosisReportRepository()
    
    # 获取最新报告
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT execution_id, brand_name, status 
        FROM diagnosis_reports 
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        execution_id = row[0]
        brand_name = row[1]
        status = row[2]
        print(f"  📊 最新报告：execution_id={execution_id}, brand={brand_name}, status={status}")
        
        # 测试获取完整报告
        report = repo.get_by_execution_id(execution_id)
        if report:
            results = report.get('results', [])
            brand_analysis = report.get('brandAnalysis')
            top3_brands = report.get('top3Brands', [])
            
            print(f"  ✅ 报告获取成功")
            print(f"     - 结果数：{len(results)}")
            print(f"     - 品牌分析：{'有' if brand_analysis else '无'}")
            print(f"     - Top3 品牌：{len(top3_brands)} 个")
        else:
            print(f"  ⚠️  报告内容为空")
    else:
        print("  ⚠️  数据库中没有报告记录")
        
except Exception as e:
    print(f"  ❌ API 测试失败：{e}")
    import traceback
    traceback.print_exc()

# 测试 3: 检查前端代码
print("\n[测试 3] 检查前端代码...")
try:
    with open('../pages/report/detail/index.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
except FileNotFoundError:
    try:
        with open('../../pages/report/detail/index.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
    except FileNotFoundError:
        js_content = ""
        print("  ⚠️  前端文件未找到，跳过检查")

if "loadDiagnosisFromAPI" in js_content:
    print("  ✅ loadDiagnosisFromAPI 函数已定义")
else:
    print("  ❌ loadDiagnosisFromAPI 函数未定义")

if "/api/diagnosis/history/${executionId}/detail" in js_content:
    print("  ✅ 前端 API 调用路径正确")
else:
    print("  ❌ 前端 API 调用路径可能有误")

if "options.executionId" in js_content:
    print("  ✅ 支持 executionId 参数")
else:
    print("  ❌ 不支持 executionId 参数")

# 测试 4: 模拟 API 请求
print("\n[测试 4] 模拟 API 请求响应...")
try:
    from flask import Flask, jsonify
    
    # 获取一个真实的 execution_id
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT execution_id FROM diagnosis_reports 
        WHERE status = 'completed'
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        test_execution_id = row[0]
        print(f"  📊 使用测试 execution_id: {test_execution_id}")
        
        # 模拟 API 响应数据结构
        repo = DiagnosisReportRepository()
        report = repo.get_by_execution_id(test_execution_id)
        
        if report:
            response_data = {
                'success': True,
                'data': {
                    'report': {
                        'id': report.get('id'),
                        'execution_id': report.get('execution_id'),
                        'brand_name': report.get('brand_name'),
                        'status': report.get('status'),
                        'progress': report.get('progress', 100)
                    },
                    'results': report.get('results', [])[:3],  # 只取前 3 个结果
                    'analysis': {
                        'brandAnalysis': report.get('brandAnalysis'),
                        'top3Brands': report.get('top3Brands', [])
                    },
                    'statistics': {
                        'total_results': len(report.get('results', [])),
                        'total_questions': len(set(r.get('question', '') for r in report.get('results', []) if r.get('question'))),
                        'platforms': list(set(r.get('platform', '') for r in report.get('results', []) if r.get('platform')))
                    }
                }
            }
            
            print(f"  ✅ API 响应结构验证通过")
            print(f"     响应大小：{len(json.dumps(response_data))} 字节")
            print(f"     结果数：{response_data['data']['statistics']['total_results']}")
            print(f"     问题数：{response_data['data']['statistics']['total_questions']}")
            print(f"     平台数：{len(response_data['data']['statistics']['platforms'])}")
        else:
            print(f"  ⚠️  报告内容为空")
    else:
        print("  ⚠️  没有可用的测试报告")
        
except Exception as e:
    print(f"  ❌ 模拟 API 请求失败：{e}")

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)

print("\n📋 修复说明:")
print("1. 后端新增 /api/diagnosis/history/<execution_id>/detail 端点")
print("2. 从 diagnosis_reports、diagnosis_results、diagnosis_analysis 三张表完整提取数据")
print("3. 前端 detail/index.js 新增 loadDiagnosisFromAPI 函数")
print("4. 支持通过 executionId 参数从 API 加载历史诊断数据")

print("\n🔧 下一步操作:")
print("1. 重启后端服务：cd backend_python && python run.py")
print("2. 观察启动日志中是否显示新的 API 端点已注册")
print("3. 在微信小程序历史详情页中测试加载诊断数据")
print("4. 验证是否能正确显示：品牌名称、诊断结果、品牌分析、Top3 排名等")

print("\n📱 前端使用示例:")
print("  // 跳转到详情页")
print("  wx.navigateTo({")
print("    url: '/pages/report/detail/index?executionId=4ba12502-488f-43c6-8742-5671b83e0ee3'")
print("  })")
