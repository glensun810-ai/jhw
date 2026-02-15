#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 DeepSeekAdapter 导入问题
"""

print("开始测试 DeepSeekAdapter 导入...")

try:
    from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter
    print("✓ DeepSeekAdapter 导入成功")
    print(f"  类型: {type(DeepSeekAdapter)}")
    print(f"  值: {DeepSeekAdapter}")
    
    # 尝试创建实例（不实际调用API）
    try:
        # 注意：这里只是测试类是否可以实例化，不实际调用API
        adapter_instance = DeepSeekAdapter.__new__(DeepSeekAdapter)
        print("✓ DeepSeekAdapter 类结构正常")
    except Exception as e:
        print(f"✗ DeepSeekAdapter 实例化失败: {e}")
        
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")
    print(f"  错误位置: {e.filename}:{e.lineno}")
    print(f"  错误文本: {e.text}")
    
except ImportError as e:
    print(f"✗ 导入错误: {e}")
    
except Exception as e:
    print(f"✗ 其他错误: {e}")
    import traceback
    traceback.print_exc()

print("\n开始测试整个 AIAdapterFactory...")
try:
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    print("✓ AIAdapterFactory 导入成功")
    print(f"  注册的适配器: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
    
    # 检查 DeepSeek 是否可用
    is_available = AIAdapterFactory.is_platform_available('deepseek')
    print(f"  DeepSeek 平台是否可用: {is_available}")
    
    is_available_caps = AIAdapterFactory.is_platform_available('DeepSeek')
    print(f"  'DeepSeek' (大写) 平台是否可用: {is_available_caps}")
    
except Exception as e:
    print(f"✗ AIAdapterFactory 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")