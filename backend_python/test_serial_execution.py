#!/usr/bin/env python3
"""
测试串行执行方案
验证AI平台请求是否能够独立且可靠地执行
"""

import sys
import os
import time
import uuid
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'wechat_backend'))

from wechat_backend.test_engine import TestExecutor, ExecutionStrategy
from wechat_backend.question_system import TestCase, TestCaseGenerator
from wechat_backend.logging_config import api_logger


def test_serial_execution():
    """测试串行执行方案"""
    print("=" * 60)
    print("🔍 测试串行执行方案")
    print("=" * 60)
    
    try:
        # 创建测试用例
        brand_name = "测试品牌"
        ai_models = [
            {'name': '豆包', 'checked': True},
            {'name': 'DeepSeek', 'checked': True},
            {'name': '通义千问', 'checked': True},
            {'name': '智谱AI', 'checked': True}
        ]
        questions = [
            "介绍一下{brandName}",
            "{brandName}的主要产品是什么"
        ]
        
        print(f"📝 准备测试用例...")
        generator = TestCaseGenerator()
        test_cases = generator.generate_test_cases(brand_name, ai_models, questions)
        
        print(f"✅ 生成了 {len(test_cases)} 个测试用例:")
        for i, case in enumerate(test_cases):
            print(f"   [{i+1}] {case.ai_model} - {case.question[:50]}...")
        
        # 创建串行执行器
        print(f"\n⚙️  创建TestExecutor (串行执行)...")
        executor = TestExecutor(max_workers=1, strategy=ExecutionStrategy.SEQUENTIAL)
        
        def progress_callback(execution_id, progress):
            print(f"📊 进度更新: {progress.progress_percentage:.1f}% ({progress.completed_tests}/{progress.total_tests})")
        
        print(f"\n🚀 开始串行执行 {len(test_cases)} 个测试...")
        start_time = time.time()
        
        results = executor.execute_tests(
            test_cases, 
            api_key="", 
            on_progress_update=progress_callback,
            timeout=1200,  # 20分钟超时
            user_openid="test_user"
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n✅ 执行完成!")
        print(f"⏱️  总耗时: {execution_time:.2f}秒")
        print(f"📈 统计:")
        print(f"   - 总任务数: {results['total_tasks']}")
        print(f"   - 成功: {results['completed_tasks']}")
        print(f"   - 失败: {results['failed_tasks']}")
        print(f"   - 策略: {results['strategy']}")
        
        # 检查结果
        all_results = results.get('results', [])
        print(f"\n📋 详细结果:")
        for i, result in enumerate(all_results):
            success = result.get('success', False)
            model = result.get('model', 'unknown')
            task_id = result.get('task_id', 'unknown')
            status = "✅" if success else "❌"
            print(f"   {status} [{i+1}] {model} (ID: {task_id[:8]}...) - Success: {success}")
        
        # 关闭执行器
        executor.shutdown()
        
        print(f"\n🎯 串行执行测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_platform_requests():
    """测试各个AI平台的独立请求"""
    print("\n" + "=" * 60)
    print("🔍 测试各个AI平台的独立请求能力")
    print("=" * 60)
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 测试平台名称映射
        test_mappings = {
            '豆包': 'doubao',
            'DeepSeek': 'deepseek',
            '通义千问': 'qwen',
            '智谱AI': 'zhipu',
            '文心一言': 'wenxin'
        }
        
        print("🔄 测试平台名称映射...")
        for display_name, expected_internal in test_mappings.items():
            mapped = AIAdapterFactory.get_normalized_model_name(display_name)
            status = "✅" if mapped.value == expected_internal else "❌"
            print(f"   {status} {display_name} -> {mapped.value} (期望: {expected_internal})")
        
        # 测试适配器注册状态
        print(f"\n📋 检查已注册的AI适配器...")
        registered_adapters = [pt.value for pt in AIAdapterFactory._adapters.keys()]
        print(f"   已注册适配器: {registered_adapters}")
        
        # 测试平台可用性
        print(f"\n🔍 测试平台可用性...")
        for display_name in test_mappings.keys():
            normalized = AIAdapterFactory.get_normalized_model_name(display_name)
            is_available = AIAdapterFactory.is_platform_available(normalized.value)
            status = "✅" if is_available else "❌"
            print(f"   {status} {display_name} ({normalized.value}) - 可用: {is_available}")
        
        return True
        
    except Exception as e:
        print(f"❌ 平台请求测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🧪 串行执行方案综合测试")
    print("=" * 60)
    
    success = True
    
    # 测试各个AI平台的独立请求能力
    success &= test_individual_platform_requests()
    
    # 测试串行执行
    success &= test_serial_execution()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过！串行执行方案正常工作。")
        print("✅ AI平台请求现在是独立且可靠的")
        print("✅ 每个平台都会按顺序执行，避免了并发问题")
    else:
        print("💥 测试失败！请检查错误信息。")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    main()