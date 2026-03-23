#!/usr/bin/env python3
"""
诊断系统第 29.5 次修复验证脚本

验证执行 ID 格式和 API 响应
"""

import requests
import json
import sqlite3
import re

DATABASE_PATH = 'backend_python/database.db'
API_BASE_URL = 'http://127.0.0.1:5001'

def check_database():
    """检查数据库中的 execution_id 格式"""
    print("="*60)
    print("1. 检查数据库中的 execution_id 格式")
    print("="*60)
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT execution_id, brand_name, status, created_at 
            FROM diagnosis_reports 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ 数据库中没有诊断记录")
            return None
        
        print(f"最近 10 条诊断记录:\n")
        uuid_count = 0
        digit_count = 0
        
        for row in rows:
            execution_id = row[0]
            is_uuid = bool(re.match(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                execution_id,
                re.IGNORECASE
            ))
            is_digit = execution_id.isdigit()
            
            if is_uuid:
                uuid_count += 1
                id_type = "UUID"
            elif is_digit:
                digit_count += 1
                id_type = "数字 ID"
            else:
                id_type = "其他格式"
            
            print(f"  {execution_id}")
            print(f"    类型：{id_type}, 品牌：{row[1]}, 状态：{row[2]}, 时间：{row[3]}")
        
        print(f"\n统计:")
        print(f"  UUID 格式：{uuid_count} 条")
        print(f"  数字 ID: {digit_count} 条")
        print(f"  其他格式：{len(rows) - uuid_count - digit_count} 条")
        
        # 返回最新的 execution_id 用于测试
        latest_id = rows[0][0]
        print(f"\n最新的 execution_id: {latest_id}")
        
        conn.close()
        return latest_id
        
    except Exception as e:
        print(f"❌ 数据库检查失败：{e}")
        return None

def test_api(execution_id):
    """测试 API 响应"""
    print("\n" + "="*60)
    print(f"2. 测试 API: /api/diagnosis/report/{execution_id}")
    print("="*60)
    
    try:
        url = f"{API_BASE_URL}/api/diagnosis/report/{execution_id}"
        response = requests.get(url, timeout=5)
        
        print(f"状态码：{response.status_code}")
        
        data = response.json()
        
        # 检查响应中是否有 uniqueId 字段
        if 'uniqueId' in data:
            print(f"\n❌ 警告：响应中包含 uniqueId 字段：{data['uniqueId']}")
            print("   这可能是云开发数据库的_id，而非后端的 execution_id")
        
        # 检查错误信息
        if 'error' in data:
            error = data['error']
            if isinstance(error, dict):
                print(f"\n后端返回错误:")
                print(f"  消息：{error.get('message', 'Unknown')}")
                print(f"  状态：{error.get('status', 'Unknown')}")
            else:
                print(f"\n后端返回错误：{error}")
        
        # 检查数据是否有效
        has_data = (
            data.get('brandDistribution', {}).get('data') or
            data.get('results', [])
        )
        
        if has_data:
            print(f"\n✅ API 返回了有效数据")
            if data.get('brandDistribution', {}).get('data'):
                brands = list(data['brandDistribution']['data'].keys())
                print(f"  品牌：{brands}")
            if data.get('results'):
                print(f"  结果数：{len(data['results'])}")
        else:
            print(f"\n❌ API 返回的数据为空或缺少必要字段")
        
        return data
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到后端 API: {API_BASE_URL}")
        print(f"   请确认后端服务已启动")
        return None
    except Exception as e:
        print(f"\n❌ API 测试失败：{e}")
        return None

def test_digit_id():
    """测试数字 ID（模拟前端错误）"""
    print("\n" + "="*60)
    print("3. 测试数字 ID（模拟前端错误场景）")
    print("="*60)
    
    digit_id = "17737523875363016"
    print(f"测试 ID: {digit_id}")
    
    try:
        url = f"{API_BASE_URL}/api/diagnosis/report/{digit_id}"
        response = requests.get(url, timeout=5)
        
        print(f"状态码：{response.status_code}")
        data = response.json()
        
        if 'error' in data:
            print(f"\n✅ 确认：数字 ID 会导致'报告不存在'错误")
            print(f"   这验证了前端使用了错误的 ID 格式")
        else:
            print(f"\n⚠️ 数字 ID 居然成功了？这很奇怪...")
        
        return data
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        return None

def main():
    """主函数"""
    print("\n" + "="*60)
    print("诊断系统第 29.5 次修复验证")
    print("检查 execution_id 格式和 API 响应")
    print("="*60)
    
    # 步骤 1：检查数据库
    latest_id = check_database()
    
    if not latest_id:
        print("\n❌ 无法继续测试：数据库中没有有效记录")
        return 1
    
    # 步骤 2：测试 API
    test_api(latest_id)
    
    # 步骤 3：测试数字 ID
    test_digit_id()
    
    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    print("""
问题确认:
1. 后端数据库使用 UUID 格式的 execution_id
2. 前端可能使用了云开发数据库的数字_id
3. 导致 API 返回"报告不存在"错误

修复建议:
1. 检查前端历史列表的数据源
2. 确保使用 execution_id 而非_id
3. 清理 Storage 中的旧数据

详细修复方案请参考:
docs/2026-03-17_诊断系统第 29.5 次修复 - 执行 ID 不匹配问题.md
""")
    
    return 0

if __name__ == '__main__':
    exit(main())
