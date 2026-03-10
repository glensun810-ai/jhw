#!/usr/bin/env python3
"""
API Key 配置补充脚本

功能：
1. 检查当前 .env 文件中的 API Key 配置
2. 补充缺失的 ChatGPT 和 Wenxin API Key 配置项
3. 提供配置获取指南

使用方法:
    cd /Users/sgl/PycharmProjects/PythonProject
    python3 backend_python/scripts/supplement_api_keys.py
"""

import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / '.env'
ENV_EXAMPLE_FILE = PROJECT_ROOT / '.env.example'

# 需要补充的 API Key 配置
MISSING_API_KEYS = {
    'OPENAI_API_KEY': {
        'alias': 'CHATGPT_API_KEY',
        'platform': 'ChatGPT/OpenAI',
        'get_key_url': 'https://platform.openai.com/api-keys',
        'description': 'OpenAI API Key，用于 ChatGPT 平台诊断'
    },
    'BAIDU_API_KEY': {
        'alias': 'WENXIN_API_KEY',
        'platform': '文心一言/百度',
        'get_key_url': 'https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilkryb8zt',
        'description': '百度 API Key，用于文心一言平台诊断'
    }
}


def check_env_file():
    """检查 .env 文件是否存在"""
    if not ENV_FILE.exists():
        print(f"❌ .env 文件不存在：{ENV_FILE}")
        print(f"💡 请复制 .env.example 创建 .env 文件:")
        print(f"   cp {ENV_EXAMPLE_FILE} {ENV_FILE}")
        return False
    return True


def load_env_config():
    """加载 .env 文件配置"""
    config = {}
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                config[key] = value
    return config


def check_api_keys(config):
    """检查 API Key 配置状态"""
    print("\n" + "=" * 60)
    print("📋 API Key 配置检查报告")
    print("=" * 60 + "\n")
    
    missing = []
    configured = []
    
    for env_key, info in MISSING_API_KEYS.items():
        alias_key = info.get('alias', env_key)
        
        # 检查两个键名（主键和别名）
        has_key = env_key in config or alias_key in config
        
        if has_key:
            value = config.get(env_key) or config.get(alias_key, '')
            if value and value not in ['your-api-key-here', 'your-openai-api-key-here', 
                                       'your-baidu-api-key-here', 'your-chatgpt-api-key-here',
                                       'your-wenxin-api-key-here']:
                configured.append((env_key, info))
            else:
                missing.append((env_key, info))
        else:
            missing.append((env_key, info))
    
    # 打印结果
    print("✅ 已配置的 API Key:")
    if configured:
        for key, info in configured:
            print(f"   ✓ {info['platform']} ({key})")
    else:
        print("   (无)")
    
    print("\n❌ 缺失的 API Key:")
    if missing:
        for key, info in missing:
            print(f"   ✗ {info['platform']} ({key})")
            print(f"     说明：{info['description']}")
            print(f"     获取：{info['get_key_url']}")
    else:
        print("   (无)")
    
    print("\n" + "=" * 60)
    
    return len(missing) == 0, missing


def supplement_api_keys(config):
    """补充缺失的 API Key 配置"""
    print("\n📝 开始补充 API Key 配置...\n")
    
    # 读取当前 .env 文件内容
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 检查是否已有相关配置行
    new_lines = []
    added_keys = []
    
    for env_key, info in MISSING_API_KEYS.items():
        alias_key = info.get('alias', env_key)
        
        # 检查是否已存在
        exists = False
        for line in lines:
            if line.strip().startswith(f'{env_key}=') or line.strip().startswith(f'{alias_key}='):
                exists = True
                break
        
        if not exists:
            # 添加新配置
            default_value = f"your-{env_key.split('_')[0].lower()}-api-key-here"
            new_config = f"\n# {info['platform']} API Key (补充配置)\n{env_key}=\"{default_value}\"\n"
            new_lines.append(new_config)
            added_keys.append((env_key, info))
    
    # 写入文件
    if new_lines:
        with open(ENV_FILE, 'a', encoding='utf-8') as f:
            f.write("\n# ==================== 补充配置 ====================\n")
            for line in new_lines:
                f.write(line)
        
        print("✅ 已补充以下配置项到 .env 文件:")
        for key, info in added_keys:
            print(f"   - {key} (用于 {info['platform']})")
        print(f"\n📁 文件位置：{ENV_FILE}")
        print("\n💡 请编辑 .env 文件，填入真实的 API Key:")
        for key, info in added_keys:
            print(f"   {key}=\"your-actual-api-key-here\"")
            print(f"   获取方式：{info['get_key_url']}")
    else:
        print("✅ 所有配置项已存在，无需补充")
    
    return len(added_keys) > 0


def print_manual_instructions():
    """打印手动配置说明"""
    print("\n" + "=" * 60)
    print("📖 手动配置指南")
    print("=" * 60 + "\n")
    
    print("1️⃣ 编辑 .env 文件:")
    print(f"   {ENV_FILE}\n")
    
    print("2️⃣ 添加或修改以下配置:\n")
    
    print("   # ChatGPT/OpenAI 配置")
    print("   OPENAI_API_KEY=\"sk-your-actual-openai-key\"")
    print("   CHATGPT_API_KEY=\"sk-your-actual-openai-key\"\n")
    
    print("   # 文心一言/百度配置")
    print("   BAIDU_API_KEY=\"your-actual-baidu-key\"")
    print("   WENXIN_API_KEY=\"your-actual-baidu-key\"\n")
    
    print("3️⃣ 获取 API Key:\n")
    print("   OpenAI (ChatGPT):")
    print("   👉 https://platform.openai.com/api-keys\n")
    print("   百度 (文心一言):")
    print("   👉 https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilkryb8zt\n")
    
    print("4️⃣ 重启应用使配置生效:")
    print("   cd /Users/sgl/PycharmProjects/PythonProject")
    print("   # 停止当前运行的服务 (Ctrl+C)")
    print("   # 重新启动")
    print("   cd backend_python && python3 wechat_backend/app.py\n")
    
    print("=" * 60)


def verify_after_supplement():
    """验证补充后的配置"""
    print("\n🔍 验证配置...\n")
    
    # 重新加载配置
    config = load_env_config()
    
    all_configured = True
    for env_key, info in MISSING_API_KEYS.items():
        alias_key = info.get('alias', env_key)
        value = config.get(env_key) or config.get(alias_key, '')
        
        if value and value not in ['your-api-key-here', 'your-openai-api-key-here', 
                                   'your-baidu-api-key-here', 'your-chatgpt-api-key-here',
                                   'your-wenxin-api-key-here']:
            print(f"   ✅ {info['platform']} ({env_key}) - 已配置")
        else:
            print(f"   ⚠️  {info['platform']} ({env_key}) - 待配置")
            all_configured = False
    
    print()
    return all_configured


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 API Key 配置补充工具")
    print("=" * 60)
    
    # 检查 .env 文件
    if not check_env_file():
        sys.exit(1)
    
    # 加载配置
    config = load_env_config()
    
    # 检查 API Key
    all_valid, missing = check_api_keys(config)
    
    if all_valid:
        print("\n✅ 所有必需的 API Key 已配置!")
        print("\n💡 提示：如果诊断功能正常工作，可以忽略此脚本。")
        print("   只有当你需要使用 ChatGPT 或文心一言平台时才需要配置。")
    else:
        # 补充缺失的配置
        supplement_api_keys(config)
        
        # 打印手动配置说明
        print_manual_instructions()
        
        # 验证
        if verify_after_supplement():
            print("\n✅ 配置验证通过!")
            print("\n💡 请重启应用使配置生效。")
        else:
            print("\n⚠️  仍有 API Key 未配置，但不影响其他平台使用。")
            print("   当前可用平台：DeepSeek, Qwen, Doubao, Gemini, Zhipu")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
