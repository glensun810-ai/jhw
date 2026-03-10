#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包 429 错误模型切换测试

验证当第一个模型配额用尽时，能否自动切换到下一个模型
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env')

# 添加项目路径
sys.path.insert(0, '.')

from wechat_backend.ai_adapters.doubao_priority_adapter import DoubaoPriorityAdapter
from wechat_backend.logging_config import api_logger

def test_model_switching():
    """测试模型切换功能"""
    print("="*60)
    print("豆包 429 错误模型切换测试")
    print("="*60)
    
    # 获取 API Key
    api_key = os.getenv('DOUBAO_API_KEY')
    if not api_key:
        print("❌ DOUBAO_API_KEY 未设置")
        return
    
    print(f"✅ API Key: {api_key[:10]}...{api_key[-5:]}")
    
    # 创建优先级适配器
    print("\n创建 DoubaoPriorityAdapter...")
    adapter = DoubaoPriorityAdapter(api_key=api_key)
    
    print(f"✅ 适配器创建成功")
    print(f"   优先级模型列表：{adapter.priority_models}")
    print(f"   当前选中模型：{adapter.selected_model}")
    print(f"   已耗尽模型：{adapter.exhausted_models}")
    
    # 测试发送提示词
    test_prompt = "你好，请简单回复"
    
    print(f"\n发送测试提示词：{test_prompt}")
    print("-"*60)
    
    try:
        response = adapter.generate_response(test_prompt)
        
        print(f"\n响应结果:")
        print(f"   成功：{response.success}")
        print(f"   模型：{response.model}")
        print(f"   平台：{response.platform}")
        
        if response.success:
            print(f"   内容：{response.content[:100] if response.content else 'N/A'}")
        else:
            print(f"   错误：{response.error_message}")
            print(f"   错误类型：{response.error_type}")
        
        print(f"\n当前状态:")
        print(f"   选中模型：{adapter.selected_model}")
        print(f"   已耗尽模型：{adapter.exhausted_models}")
        
    except Exception as e:
        print(f"\n❌ 调用失败：{e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    test_model_switching()
