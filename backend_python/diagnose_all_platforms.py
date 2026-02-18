#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断所有 AI 平台的配置和连接状态
检查为什么只有 Deepseek 获得了结果，而其他平台没有
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'wechat_backend'))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 60)
print("AI 平台配置诊断工具")
print("=" * 60)

# 1. 检查环境变量
print("\n【1】检查环境变量配置...")
print("-" * 60)

env_vars = {
    'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY', ''),
    'QWEN_API_KEY': os.getenv('QWEN_API_KEY', ''),
    'DOUBAO_API_KEY': os.getenv('DOUBAO_API_KEY', ''),
    'ZHIPU_API_KEY': os.getenv('ZHIPU_API_KEY', ''),
}

for key, value in env_vars.items():
    if value:
        masked = value[:8] + '***' if len(value) > 8 else '***'
        print(f"✅ {key}: {masked}")
    else:
        print(f"❌ {key}: 未配置")

# 2. 检查模型 ID 配置
print("\n【2】检查模型 ID 配置...")
print("-" * 60)

model_ids = {
    'DEEPSEEK_MODEL_ID': os.getenv('DEEPSEEK_MODEL_ID', 'deepseek-chat'),
    'QWEN_MODEL_ID': os.getenv('QWEN_MODEL_ID', 'qwen-turbo'),
    'DOUBAO_MODEL_ID': os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq'),
    'ZHIPU_MODEL_ID': os.getenv('ZHIPU_MODEL_ID', 'glm-4'),
}

for key, value in model_ids.items():
    print(f"   {key}: {value}")

# 3. 检查适配器导入
print("\n【3】检查适配器导入状态...")
print("-" * 60)

try:
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    print("✅ AIAdapterFactory 导入成功")
    
    # 检查已注册的适配器
    registered = list(AIAdapterFactory._adapters.keys())
    print(f"   已注册的适配器：{[pt.value for pt in registered]}")
    
    # 检查每个适配器是否可用
    platforms = ['deepseek', 'qwen', 'doubao', 'zhipu']
    for platform in platforms:
        available = AIAdapterFactory.is_platform_available(platform)
        status = "✅ 可用" if available else "❌ 不可用"
        print(f"   {platform}: {status}")
        
except Exception as e:
    print(f"❌ 导入失败：{e}")
    import traceback
    traceback.print_exc()

# 4. 检查电路断路器状态
print("\n【4】检查电路断路器状态...")
print("-" * 60)

try:
    from wechat_backend.circuit_breaker import get_circuit_breaker
    
    platforms = ['deepseek', 'qwen', 'doubao', 'zhipu']
    for platform in platforms:
        try:
            cb = get_circuit_breaker(platform_name=platform, model_name='test')
            print(f"   {platform}: 状态={cb.state.value}, 失败计数={cb.failure_count}")
        except Exception as e:
            print(f"   {platform}: 检查失败 - {e}")
            
except Exception as e:
    print(f"❌ 电路断路器模块导入失败：{e}")

# 5. 测试适配器创建
print("\n【5】测试适配器创建（使用虚拟 API 密钥）...")
print("-" * 60)

try:
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    from wechat_backend.ai_adapters.base_adapter import AIPlatformType
    
    platforms = [
        ('deepseek', AIPlatformType.DEEPSEEK),
        ('qwen', AIPlatformType.QWEN),
        ('doubao', AIPlatformType.DOUBAO),
        ('zhipu', AIPlatformType.ZHIPU),
    ]
    
    for platform_name, platform_type in platforms:
        try:
            adapter = AIAdapterFactory.create(
                platform_type=platform_name,
                api_key='sk-test-dummy-key',
                model_name='test-model'
            )
            print(f"✅ {platform_name}: 适配器创建成功 - {type(adapter).__name__}")
            
            # 检查是否有 circuit_breaker 属性
            if hasattr(adapter, 'circuit_breaker'):
                print(f"      电路断路器：已集成")
            else:
                print(f"      电路断路器：❌ 未集成")
                
            # 检查 send_prompt 方法
            if hasattr(adapter, 'send_prompt') and callable(adapter.send_prompt):
                print(f"      send_prompt 方法：✅ 存在")
            else:
                print(f"      send_prompt 方法：❌ 不存在")
                
        except Exception as e:
            print(f"❌ {platform_name}: 适配器创建失败 - {e}")
            
except Exception as e:
    print(f"❌ 测试失败：{e}")
    import traceback
    traceback.print_exc()

# 6. 检查模型名称映射
print("\n【6】检查模型名称映射...")
print("-" * 60)

try:
    from wechat_backend.test_engine.scheduler import TestScheduler
    
    scheduler = TestScheduler()
    
    test_models = ['豆包', '通义千问', '智谱 AI', 'DeepSeek']
    for model in test_models:
        platform = scheduler._map_model_to_platform(model)
        print(f"   {model} -> {platform}")
        
except Exception as e:
    print(f"❌ 模型映射检查失败：{e}")

# 7. 总结
print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
print("\n建议检查以下常见问题：")
print("1. API 密钥是否正确配置在 .env 文件中")
print("2. 电路断路器是否因之前失败而处于打开状态")
print("3. 适配器是否正确导入和注册")
print("4. 模型名称映射是否正确")
print("5. 网络连接是否正常")
