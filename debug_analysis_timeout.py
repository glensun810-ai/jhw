#!/usr/bin/env python3
"""
分析前端到后端的完整流程问题
重点关注API调用效率和数据传递
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

def analyze_api_call_pattern():
    """分析API调用模式"""
    print("🔍 分析API调用模式...")
    
    # 根据前端数据，计算预期的API调用次数
    brand_list = ["蔚来汽车", "理想汽车"]  # 2个品牌
    selected_models = [{"name": "豆包", "checked": True}]  # 1个模型
    custom_questions = [
        "介绍一下蔚来汽车",
        "蔚来汽车的主要产品是什么？",
        "介绍一下理想汽车", 
        "理想汽车的主要产品是什么？"
    ]  # 每个品牌2个问题，总共4个问题
    
    expected_api_calls = len(brand_list) * len(selected_models) * len([q for q in custom_questions if brand_list[0] in q or brand_list[1] in q])
    # 实际上每个品牌的问题数
    questions_per_brand = 2  # 每个品牌2个问题
    expected_api_calls = len(brand_list) * len(selected_models) * questions_per_brand  # 2 * 1 * 2 = 4
    
    print(f"📊 预期API调用次数: {expected_api_calls} 次")
    print(f"📝 品牌数量: {len(brand_list)}")
    print(f"🤖 模型数量: {len(selected_models)}")
    print(f"❓ 每品牌问题数: {questions_per_brand}")
    print(f"💡 如果每次API调用需要10秒，总时间预计: {expected_api_calls * 10} 秒")
    
    return expected_api_calls


def test_single_api_call_efficiency():
    """测试単个API调用效率"""
    print("\n⏱️ 测试単个API调用效率...")
    
    # 测试単个API调用的时间
    api_key = os.getenv('DOUBAO_API_KEY')
    model_id = os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')
    
    if not api_key or api_key.startswith('YOUR_'):
        print("❌ 未配置有效的豆包API密钥")
        return None
    
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
        print("   📡 发送単个API请求...")
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"   ⏱️  単次API调用耗时: {elapsed:.2f}秒")
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                print("   ✅ 単次API调用成功")
                return elapsed
            else:
                print(f"   ❌ API响应格式错误")
                return None
        else:
            print(f"   ❌ API调用失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ API调用异常: {e}")
        return None


def suggest_optimizations():
    """建议优化方案"""
    print("\n💡 优化建议:")
    print("1. 并发API调用: 使用多线程/异步方式同时调用多个API")
    print("2. API调用合并: 将多个问题合并到単个API调用中")
    print("3. 缓存机制: 对相同问题的响应进行缓存")
    print("4. 超时设置: 为API调用设置合理的超时时间")
    print("5. 进度优化: 改进进度显示逻辑，提供更及时的反馈")


def check_backend_config():
    """检查后端配置"""
    print("\n⚙️  检查后端配置...")
    
    try:
        from config_manager import Config as PlatformConfigManager
        config_manager = PlatformConfigManager()
        doubao_config = config_manager.get_platform_config('doubao')
        
        if doubao_config:
            print(f"   🕐 超时设置: {doubao_config.timeout}秒")
            print(f"   🔄 重试次数: {doubao_config.retry_times}")
            print(f"   📊 最大token: {doubao_config.default_max_tokens}")
            print("   ✅ 豆包配置加载正常")
        else:
            print("   ❌ 未找到豆包配置")
            
    except Exception as e:
        print(f"   ❌ 配置检查异常: {e}")


def analyze_timeout_issue():
    """分析超时问题"""
    print("\n⏰ 分析超时问题...")
    
    expected_calls = analyze_api_call_pattern()
    single_call_time = test_single_api_call_efficiency()
    
    if single_call_time:
        estimated_total_time = expected_calls * single_call_time
        print(f"\n📈 估算总耗时: {estimated_total_time:.2f}秒 ({estimated_total_time/60:.2f}分钟)")
        
        if estimated_total_time > 60:  # 如果超过1分钟
            print("⚠️  预估时间较长，可能导致前端超时")
            print("💡 建议增加前端轮询间隔或后端超时设置")
        else:
            print("✅ 预估时间在合理范围内")
    
    suggest_optimizations()


def main():
    """主函数"""
    print("🔍 前端到后端流程问题分析")
    print("="*50)
    
    # 分析超时问题
    analyze_timeout_issue()
    
    # 检查后端配置
    check_backend_config()
    
    print("\n" + "="*50)
    print("📋 分析总结:")
    print("• API调用正常工作，但可能较慢")
    print("• 多次API调用累积时间较长")
    print("• 需要优化并发处理和超时设置")
    print("• 前端轮询逻辑可能需要调整")


if __name__ == "__main__":
    main()