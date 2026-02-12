#!/usr/bin/env python3
"""
测试AI平台API密钥有效性
"""
import os
import requests
import time
from typing import Dict, Any

def test_deepseek_api(api_key: str):
    """测试DeepSeek API密钥"""
    print("Testing DeepSeek API...")
    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"DeepSeek API Response Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ DeepSeek API key is valid")
            return True
        else:
            print(f"✗ DeepSeek API Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ DeepSeek API Request failed: {e}")
        return False

def test_qwen_api(api_key: str):
    """测试Qwen API密钥"""
    print("\nTesting Qwen API...")
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "qwen-turbo",
        "input": {
            "messages": [{"role": "user", "content": "Hello"}]
        },
        "parameters": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Qwen API Response Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Qwen API key is valid")
            return True
        else:
            print(f"✗ Qwen API Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Qwen API Request failed: {e}")
        return False

def test_doubao_api(api_key: str):
    """测试Doubao API密钥"""
    print("\nTesting Doubao API...")
    # 根据字节跳动文档，Doubao API端点可能不同
    # 这里使用通用的字节跳动API端点
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "ep-20240520111905-bavcb",  # 示例模型ID，需要替换为实际模型
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Doubao API Response Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Doubao API key is valid")
            return True
        else:
            print(f"✗ Doubao API Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Doubao API Request failed: {e}")
        return False

def main():
    """主函数"""
    print("Testing AI Platform API Keys\n")
    
    # 从环境变量读取API密钥
    deepseek_key = os.getenv('DEEPSEEK_API_KEY', 'YOUR_DEEPSEEK_API_KEY')
    qwen_key = os.getenv('QWEN_API_KEY', 'YOUR_QWEN_API_KEY')
    doubao_key = os.getenv('DOUBAO_API_KEY', 'YOUR_DOUBAO_API_KEY')
    
    print(f"Testing with keys:")
    print(f"- DeepSeek: {deepseek_key[:6]}..." if len(deepseek_key) > 6 else "- DeepSeek: {deepseek_key}")
    print(f"- Qwen: {qwen_key[:6]}..." if len(qwen_key) > 6 else "- Qwen: {qwen_key}")
    print(f"- Doubao: {doubao_key[:6]}..." if len(doubao_key) > 6 else "- Doubao: {doubao_key}")
    
    results = {}
    results['deepseek'] = test_deepseek_api(deepseek_key)
    results['qwen'] = test_qwen_api(qwen_key)
    results['doubao'] = test_doubao_api(doubao_key)
    
    print(f"\nTest Results:")
    for platform, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"- {platform.capitalize()}: {status}")
    
    return results

if __name__ == "__main__":
    main()