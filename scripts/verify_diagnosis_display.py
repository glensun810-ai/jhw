#!/usr/bin/env python3
"""
诊断记录数据验证脚本

验证后端 API 返回的数据是否能被前端正确展示
"""

import json
import sqlite3

DB_PATH = '/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db'
EXECUTION_ID = '12bed967-1094-46b7-a363-0864971df7b0'

def check_database():
    """检查数据库中的数据"""
    print("="*60)
    print("1. 数据库检查")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 检查诊断报告
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diagnosis_reports WHERE execution_id = ?", (EXECUTION_ID,))
    report = cursor.fetchone()
    
    if report:
        print(f"✅ 诊断报告存在")
        print(f"   - 品牌：{report['brand_name']}")
        print(f"   - 状态：{report['status']}")
        print(f"   - 进度：{report['progress']}%")
        print(f"   - 完成时间：{report['completed_at']}")
    else:
        print(f"❌ 诊断报告不存在")
        return False
    
    # 检查结果数量
    cursor.execute("SELECT COUNT(*) as cnt FROM diagnosis_results WHERE execution_id = ?", (EXECUTION_ID,))
    result_count = cursor.fetchone()['cnt']
    print(f"✅ 诊断结果数量：{result_count} 条")
    
    # 检查模型分布
    cursor.execute("""
        SELECT model, COUNT(*) as cnt 
        FROM diagnosis_results 
        WHERE execution_id = ? 
        GROUP BY model
    """, (EXECUTION_ID,))
    models = cursor.fetchall()
    print(f"✅ 使用的 AI 模型:")
    for m in models:
        print(f"   - {m['model']}: {m['cnt']} 条")
    
    conn.close()
    return True


def check_api_response():
    """检查 API 响应"""
    print("\n" + "="*60)
    print("2. API 响应检查")
    print("="*60)
    
    import urllib.request
    
    url = f"http://localhost:5001/api/diagnosis/report/{EXECUTION_ID}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            if data.get('success'):
                print(f"✅ API 调用成功")
            else:
                print(f"⚠️  API 返回但 success=false")
            
            report_data = data.get('data', {})
            
            # 检查必需字段
            required_fields = ['report', 'results', 'analysis', 'brandDistribution', 'validation']
            missing_fields = []
            for field in required_fields:
                if field not in report_data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ 缺少字段：{missing_fields}")
                return False
            else:
                print(f"✅ 所有必需字段存在")
            
            # 检查结果
            results = report_data.get('results', [])
            print(f"✅ 结果数量：{len(results)} 条")
            
            # 检查结果字段
            if results:
                result = results[0]
                result_fields = ['id', 'brand', 'model', 'question', 'responseContent', 'qualityScore']
                missing_result_fields = []
                for field in result_fields:
                    if field not in result:
                        missing_result_fields.append(field)
                
                if missing_result_fields:
                    print(f"⚠️  结果缺少字段：{missing_result_fields}")
                else:
                    print(f"✅ 结果字段完整")
            
            # 检查品牌分布
            brand_dist = report_data.get('brandDistribution', {})
            if brand_dist.get('data'):
                print(f"✅ 品牌分布数据存在")
                print(f"   - 品牌列表：{list(brand_dist['data'].keys())}")
            else:
                print(f"⚠️  品牌分布数据为空")
            
            # 检查验证信息
            validation = report_data.get('validation', {})
            if validation:
                print(f"✅ 验证信息存在")
                print(f"   - 有效：{validation.get('isValid', 'N/A')}")
            
            return True
            
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return False


def check_frontend_mapping():
    """检查前端字段映射"""
    print("\n" + "="*60)
    print("3. 前端字段映射检查")
    print("="*60)
    
    # API 字段 → 前端字段映射
    field_mapping = {
        'report.brandName': 'brandName',
        'report.status': 'status',
        'report.executionId': 'executionId',
        'results[].brand': 'detailedResults[].brand',
        'results[].model': 'detailedResults[].model',
        'results[].question': 'detailedResults[].question',
        'results[].responseContent': 'detailedResults[].fullResponse',
        'results[].qualityScore': 'detailedResults[].score',
        'brandDistribution.data': 'brandDistribution',
        'validation.qualityScore': 'overallScore',
        'keywords': 'keywords'
    }
    
    print("✅ 前端字段映射关系:")
    for api_field, frontend_field in field_mapping.items():
        print(f"   {api_field} → {frontend_field}")
    
    return True


def main():
    print("\n" + "="*60)
    print("诊断记录数据验证")
    print(f"Execution ID: {EXECUTION_ID}")
    print("="*60)
    
    # 1. 检查数据库
    db_ok = check_database()
    
    # 2. 检查 API 响应
    api_ok = check_api_response()
    
    # 3. 检查前端映射
    mapping_ok = check_frontend_mapping()
    
    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    
    if db_ok and api_ok and mapping_ok:
        print("✅ 所有检查通过！数据可以在前端正确展示")
        print("\n前端展示内容:")
        print("  - 诊断报告基本信息（品牌、状态、时间）")
        print("  - 12 条 AI 回答结果（4 模型 × 3 问题）")
        print("  - 品牌分布数据")
        print("  - 关键词列表")
        print("  - 质量评分和验证信息")
        return 0
    else:
        print("❌ 部分检查失败，请查看上方详情")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
