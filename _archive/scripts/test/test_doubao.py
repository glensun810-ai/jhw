#!/usr/bin/env python3
"""
豆包 API 综合测试脚本
整合了配置验证、优先级测试、API 调用测试

用途:
1. 验证 .env 配置是否正确
2. 测试豆包多模型优先级功能
3. 测试 API 调用是否正常

使用方法:
    python scripts/test_doubao.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 获取项目根目录
script_dir = Path(__file__).parent
root_dir = script_dir.parent
env_file = root_dir / '.env'

print("="*70)
print("豆包 API 综合测试")
print("="*70)
print()

# 加载 .env 文件
print(f"📄 尝试加载 .env 文件：{env_file}")

if not env_file.exists():
    print(f"❌ .env 文件不存在：{env_file}")
    print("\n请按照以下步骤配置：")
    print("1. 复制 .env.example 为 .env")
    print("2. 编辑 .env 文件，填入您的 API Key 和模型 ID")
    sys.exit(1)

load_dotenv(str(env_file))
print("✅ .env 文件加载成功")
print()

# 导入配置和适配器
import sys
sys.path.insert(0, str(root_dir / 'backend_python'))

from config import Config
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType

print("="*70)
print("🔍 配置验证")
print("="*70)
print()

# 检查 API Key 配置
ark_api_key = os.getenv('ARK_API_KEY', '')
doubao_api_key = os.getenv('DOUBAO_API_KEY', '')
auto_select = Config.is_doubao_auto_select()

print("📌 API Key 配置:")
print(f"  ARK_API_KEY: {'✅ 已配置' if ark_api_key else '❌ 未配置'}")
print(f"  DOUBAO_API_KEY: {'✅ 已配置' if doubao_api_key else '❌ 未配置'}")

if not ark_api_key and not doubao_api_key:
    print("\n❌ 错误：未配置豆包 API Key")
    print("\n请在 .env 文件中配置以下至少一项：")
    print("  ARK_API_KEY=your-api-key-here")
    print("  DOUBAO_API_KEY=your-api-key-here")
    sys.exit(1)

# 获取实际使用的 API Key
actual_api_key = ark_api_key or doubao_api_key
print(f"\n✅ 使用 API Key: {actual_api_key[:20]}...{actual_api_key[-10:]}")

# 检查优先级模型配置
priority_models = Config.get_doubao_priority_models()
all_models = priority_models if priority_models else Config.get_api_key('doubao')

print(f"\n📌 模型配置:")
print(f"  自动选择模式：{'✅ 启用' if auto_select else '❌ 禁用'}")
print(f"  优先级模型数量：{len(priority_models)}")
print(f"  总模型数量：{len(all_models)}")

if priority_models:
    print(f"\n📋 优先级模型列表（按优先级排序）:")
    for i, model in enumerate(priority_models, 1):
        print(f"  {i}. {model} {'(首选)' if i == 1 else ''}")
else:
    print(f"\n⚠️  未配置优先级模型，使用兼容模式：{all_models}")

print()
print("="*70)
print("🧪 适配器测试")
print("="*70)
print()

try:
    # 创建优先级适配器
    print("📍 创建豆包优先级适配器...")
    adapter = AIAdapterFactory.create(
        platform_type='doubao',
        api_key=actual_api_key
    )
    
    print(f"  ✅ 适配器创建成功")
    print(f"  📊 适配器类型：{type(adapter).__name__}")
    
    # 检查是否使用了优先级适配器
    if hasattr(adapter, 'get_priority_models'):
        selected_model = adapter.get_selected_model()
        priority_list = adapter.get_priority_models()
        
        print(f"  📋 优先级模型列表：{len(priority_list)} 个")
        print(f"  ✅ 选中的模型：{selected_model}")
        print(f"  💡 说明：系统自动选择了优先级最高的可用模型")
    else:
        print(f"  ⚠️  使用普通适配器（未启用优先级功能）")
        selected_model = adapter.model_name
        print(f"  📊 使用模型：{selected_model}")
    
    # 发送测试请求
    print("\n📍 发送测试请求...")
    test_prompt = "请用一句话介绍你自己"
    
    response = adapter.send_prompt(
        prompt=test_prompt,
        temperature=0.7,
        max_tokens=100
    )
    
    if response.success:
        print("\n" + "="*70)
        print("✅ API 调用成功")
        print("="*70)
        print(f"  📊 使用 Token: {response.tokens_used}")
        print(f"  ⏱️  响应延迟：{response.latency:.2f}s")
        print(f"  💬 回复预览：{response.content[:100]}...")
        
        test_result = {
            'success': True,
            'model': selected_model,
            'tokens': response.tokens_used,
            'latency': response.latency,
            'content': response.content
        }
    else:
        print("\n" + "="*70)
        print("❌ API 调用失败")
        print("="*70)
        print(f"  错误信息：{response.error_message}")
        
        test_result = {
            'success': False,
            'model': selected_model,
            'error': response.error_message
        }
        
except Exception as e:
    print(f"\n❌ 测试异常：{str(e)}")
    import traceback
    traceback.print_exc()
    
    test_result = {
        'success': False,
        'error': str(e)
    }

# 打印测试总结
print()
print("="*70)
print("📊 测试总结")
print("="*70)

if test_result.get('success'):
    print("\n✅ 测试成功!")
    print(f"  • 使用模型：{test_result['model']}")
    print(f"  • 消耗 Token: {test_result['tokens']}")
    print(f"  • 响应时间：{test_result['latency']:.2f}s")
else:
    print("\n❌ 测试失败")
    print(f"  • 错误信息：{test_result.get('error', '未知错误')}")
    print("\n💡 建议检查:")
    print("  1. API Key 是否正确")
    print("  2. 网络连接是否正常")
    print("  3. 模型 ID 是否有效")

print()
print("="*70)
print("✨ 测试完成")
print("="*70)

# 退出码
sys.exit(0 if test_result.get('success') else 1)
