#!/usr/bin/env python3
"""
测试真实的AI平台诊断功能
"""
import os
import sys
import time
import requests
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

def test_brand_diagnosis():
    """测试品牌诊断功能"""
    print("=== 测试品牌诊断功能 ===\n")
    
    # 测试端点
    url = "http://127.0.0.1:5001/api/perform-brand-test"
    
    # 测试数据
    test_data = {
        "brand_list": ["苹果"],
        "selectedModels": [
            {"name": "deepseek", "displayName": "DeepSeek"},
            {"name": "qwen", "displayName": "通义千问"}
        ],
        "customQuestions": [
            "介绍一下{brandName}的主要产品",
            "{brandName}的核心竞争力是什么"
        ],
        "apiKey": ""
    }
    
    print("发送品牌诊断请求...")
    print(f"品牌: {test_data['brand_list']}")
    print(f"模型: {[model['displayName'] for model in test_data['selectedModels']]}")
    print(f"问题: {test_data['customQuestions']}\n")
    
    try:
        response = requests.post(url, json=test_data, timeout=120)
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}\n")
            
            if result.get('status') == 'success':
                execution_id = result.get('executionId')
                print(f"执行ID: {execution_id}")
                
                # 获取进度
                progress_url = f"http://127.0.0.1:5001/api/test-progress?executionId={execution_id}"
                print("\n开始轮询进度...")
                
                for i in range(30):  # 最多等待30次轮询
                    time.sleep(2)
                    progress_response = requests.get(progress_url, timeout=30)
                    
                    if progress_response.status_code == 200:
                        progress_data = progress_response.json()
                        progress = progress_data.get('progress', 0)
                        completed = progress_data.get('completed', 0)
                        total = progress_data.get('total', 0)
                        
                        print(f"进度: {progress}% ({completed}/{total})")
                        
                        if progress >= 100:
                            print("\n=== 诊断完成 ===")
                            print(f"总体分数: {progress_data.get('overallScore', 'N/A')}")
                            print(f"总体等级: {progress_data.get('overallGrade', 'N/A')}")
                            
                            results = progress_data.get('results', [])
                            print(f"\n结果数量: {len(results)}")
                            
                            for idx, result in enumerate(results):
                                print(f"\n结果 {idx+1}:")
                                print(f"  AI模型: {result.get('aiModel', 'N/A')}")
                                print(f"  品牌: {result.get('brand', 'N/A')}")
                                print(f"  问题: {result.get('question', 'N/A')}")
                                print(f"  成功: {result.get('success', 'N/A')}")
                                
                                if result.get('success'):
                                    print(f"  分数: {result.get('score', 'N/A')}")
                                    print(f"  回答: {result.get('response', 'N/A')[:100]}...")
                                else:
                                    print(f"  错误: {result.get('error_message', 'N/A')}")
                            
                            return progress_data
                    else:
                        print(f"进度查询失败，状态码: {progress_response.status_code}")
                        break
                        
            else:
                print(f"请求失败: {result}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    
    return None

def test_individual_platforms():
    """测试各个AI平台的独立连接"""
    print("\n=== 测试各AI平台独立连接 ===\n")
    
    platforms = [
        {"name": "deepseek", "endpoint": "/api/deepseek/test", "display": "DeepSeek"},
        {"name": "qwen", "endpoint": "/api/qwen/test", "display": "通义千问"},
        {"name": "doubao", "endpoint": "/api/doubao/test", "display": "豆包"}
    ]
    
    for platform in platforms:
        print(f"测试 {platform['display']} 平台...")
        try:
            test_url = f"http://127.0.0.1:5001{platform['endpoint']}"
            response = requests.post(test_url, json={"prompt": "你好，请简单介绍一下自己"}, timeout=30)
            print(f"{platform['display']} 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  成功: {result.get('success', 'N/A')}")
                if result.get('success'):
                    print(f"  内容: {result.get('content', '')[:100]}...")
                else:
                    print(f"  错误: {result.get('error_message', 'N/A')}")
            else:
                print(f"  错误: {response.text[:200]}")
        except Exception as e:
            print(f"  连接错误: {e}")
        print()

def main():
    """主函数"""
    print("开始测试真实的AI平台诊断功能...\n")
    
    # 首先测试各个平台的独立连接
    test_individual_platforms()
    
    # 然后测试品牌诊断功能
    test_brand_diagnosis()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()