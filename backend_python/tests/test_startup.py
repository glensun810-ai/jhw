#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证 /api/perform-brand-test 接口在各种模型组合下的稳定性
确保后端能稳定返回 200 Success 及 executionId
"""

import requests
import json
import time
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_perform_brand_test():
    """测试 perform-brand-test 接口"""
    print("🧪 开始测试 /api/perform-brand-test 接口...")
    
    # 测试不同的模型组合
    test_cases = [
        {
            "name": "单个模型测试 - DeepSeek",
            "payload": {
                "brand_list": ["测试品牌"],
                "selectedModels": [{"name": "DeepSeek", "checked": True}],
                "customQuestions": ["介绍一下{brandName}"],
                "userLevel": "Free"
            }
        },
        {
            "name": "单个模型测试 - 豆包",
            "payload": {
                "brand_list": ["测试品牌"],
                "selectedModels": [{"name": "doubao", "checked": True}],
                "customQuestions": ["介绍一下{brandName}"],
                "userLevel": "Free"
            }
        },
        {
            "name": "多个模型测试",
            "payload": {
                "brand_list": ["测试品牌"],
                "selectedModels": [
                    {"name": "deepseek", "checked": True},
                    {"name": "doubao", "checked": True}
                ],
                "customQuestions": ["介绍一下{brandName}", "{brandName}的主要产品是什么"],
                "userLevel": "Free"
            }
        },
        {
            "name": "多品牌测试",
            "payload": {
                "brand_list": ["品牌A", "品牌B"],
                "selectedModels": [{"name": "DeepSeek", "checked": True}],
                "customQuestions": ["介绍一下{brandName}"],
                "userLevel": "Free"
            }
        }
    ]
    
    base_url = "http://127.0.0.1:5001"
    endpoint = f"{base_url}/api/perform-brand-test"
    
    all_tests_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试 {i}: {test_case['name']}")
        print(f"   Payload: {json.dumps(test_case['payload'], ensure_ascii=False)[:100]}...")
        
        try:
            response = requests.post(
                endpoint,
                json=test_case['payload'],
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Test-Client/1.0'
                },
                timeout=30
            )
            
            print(f"   HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"   响应数据: {json.dumps(response_data, ensure_ascii=False)[:200]}...")
                    
                    # 检查是否包含必需的字段
                    if 'status' in response_data and response_data['status'] == 'success':
                        if 'executionId' in response_data:
                            print(f"   ✅ 测试通过 - 返回了正确的 executionId: {response_data['executionId'][:8]}...")
                            
                            # 尝试轮询进度
                            progress_endpoint = f"{base_url}/api/test-progress?executionId={response_data['executionId']}"
                            progress_response = requests.get(progress_endpoint, timeout=10)
                            
                            if progress_response.status_code == 200:
                                progress_data = progress_response.json()
                                print(f"   ✅ 进度查询成功 - 状态: {progress_data.get('status', 'unknown')}, 进度: {progress_data.get('progress', 0)}%")
                            else:
                                print(f"   ⚠️  进度查询失败 - 状态码: {progress_response.status_code}")
                        else:
                            print(f"   ❌ 测试失败 - 缺少 executionId 字段")
                            all_tests_passed = False
                    else:
                        print(f"   ❌ 测试失败 - 响应中缺少 'status': 'success'")
                        print(f"      详细错误: {response_data}")
                        all_tests_passed = False
                        
                except json.JSONDecodeError:
                    print(f"   ❌ 测试失败 - 响应不是有效的JSON格式")
                    print(f"      响应内容: {response.text[:200]}...")
                    all_tests_passed = False
            else:
                print(f"   ❌ 测试失败 - HTTP状态码: {response.status_code}")
                try:
                    error_response = response.json()
                    print(f"      错误详情: {json.dumps(error_response, ensure_ascii=False)}")
                except:
                    print(f"      错误详情: {response.text[:200]}...")
                all_tests_passed = False
                
        except requests.exceptions.Timeout:
            print(f"   ❌ 测试失败 - 请求超时")
            all_tests_passed = False
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 测试失败 - 请求异常: {str(e)}")
            all_tests_passed = False
    
    print(f"\n{'🎉 所有测试通过!' if all_tests_passed else '❌ 部分测试失败'}")
    return all_tests_passed

def test_provider_availability():
    """测试Provider可用性检查功能"""
    print(f"\n🔍 测试Provider可用性检查功能...")
    
    # 测试不存在的模型
    payload = {
        "brand_list": ["测试品牌"],
        "selectedModels": [{"name": "NonExistentModel", "checked": True}],
        "customQuestions": ["介绍一下{brandName}"],
        "userLevel": "Free"
    }
    
    response = requests.post(
        "http://127.0.0.1:5001/api/perform-brand-test",
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    if response.status_code == 400:
        try:
            error_data = response.json()
            if 'error' in error_data and 'not registered' in error_data['error']:
                print("   ✅ Provider可用性检查功能正常 - 正确拒绝了未注册的模型")
                return True
        except:
            pass
    
    print(f"   ❌ Provider可用性检查功能异常 - 应该拒绝未注册的模型")
    return False

def main():
    """主函数"""
    print("="*60)
    print("🚀 微信小程序后端启动测试脚本")
    print("="*60)
    
    # 首先检查服务是否运行
    try:
        health_resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if health_resp.status_code == 200:
            print("✅ 后端服务正在运行")
        else:
            print("❌ 后端服务未运行，请先启动服务")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请先启动服务")
        return False
    
    # 运行测试
    basic_test_passed = test_perform_brand_test()
    provider_test_passed = test_provider_availability()
    
    print("\n" + "="*60)
    print("📊 测试结果汇总:")
    print(f"   基础功能测试: {'✅ 通过' if basic_test_passed else '❌ 失败'}")
    print(f"   Provider检查测试: {'✅ 通过' if provider_test_passed else '❌ 失败'}")
    print("="*60)
    
    overall_success = basic_test_passed and provider_test_passed
    print(f"整体结果: {'🎉 全部通过' if overall_success else '❌ 存在问题'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)