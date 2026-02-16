#!/usr/bin/env python3
"""
测试所有AI平台适配器是否正常工作
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType
from wechat_backend.circuit_breaker import get_all_circuit_breaker_states, reset_all_circuit_breakers

def test_ai_platform(platform_name: str, test_prompt: str = "你好，请简单回复"):
    """测试单个AI平台"""
    print(f"\n{'='*60}")
    print(f"测试平台: {platform_name}")
    print(f"{'='*60}")
    
    try:
        # 尝试创建适配器实例
        if not AIAdapterFactory.is_platform_available(platform_name):
            print(f"❌ 平台 {platform_name} 不可用（未注册）")
            return False
        
        # 获取API密钥（这里假设密钥已配置在环境中）
        from wechat_backend.config_manager import config_manager
        api_key = config_manager.get_api_key(platform_name)
        
        if not api_key:
            print(f"❌ 平台 {platform_name} 缺少API密钥")
            return False
        
        # 获取默认模型名
        model_name = config_manager.get_platform_model(platform_name) or f"default-{platform_name}-model"
        
        print(f"使用模型: {model_name}")
        print(f"API密钥存在: {'是' if api_key else '否'}")
        
        # 创建适配器
        adapter = AIAdapterFactory.create(
            platform_type=platform_name,
            api_key=api_key,
            model_name=model_name
        )
        
        print(f"✅ 适配器创建成功: {type(adapter).__name__}")
        
        # 测试发送请求
        print(f"发送测试请求: {test_prompt[:30]}...")
        start_time = time.time()
        
        response = adapter.send_prompt(test_prompt)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ 请求完成，耗时: {duration:.2f}秒")
        print(f"   成功: {response.success}")
        print(f"   模型: {response.model}")
        print(f"   平台: {response.platform}")
        print(f"   延迟: {response.latency:.2f}秒")
        print(f"   令牌数: {response.tokens_used}")
        
        if response.success:
            print(f"   内容预览: {response.content[:100]}...")
            print(f"✅ 平台 {platform_name} 测试成功")
            return True
        else:
            print(f"❌ 平台 {platform_name} 请求失败")
            print(f"   错误信息: {response.error_message}")
            print(f"   错误类型: {response.error_type}")
            return False
            
    except Exception as e:
        print(f"❌ 平台 {platform_name} 测试异常: {e}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False


def main():
    """主测试函数"""
    print("AI平台适配器测试工具")
    print("="*60)
    
    # 首先重置所有熔断器
    print("正在重置所有熔断器...")
    reset_all_circuit_breakers()
    
    # 显示熔断器初始状态
    print("\n熔断器初始状态:")
    initial_states = get_all_circuit_breaker_states()
    for name, state in initial_states.items():
        print(f"  {name}: {state['state']} (失败计数: {state['failure_count']}/{state['failure_threshold']})")
    
    # 定义要测试的平台
    platforms_to_test = [
        "doubao",      # 豆包
        "qwen",        # 通义千问
        "zhipu",       # 智谱AI
        "deepseek",    # DeepSeek
        "deepseekr1",  # DeepSeek R1
    ]
    
    # 测试每个平台
    results = {}
    for platform in platforms_to_test:
        results[platform] = test_ai_platform(platform)
    
    # 显示最终结果
    print(f"\n{'='*60}")
    print("测试结果汇总:")
    print(f"{'='*60}")
    
    total_tests = len(results)
    successful_tests = sum(1 for success in results.values() if success)
    
    for platform, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {platform}: {status}")
    
    print(f"\n总计: {successful_tests}/{total_tests} 个平台通过测试")
    
    # 显示最终熔断器状态
    print(f"\n最终熔断器状态:")
    final_states = get_all_circuit_breaker_states()
    for name, state in final_states.items():
        print(f"  {name}: {state['state']} (失败计数: {state['failure_count']}/{state['failure_threshold']})")


if __name__ == "__main__":
    main()