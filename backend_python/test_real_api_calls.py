"""
测试真实API调用
"""

import os
import sys
import time

# 设置环境变量中的API密钥
os.environ['DEEPSEEK_API_KEY'] = 'sk-13908093890f46fb82c52a01c8dfc464'
os.environ['DOUBAO_API_KEY'] = '2a376e32-8877-4df8-9865-7eb3e99c9f92'
os.environ['QWEN_API_KEY'] = 'sk-5261a4dfdf964a5c9a6364128cc4c653'
os.environ['ZHIPU_API_KEY'] = '504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh'
os.environ['OPENAI_API_KEY'] = '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'
os.environ['GOOGLE_API_KEY'] = 'AIzaSyCOeSqGt-YluHUQkdStzc-RVkufFKBldCE'

def test_deepseek_api():
    """测试DeepSeek API"""
    print("=== 测试DeepSeek API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("✗ DeepSeek API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.DEEPSEEK, api_key, 'deepseek-chat')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ DeepSeek API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            print(f"  Token数: {response.tokens_used}")
            return True
        else:
            print(f"✗ DeepSeek API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ DeepSeek API测试异常: {e}")
        return False


def test_qwen_api():
    """测试Qwen API"""
    print("\n=== 测试Qwen API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('QWEN_API_KEY')
        if not api_key:
            print("✗ Qwen API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.QWEN, api_key, 'qwen-turbo')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ Qwen API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ Qwen API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ Qwen API测试异常: {e}")
        return False


def test_doubao_api():
    """测试Doubao API"""
    print("\n=== 测试Doubao API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('DOUBAO_API_KEY')
        if not api_key:
            print("✗ Doubao API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, 'ernie-bot-4')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ Doubao API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ Doubao API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ Doubao API测试异常: {e}")
        return False


def test_chatgpt_api():
    """测试ChatGPT API"""
    print("\n=== 测试ChatGPT API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("✗ ChatGPT API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.CHATGPT, api_key, 'gpt-3.5-turbo')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ ChatGPT API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ ChatGPT API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ ChatGPT API测试异常: {e}")
        return False


def test_zhipu_api():
    """测试智谱API"""
    print("\n=== 测试智谱API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('ZHIPU_API_KEY')
        if not api_key:
            print("✗ 智谱API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.ZHIPU, api_key, 'glm-4')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ 智谱API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ 智谱API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ 智谱API测试异常: {e}")
        return False


def test_gemin_api():
    """测试Gemini API"""
    print("\n=== 测试Gemini API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("✗ Gemini API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.GEMINI, api_key, 'gemini-pro')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ Gemini API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ Gemini API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ Gemini API测试异常: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试真实API调用...\n")
    
    results = []
    
    # 测试各个API
    results.append(("DeepSeek", test_deepseek_api()))
    results.append(("Qwen", test_qwen_api()))
    results.append(("Doubao", test_doubao_api()))
    results.append(("ChatGPT", test_chatgpt_api()))
    results.append(("智谱", test_zhipu_api()))
    results.append(("Gemini", test_gemin_api()))
    
    print(f"\n=== 测试总结 ===")
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}: {'成功' if success else '失败'}")
    
    total_success = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\n总计: {total_success}/{total_tests} 个API调用成功")
    
    if total_success > 0:
        print("✅ 部分或全部API测试成功！真实API调用已验证。")
        return True
    else:
        print("❌ 所有API测试失败，请检查API密钥和网络连接。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)