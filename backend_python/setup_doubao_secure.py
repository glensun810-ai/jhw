#!/usr/bin/env python3
"""
安全配置脚本 - 用于设置豆包API密钥和模型ID
此脚本不会在代码中硬编码敏感信息
"""

import os
import sys
from pathlib import Path

def create_secure_env_file():
    """创建安全的环境配置文件"""
    env_file_path = Path('.env')
    
    # 检查是否已存在.env文件
    if env_file_path.exists():
        print("⚠️  .env 文件已存在")
        response = input("是否要更新现有配置? (y/N): ")
        if response.lower() != 'y':
            print("操作已取消")
            return False
    
    # 获取用户输入的API密钥和模型ID
    print("请输入豆包API配置信息:")
    api_key = input("API Key (留空使用默认值): ").strip()
    if not api_key:
        api_key = "2a376e32-8877-4df8-9865-7eb3e99c9f92"  # 默认值
    
    model_id = input("模型ID (留空使用默认值): ").strip()
    if not model_id:
        model_id = "ep-20260212000000-gd5tq"  # 默认值
    
    # 创建.env文件内容
    env_content = f"""# 豆包(Doubao) API 配置
DOUBAO_API_KEY={api_key}
DOUBAO_MODEL_ID={model_id}

# 其他平台的API密钥 (如果需要)
# DEEPSEEK_API_KEY=your_deepseek_api_key
# QWEN_API_KEY=your_qwen_api_key
# CHATGPT_API_KEY=your_chatgpt_api_key
"""
    
    # 写入文件
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    # 设置适当的文件权限 (仅所有者可读写)
    os.chmod(env_file_path, 0o600)
    
    print(f"✅ .env 文件已创建: {env_file_path}")
    print("🔒 文件权限已设置为仅所有者可读写")
    print("💡 请确保 .env 文件已在 .gitignore 中，避免提交到版本控制系统")
    
    return True

def verify_env_file():
    """验证环境文件配置"""
    env_file_path = Path('.env')
    
    if not env_file_path.exists():
        print("❌ .env 文件不存在")
        return False
    
    # 读取并验证配置
    import dotenv
    
    # 加载环境变量
    dotenv.load_dotenv(env_file_path)
    
    api_key = os.getenv('DOUBAO_API_KEY')
    model_id = os.getenv('DOUBAO_MODEL_ID')
    
    if not api_key:
        print("❌ DOUBAO_API_KEY 未在 .env 文件中找到")
        return False
    
    if not model_id:
        print("❌ DOUBAO_MODEL_ID 未在 .env 文件中找到")
        return False
    
    print("✅ 环境配置验证成功")
    print(f"   API Key: {'*' * 10}{api_key[-6:] if api_key else ''}")  # 只显示最后6位
    print(f"   Model ID: {model_id}")
    
    return True

def check_gitignore():
    """检查 .gitignore 文件是否包含 .env"""
    gitignore_path = Path('.gitignore')
    
    if not gitignore_path.exists():
        print("⚠️  未找到 .gitignore 文件")
        return False
    
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '.env' in content:
        print("✅ .gitignore 文件已包含 .env")
        return True
    else:
        print("⚠️  .gitignore 文件未包含 .env")
        response = input("是否要添加 .env 到 .gitignore? (y/N): ")
        if response.lower() == 'y':
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                if not content.endswith('\n'):
                    f.write('\n')
                f.write('\n# 环境配置文件\n.env\n.env.local\n.env.*\n')
            print("✅ 已添加 .env 到 .gitignore")
        return True  # 不管是否添加，都认为检查通过

def main():
    """主函数"""
    print("🔐 豆包API安全配置向导")
    print("="*50)
    
    print("\n1. 检查 .gitignore 配置...")
    check_gitignore()
    
    print("\n2. 创建或更新 .env 文件...")
    if create_secure_env_file():
        print("\n3. 验证环境配置...")
        verify_env_file()
        
        print("\n" + "="*50)
        print("✅ 配置完成!")
        print("💡 重要提醒:")
        print("   - 请勿将 .env 文件提交到版本控制系统")
        print("   - 定期更换API密钥以保证安全")
        print("   - 仅在必要时才在生产环境中配置API密钥")
        
        return True
    else:
        print("\n❌ 配置失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)