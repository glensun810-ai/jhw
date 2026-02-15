#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断AI适配器注册问题
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def diagnose_adapters():
    """诊断AI适配器导入和注册状态"""
    print("=" * 60)
    print("🔍 AI适配器注册诊断工具")
    print("=" * 60)
    
    # 1. 检查适配器工厂的导入
    print("\n1. 🏭 检查AIAdapterFactory导入...")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory, AIPlatformType
        print("   ✅ AIAdapterFactory导入成功")
        print(f"   📋 当前注册的适配器: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
        print(f"   🗺️  模型名称映射: {AIAdapterFactory.MODEL_NAME_MAP}")
    except Exception as e:
        print(f"   ❌ AIAdapterFactory导入失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 检查各个适配器的导入
    print("\n2. 🔧 检查各个适配器导入...")
    adapters_to_check = [
        ('DeepSeekAdapter', 'DEEPSEEK'),
        ('DeepSeekR1Adapter', 'DEEPSEEKR1'), 
        ('QwenAdapter', 'QWEN'),
        ('DoubaoAdapter', 'DOUBAO'),
        ('ZhipuAdapter', 'ZHIPU')
    ]
    
    for adapter_name, platform_enum in adapters_to_check:
        print(f"\n   检查 {adapter_name}...")
        try:
            # 动态导入适配器
            module_path = f"wechat_backend.ai_adapters.{adapter_name.lower().replace('adapter', '')}_adapter"
            module = __import__(module_path, fromlist=[adapter_name])
            adapter_class = getattr(module, adapter_name)
            print(f"      ✅ {adapter_name} 导入成功")
            
            # 检查是否在工厂中注册
            platform_type = getattr(AIPlatformType, platform_enum)
            if platform_type in AIAdapterFactory._adapters:
                print(f"      ✅ {adapter_name} 已注册到工厂 (平台类型: {platform_type.value})")
            else:
                print(f"      ❌ {adapter_name} 未注册到工厂 (平台类型: {platform_type.value})")
                
        except ImportError as e:
            print(f"      ❌ {adapter_name} 导入失败: {e}")
        except AttributeError as e:
            print(f"      ❌ {adapter_name} 属性错误: {e}")
        except Exception as e:
            print(f"      ❌ {adapter_name} 其他错误: {e}")
            import traceback
            traceback.print_exc()
    
    # 3. 测试模型名称映射
    print("\n3. 🗺️ 测试模型名称映射...")
    test_models = ['DeepSeek', '豆包', '通义千问', '智谱AI']
    for model_name in test_models:
        normalized = AIAdapterFactory.get_normalized_model_name(model_name)
        print(f"   '{model_name}' -> '{normalized}' (注册状态: {AIAdapterFactory.is_platform_available(normalized)})")
    
    # 4. 检查具体的注册状态
    print("\n4. 📊 详细注册状态检查...")
    platform_checks = [
        ('DeepSeek', 'deepseek'),
        ('DeepSeek', 'deepseekr1'),  # 这可能是问题所在
        ('豆包', 'doubao'),
        ('通义千问', 'qwen'),
        ('智谱AI', 'zhipu')
    ]
    
    for display_name, internal_name in platform_checks:
        is_available = AIAdapterFactory.is_platform_available(internal_name)
        print(f"   {display_name} ({internal_name}): {'✅ 可用' if is_available else '❌ 不可用'}")
    
    print("\n" + "=" * 60)
    print("💡 诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_adapters()