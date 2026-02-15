#!/usr/bin/env python3
"""
测试平台名称映射功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_scheduler_mapping():
    """测试调度器中的平台映射功能"""
    print("🔍 测试调度器平台名称映射...")
    
    try:
        from wechat_backend.test_engine.scheduler import TestScheduler
        
        scheduler = TestScheduler()
        
        # 测试各种平台名称映射
        test_cases = [
            ("DeepSeek", "deepseek"),
            ("deepseek", "deepseek"),
            ("豆包", "doubao"),
            ("doubao", "doubao"),
            ("通义千问", "qwen"),
            ("千问", "qwen"),
            ("qwen", "qwen"),
            ("智谱AI", "zhipu"),
            ("智谱", "zhipu"),
            ("zhipu", "zhipu"),
            ("文心一言", "wenxin"),
            ("ernie", "wenxin"),
        ]
        
        all_passed = True
        for input_name, expected_output in test_cases:
            result = scheduler._map_model_to_platform(input_name)
            status = "✅" if result == expected_output else "❌"
            print(f"   {status} {input_name} -> {result} (期望: {expected_output})")
            if result != expected_output:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_factory_mapping():
    """测试适配器工厂中的平台映射功能"""
    print("\n🔍 测试适配器工厂平台名称映射...")
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        # 测试各种平台名称映射
        test_cases = [
            ("DeepSeek", "deepseek"),
            ("deepseek", "deepseek"),
            ("豆包", "doubao"),
            ("doubao", "doubao"),
            ("通义千问", "qwen"),
            ("千问", "qwen"),
            ("qwen", "qwen"),
            ("智谱AI", "zhipu"),
            ("智谱", "zhipu"),
            ("zhipu", "zhipu"),
            ("文心一言", "wenxin"),
            ("ernie", "wenxin"),
        ]
        
        all_passed = True
        for input_name, expected_output in test_cases:
            result = AIAdapterFactory.get_normalized_model_name(input_name)
            status = "✅" if result == expected_output else "❌"
            print(f"   {status} {input_name} -> {result} (期望: {expected_output})")
            if result != expected_output:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_adapter_creation():
    """测试适配器创建功能"""
    print("\n🔍 测试适配器创建...")
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory, AIPlatformType
        from wechat_backend.config_manager import Config
        
        config_manager = Config()
        
        # 测试已注册的平台
        registered_platforms = [pt.value for pt in AIAdapterFactory._adapters.keys()]
        print(f"   已注册平台: {registered_platforms}")
        
        # 尝试创建适配器（使用模拟API密钥进行测试）
        test_platforms = ['deepseek', 'qwen', 'zhipu', 'doubao']
        all_passed = True
        
        for platform in test_platforms:
            if platform in registered_platforms:
                try:
                    # 获取配置
                    platform_config = config_manager.get_platform_config(platform)
                    if platform_config and platform_config.api_key:
                        # 如果有API密钥，尝试创建适配器
                        adapter = AIAdapterFactory.create(platform, platform_config.api_key, platform_config.default_model)
                        print(f"   ✅ {platform} 适配器创建成功: {type(adapter).__name__}")
                    else:
                        # 没有API密钥，至少验证适配器类存在
                        platform_type = AIPlatformType(platform)
                        adapter_class = AIAdapterFactory.get_adapter_class(platform_type)
                        print(f"   ✅ {platform} 适配器类存在: {adapter_class.__name__} (缺少API密钥)")
                except Exception as e:
                    print(f"   ❌ {platform} 适配器创建失败: {e}")
                    all_passed = False
            else:
                print(f"   ⚠️  {platform} 未注册")
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🧪 平台名称映射功能测试")
    print("="*60)
    
    results = []
    
    results.append(("调度器映射", test_scheduler_mapping()))
    results.append(("工厂映射", test_factory_mapping()))
    results.append(("适配器创建", test_adapter_creation()))
    
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print(f"\n🎉 所有测试通过！平台集成修复完成。")
        return 0
    else:
        failed_items = [name for name, passed in results if not passed]
        print(f"\n⚠️  部分测试失败: {', '.join(failed_items)}")
        return 1

if __name__ == "__main__":
    exit(main())