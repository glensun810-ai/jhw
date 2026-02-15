#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 AIAdapterFactory 导入和注册功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_factory_import():
    """测试 factory.py 模块导入"""
    print("开始测试 factory.py 模块导入...")
    
    try:
        print("正在导入 AIAdapterFactory...")
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        print("✓ AIAdapterFactory 导入成功")
        
        print("正在检查已注册的适配器...")
        registered_models = [pt.value for pt in AIAdapterFactory._adapters.keys()]
        print(f"✓ 已注册的模型: {registered_models}")
        
        print("正在检查 MODEL_NAME_MAP...")
        print(f"✓ MODEL_NAME_MAP: {list(AIAdapterFactory.MODEL_NAME_MAP.keys())[:10]}...")  # 显示前10个
        
        # 测试平台可用性检查
        print("\n测试平台可用性检查:")
        platforms_to_test = ['deepseek', 'doubao', 'qwen', 'zhipu', 'chatgpt']
        for platform in platforms_to_test:
            is_available = AIAdapterFactory.is_platform_available(platform)
            print(f"  {platform}: {'✓' if is_available else '✗'}")
        
        # 测试名称规范化
        print("\n测试名称规范化:")
        test_names = ['DeepSeek', '豆包', '通义千问', '智谱AI']
        for name in test_names:
            normalized = AIAdapterFactory.get_normalized_model_name(name)
            print(f"  {name} -> {normalized}")
        
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_adapters():
    """测试各个适配器的导入"""
    print("\n开始测试各个适配器导入...")
    
    adapters_to_test = [
        ('DeepSeekAdapter', 'deepseek_adapter'),
        ('QwenAdapter', 'qwen_adapter'),
        ('DoubaoAdapter', 'doubao_adapter'),
        ('ZhipuAdapter', 'zhipu_adapter'),
        ('ChatGPTAdapter', 'chatgpt_adapter'),
        ('GeminiAdapter', 'gemini_adapter'),
        ('ErnieBotAdapter', 'erniebot_adapter'),
        ('DeepSeekR1Adapter', 'deepseek_r1_adapter'),
    ]
    
    for adapter_name, module_name in adapters_to_test:
        try:
            module = __import__(f'wechat_backend.ai_adapters.{module_name}', fromlist=[adapter_name])
            adapter_class = getattr(module, adapter_name)
            print(f"✓ {adapter_name} 导入成功: {adapter_class}")
        except Exception as e:
            print(f"✗ {adapter_name} 导入失败: {e}")

if __name__ == "__main__":
    print("AIAdapterFactory 导入测试")
    print("="*50)
    
    success = test_factory_import()
    test_individual_adapters()
    
    print("\n" + "="*50)
    if success:
        print("测试结果: 所有导入测试通过")
    else:
        print("测试结果: 导入测试失败")