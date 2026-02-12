#!/usr/bin/env python3
"""
详细分析前端到后端的API调用流程
特别关注豆包API调用的问题
"""

import json
import requests
import time
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

def test_direct_doubao_api():
    """直接测试豆包API调用"""
    print("🔍 直接测试豆包API调用...")
    
    # 获取API密钥和模型ID
    api_key = os.getenv('DOUBAO_API_KEY')
    model_id = os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')
    
    if not api_key or api_key.startswith('YOUR_'):
        print("❌ 未配置有效的豆包API密钥")
        return False
    
    print(f"使用模型ID: {model_id}")
    
    # 构造API请求
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": "你好，请简单介绍一下自己，用一句话回答。"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        print("📡 发送API请求...")
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"⏱️  响应时间: {elapsed:.2f}秒")
        print(f"📊 HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens', 'N/A')
                print(f"✅ API调用成功!")
                print(f"📝 响应内容: {content[:100]}...")
                print(f"🔢 使用token: {tokens_used}")
                return True
            else:
                print(f"❌ API响应格式错误: {json.dumps(result, indent=2)[:500]}")
                return False
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"❌ 错误信息: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ API请求超时")
        return False
    except Exception as e:
        print(f"❌ API请求异常: {e}")
        return False


def test_backend_api_endpoint():
    """测试后端API端点"""
    print("\n🔍 测试后端API端点...")
    
    # 测试数据 - 简化的测试
    test_data = {
        "brand_list": ["测试品牌"],
        "selectedModels": [
            {"name": "豆包", "checked": True}
        ],
        "customQuestions": [
            "介绍一下{brandName}"
        ]
    }
    
    try:
        print("📡 发送品牌测试请求...")
        response = requests.post(
            "http://127.0.0.1:5002/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=10  # 较短的超时时间
        )
        
        print(f"📊 HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('status') == 'success':
                execution_id = response_data.get('executionId')
                print(f"✅ 请求成功，执行ID: {execution_id}")
                
                # 立即检查进度
                progress_response = requests.get(
                    f"http://127.0.0.1:5002/api/test-progress?executionId={execution_id}",
                    timeout=5
                )
                
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    print(f"📈 初始进度: {progress_data.get('progress', 0)}%")
                    print(f"📍 初始状态: {progress_data.get('status', 'unknown')}")
                    
                    return execution_id
                else:
                    print(f"❌ 进度查询失败: {progress_response.status_code}")
                    return execution_id
            else:
                print(f"❌ 后端处理失败: {response_data}")
                return None
        else:
            print(f"❌ API请求失败: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def analyze_model_mapping():
    """分析模型名称映射"""
    print("\n🔍 分析模型名称映射...")
    
    # 检查调度器中的模型映射
    try:
        from wechat_backend.test_engine.scheduler import TestScheduler
        scheduler = TestScheduler()
        
        # 测试"豆包"到平台的映射
        platform = scheduler._map_model_to_platform("豆包")
        print(f"'豆包' 映射到平台: {platform}")
        
        # 测试获取实际模型ID
        actual_id = scheduler._get_actual_model_id("豆包", "doubao")
        print(f"'豆包' 对应的实际模型ID: {actual_id}")
        
        scheduler.shutdown()
        print("✅ 模型映射正常")
        return True
        
    except Exception as e:
        print(f"❌ 模型映射异常: {e}")
        return False


def check_adapter_creation():
    """检查适配器创建"""
    print("\n🔍 检查适配器创建...")
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        api_key = os.getenv('DOUBAO_API_KEY')
        model_id = os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')
        
        if not api_key or api_key.startswith('YOUR_'):
            print("❌ 未配置有效的豆包API密钥")
            return False
        
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, model_id)
        print(f"✅ 适配器创建成功，模型: {adapter.model_name}")
        
        # 测试适配器的基本功能
        print("🧪 测试适配器功能...")
        response = adapter.send_prompt("你好", timeout=10)
        
        if response.success:
            print("✅ 适配器功能正常")
            print(f"📝 响应预览: {response.content[:50]}...")
            return True
        else:
            print(f"❌ 适配器调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ 适配器创建异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🔍 前端到后端API调用详细分析")
    print("="*50)
    
    # 1. 直接测试豆包API
    print("\n1️⃣ 直接测试豆包API")
    api_success = test_direct_doubao_api()
    
    # 2. 分析模型映射
    print("\n2️⃣ 分析模型名称映射")
    mapping_success = analyze_model_mapping()
    
    # 3. 检查适配器创建
    print("\n3️⃣ 检查适配器创建")
    adapter_success = check_adapter_creation()
    
    # 4. 测试后端API端点
    print("\n4️⃣ 测试后端API端点")
    execution_id = test_backend_api_endpoint()
    
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    print(f"   直接API调用: {'✅ 通过' if api_success else '❌ 失败'}")
    print(f"   模型映射: {'✅ 正常' if mapping_success else '❌ 异常'}")
    print(f"   适配器功能: {'✅ 正常' if adapter_success else '❌ 异常'}")
    print(f"   后端API端点: {'✅ 可用' if execution_id else '❌ 问题'}")
    
    if execution_id:
        print(f"   执行ID: {execution_id}")
    
    # 分析可能的问题
    print("\n🔍 问题分析:")
    if not api_success:
        print("   • 豆包API可能存在问题（网络、密钥、模型ID等）")
    if not adapter_success:
        print("   • 适配器创建或调用存在问题")
    if not execution_id:
        print("   • 后端API端点可能存在问题")
    
    return api_success and mapping_success and adapter_success and execution_id is not None


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)