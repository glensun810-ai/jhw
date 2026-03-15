#!/usr/bin/env python3
"""
快速测试诊断流程

执行一次完整的品牌诊断测试，验证修复是否生效。
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5001'

def test_diagnosis():
    """执行测试诊断"""
    print("=" * 60)
    print("执行测试诊断")
    print("=" * 60)
    
    # 测试数据 - 只使用 deepseek API（更稳定）
    payload = {
        'brand_list': ['宝马', '奔驰', '奥迪'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True}  # 只使用 DeepSeek
        ],
        'customQuestions': [
            '请分析该品牌在新能源汽车市场的竞争优势？'
        ]
    }
    
    print("\n📤 发送诊断请求...")
    print(f"   品牌：{payload['brand_list']}")
    print(f"   模型：{[m['name'] for m in payload['selectedModels']]}")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/perform-brand-test',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        result = response.json()
        print(f"\n📥 响应状态：{response.status_code}")
        print(f"📥 响应数据：{json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200 and result.get('status') == 'success':
            execution_id = result.get('execution_id')
            print(f"\n✅ 诊断启动成功！Execution ID: {execution_id}")
            return execution_id
        else:
            print(f"\n❌ 诊断启动失败：{result.get('error', 'Unknown error')}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到后端服务，请确保服务已启动")
        return None
    except Exception as e:
        print(f"\n❌ 请求失败：{e}")
        return None

def check_result(execution_id):
    """检查结果"""
    if not execution_id:
        return
    
    print("\n" + "=" * 60)
    print("等待诊断完成...")
    print("=" * 60)
    
    # 等待 30 秒让诊断完成
    time.sleep(30)
    
    print("\n📤 查询诊断结果...")
    try:
        response = requests.get(
            f'{BASE_URL}/api/diagnosis/report/{execution_id}',
            timeout=30
        )
        
        if response.status_code == 200:
            report = response.json()
            print(f"\n📥 报告状态：{response.status_code}")
            
            # 检查品牌分布
            brand_dist = report.get('brandDistribution', {})
            if brand_dist:
                print(f"✅ 品牌分布数据：{json.dumps(brand_dist, indent=2, ensure_ascii=False)}")
            else:
                print("⚠️  品牌分布数据为空")
            
            # 检查原始数据
            if hasattr(report, 'get'):
                raw_data = report.get('rawData', {})
                if raw_data:
                    print(f"\n📊 原始数据条数：{len(raw_data) if isinstance(raw_data, list) else 'N/A'}")
                    if isinstance(raw_data, list) and len(raw_data) > 0:
                        first_item = raw_data[0]
                        extracted_brand = first_item.get('extractedBrand') if isinstance(first_item, dict) else 'N/A'
                        print(f"📊 第一条记录的 extractedBrand: {extracted_brand}")
            return True
        else:
            print(f"\n❌ 获取报告失败：{response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ 查询结果失败：{e}")
        return False

def check_database():
    """检查数据库最新记录"""
    import sqlite3
    
    print("\n" + "=" * 60)
    print("检查数据库最新记录")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('backend_python/database.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT execution_id, brand, extracted_brand, extraction_method, created_at
            FROM diagnosis_results
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            print("\n📊 最新 5 条记录:")
            for row in rows:
                exec_id, brand, extracted, method, created = row
                extracted_preview = (extracted[:20] + '...') if extracted and len(extracted) > 20 else extracted
                print(f"   • {brand:15} | extracted: {extracted_preview or 'NULL':25} | method: {method or 'NULL'}")
            
            # 检查提取率
            total = len(rows)
            has_extracted = sum(1 for row in rows if row[2] is not None)
            print(f"\n📊 提取率：{has_extracted}/{total} ({has_extracted/total*100:.1f}%)")
            
            if has_extracted > 0:
                print("✅ 品牌提取功能正常工作！")
            else:
                print("❌ 品牌提取功能仍未工作")
        else:
            print("\n⚠️  数据库中没有记录")
            
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 检查数据库失败：{e}")

if __name__ == '__main__':
    # 执行测试
    execution_id = test_diagnosis()
    
    if execution_id:
        check_result(execution_id)
    
    check_database()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
