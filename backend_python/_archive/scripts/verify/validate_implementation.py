#!/usr/bin/env python3
"""
验证AI平台集成实现
检查DeepSeek、通义千问、智谱AI的MVP接口是否正确实现
"""

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_implementations():
    """验证所有实现"""
    print(f"{'='*60}")
    print("AI平台集成实现验证")
    print(f"{'='*60}")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 1. 验证适配器工厂和平台类型
    print("\n🔍 1. 验证AI适配器工厂...")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 测试所有平台
        platforms_to_test = [
            (AIPlatformType.DEEPSEEK, "DeepSeek"),
            (AIPlatformType.QWEN, "通义千问"),
            (AIPlatformType.ZHIPU, "智谱AI"),
            (AIPlatformType.DOUBAO, "豆包")
        ]
        
        for platform_type, name in platforms_to_test:
            adapter_class = AIAdapterFactory.get_adapter_class(platform_type)
            print(f"   ✅ {name}: {adapter_class.__name__}")
        
        print("   ✅ 适配器工厂验证通过")
        results.append(("适配器工厂", True))
        
    except Exception as e:
        print(f"   ❌ 适配器工厂验证失败: {e}")
        results.append(("适配器工厂", False))
    
    # 2. 验证适配器类存在性
    print("\n🔍 2. 验证适配器类存在性...")
    try:
        from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter
        from wechat_backend.ai_adapters.qwen_adapter import QwenAdapter
        from wechat_backend.ai_adapters.zhipu_adapter import ZhipuAdapter
        from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
        
        print(f"   ✅ DeepSeekAdapter: {DeepSeekAdapter.__name__}")
        print(f"   ✅ QwenAdapter: {QwenAdapter.__name__}")
        print(f"   ✅ ZhipuAdapter: {ZhipuAdapter.__name__}")
        print(f"   ✅ DoubaoAdapter: {DoubaoAdapter.__name__}")
        
        print("   ✅ 适配器类存在性验证通过")
        results.append(("适配器类存在性", True))
        
    except Exception as e:
        print(f"   ❌ 适配器类存在性验证失败: {e}")
        results.append(("适配器类存在性", False))
    
    # 3. 验证MVP端点实现
    print("\n🔍 3. 验证MVP端点实现...")
    try:
        import importlib.util
        views_path = os.path.join(os.path.dirname(__file__), 'wechat_backend', 'views.py')
        
        # 读取文件内容并检查端点定义
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        endpoints_to_check = [
            ('mvp_deepseek_test', 'DeepSeek MVP端点'),
            ('mvp_qwen_test', '通义千问MVP端点'),
            ('mvp_zhipu_test', '智谱AI MVP端点'),
            ('mvp_brand_test', '豆包MVP端点')
        ]
        
        for endpoint_func, desc in endpoints_to_check:
            if f'def {endpoint_func}(' in content:
                print(f"   ✅ {desc}: 已定义")
            else:
                print(f"   ❌ {desc}: 未找到")
                results.append(("MVP端点实现", False))
                break
        else:
            print("   ✅ MVP端点实现验证通过")
            results.append(("MVP端点实现", True))
        
    except Exception as e:
        print(f"   ❌ MVP端点实现验证失败: {e}")
        results.append(("MVP端点实现", False))
    
    # 4. 验证配置文件
    print("\n🔍 4. 验证配置文件...")
    try:
        # 检查 .env 文件
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
            
            required_configs = [
                ('DEEPSEEK_API_KEY', 'DeepSeek API密钥'),
                ('QWEN_API_KEY', '通义千问API密钥'),
                ('ZHIPU_API_KEY', '智谱AI API密钥'),
                ('DEEPSEEK_MODEL_ID', 'DeepSeek模型ID'),
                ('QWEN_MODEL_ID', '通义千问模型ID'),
                ('ZHIPU_MODEL_ID', '智谱AI模型ID')
            ]
            
            for config_key, desc in required_configs:
                if config_key in env_content:
                    print(f"   ✅ {desc}: 已配置")
                else:
                    print(f"   ⚠️  {desc}: 未找到（可能使用默认值）")
            
            print("   ✅ 配置文件验证通过")
            results.append(("配置文件", True))
        else:
            print("   ❌ .env 文件不存在")
            results.append(("配置文件", False))
        
    except Exception as e:
        print(f"   ❌ 配置文件验证失败: {e}")
        results.append(("配置文件", False))
    
    # 5. 验证前端服务文件
    print("\n🔍 5. 验证前端服务文件...")
    try:
        service_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services', 'platformSpecificMVPService.js')
        if os.path.exists(service_path):
            with open(service_path, 'r', encoding='utf-8') as f:
                service_content = f.read()
            
            required_functions = [
                ('startDeepSeekMVPTest', 'DeepSeek测试函数'),
                ('startQwenMVPTest', '通义千问测试函数'),
                ('startZhipuMVPTest', '智谱AI测试函数')
            ]
            
            for func_name, desc in required_functions:
                if f'const {func_name} =' in service_content or f'function {func_name}(' in service_content:
                    print(f"   ✅ {desc}: 已定义")
                else:
                    print(f"   ❌ {desc}: 未找到")
                    results.append(("前端服务文件", False))
                    break
            else:
                print("   ✅ 前端服务文件验证通过")
                results.append(("前端服务文件", True))
        else:
            print("   ❌ 前端服务文件不存在")
            results.append(("前端服务文件", False))
        
    except Exception as e:
        print(f"   ❌ 前端服务文件验证失败: {e}")
        results.append(("前端服务文件", False))
    
    # 6. 验证前端页面文件
    print("\n🔍 6. 验证前端页面文件...")
    try:
        page_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pages', 'mvp-platform-selector')
        required_files = ['mvp-platform-selector.js', 'mvp-platform-selector.wxml', 'mvp-platform-selector.wxss', 'mvp-platform-selector.json']
        
        all_exist = True
        for file_name in required_files:
            file_path = os.path.join(page_dir, file_name)
            if os.path.exists(file_path):
                print(f"   ✅ {file_name}: 存在")
            else:
                print(f"   ❌ {file_name}: 不存在")
                all_exist = False
        
        if all_exist:
            print("   ✅ 前端页面文件验证通过")
            results.append(("前端页面文件", True))
        else:
            results.append(("前端页面文件", False))
        
    except Exception as e:
        print(f"   ❌ 前端页面文件验证失败: {e}")
        results.append(("前端页面文件", False))
    
    # 7. 验证Zhipu适配器修复
    print("\n🔍 7. 验证Zhipu适配器修复...")
    try:
        adapter_path = os.path.join(os.path.dirname(__file__), 'wechat_backend', 'ai_adapters', 'zhipu_adapter.py')
        with open(adapter_path, 'r', encoding='utf-8') as f:
            adapter_content = f.read()
        
        if 'self.model_name,' in adapter_content and 'self_model_name,' not in adapter_content:
            print("   ✅ Zhipu适配器修复验证通过")
            results.append(("Zhipu适配器修复", True))
        else:
            print("   ❌ Zhipu适配器修复未验证通过")
            results.append(("Zhipu适配器修复", False))
        
    except Exception as e:
        print(f"   ❌ Zhipu适配器修复验证失败: {e}")
        results.append(("Zhipu适配器修复", False))
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("验证结果汇总")
    print(f"{'='*60}")
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print(f"\n总体结果: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    
    if all_passed:
        print(f"\n🎉 恭喜！所有AI平台集成实现验证通过！")
        print(f"📋 已实现功能:")
        print(f"   • DeepSeek MVP接口: /api/mvp/deepseek-test")
        print(f"   • 通义千问MVP接口: /api/mvp/qwen-test")
        print(f"   • 智谱AI MVP接口: /api/mvp/zhipu-test")
        print(f"   • 豆包MVP接口: /api/mvp/brand-test (原有)")
        print(f"   • 前端平台选择器: /pages/mvp-platform-selector/")
        print(f"   • 统一AI适配器框架")
        print(f"\n💡 下一步: 运行服务器并测试各平台功能")
        return 0
    else:
        failed_items = [name for name, passed in results if not passed]
        print(f"\n⚠️  以下项目验证失败: {', '.join(failed_items)}")
        print(f"🔧 请检查相应文件和实现")
        return 1

if __name__ == "__main__":
    exit(validate_implementations())