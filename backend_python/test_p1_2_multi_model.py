#!/usr/bin/env python3
"""
P1-2 多模型冗余调用机制验证测试

验证内容:
1. 主模型失败时自动切换到备用模型
2. 返回第一个成功的有效结果
3. 所有模型都失败时返回最佳错误信息
4. 并发控制正常工作

@author: 系统架构组
@date: 2026-02-28
"""

import sys
import asyncio
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.multi_model_executor import MultiModelExecutor, ConcurrentMultiModelExecutor
from wechat_backend.ai_adapters.base_adapter import AIResponse, AIErrorType


# Mock AI 客户端用于测试
class MockAIClient:
    """模拟 AI 客户端"""
    
    def __init__(self, model_name: str, behavior: str = 'success'):
        self.model_name = model_name
        self.behavior = behavior  # 'success', 'fail', 'slow'
    
    def send_prompt(self, prompt: str) -> AIResponse:
        """模拟 send_prompt"""
        if self.behavior == 'success':
            return AIResponse(
                success=True,
                content=f"这是来自 {self.model_name} 的成功响应",
                model=self.model_name,
                latency=0.5
            )
        elif self.behavior == 'fail':
            return AIResponse(
                success=False,
                error_message=f"模型 {self.model_name} 调用失败",
                model=self.model_name,
                error_type=AIErrorType.SERVICE_UNAVAILABLE
            )
        elif self.behavior == 'slow':
            import time
            time.sleep(2)  # 模拟慢响应
            return AIResponse(
                success=True,
                content=f"这是来自 {self.model_name} 的慢响应",
                model=self.model_name,
                latency=2.0
            )
        else:
            return AIResponse(
                success=False,
                error_message="Unknown behavior",
                model=self.model_name
            )


# Mock AIAdapterFactory
class MockAIAdapterFactory:
    """模拟 AI 适配器工厂"""
    
    _models = {}
    
    @classmethod
    def register_model(cls, model_name: str, behavior: str):
        """注册模拟模型"""
        cls._models[model_name] = MockAIClient(model_name, behavior)
    
    @classmethod
    def create(cls, model_name: str):
        """创建 AI 客户端"""
        if model_name not in cls._models:
            # 默认成功
            return MockAIClient(model_name, 'success')
        return cls._models[model_name]


def setup_mock_factory():
    """设置模拟工厂"""
    # 替换真实的工厂
    import wechat_backend.multi_model_executor as mme
    original_factory = mme.AIAdapterFactory
    mme.AIAdapterFactory = MockAIAdapterFactory
    return original_factory


def restore_mock_factory(original_factory):
    """恢复原始工厂"""
    import wechat_backend.multi_model_executor as mme
    mme.AIAdapterFactory = original_factory


async def test_primary_success():
    """测试 1: 主模型成功"""
    print("=" * 60)
    print("测试 1: 主模型成功")
    print("=" * 60)
    
    # 设置：主模型成功
    MockAIAdapterFactory.register_model('doubao', 'success')
    MockAIAdapterFactory.register_model('qwen', 'success')
    MockAIAdapterFactory.register_model('deepseek', 'success')
    
    executor = MultiModelExecutor(timeout_seconds=5)
    result, actual_model = await executor.execute_with_redundancy(
        prompt="测试问题",
        primary_model='doubao'
    )
    
    assert result.success, "主模型应该成功"
    assert actual_model == 'doubao', f"实际模型应为 doubao，实际为 {actual_model}"
    
    print(f"✓ 主模型成功：{actual_model}")
    print(f"  响应内容：{result.content[:50]}...")
    print()
    return True


async def test_primary_fail_fallback():
    """测试 2: 主模型失败，备用模型成功"""
    print("=" * 60)
    print("测试 2: 主模型失败，备用模型成功")
    print("=" * 60)
    
    # 设置：主模型失败，备用模型成功
    MockAIAdapterFactory.register_model('doubao', 'fail')
    MockAIAdapterFactory.register_model('qwen', 'success')
    MockAIAdapterFactory.register_model('deepseek', 'success')
    
    executor = MultiModelExecutor(timeout_seconds=5)
    result, actual_model = await executor.execute_with_redundancy(
        prompt="测试问题",
        primary_model='doubao'
    )
    
    assert result.success, "备用模型应该成功"
    assert actual_model in ['qwen', 'deepseek'], f"实际模型应为备用模型，实际为 {actual_model}"
    
    print(f"✓ 备用模型接管：{actual_model}")
    print(f"  响应内容：{result.content[:50]}...")
    print()
    return True


async def test_all_fail():
    """测试 3: 所有模型都失败"""
    print("=" * 60)
    print("测试 3: 所有模型都失败")
    print("=" * 60)
    
    # 设置：所有模型都失败（包括 wenxin）
    MockAIAdapterFactory.register_model('doubao', 'fail')
    MockAIAdapterFactory.register_model('qwen', 'fail')
    MockAIAdapterFactory.register_model('deepseek', 'fail')
    MockAIAdapterFactory.register_model('wenxin', 'fail')
    
    executor = MultiModelExecutor(timeout_seconds=5)
    result, actual_model = await executor.execute_with_redundancy(
        prompt="测试问题",
        primary_model='doubao'
    )
    
    assert not result.success, "所有模型应该都失败"
    assert result.error_message, "应该有错误信息"
    
    print(f"✓ 所有模型失败，返回错误信息")
    print(f"  错误信息：{result.error_message}")
    print()
    return True


async def test_concurrent_execution():
    """测试 4: 并发调用多个模型"""
    print("=" * 60)
    print("测试 4: 并发调用多个模型")
    print("=" * 60)
    
    # 设置：多个成功模型
    MockAIAdapterFactory.register_model('doubao', 'success')
    MockAIAdapterFactory.register_model('qwen', 'success')
    MockAIAdapterFactory.register_model('deepseek', 'success')
    
    executor = ConcurrentMultiModelExecutor(timeout_seconds=5)
    results = await executor.execute_all_models(
        prompt="测试问题",
        models=['doubao', 'qwen', 'deepseek']
    )
    
    assert len(results) == 3, f"应该有 3 个结果，实际有 {len(results)} 个"
    success_count = sum(1 for _, r in results if r.success)
    assert success_count == 3, f"所有模型应该都成功，实际成功 {success_count} 个"
    
    print(f"✓ 并发调用完成：{success_count}/{len(results)} 成功")
    for model_name, result in results:
        print(f"  - {model_name}: {'成功' if result.success else '失败'}")
    print()
    return True


async def test_fallback_order():
    """测试 5: 备用模型顺序"""
    print("=" * 60)
    print("测试 5: 备用模型顺序")
    print("=" * 60)
    
    executor = MultiModelExecutor()
    
    # 测试 doubao 的备用顺序
    order = executor.get_optimal_model_order('doubao')
    print(f"  doubao 的调用顺序：{order}")
    assert order[0] == 'doubao', "首选模型应该在最前面"
    
    # 测试 qwen 的备用顺序
    order = executor.get_optimal_model_order('qwen')
    print(f"  qwen 的调用顺序：{order}")
    assert order[0] == 'qwen', "首选模型应该在最前面"
    
    print(f"✓ 备用模型顺序正确")
    print()
    return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("P1-2 多模型冗余调用机制验证测试")
    print("=" * 60)
    print()
    
    # 设置模拟工厂
    original_factory = setup_mock_factory()
    
    tests = [
        ("主模型成功", test_primary_success),
        ("主模型失败备用成功", test_primary_fail_fallback),
        ("所有模型失败", test_all_fail),
        ("并发调用", test_concurrent_execution),
        ("备用顺序", test_fallback_order),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
        except AssertionError as e:
            print(f"✗ {test_name} 测试失败：{e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name} 异常：{e}\n")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # 恢复原始工厂
    restore_mock_factory(original_factory)
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
