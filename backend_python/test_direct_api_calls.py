#!/usr/bin/env python3
"""
直接测试API调用格式
"""
import os
import requests
import json

def test_deepseek_api_call():
    """直接测试DeepSeek API调用"""
    print("🔍 测试DeepSeek API调用格式...")
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        return False
        
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
            print(f"✅ DeepSeek API 调用成功!")
            print(f"Response: {result['choices'][0]['message']['content'][:100]}...")
            return True
        else:
            print(f"❌ DeepSeek API 错误: {response.status_code}")
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ DeepSeek API 请求失败: {e}")
        return False

def test_qwen_api_call():
    """直接测试Qwen API调用"""
    print("\n🔍 测试Qwen API调用格式...")
    
    api_key = os.getenv('QWEN_API_KEY')
    if not api_key:
        print("❌ QWEN_API_KEY 未设置")
        return False
        
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
                print(f"✅ Qwen API 调用成功!")
                print(f"Response: {result['output']['text'][:100]}...")
                return True
            else:
                print(f"⚠️ Qwen API 响应格式不符: {json.dumps(result, indent=2)[:500]}")
                return False
        else:
            print(f"❌ Qwen API 错误: {response.status_code}")
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ Qwen API 请求失败: {e}")
        return False

def test_doubao_api_call():
    """直接测试Doubao API调用"""
    print("\n🔍 测试Doubao API调用格式...")
    
    api_key = os.getenv('DOUBAO_API_KEY')
    if not api_key:
        print("❌ DOUBAO_API_KEY 未设置")
        return False
        
    # 根据字节跳动文档，正确的API端点可能是这样的
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "ep-20240520111905-bavcb",  # 示例模型ID，需要替换为实际模型
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
            if 'choices' in result and len(result['choices']) > 0:
                print(f"✅ Doubao API 调用成功!")
                print(f"Response: {result['choices'][0]['message']['content'][:100]}...")
                return True
            else:
                print(f"⚠️ Doubao API 响应格式不符: {json.dumps(result, indent=2)[:500]}")
                return False
        else:
            print(f"❌ Doubao API 错误: {response.status_code}")
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ Doubao API 请求失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始测试API调用格式...\n")
    
    deepseek_ok = test_deepseek_api_call()
    qwen_ok = test_qwen_api_call()
    doubao_ok = test_doubao_api_call()
    
    print(f"\n📊 直接API测试结果:")
    print(f"DeepSeek: {'✅ 通过' if deepseek_ok else '❌ 失败'}")
    print(f"Qwen: {'✅ 通过' if qwen_ok else '❌ 失败'}")
    print(f"Doubao: {'✅ 通过' if doubao_ok else '❌ 失败'}")
    
    if deepseek_ok and qwen_ok:
        print("\n🎉 直接API调用测试成功！问题可能出在适配器实现上。")
    else:
        print("\n⚠️  直接API调用测试部分失败，需要检查API密钥或端点。")

if __name__ == "__main__":
    main()