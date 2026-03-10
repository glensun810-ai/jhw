#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试所有 AI 平台的实际 API 调用
验证修复后所有平台是否都能正常工作
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'wechat_backend'))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("AI 平台 API 调用测试")
print("=" * 70)

# 测试配置
test_prompt = "请用一句话介绍品牌战略诊断的重要性。"

platforms_to_test = [
    ('deepseek', 'DEEPSEEK_API_KEY', 'deepseek-chat'),
    ('qwen', 'QWEN_API_KEY', 'qwen-turbo'),
    ('doubao', 'DOUBAO_API_KEY', os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')),
    ('zhipu', 'ZHIPU_API_KEY', 'glm-4'),
]

results = []

for platform_name, api_key_env, model_id in platforms_to_test:
    print(f"\n{'='*70}")
    print(f"测试平台：{platform_name.upper()}")
    print(f"{'='*70}")
    
    api_key = os.getenv(api_key_env, '')
    
    if not api_key or api_key.startswith('${') or api_key == 'your-api-key-here':
        print(f"⚠️  跳过：{platform_name} API 密钥未配置")
        results.append((platform_name, 'SKIP', 'API key not configured'))
        continue
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        print(f"正在创建适配器...")
        adapter = AIAdapterFactory.create(
            platform_type=platform_name,
            api_key=api_key,
            model_name=model_id
        )
        print(f"✅ 适配器创建成功：{type(adapter).__name__}")
        
        print(f"正在发送测试请求 (模型：{model_id})...")
        print(f"测试 prompt: {test_prompt[:50]}...")
        
        response = adapter.send_prompt(test_prompt, timeout=120)
        
        if response.success:
            print(f"✅ 请求成功!")
            print(f"   响应内容：{response.content[:100]}...")
            print(f"   延迟：{response.latency:.2f}秒")
            print(f"   Token 使用：{response.tokens_used}")
            results.append((platform_name, 'SUCCESS', response.content[:50]))
        else:
            print(f"❌ 请求失败!")
            print(f"   错误信息：{response.error_message}")
            print(f"   错误类型：{response.error_type}")
            results.append((platform_name, 'FAIL', response.error_message))
            
    except Exception as e:
        print(f"❌ 异常：{e}")
        import traceback
        traceback.print_exc()
        results.append((platform_name, 'ERROR', str(e)))

# 汇总结果
print(f"\n{'='*70}")
print("测试结果汇总")
print(f"{'='*70}")

success_count = sum(1 for _, status, _ in results if status == 'SUCCESS')
fail_count = sum(1 for _, status, _ in results if status == 'FAIL')
error_count = sum(1 for _, status, _ in results if status == 'ERROR')
skip_count = sum(1 for _, status, _ in results if status == 'SKIP')

print(f"\n总计：{len(results)} 个平台")
print(f"✅ 成功：{success_count}")
print(f"❌ 失败：{fail_count}")
print(f"💥 错误：{error_count}")
print(f"⚠️  跳过：{skip_count}")

print(f"\n详细结果:")
for platform, status, detail in results:
    status_icon = {'SUCCESS': '✅', 'FAIL': '❌', 'ERROR': '💥', 'SKIP': '⚠️'}.get(status, '?')
    print(f"  {status_icon} {platform}: {detail[:80] if detail else 'N/A'}...")

if success_count == len([p for p in results if p[1] != 'SKIP']):
    print(f"\n🎉 所有已配置的平台测试通过!")
elif success_count > 0:
    print(f"\n✓ 部分平台测试通过，请检查失败的平台")
else:
    print(f"\n✗ 所有平台测试失败，请检查配置和网络连接")

print(f"\n{'='*70}")
