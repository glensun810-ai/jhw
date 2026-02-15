#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI适配器导入和注册诊断工具
用于检测AI适配器是否能够正确导入和注册
"""

import sys
import os
import traceback

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

def test_adapter_imports():
    """测试各个AI适配器的导入"""
    print("="*60)
    print("AI适配器导入诊断")
    print("="*60)
    
    adapters_to_test = [
        ('DeepSeekAdapter', 'wechat_backend.ai_adapters.deepseek_adapter'),
        ('QwenAdapter', 'wechat_backend.ai_adapters.qwen_adapter'), 
        ('DoubaoAdapter', 'wechat_backend.ai_adapters.doubao_adapter'),
        ('ZhipuAdapter', 'wechat_backend.ai_adapters.zhipu_adapter'),
        ('ChatGPTAdapter', 'wechat_backend.ai_adapters.chatgpt_adapter'),
        ('GeminiAdapter', 'wechat_backend.ai_adapters.gemini_adapter'),
        ('ErnieBotAdapter', 'wechat_backend.ai_adapters.erniebot_adapter'),
        ('DeepSeekR1Adapter', 'wechat_backend.ai_adapters.deepseek_r1_adapter'),
    ]
    
    successful_imports = []
    failed_imports = []
    
    for adapter_name, module_path in adapters_to_test:
        try:
            module = __import__(module_path, fromlist=[adapter_name])
            adapter_class = getattr(module, adapter_name)
            print(f"✓ {adapter_name} from {module_path} - SUCCESS")
            successful_imports.append((adapter_name, module_path, adapter_class))
        except ImportError as e:
            print(f"✗ {adapter_name} from {module_path} - FAILED: {e}")
            failed_imports.append((adapter_name, module_path, str(e)))
        except AttributeError as e:
            print(f"✗ {adapter_name} from {module_path} - FAILED: {e}")
            failed_imports.append((adapter_name, module_path, str(e)))
        except Exception as e:
            print(f"? {adapter_name} from {module_path} - ERROR: {e}")
            failed_imports.append((adapter_name, module_path, str(e)))
    
    print(f"\n导入结果: {len(successful_imports)} 成功, {len(failed_imports)} 失败")
    return successful_imports, failed_imports

def test_factory_registration():
    """测试AI适配器工厂的注册状态"""
    print("\n" + "="*60)
    print("AI适配器工厂注册诊断")
    print("="*60)
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        print("✓ AIAdapterFactory import - SUCCESS")
        
        # 检查注册的适配器
        registered_adapters = list(AIAdapterFactory._adapters.keys())
        print(f"✓ 已注册适配器数量: {len(registered_adapters)}")
        
        for platform_type in registered_adapters:
            print(f"  - {platform_type.value}")
        
        return True, registered_adapters
    except Exception as e:
        print(f"✗ AIAdapterFactory import/registration - FAILED: {e}")
        traceback.print_exc()
        return False, []

def test_name_mapping():
    """测试名称映射功能"""
    print("\n" + "="*60)
    print("AI平台名称映射诊断")
    print("="*60)
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        # 测试各种平台名称的映射
        test_names = ['DeepSeek', '豆包', '通义千问', '智谱AI', 'doubao', 'qwen', 'zhipu', 'chatgpt']
        
        for name in test_names:
            mapped_name = AIAdapterFactory.get_normalized_model_name(name)
            print(f"  {name} -> {mapped_name}")
        
        return True
    except Exception as e:
        print(f"✗ 名称映射测试 - FAILED: {e}")
        traceback.print_exc()
        return False

def test_platform_availability():
    """测试平台可用性检查"""
    print("\n" + "="*60)
    print("AI平台可用性诊断")
    print("="*60)
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        # 测试各种平台的可用性
        test_platforms = ['doubao', 'deepseek', 'qwen', 'zhipu', 'chatgpt', 'gemini']
        
        for platform in test_platforms:
            is_available = AIAdapterFactory.is_platform_available(platform)
            status = "✓" if is_available else "✗"
            print(f"  {platform}: {status}")
        
        return True
    except Exception as e:
        print(f"✗ 平台可用性测试 - FAILED: {e}")
        traceback.print_exc()
        return False

def main():
    """主诊断函数"""
    print("开始AI适配器诊断...")
    
    # 测试导入
    successful_imports, failed_imports = test_adapter_imports()
    
    # 测试工厂注册
    factory_success, registered_adapters = test_factory_registration()
    
    # 测试名称映射
    mapping_success = test_name_mapping()
    
    # 测试平台可用性
    availability_success = test_platform_availability()
    
    print("\n" + "="*60)
    print("诊断汇总")
    print("="*60)
    print(f"导入测试: {'✓' if successful_imports else '✗'} ({len(successful_imports)} 成功, {len(failed_imports)} 失败)")
    print(f"工厂注册: {'✓' if factory_success else '✗'} ({len(registered_adapters)} 已注册)")
    print(f"名称映射: {'✓' if mapping_success else '✗'}")
    print(f"平台可用: {'✓' if availability_success else '✗'}")
    
    if failed_imports:
        print(f"\n失败的导入:")
        for adapter_name, module_path, error in failed_imports:
            print(f"  - {adapter_name} from {module_path}: {error}")
    
    print("\n诊断完成!")

if __name__ == "__main__":
    main()