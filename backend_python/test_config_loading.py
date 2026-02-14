#!/usr/bin/env python3
"""
检查配置管理器是否正确加载API密钥
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from config_manager import Config as PlatformConfigManager

def test_config_loading():
    """测试配置加载"""
    print("🔍 测试配置管理器是否正确加载API密钥...\n")
    
    config_manager = PlatformConfigManager()
    
    print("可用平台:", config_manager.get_available_platforms())
    
    platforms_to_test = ['deepseek', 'qwen', 'doubao']
    
    for platform in platforms_to_test:
        config = config_manager.get_platform_config(platform)
        if config:
            print(f"✅ {platform}: API密钥已加载 (前缀: {config.api_key[:8]}...)")
            print(f"   Base URL: {config.base_url}")
            print(f"   温度: {config.default_temperature}")
            print(f"   最大令牌数: {config.default_max_tokens}")
        else:
            print(f"❌ {platform}: 未找到配置")
        
        # 检查环境变量
        env_key = os.getenv(f'{platform.upper()}_API_KEY')
        if env_key:
            print(f"   环境变量 {platform.upper()}_API_KEY: 已设置 (前缀: {env_key[:8]}...)")
        else:
            print(f"   环境变量 {platform.upper()}_API_KEY: 未设置")
        print()

if __name__ == "__main__":
    test_config_loading()