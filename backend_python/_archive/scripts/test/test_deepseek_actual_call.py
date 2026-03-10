#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DeepSeek API 实际调用测试
使用 AIAdapterFactory 直接测试 API 调用
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 设置路径
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

src_dir = os.path.join(base_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

wechat_backend_dir = os.path.join(base_dir, 'wechat_backend')
if wechat_backend_dir not in sys.path:
    sys.path.insert(0, wechat_backend_dir)

# 加载 .env 文件
root_dir = Path(base_dir).parent
env_file = root_dir / '.env'

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载配置文件：{env_file}")
else:
    print(f"❌ 未找到配置文件：{env_file}")
    sys.exit(1)

def test_deepseek_adapter():
    """使用 DeepSeekAdapter 直接测试 API 调用"""
    print("\n" + "="*60)
    print("DeepSeek Adapter API 调用测试")
    print("="*60)
    
    try:
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        from src.adapters.deepseek_adapter import DeepSeekAdapter
        
        api_key = os.getenv('DEEPSEEK_API_KEY')
        print(f"使用 API Key: sk-...{api_key[-16:] if api_key else 'None'}")
        
        if not api_key:
            print("❌ DEEPSEEK_API_KEY 未设置")
            return False
        
        # 创建适配器实例
        adapter = DeepSeekAdapter(
            api_key=api_key,
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=200
        )
        
        print(f"✅ DeepSeekAdapter 创建成功")
        print(f"   模型：{adapter.model_name}")
        print(f"   平台：{adapter.platform_type.value}")
        
        # 发送测试问题
        test_prompt = "你好，请用一句话介绍你自己。"
        print(f"\n发送测试问题：{test_prompt}")
        
        response = adapter.send_prompt(test_prompt)
        
        if response.success:
            print(f"\n✅ API 调用成功!")
            print(f"   响应内容：{response.content[:200]}...")
            print(f"   模型：{response.model}")
            print(f"   平台：{response.platform}")
            print(f"   延迟：{response.latency:.2f}s")
            if response.tokens_used:
                print(f"   Token 使用：{response.tokens_used}")
            return True
        else:
            print(f"\n❌ API 调用失败：{response.error_message}")
            print(f"   错误类型：{response.error_type}")
            return False
            
    except Exception as e:
        print(f"\n❌ 异常：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_factory():
    """使用 AIAdapterFactory 测试 API 调用"""
    print("\n" + "="*60)
    print("AIAdapterFactory API 调用测试")
    print("="*60)
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        api_key = os.getenv('DEEPSEEK_API_KEY')
        
        print(f"使用 API Key: sk-...{api_key[-16:] if api_key else 'None'}")
        
        # 创建客户端
        client = AIAdapterFactory.create('deepseek', api_key, 'deepseek-chat')
        
        print(f"✅ 客户端创建成功")
        
        # 发送测试问题
        test_prompt = "你好，请用一句话介绍你自己。"
        print(f"\n发送测试问题：{test_prompt}")
        
        response = client.send_prompt(test_prompt)
        
        if response.success:
            print(f"\n✅ API 调用成功!")
            print(f"   响应内容：{response.content[:200]}...")
            print(f"   模型：{response.model}")
            print(f"   延迟：{response.latency:.2f}s")
            return True
        else:
            print(f"\n❌ API 调用失败：{response.error_message}")
            return False
            
    except Exception as e:
        print(f"\n❌ 异常：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_judge_llm_config():
    """测试 JUDGE_LLM 配置"""
    print("\n" + "="*60)
    print("JUDGE_LLM 配置测试")
    print("="*60)
    
    try:
        judge_platform = os.getenv('JUDGE_LLM_PLATFORM', 'deepseek')
        judge_model = os.getenv('JUDGE_LLM_MODEL', 'deepseek-chat')
        judge_key = os.getenv('JUDGE_LLM_API_KEY')
        
        print(f"JUDGE_LLM_PLATFORM: {judge_platform}")
        print(f"JUDGE_LLM_MODEL: {judge_model}")
        print(f"JUDGE_LLM_API_KEY: {'✅ 已配置' if judge_key else '❌ 未配置'}")
        
        if not judge_key:
            print("⚠️  JUDGE_LLM_API_KEY 未配置，将使用 DEEPSEEK_API_KEY")
            judge_key = os.getenv('DEEPSEEK_API_KEY')
        
        # 使用 AIAdapterFactory 测试
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        client = AIAdapterFactory.create(judge_platform, judge_key, judge_model)
        print(f"✅ Judge Client 创建成功")
        
        test_prompt = "请判断以下回答是否准确：'地球是圆的'"
        print(f"\n发送测试问题：{test_prompt}")
        
        response = client.send_prompt(test_prompt)
        
        if response.success:
            print(f"\n✅ Judge API 调用成功!")
            print(f"   响应内容：{response.content[:200]}...")
            return True
        else:
            print(f"\n❌ Judge API 调用失败：{response.error_message}")
            return False
            
    except Exception as e:
        print(f"\n❌ 异常：{e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("DeepSeek API 实际调用测试")
    print("="*60)
    
    # 1. 测试 DeepSeekAdapter
    adapter_ok = test_deepseek_adapter()
    
    # 2. 测试 AIAdapterFactory
    factory_ok = test_ai_factory()
    
    # 3. 测试 JUDGE_LLM 配置
    judge_ok = test_judge_llm_config()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"DeepSeekAdapter: {'✅ 通过' if adapter_ok else '❌ 失败'}")
    print(f"AIAdapterFactory: {'✅ 通过' if factory_ok else '❌ 失败'}")
    print(f"JUDGE_LLM: {'✅ 通过' if judge_ok else '❌ 失败'}")
    
    if adapter_ok or factory_ok or judge_ok:
        print("\n🎉 DeepSeek API 可以正常调用!")
        return True
    else:
        print("\n⚠️  DeepSeek API 调用失败，请检查上述错误信息")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
