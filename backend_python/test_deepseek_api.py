#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DeepSeek API 配置验证与调用测试脚本
用于检查 DeepSeek API 配置是否正确，以及能否成功调用 API
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

def test_env_configuration():
    """测试环境变量配置"""
    print("\n" + "="*60)
    print("1. 环境变量配置检查")
    print("="*60)
    
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    judge_llm_key = os.getenv('JUDGE_LLM_API_KEY')
    
    print(f"DEEPSEEK_API_KEY: {'✅ 已配置' if deepseek_key else '❌ 未配置'}")
    if deepseek_key:
        print(f"  值：sk-...{deepseek_key[-16:]}")
    
    print(f"JUDGE_LLM_API_KEY: {'✅ 已配置' if judge_llm_key else '❌ 未配置'}")
    if judge_llm_key:
        print(f"  值：sk-...{judge_llm_key[-16:]}")
    
    # 检查两个密钥是否相同
    if deepseek_key and judge_llm_key and deepseek_key == judge_llm_key:
        print(f"ℹ️  注意：DEEPSEEK_API_KEY 和 JUDGE_LLM_API_KEY 使用相同的密钥")
    
    return deepseek_key and judge_llm_key

def test_legacy_config():
    """测试 legacy_config 模块"""
    print("\n" + "="*60)
    print("2. Legacy Config 模块检查")
    print("="*60)
    
    try:
        from legacy_config import Config
        
        deepseek_key = Config.get_api_key('deepseek')
        is_configured = Config.is_api_key_configured('deepseek')
        
        print(f"Config.get_api_key('deepseek'): {'✅ 成功' if deepseek_key else '❌ 失败'}")
        if deepseek_key:
            print(f"  值：sk-...{deepseek_key[-16:]}")
        
        print(f"Config.is_api_key_configured('deepseek'): {'✅ True' if is_configured else '❌ False'}")
        
        return is_configured
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_provider_factory():
    """测试 Provider Factory"""
    print("\n" + "="*60)
    print("3. Provider Factory 检查")
    print("="*60)
    
    try:
        from src.adapters.provider_factory import ProviderFactory
        
        available = ProviderFactory.get_available_providers()
        print(f"可用 providers: {available}")
        
        if 'deepseek' in available:
            print("✅ DeepSeek 已在 ProviderFactory 中注册")
            
            # 尝试创建 DeepSeek provider
            try:
                provider = ProviderFactory.create('deepseek')
                print(f"✅ DeepSeek Provider 创建成功")
                print(f"   模型：{provider.model_name}")
                print(f"   平台：{provider.platform_type.value}")
                return provider
            except Exception as e:
                print(f"❌ DeepSeek Provider 创建失败：{e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ DeepSeek 未在 ProviderFactory 中注册")
            print(f"   初始化错误：{ProviderFactory._initialization_errors}")
        
        return None
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return None

def test_deepseek_api_call(provider=None):
    """测试实际的 DeepSeek API 调用"""
    print("\n" + "="*60)
    print("4. DeepSeek API 实际调用测试")
    print("="*60)
    
    if not provider:
        print("❌ 跳过测试：没有可用的 DeepSeek Provider")
        return False
    
    try:
        # 发送一个简单的测试问题
        test_prompt = "你好，请用一句话介绍你自己。"
        print(f"发送测试请求：{test_prompt}")
        
        response = provider.ask_question(test_prompt)
        
        if response.success:
            print("✅ API 调用成功!")
            print(f"   响应内容：{response.content[:100]}...")
            print(f"   模型：{response.model}")
            print(f"   延迟：{response.latency:.2f}s")
            if response.tokens_used:
                print(f"   Token 使用：{response.tokens_used}")
            return True
        else:
            print(f"❌ API 调用失败：{response.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ API 调用异常：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_judge_client():
    """测试 AI Judge Client"""
    print("\n" + "="*60)
    print("5. AI Judge Client 检查")
    print("="*60)
    
    try:
        from ai_judge_module import AIJudgeClient
        
        # 尝试创建 AI Judge Client
        judge_client = AIJudgeClient()
        
        if judge_client.ai_client:
            print("✅ AI Judge Client 初始化成功")
            print(f"   平台：{judge_client.judge_platform}")
            print(f"   模型：{judge_client.judge_model}")
            return judge_client
        else:
            print("❌ AI Judge Client 初始化失败（ai_client 为 None）")
            print(f"   平台：{judge_client.judge_platform}")
            print(f"   模型：{judge_client.judge_model}")
            return None
            
    except Exception as e:
        print(f"❌ AI Judge Client 初始化异常：{e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("DeepSeek API 配置验证与调用测试")
    print("="*60)
    
    # 1. 测试环境变量配置
    env_ok = test_env_configuration()
    
    # 2. 测试 legacy_config 模块
    config_ok = test_legacy_config()
    
    # 3. 测试 Provider Factory
    provider = test_provider_factory()
    
    # 4. 测试实际 API 调用
    api_ok = test_deepseek_api_call(provider)
    
    # 5. 测试 AI Judge Client
    judge_client = test_ai_judge_client()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"环境变量配置：{'✅ 通过' if env_ok else '❌ 失败'}")
    print(f"Config 模块：{'✅ 通过' if config_ok else '❌ 失败'}")
    print(f"Provider 创建：{'✅ 通过' if provider else '❌ 失败'}")
    print(f"API 调用：{'✅ 通过' if api_ok else '❌ 失败'}")
    print(f"AI Judge Client: {'✅ 通过' if judge_client else '❌ 失败'}")
    
    if api_ok:
        print("\n🎉 DeepSeek API 配置正确，可以正常调用!")
    else:
        print("\n⚠️  DeepSeek API 调用失败，请检查上述错误信息")
    
    return api_ok

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
