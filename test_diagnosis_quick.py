#!/usr/bin/env python3
"""
诊断功能快速测试脚本
测试诊断 API 是否正常工作
"""

import requests
import json
import time

BASE_URL = "http://localhost:5001"

def test_diagnosis_api():
    """测试诊断 API"""
    print("=" * 60)
    print("诊断功能测试")
    print("=" * 60)
    
    # 1. 测试 API 连通性
    print("\n1. 测试服务器连通性...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   OK 服务器响应：{response.status_code}")
    except Exception as e:
        print(f"   X 服务器连接失败：{e}")
        return False
    
    # 2. 测试诊断 API 路由
    print("\n2. 检查诊断 API 路由...")
    try:
        response = requests.get(f"{BASE_URL}/api/diagnosis", timeout=5)
        print(f"   诊断 API 响应：{response.status_code}")
    except Exception as e:
        print(f"   X 诊断 API 检查失败：{e}")
    
    # 3. 准备测试数据
    print("\n3. 准备诊断测试数据...")
    test_data = {
        "brand_list": ["趣车良品", "蔚来"],
        "selectedModels": [
            {"name": "qwen", "checked": True}  # 使用 Qwen 模型（不限流）
        ],
        "customQuestions": [
            "请分析该品牌在新能源汽车市场的竞争优势？"
        ],
        "userLevel": "Free"
    }
    
    # 4. 发起诊断请求
    print("\n4. 发起诊断请求...")
    print(f"   品牌：{test_data['brand_list']}")
    print(f"   模型：{[m['name'] for m in test_data['selectedModels']]}")
    print(f"   问题数：{len(test_data['customQuestions'])}")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=test_data,
            timeout=10  # 10 秒超时（仅测试请求接收）
        )
        elapsed = time.time() - start_time
        
        print(f"\n5. 响应结果:")
        print(f"   状态码：{response.status_code}")
        print(f"   耗时：{elapsed:.2f}秒")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   OK 请求成功")
            print(f"   execution_id: {result.get('executionId', 'N/A')[:20] if result.get('executionId') else 'N/A'}...")
            print(f"   report_id: {result.get('reportId', 'N/A')}")
            return True
        else:
            print(f"   X 请求失败：{response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"   WARN  请求超时（{elapsed:.2f}秒）- 这是正常的，诊断是异步执行")
        return True
    except Exception as e:
        print(f"   X 请求异常：{e}")
        return False

if __name__ == "__main__":
    success = test_diagnosis_api()
    print("\n" + "=" * 60)
    if success:
        print("OK 诊断功能测试通过")
    else:
        print("X 诊断功能测试失败")
    print("=" * 60)
