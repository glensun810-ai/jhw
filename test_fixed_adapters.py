#!/usr/bin/env python3
"""
测试修复后的AI适配器
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter
from wechat_backend.ai_adapters.qwen_adapter import QwenAdapter
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter

def test_deepseek():
    """测试DeepSeek适配器"""
    print("Testing DeepSeek Adapter...")
    api_key = os.getenv('DEEPSEEK_API_KEY', 'YOUR_DEEPSEEK_API_KEY')
    adapter = DeepSeekAdapter(api_key, "deepseek-chat")
    
    response = adapter.send_prompt("Hello, how are you?")
    print(f"DeepSeek Response Success: {response.success}")
    if response.success:
        print(f"Content: {response.content[:100]}...")
    else:
        print(f"Error: {response.error_message}")
    print(f"Tokens Used: {response.tokens_used}, Latency: {response.latency:.2f}s\n")

def test_qwen():
    """测试Qwen适配器"""
    print("Testing Qwen Adapter...")
    api_key = os.getenv('QWEN_API_KEY', 'YOUR_QWEN_API_KEY')
    adapter = QwenAdapter(api_key, "qwen-max")
    
    response = adapter.send_prompt("Hello, how are you?")
    print(f"Qwen Response Success: {response.success}")
    if response.success:
        print(f"Content: {response.content[:100]}...")
    else:
        print(f"Error: {response.error_message}")
    print(f"Tokens Used: {response.tokens_used}, Latency: {response.latency:.2f}s\n")

def test_doubao():
    """测试Doubao适配器"""
    print("Testing Doubao Adapter...")
    api_key = os.getenv('DOUBAO_API_KEY', 'YOUR_DOUBAO_API_KEY')
    adapter = DoubaoAdapter(api_key, "Doubao-pro")
    
    response = adapter.send_prompt("Hello, how are you?")
    print(f"Doubao Response Success: {response.success}")
    if response.success:
        print(f"Content: {response.content[:100]}...")
    else:
        print(f"Error: {response.error_message}")
    print(f"Tokens Used: {response.tokens_used}, Latency: {response.latency:.2f}s\n")

def main():
    """主函数"""
    print("Testing Fixed AI Adapters\n")
    
    try:
        test_deepseek()
    except Exception as e:
        print(f"DeepSeek test failed with exception: {e}\n")
    
    try:
        test_qwen()
    except Exception as e:
        print(f"Qwen test failed with exception: {e}\n")
    
    try:
        test_doubao()
    except Exception as e:
        print(f"Doubao test failed with exception: {e}\n")

if __name__ == "__main__":
    main()