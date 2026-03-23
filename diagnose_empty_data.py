#!/usr/bin/env python3
"""
诊断脚本：检查为什么前端显示"诊断数据为空"

问题现象：
- 数据库中有诊断报告（status=completed, progress=100）
- 数据库中有 3 条 diagnosis_results 记录
- 但前端显示"诊断数据为空"

可能的原因：
1. get_full_report 返回的数据中 brandDistribution.data 为空
2. results 数据中的 brand/extracted_brand 字段为空
3. API 返回的数据格式与前端期望不匹配
"""

import sqlite3
import json
import sys
import os

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

DB_PATH = os.path.join(os.path.dirname(__file__), 'backend_python', 'database.db')

def check_report(execution_id: str):
    """检查特定执行 ID 的报告数据"""
    print(f"\n{'='*60}")
    print(f"诊断报告检查：{execution_id}")
    print(f"{'='*60}\n")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 检查报告主数据
    print("1️⃣  检查诊断报告主数据...")
    cursor.execute('''
        SELECT id, execution_id, user_id, brand_name, status, stage, progress, 
               is_completed, competitor_brands, selected_models, created_at
        FROM diagnosis_reports
        WHERE execution_id = ?
    ''', (execution_id,))
    
    report = cursor.fetchone()
    if not report:
        print(f"   ❌ 报告不存在：{execution_id}")
        conn.close()
        return
    
    print(f"   ✅ 报告存在:")
    print(f"      - id: {report['id']}")
    print(f"      - brand_name: {report['brand_name']}")
    print(f"      - status: {report['status']}")
    print(f"      - stage: {report['stage']}")
    print(f"      - progress: {report['progress']}")
    print(f"      - is_completed: {report['is_completed']}")
    print(f"      - competitor_brands: {report['competitor_brands']}")
    print(f"      - selected_models: {report['selected_models']}")
    
    # 2. 检查结果数据
    print(f"\n2️⃣  检查诊断结果数据...")
    cursor.execute('''
        SELECT id, execution_id, brand, extracted_brand, question, model, 
               response_content, status, quality_score, quality_level
        FROM diagnosis_results
        WHERE execution_id = ?
        ORDER BY brand, question, model
    ''', (execution_id,))
    
    results = cursor.fetchall()
    print(f"   结果数量：{len(results)}")
    
    if len(results) == 0:
        print(f"   ❌ 结果数据为空！这是问题所在！")
    else:
        print(f"   ✅ 有 {len(results)} 条结果")
        for i, r in enumerate(results, 1):
            print(f"\n   结果 {i}:")
            print(f"      - brand: '{r['brand']}'")
            print(f"      - extracted_brand: '{r['extracted_brand']}'")
            print(f"      - question: {r['question'][:50]}...")
            print(f"      - model: {r['model']}")
            print(f"      - status: {r['status']}")
            print(f"      - quality_score: {r['quality_score']}")
            print(f"      - response_content (前 100 字符): {r['response_content'][:100]}...")
            
            # 检查品牌字段
            brand_val = r['brand']
            extracted_val = r['extracted_brand']
            
            if not brand_val or not str(brand_val).strip():
                print(f"      ⚠️  警告：brand 字段为空或无效！")
            if not extracted_val or not str(extracted_val).strip():
                print(f"      ⚠️  警告：extracted_brand 字段为空或无效！")
    
    # 3. 检查分析数据
    print(f"\n3️⃣  检查诊断分析数据...")
    cursor.execute('''
        SELECT analysis_type, analysis_data
        FROM diagnosis_analysis
        WHERE execution_id = ?
    ''', (execution_id,))
    
    analyses = cursor.fetchall()
    print(f"   分析数据数量：{len(analyses)}")
    
    if len(analyses) == 0:
        print(f"   ⚠️  分析数据为空（可能正常，取决于实现）")
    else:
        for a in analyses:
            try:
                data = json.loads(a['analysis_data'])
                print(f"   - {a['analysis_type']}: {len(data)} 项")
            except:
                print(f"   - {a['analysis_type']}: (无法解析)")
    
    # 4. 检查文件存储
    print(f"\n4️⃣  检查文件存储...")
    import os
    from datetime import datetime
    
    created_at = report['created_at']
    try:
        created_dt = datetime.fromisoformat(created_at)
        year = created_dt.year
        month = f"{created_dt.month:02d}"
        day = f"{created_dt.day:02d}"
        
        file_path = os.path.join(
            os.path.dirname(__file__), 'data', 'diagnosis', 'reports',
            str(year), month, day, f"{execution_id}.json"
        )
        
        if os.path.exists(file_path):
            print(f"   ✅ 文件存在：{file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                print(f"   文件内容:")
                print(f"      - report: {type(file_data.get('report', {}))}")
                print(f"      - results: {len(file_data.get('results', []))} 项")
                print(f"      - analysis: {type(file_data.get('analysis', {}))}")
                
                # 检查 brandDistribution
                if 'brandDistribution' in file_data:
                    bd = file_data['brandDistribution']
                    print(f"      - brandDistribution.data: {bd.get('data', {})}")
                else:
                    print(f"      ⚠️  文件中缺少 brandDistribution 字段")
        else:
            print(f"   ❌ 文件不存在：{file_path}")
            print(f"      可能原因：文件保存逻辑未执行或路径错误")
    except Exception as e:
        print(f"   ❌ 文件检查失败：{e}")
    
    # 5. 模拟 brandDistribution 计算
    print(f"\n5️⃣  模拟品牌分布计算...")
    brand_distribution = {}
    for r in results:
        # 优先使用 extracted_brand
        brand = r['extracted_brand']
        if not brand or not str(brand).strip():
            # 降级到 brand 字段
            brand = r['brand']
        
        if brand and str(brand).strip():
            brand = brand.strip()
            brand_distribution[brand] = brand_distribution.get(brand, 0) + 1
    
    print(f"   计算结果：{brand_distribution}")
    if not brand_distribution:
        print(f"   ❌ 品牌分布为空！这就是前端显示'诊断数据为空'的原因！")
        print(f"   可能原因：")
        print(f"      1. results 中的 brand 和 extracted_brand 字段都为空")
        print(f"      2. 品牌名称包含空格或特殊字符")
        print(f"      3. 数据提取逻辑有问题")
    else:
        print(f"   ✅ 品牌分布计算成功")
        print(f"      预期前端会显示：{brand_distribution}")
    
    conn.close()
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    # 获取最新的 execution_id
    if len(sys.argv) > 1:
        exec_id = sys.argv[1]
    else:
        # 自动获取最新的 execution_id
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT execution_id FROM diagnosis_reports 
            ORDER BY created_at DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        if row:
            exec_id = row[0]
            print(f"使用最新的 execution_id: {exec_id}")
        else:
            print("数据库中没有诊断报告记录")
            sys.exit(1)
        conn.close()
    
    check_report(exec_id)
