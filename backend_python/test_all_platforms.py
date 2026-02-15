#!/usr/bin/env python3
"""
测试所有AI平台连接
验证DeepSeek、Qwen、Zhipu适配器能否正常工作
"""

import os
import sys
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType


def test_platform(platform_type, platform_name, api_key, model_name, timeout=30):
    """测试单个平台"""
    print(f"\n{'='*60}")
    print(f"测试 {platform_name}")
    print(f"{'='*60}")
    
    try:
        print(f"1. 创建 {platform_name} 适配器...")
        print(f"   Model: {model_name}")
        
        adapter = AIAdapterFactory.create(platform_type, api_key, model_name)
        print(f"   ✅ 适配器创建成功")
        
        print(f"\n2. 测试简单请求...")
        test_prompt = "你好，请用一句话介绍你自己"
        print(f"   Prompt: {test_prompt}")
        
        start_time = time.time()
        response = adapter.send_prompt(test_prompt, timeout=timeout)
        elapsed = time.time() - start_time
        
        print(f"   响应时间: {elapsed:.2f}秒")
        print(f"   成功状态: {response.success}")
        
        if response.success:
            print(f"   ✅ API调用成功")
            print(f"   内容预览: {response.content[:100]}...")
            if hasattr(response, 'tokens_used') and response.tokens_used:
                print(f"   Token使用: {response.tokens_used}")
            print(f"   模型: {response.model}")
            return True
        else:
            print(f"   ❌ API调用失败")
            print(f"   错误: {response.error_message}")
            print(f"   错误类型: {response.error_type}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print("AI平台连接测试")
    print(f"{'='*60}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 从环境变量获取API密钥
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    qwen_key = os.getenv('QWEN_API_KEY')
    zhipu_key = os.getenv('ZHIPU_API_KEY')
    
    print(f"\nAPI密钥状态:")
    print(f"   DeepSeek: {'✅ 已配置' if deepseek_key else '❌ 未配置'}")
    print(f"   通义千问: {'✅ 已配置' if qwen_key else '❌ 未配置'}")
    print(f"   智谱AI: {'✅ 已配置' if zhipu_key else '❌ 未配置'}")
    
    if not all([deepseek_key, qwen_key, zhipu_key]):
        print("\n⚠️  缺少必要的API密钥，无法进行完整测试")
        return 1
    
    results = []
    
    # 测试DeepSeek
    print(f"\n{'='*80}")
    print("开始测试 DeepSeek 平台")
    print(f"{'='*80}")
    results.append(("DeepSeek", test_platform(
        AIPlatformType.DEEPSEEK,
        "DeepSeek",
        deepseek_key,
        "deepseek-chat",
        timeout=30
    )))
    
    # 测试Qwen
    print(f"\n{'='*80}")
    print("开始测试 通义千问 平台")
    print(f"{'='*80}")
    results.append(("通义千问", test_platform(
        AIPlatformType.QWEN,
        "通义千问",
        qwen_key,
        "qwen-max",
        timeout=45
    )))
    
    # 测试Zhipu
    print(f"\n{'='*80}")
    print("开始测试 智谱AI 平台")
    print(f"{'='*80}")
    results.append(("智谱AI", test_platform(
        AIPlatformType.ZHIPU,
        "智谱AI",
        zhipu_key,
        "glm-4",
        timeout=45
    )))
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print(f"\n🎉 所有平台测试通过！")
        print(f"✅ DeepSeek、通义千问、智谱AI均已成功连接")
        print(f"✅ 可以开始MVP接口测试")
        return 0
    else:
        print(f"\n⚠️  部分平台测试失败")
        failed_platforms = [name for name, passed in results if not passed]
        print(f"❌ 失败平台: {', '.join(failed_platforms)}")
        return 1


if __name__ == "__main__":
    exit(main())