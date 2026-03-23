#!/usr/bin/env python3
"""
测试脚本：模拟 API 完整响应

用于诊断为什么前端显示"诊断数据为空"
"""

import sys
import os
import json

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

def test_api_response(execution_id: str):
    """测试 API 完整响应"""
    print(f"\n{'='*60}")
    print(f"测试 API 响应：{execution_id}")
    print(f"{'='*60}\n")
    
    try:
        from wechat_backend.diagnosis_report_service import get_report_service
        
        service = get_report_service()
        report = service.get_full_report(execution_id)
        
        if not report:
            print("❌ service.get_full_report 返回 None")
            return
        
        print("1️⃣  service.get_full_report 返回:")
        print(f"   - results 数量：{len(report.get('results', []))}")
        print(f"   - brandDistribution.data: {report.get('brandDistribution', {}).get('data', {})}")
        
        # 模拟 API 层的验证逻辑
        has_raw_results = len(report.get('results', [])) > 0
        has_valid_data = (
            report.get('brandDistribution', {}).get('data') and
            len(report.get('brandDistribution', {}).get('data', {})) > 0
        )
        
        print(f"\n2️⃣  API 层验证:")
        print(f"   - has_raw_results: {has_raw_results}")
        print(f"   - has_valid_data: {has_valid_data}")
        
        # 检查 validation
        validation = report.get('validation', {})
        print(f"\n3️⃣  validation 字段:")
        print(f"   - is_valid: {validation.get('is_valid', 'N/A')}")
        print(f"   - errors: {validation.get('errors', [])}")
        print(f"   - is_empty_data: {validation.get('is_empty_data', 'N/A')}")
        
        # 检查 qualityHints
        quality_hints = report.get('qualityHints', {})
        print(f"\n4️⃣  qualityHints 字段:")
        print(f"   - is_empty_data: {quality_hints.get('is_empty_data', 'N/A')}")
        print(f"   - warnings: {quality_hints.get('warnings', [])}")
        
        # 检查 error
        error = report.get('error', {})
        print(f"\n5️⃣  error 字段:")
        print(f"   - status: {error.get('status', 'N/A')}")
        print(f"   - is_empty_data: {error.get('is_empty_data', 'N/A')}")
        
        # 模拟前端检测逻辑
        print(f"\n6️⃣  前端检测逻辑模拟:")
        is_empty_data = (
            validation.get('is_empty_data', False) or
            quality_hints.get('is_empty_data', False) or
            error.get('is_empty_data', False)
        )
        print(f"   - isEmptyData (前端判断): {is_empty_data}")
        
        has_valid_brand_data = (
            report.get('brandDistribution', {}).get('data') and
            len(report.get('brandDistribution', {}).get('data', {})) > 0
        )
        print(f"   - hasValidBrandData: {has_valid_brand_data}")
        
        if is_empty_data:
            print(f"\n   ❌ 前端会显示'诊断数据为空'卡片！")
            print(f"   原因：validation.is_empty_data、qualityHints.is_empty_data 或 error.is_empty_data 为 True")
        elif has_valid_brand_data:
            print(f"\n   ✅ 前端会正常显示数据")
        else:
            print(f"\n   ⚠️  前端会进入其他错误处理分支")
        
        # 输出完整的响应数据结构
        print(f"\n7️⃣  完整响应数据结构预览:")
        response_keys = list(report.keys())
        print(f"   - 顶层 keys: {response_keys}")
        
        # 保存完整响应到文件
        output_file = '/tmp/api_response.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n   ✅ 完整响应已保存到：{output_file}")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 获取最新的 execution_id
    if len(sys.argv) > 1:
        exec_id = sys.argv[1]
    else:
        import sqlite3
        DB_PATH = os.path.join(os.path.dirname(__file__), 'backend_python', 'database.db')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT execution_id FROM diagnosis_reports ORDER BY created_at DESC LIMIT 1')
        row = cursor.fetchone()
        if row:
            exec_id = row[0]
            print(f"使用最新的 execution_id: {exec_id}")
        else:
            print("数据库中没有诊断报告记录")
            sys.exit(1)
        conn.close()
    
    test_api_response(exec_id)
