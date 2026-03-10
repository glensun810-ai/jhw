#!/usr/bin/env python3
"""
环境变量配置验证脚本
用于检查.env文件中的配置是否正确加载
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def load_env_file():
    """加载.env文件"""
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 移除可能的引号
                    value = value.strip().strip('"\'')
                    os.environ[key] = value
        print("✅ .env 文件加载成功")
        return True
    else:
        print("❌ .env 文件未找到")
        return False

def test_api_key_configuration():
    """测试API密钥配置"""
    print("\n" + "="*50)
    print("API密钥配置验证")
    print("="*50)
    
    # 测试各个平台的API密钥
    api_keys = {
        'DEEPSEEK': os.environ.get('DEEPSEEK_API_KEY'),
        'QWEN': os.environ.get('QWEN_API_KEY'),
        'DOUBAO': os.environ.get('DOUBAO_API_KEY'),
        'CHATGPT': os.environ.get('CHATGPT_API_KEY'),
        'GEMINI': os.environ.get('GEMINI_API_KEY'),
        'ZHIPU': os.environ.get('ZHIPU_API_KEY')
    }
    
    for platform, key in api_keys.items():
        if key:
            # 检查密钥格式
            is_valid = len(key) > 10 and not key.startswith('sk-') and not key.endswith('[在此粘贴你的Key]')
            status = "✅" if is_valid else "⚠️"
            print(f"{status} {platform:8} | 长度: {len(key):3} | 示例: {key[:15]}...")
        else:
            print(f"❌ {platform:8} | 未配置")

def test_wechat_configuration():
    """测试微信配置"""
    print("\n" + "="*50)
    print("微信配置验证")
    print("="*50)
    
    wechat_config = {
        'APP_ID': os.environ.get('WECHAT_APP_ID'),
        'APP_SECRET': os.environ.get('WECHAT_APP_SECRET'),
        'TOKEN': os.environ.get('WECHAT_TOKEN'),
        'SECRET_KEY': os.environ.get('SECRET_KEY')
    }
    
    for key, value in wechat_config.items():
        if value:
            # 检查是否包含中文引号
            has_chinese_quotes = '“' in value or '”' in value or '‘' in value or '’' in value
            status = "❌" if has_chinese_quotes else "✅"
            print(f"{status} {key:12} | 值: {value[:30]}{'...' if len(value) > 30 else ''}")
            if has_chinese_quotes:
                print(f"    ⚠️  发现中文引号，可能导致解析错误")
        else:
            print(f"❌ {key:12} | 未配置")

def test_config_module():
    """测试配置模块加载"""
    print("\n" + "="*50)
    print("配置模块验证")
    print("="*50)
    
    try:
        from backend_python.config import Config
        
        # 测试API密钥获取
        platforms = ['deepseek', 'qwen', 'doubao', 'chatgpt', 'gemini', 'zhipu']
        print("通过Config模块获取的API密钥:")
        for platform in platforms:
            api_key = Config.get_api_key(platform)
            if api_key:
                is_configured = Config.is_api_key_configured(platform)
                status = "✅" if is_configured else "⚠️"
                print(f"{status} {platform:8} | 配置状态: {'已配置' if is_configured else '未配置'}")
            else:
                print(f"❌ {platform:8} | 未获取到API密钥")
                
    except Exception as e:
        print(f"❌ 配置模块加载失败: {e}")
        import traceback
        traceback.print_exc()

def test_adapter_factory():
    """测试适配器工厂配置"""
    print("\n" + "="*50)
    print("适配器工厂验证")
    print("="*50)
    
    try:
        from backend_python.wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        # 测试模型名称映射
        test_models = ['DeepSeek', '豆包', '通义千问', '智谱AI']
        print("模型名称映射测试:")
        for model in test_models:
            normalized = AIAdapterFactory.get_normalized_model_name(model)
            print(f"  {model} -> {normalized}")
            
        # 测试平台可用性
        platforms = ['deepseek', 'doubao', 'qwen', 'zhipu']
        print("\n平台可用性检查:")
        for platform in platforms:
            is_available = AIAdapterFactory.is_platform_available(platform)
            print(f"  {platform}: {'✅ 可用' if is_available else '❌ 不可用'}")
            
    except Exception as e:
        print(f"❌ 适配器工厂测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("环境变量配置诊断工具")
    print("="*60)
    
    # 加载环境变量
    if not load_env_file():
        return
    
    # 运行各项测试
    test_api_key_configuration()
    test_wechat_configuration()
    test_config_module()
    test_adapter_factory()
    
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)

if __name__ == '__main__':
    main()