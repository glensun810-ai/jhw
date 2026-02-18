#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 response 内容是否正确提取
验证 executor.py 修复后，response 字段是否正确包含 AI 响应内容
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'wechat_backend'))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("测试 Response 内容提取修复")
print("=" * 70)

# 模拟 scheduler 返回的结果结构
mock_scheduler_result = {
    'task_id': 'test-123',
    'success': True,
    'result': {
        'success': True,
        'content': '这是一个测试响应内容',
        'error_message': None,
        'model': 'glm-4',
        'platform': 'zhipu',
        'tokens_used': 50,
        'latency': 1.23,
        'metadata': {}
    },
    'attempt': 1,
    'model': '智谱 AI',
    'question': '测试问题',
    'brand_name': '测试品牌',
    'latency': 1.23
}

# 模拟 executor.py 中的代码（修复前）
print("\n【修复前】直接获取 result.get('result', ''):")
old_response = mock_scheduler_result.get('result', '')
print(f"  response 类型：{type(old_response)}")
print(f"  response 值：{old_response}")
print(f"  response 长度：{len(str(old_response))}")

# 模拟 executor.py 中的代码（修复后）
print("\n【修复后】提取 result['result'].get('content', ''):")
result_dict = mock_scheduler_result.get('result', {})
if isinstance(result_dict, dict):
    new_response = result_dict.get('content', '')
else:
    new_response = ''
print(f"  response 类型：{type(new_response)}")
print(f"  response 值：{new_response}")
print(f"  response 长度：{len(new_response)}")

# 测试真实 API 调用
print("\n" + "=" * 70)
print("真实 API 调用测试")
print("=" * 70)

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.test_engine.scheduler import TestTask

platforms_to_test = [
    ('deepseek', 'DEEPSEEK_API_KEY', 'deepseek-chat'),
    ('qwen', 'QWEN_API_KEY', 'qwen-turbo'),
    ('doubao', 'DOUBAO_API_KEY', os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')),
    ('zhipu', 'ZHIPU_API_KEY', 'glm-4'),
]

for platform_name, api_key_env, model_id in platforms_to_test:
    print(f"\n测试平台：{platform_name.upper()}")
    
    api_key = os.getenv(api_key_env, '')
    
    if not api_key or api_key.startswith('${'):
        print(f"  ⚠️  跳过：API 密钥未配置")
        continue
    
    try:
        adapter = AIAdapterFactory.create(
            platform_type=platform_name,
            api_key=api_key,
            model_name=model_id
        )
        
        test_prompt = "请用一句话介绍品牌战略诊断的重要性。"
        response = adapter.send_prompt(test_prompt, timeout=120)
        
        if response.success:
            # 模拟 scheduler 返回的结果
            scheduler_result = {
                'task_id': 'test-123',
                'success': True,
                'result': response.to_dict(),
                'attempt': 1,
                'model': platform_name,
                'question': test_prompt,
                'brand_name': '测试品牌',
                'latency': response.latency
            }
            
            # 测试修复后的代码
            result_dict = scheduler_result.get('result', {})
            if isinstance(result_dict, dict):
                response_content = result_dict.get('content', '')
            else:
                response_content = ''
            
            print(f"  ✅ 请求成功")
            print(f"  response 类型：{type(response_content)}")
            print(f"  response 内容：{response_content[:50]}...")
            print(f"  response 长度：{len(response_content)} 字符")
            
            # 验证 response 不为空
            if response_content:
                print(f"  ✅ response 内容正确提取")
            else:
                print(f"  ❌ response 内容为空！")
        else:
            print(f"  ❌ 请求失败：{response.error_message}")
            
    except Exception as e:
        print(f"  ❌ 异常：{e}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
