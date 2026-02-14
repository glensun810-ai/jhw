#!/usr/bin/env python3
"""
简单测试API密钥是否有效
"""
import os
import requests
import json

def test_deepseek_api():
    """测试DeepSeek API"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        return False
    
    print(f"🔍 测试DeepSeek API连接...")
    print(f"API Key前缀: {api_key[:8]}...")
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Hello, please respond with just 'Hello'."}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ DeepSeek API 连接成功!")
            print(f"Response: {result['choices'][0]['message']['content'][:50]}...")
            return True
        else:
            print(f"❌ DeepSeek API 错误: {response.status_code}")
            print(f"Error: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ DeepSeek API 请求失败: {e}")
        return False

def test_qwen_api():
    """测试Qwen API"""
    api_key = os.getenv('QWEN_API_KEY')
    if not api_key:
        print("\n❌ QWEN_API_KEY 未设置")
        return False
    
    print(f"\n🔍 测试Qwen API连接...")
    print(f"API Key前缀: {api_key[:8]}...")
    
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {"role": "user", "content": "Hello, please respond with just 'Hello'."}
            ]
        },
        "parameters": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if 'output' in result and 'text' in result['output']:
                print(f"✅ Qwen API 连接成功!")
                print(f"Response: {result['output']['text'][:50]}...")
                return True
            else:
                print(f"⚠️ Qwen API 响应格式不符: {result}")
                return False
        else:
            print(f"❌ Qwen API 错误: {response.status_code}")
            print(f"Error: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Qwen API 请求失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 开始测试API密钥有效性...\n")
    
    deepseek_ok = test_deepseek_api()
    qwen_ok = test_qwen_api()
    
    print(f"\n📊 测试结果:")
    print(f"DeepSeek: {'✅ 有效' if deepseek_ok else '❌ 无效'}")
    print(f"Qwen: {'✅ 有效' if qwen_ok else '❌ 无效'}")
    
    if deepseek_ok or qwen_ok:
        print("\n🎉 至少有一个API密钥有效，AI搜索平台可以正常工作!")
    else:
        print("\n❌ 所有API密钥都无效，需要更新密钥才能使用AI搜索功能。")

if __name__ == "__main__":
    main()