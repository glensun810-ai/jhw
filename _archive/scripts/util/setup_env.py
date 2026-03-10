#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境配置助手
用于设置后端所需的API密钥和环境变量
"""

import os
from pathlib import Path

def setup_environment():
    """设置环境变量配置文件"""
    print("🔍 检查环境配置...")
    
    # 检查是否存在 .env 文件
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ 已找到 .env 文件")
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'DEEPSEEK_API_KEY' in content:
                print("✅ 检测到 DEEPSEEK_API_KEY 配置")
            else:
                print("❌ 未找到 DEEPSEEK_API_KEY 配置")
                
            if 'DOUBAO_API_KEY' in content:
                print("✅ 检测到 DOUBAO_API_KEY 配置")
            else:
                print("❌ 未找到 DOUBAO_API_KEY 配置")
    else:
        print("❌ 未找到 .env 文件，正在创建示例配置...")
        
        # 创建 .env 文件
        env_example_content = '''# AI Platform API Keys
# 请替换为你自己的API密钥
DEEPSEEK_API_KEY="sk-your-deepseek-api-key-here"
QWEN_API_KEY="your-qwen-api-key-here"
DOUBAO_API_KEY="your-doubao-api-key-here"
CHATGPT_API_KEY="your-chatgpt-api-key-here"
GEMINI_API_KEY="your-gemini-api-key-here"
ZHIPU_API_KEY="your-zhipu-api-key-here"

# 微信小程序配置
WECHAT_APP_ID="your-wechat-app-id"
WECHAT_APP_SECRET="your-wechat-app-secret"
WECHAT_TOKEN="your-wechat-token"

# Flask配置
SECRET_KEY="your-secret-key-for-production-here"
'''
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_example_content)
        
        print("✅ 已创建 .env 文件，请填入真实的API密钥")

    # 检查当前环境变量
    print("\n🔍 检查当前环境变量...")
    
    required_vars = [
        'DEEPSEEK_API_KEY',
        'QWEN_API_KEY', 
        'DOUBAO_API_KEY',
        'CHATGPT_API_KEY',
        'GEMINI_API_KEY',
        'ZHIPU_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少以下环境变量: {', '.join(missing_vars)}")
        print("💡 请确保 .env 文件中的变量已正确设置，或者在系统中设置了相应的环境变量")
    else:
        print("✅ 所有必需的环境变量均已设置")

    print("\n💡 提示:")
    print("- 如果你只使用DeepSeek，至少要设置 DEEPSEEK_API_KEY")
    print("- 你可以从 https://platform.deepseek.com/ 获取API密钥")
    print("- 对于豆包，可以从 https://www.doubao.com/ 获取API密钥")
    print("- 请确保API密钥已正确粘贴，不要包含引号")
    print("- 重启后端服务以加载新的环境变量")

def check_backend_status():
    """检查后端服务状态"""
    print("\n🔍 检查后端服务状态...")
    
    try:
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'python' in result.stdout and ('run.py' in result.stdout or 'wechat_backend' in result.stdout):
            print("✅ 检测到后端服务正在运行")
        else:
            print("ℹ️  后端服务似乎未运行")
            print("💡 请运行以下命令启动后端服务:")
            print("   cd backend_python && python run.py")
    except Exception as e:
        print(f"⚠️  无法检查后端服务状态: {e}")

if __name__ == "__main__":
    print("🚀 AI品牌战略诊断系统 - 环境配置助手")
    print("=" * 50)
    
    setup_environment()
    check_backend_status()
    
    print("\n" + "=" * 50)
    print("📋 配置完成后，请执行以下步骤:")
    print("1. 编辑 .env 文件，填入真实的API密钥")
    print("2. 重启后端服务")
    print("3. 确保前端和后端端口配置正确")
    print("4. 再次尝试启动品牌诊断任务")