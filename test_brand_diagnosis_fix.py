#!/usr/bin/env python3
"""
品牌诊断功能修复验证脚本
用于测试绕过认证后的功能是否正常
"""

import requests
import json
import time

def test_brand_diagnosis():
    """测试品牌诊断功能"""
    print("🚀 开始测试品牌诊断功能修复...")
    
    # 测试数据
    test_data = {
        "brand_list": ["测试品牌"],
        "selectedModels": ["DeepSeek"],
        "custom_question": "介绍一下{brandName}"
    }
    
    url = "http://127.0.0.1:5000/api/perform-brand-test"
    
    print(f"📤 发送请求到: {url}")
    print(f"📋 请求数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        print(f"📥 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ 请求成功!")
            print(f"📊 响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            
            if 'execution_id' in response_data:
                execution_id = response_data['execution_id']
                print(f"🎯 执行ID: {execution_id}")
                return execution_id
            else:
                print("❌ 响应中缺少 execution_id")
                return None
                
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"📝 错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_task_status(execution_id):
    """测试任务状态查询"""
    if not execution_id:
        print("⚠️  无执行ID，跳过状态查询测试")
        return
    
    print(f"\n🔍 测试任务状态查询，ID: {execution_id}")
    
    url = f"http://127.0.0.1:5000/test/status/{execution_id}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"📥 状态查询响应: {response.status_code}")
        
        if response.status_code == 200:
            status_data = response.json()
            print("✅ 状态查询成功!")
            print(f"📊 状态数据: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 状态查询失败: {response.status_code}")
            print(f"📝 错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 状态查询异常: {e}")

def main():
    """主函数"""
    print("="*60)
    print("品牌诊断功能修复验证")
    print("="*60)
    
    # 测试品牌诊断
    execution_id = test_brand_diagnosis()
    
    # 等待一段时间后测试状态查询
    if execution_id:
        print("\n⏳ 等待5秒后测试状态查询...")
        time.sleep(5)
        test_task_status(execution_id)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == '__main__':
    main()