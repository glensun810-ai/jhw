#!/usr/bin/env python3
"""
豆包API配置检查脚本
用于诊断API连接问题
"""
import os
import sys
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_doubao_config():
    """检查豆包API配置"""
    print("=" * 60)
    print("豆包API配置检查")
    print("=" * 60)
    
    # 检查API密钥
    api_key = os.getenv('DOUBAO_API_KEY')
    if not api_key:
        print("❌ DOUBAO_API_KEY 未设置")
        print("   请在 .env 文件中设置 DOUBAO_API_KEY")
        return False
    
    if api_key.startswith('your-') or api_key.startswith('YOUR_'):
        print("❌ DOUBAO_API_KEY 是占位符值")
        print("   请替换为真实的API密钥")
        return False
    
    print(f"✅ DOUBAO_API_KEY 已设置: {api_key[:10]}...{api_key[-4:]}")
    
    # 检查模型ID
    model_id = os.getenv('DOUBAO_MODEL_ID')
    if not model_id:
        print("⚠️  DOUBAO_MODEL_ID 未设置，将使用默认值")
        print("   建议设置 DOUBAO_MODEL_ID 以获得更好的效果")
        model_id = 'Doubao-pro'
    else:
        print(f"✅ DOUBAO_MODEL_ID: {model_id}")
    
    # 测试API连接
    print("\n" + "-" * 60)
    print("测试API连接...")
    print("-" * 60)
    
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API连接成功！")
            result = response.json()
            if 'choices' in result:
                print(f"响应内容: {result['choices'][0]['message']['content'][:50]}...")
            return True
        elif response.status_code == 401:
            print("❌ API密钥无效 (401)")
            print("   请检查 DOUBAO_API_KEY 是否正确")
            return False
        elif response.status_code == 404:
            print("❌ API端点或模型ID不存在 (404)")
            print(f"   请检查 DOUBAO_MODEL_ID 是否正确: {model_id}")
            print("   模型ID格式应为: ep-XXXXXXXXXXXXXXXX-XXXX")
            return False
        else:
            print(f"❌ API请求失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误")
        return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False

def main():
    success = check_doubao_config()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 豆包API配置正确，可以正常使用")
    else:
        print("❌ 豆包API配置有问题，请检查上述错误")
        print("\n修复步骤:")
        print("1. 在 backend_python/.env 文件中设置正确的 DOUBAO_API_KEY")
        print("2. 设置正确的 DOUBAO_MODEL_ID (如: ep-20260212000000-gd5tq)")
        print("3. 重启后端服务")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
