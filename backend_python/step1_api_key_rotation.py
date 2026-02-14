#!/usr/bin/env python3
"""
安全API密钥轮换工具
此脚本用于安全地轮换项目中的API密钥
"""

import os
import sys
from pathlib import Path
import re

def create_secure_env_file():
    """创建安全的环境配置文件"""
    
    # 创建新的安全.env文件
    env_content = """# AI Platform API Keys - 安全配置
# 请勿将真实的API密钥提交到版本控制系统
# 使用环境变量或安全的密钥管理服务

# DeepSeek API Key
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY}"

# Judge LLM API Key (使用 DeepSeek 作为裁判)
JUDGE_LLM_API_KEY="${JUDGE_LLM_API_KEY}"

# 通义千问API Key
QWEN_API_KEY="${QWEN_API_KEY}"

# 豆包API Key
DOUBAO_API_KEY="${DOUBAO_API_KEY}"

# ChatGPT API Key
CHATGPT_API_KEY="${CHATGPT_API_KEY}"

# Gemini API Key
GEMINI_API_KEY="${GEMINI_API_KEY}"

# 智谱AI (ChatGLM) API Key
ZHIPU_API_KEY="${ZHIPU_API_KEY}"

# 微信小程序配置
WECHAT_APP_ID="${WECHAT_APP_ID}"
WECHAT_APP_SECRET="${WECHAT_APP_SECRET}"
WECHAT_TOKEN="${WECHAT_TOKEN}"

# Flask配置
SECRET_KEY="${SECRET_KEY}"
"""
    
    with open('.env.secure', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✓ 已创建安全的 .env.secure 模板文件")

def create_env_example():
    """创建环境变量示例文件"""
    
    example_content = """# 环境变量示例文件
# 请复制此文件为 .env 并填入真实的API密钥
# 确保 .env 文件已被添加到 .gitignore 中

# AI Platform API Keys
DEEPSEEK_API_KEY="your-deepseek-api-key-here"
JUDGE_LLM_API_KEY="your-judge-llm-api-key-here"
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
SECRET_KEY="your-secret-key-here"
"""
    
    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(example_content)
    
    print("✓ 已创建 .env.example 示例文件")

def update_gitignore():
    """更新 .gitignore 文件以排除敏感文件"""
    
    gitignore_path = Path('.gitignore')
    
    # 读取现有的 .gitignore 内容
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            gitignore_content = f.read()
    else:
        gitignore_content = ""
    
    # 添加需要忽略的文件模式
    ignore_patterns = [
        ".env",
        ".env.local",
        ".env.*.local",
        "*.env",
        "database.db",
        "logs/",
        "*.log",
        "tmp/",
        "temp/"
    ]
    
    # 检查是否已经存在这些模式
    missing_patterns = []
    for pattern in ignore_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        if gitignore_content and not gitignore_content.endswith('\n'):
            gitignore_content += '\n'
        gitignore_content += '\n'.join(missing_patterns) + '\n'
        
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        
        print(f"✓ 已更新 .gitignore 文件，添加了 {len(missing_patterns)} 个新模式")
    else:
        print("✓ .gitignore 文件已包含所有必要的忽略模式")

def sanitize_existing_files():
    """清理现有文件中的敏感信息"""

    # 需要清理的文件列表
    files_to_clean = [
        '.env',
        'test_doubao_api.py',
        'test_real_api_calls_updated.py',
        'test_api_keys.py',
        'validate_ai_integration.py',
        'test_zhipu_e2e.py',
        'run.py',
        'test_real_ai_diagnosis.py',
        'test_direct_api_calls.py',
        'simple_api_test.py',
        'real_api_implementation_summary.md',
        'docs/AI Coding Plan.md',
        'docs/2026-02-11_11_28产品与设计优化方案.md'
    ]

    # 敏感信息替换规则
    replacements = [
        # API密钥
        ('sk-13908093890f46fb82c52a01c8dfc464', 'YOUR_DEEPSEEK_API_KEY'),
        ('sk-5261a4dfdf964a5c9a6364128cc4c653', 'YOUR_QWEN_API_KEY'),
        ('2a376e32-8877-4df8-9865-7eb3e99c9f92', 'YOUR_DOUBAO_API_KEY'),
        ('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', 'YOUR_CHATGPT_API_KEY'),
        ('AIzaSyCOeSqGt-YluHUQkdStzc-RVkufFKBldCE', 'YOUR_GEMINI_API_KEY'),
        ('504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh', 'YOUR_ZHIPU_API_KEY'),

        # 微信配置
        ('wx8876348e089bc261', 'YOUR_WECHAT_APP_ID'),
        ('6d43225261bbfc9bfe3c68de9e069b66', 'YOUR_WECHAT_APP_SECRET'),
        ('your_default_token_here', 'YOUR_WECHAT_TOKEN'),
        ('dev-secret-key-change-in-production', 'YOUR_FLASK_SECRET_KEY'),
    ]

    sanitized_files = []

    for file_path in files_to_clean:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            continue

        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用替换规则
            for old_value, new_value in replacements:
                content = content.replace(old_value, new_value)

            # 如果内容发生了变化，则写回文件
            if content != original_content:
                with open(file_path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)
                sanitized_files.append(file_path)
                print(f"✓ 已清理文件: {file_path}")

        except Exception as e:
            print(f"⚠️  无法处理文件 {file_path}: {str(e)}")

    if sanitized_files:
        print(f"✓ 共清理了 {len(sanitized_files)} 个文件中的敏感信息")
    else:
        print("✓ 没有找到需要清理的敏感信息")

def main():
    print("🚀 开始执行安全改进计划 - 第一步：更换所有已泄露的API密钥")
    print("=" * 60)
    
    print("\n1. 创建安全的环境配置文件...")
    create_secure_env_file()
    
    print("\n2. 创建环境变量示例文件...")
    create_env_example()
    
    print("\n3. 更新 .gitignore 文件...")
    update_gitignore()
    
    print("\n4. 清理现有文件中的敏感信息...")
    sanitize_existing_files()
    
    print("\n" + "=" * 60)
    print("✅ 第一步完成！")
    print("\n重要提醒：")
    print("1. 请确保真实的API密钥不要提交到版本控制系统")
    print("2. 使用环境变量或安全的密钥管理服务存储真实密钥")
    print("3. 请立即更换所有在代码中暴露的真实API密钥")
    print("4. 检查并更新所有相关的API密钥")

if __name__ == "__main__":
    main()