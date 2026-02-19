#!/usr/bin/env python3
"""
测试Doubao适配器是否正确使用环境配置
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("Environment variables loaded:")
print(f"DOUBAO_API_KEY: {os.getenv('DOUBAO_API_KEY') is not None}")
print(f"DOUBAO_MODEL_ID: {os.getenv('DOUBAO_MODEL_ID')}")

# 测试配置管理器
from config_manager import Config as PlatformConfigManager
config_manager = PlatformConfigManager()
doubao_config = config_manager.get_platform_config('doubao')

print(f"\nConfig manager loaded:")
print(f"Doubao config exists: {doubao_config is not None}")
if doubao_config:
    print(f"API Key: {'*' * 10 + doubao_config.api_key[-6:] if doubao_config.api_key else 'None'}")
    print(f"Default model: {doubao_config.default_model}")

# 测试适配器初始化
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter

print(f"\nTesting adapter initialization...")
adapter = DoubaoAdapter(api_key=os.getenv('DOUBAO_API_KEY'))

print(f"Adapter model name: {adapter.model_name}")
print(f"Adapter platform: {adapter.platform_type}")
print(f"Adapter API key: {'*' * 10 + adapter.api_key[-6:] if adapter.api_key else 'None'}")