#!/usr/bin/env python3
"""
测试脚本：验证 get_full_report 返回的数据

用于诊断为什么前端显示"诊断数据为空"
"""

import sys
import os

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

def test_get_full_report(execution_id: str):
    """测试 get_full_report 方法"""
    print(f"\n{'='*60}")
    print(f"测试 get_full_report: {execution_id}")
    print(f"{'='*60}\n")
    
    try:
        from wechat_backend.diagnosis_report_service import get_report_service
        
        service = get_report_service()
        report = service.get_full_report(execution_id)
        
        if not report:
            print("❌ get_full_report 返回 None")
            return
        
        print("✅ get_full_report 返回数据:")
        print(f"   - execution_id: {report.get('execution_id', 'N/A')}")
        print(f"   - brand_name: {report.get('brand_name', 'N/A')}")
        print(f"   - status: {report.get('status', 'N/A')}")
        print(f"   - progress: {report.get('progress', 'N/A')}")
        
        # 检查结果数据
        results = report.get('results', [])
        print(f"\n   结果数据:")
        print(f"      - results 数量：{len(results)}")
        if results:
            for i, r in enumerate(results[:3], 1):
                brand = r.get('brand', 'N/A')
                extracted = r.get('extracted_brand', 'N/A')
                print(f"      - 结果 {i}: brand='{brand}', extracted_brand='{extracted}'")
        
        # 检查 brandDistribution
        brand_dist = report.get('brandDistribution', {})
        print(f"\n   品牌分布数据:")
        print(f"      - data: {brand_dist.get('data', {})}")
        print(f"      - total_count: {brand_dist.get('total_count', 'N/A')}")
        
        # 检查是否有有效数据
        has_valid_data = (
            brand_dist.get('data') and
            len(brand_dist.get('data', {})) > 0
        )
        has_raw_results = len(results) > 0
        
        print(f"\n   数据验证:")
        print(f"      - has_valid_data: {has_valid_data}")
        print(f"      - has_raw_results: {has_raw_results}")
        
        if not has_valid_data and has_raw_results:
            print(f"\n   ⚠️  警告：有 results 但 brandDistribution.data 为空！")
            print(f"   可能原因：results 中的 brand/extracted_brand 字段为空")
        elif not has_valid_data and not has_raw_results:
            print(f"\n   ❌ 问题：results 和 brandDistribution.data 都为空！")
            print(f"   这是前端显示'诊断数据为空'的原因")
        else:
            print(f"\n   ✅ 数据正常，前端应该能正常显示")
        
        # 检查 validation
        validation = report.get('validation', {})
        if validation:
            print(f"\n   验证信息:")
            print(f"      - is_valid: {validation.get('is_valid', 'N/A')}")
            print(f"      - errors: {validation.get('errors', [])}")
            print(f"      - warnings: {validation.get('warnings', [])}")
        
        # 检查 qualityHints
        quality_hints = report.get('qualityHints', {})
        if quality_hints:
            print(f"\n   质量提示:")
            print(f"      - has_low_quality_results: {quality_hints.get('has_low_quality_results', 'N/A')}")
            print(f"      - warnings: {quality_hints.get('warnings', [])}")
        
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
    
    test_get_full_report(exec_id)
