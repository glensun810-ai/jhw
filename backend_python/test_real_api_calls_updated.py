"""
测试API调用，处理速率限制问题
"""

import os
import sys
import time

# 设置环境变量中的API密钥
os.environ['DEEPSEEK_API_KEY'] = 'YOUR_DEEPSEEK_API_KEY'
os.environ['DOUBAO_API_KEY'] = 'YOUR_DOUBAO_API_KEY'
os.environ['QWEN_API_KEY'] = 'YOUR_QWEN_API_KEY'
os.environ['ZHIPU_API_KEY'] = 'YOUR_ZHIPU_API_KEY'
os.environ['OPENAI_API_KEY'] = 'YOUR_CHATGPT_API_KEY'
os.environ['GOOGLE_API_KEY'] = 'YOUR_GEMINI_API_KEY'


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
            
        # 创建适配器 - 使用正确的endpoint ID
        adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, 'ep-20260212000000-gd5tq')
        
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
    """测试ChatGPT API - 增加延时处理速率限制"""
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
        
        # 等待一下避免速率限制
        time.sleep(2)
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ ChatGPT API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ ChatGPT API调用失败: {response.error_message}")
            if "Too Many Requests" in response.error_message:
                print("  提示: 遇到速率限制，可能需要等待更长时间或降低请求频率")
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
            if "compatibility issue" in response.error_message:
                print("  提示: Python版本兼容性问题，可能需要使用较低版本的Python")
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