"""
安全改进集成测试
测试各组件之间的集成和交互
"""

import unittest
import time
from unittest.mock import Mock, patch
from wechat_backend.network.security import get_http_client
from wechat_backend.network.connection_pool import get_session_for_url
from wechat_backend.network.circuit_breaker import get_circuit_breaker
from wechat_backend.network.rate_limiter import is_rate_limited
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_end_to_end_request_flow(self):
        """测试端到端请求流程"""
        # 创建AI请求包装器
        wrapper = get_ai_request_wrapper(
            platform_name="integration-test",
            api_key="test-key",
            base_url="https://httpbin.org"  # 使用httpbin进行测试
        )

        self.assertIsNotNone(wrapper)
        self.assertEqual(wrapper.platform_name, "integration-test")

    def test_circuit_breaker_with_rate_limiter(self):
        """测试断路器与速率限制器的集成"""
        # 获取两个组件
        circuit_breaker = get_circuit_breaker("integration-test-service")
        rate_limited = is_rate_limited("integration-test-key", 100, 60)

        # 验证它们都能正常工作
        self.assertIsNotNone(circuit_breaker)
        self.assertIsInstance(rate_limited, bool)

    def test_adapter_with_all_components(self):
        """测试适配器与所有组件的集成"""
        adapter = DeepSeekAdapter(
            api_key="test-key",
            model_name="test-model",
            base_url="https://httpbin.org"
        )

        # 验证适配器使用了所有安全组件
        self.assertIsNotNone(adapter.request_wrapper)
        self.assertIsNotNone(adapter.api_key)
        self.assertEqual(adapter.model_name, "test-model")

    def test_metrics_collection_through_workflow(self):
        """测试通过完整工作流的指标收集"""
        from wechat_backend.monitoring.metrics_collector import get_metrics_collector

        collector = get_metrics_collector()

        # 模拟一个完整的API调用流程
        collector.record_api_call("integration-test", "/test-endpoint", 200, 0.05)
        collector.record_error("integration-test", "test-error-type", "Test error")

        # 验证指标被正确收集
        stats = collector.get_api_call_stats("integration-test", 1)
        self.assertIsInstance(stats, dict)

        error_stats = collector.get_error_stats("integration-test", 1)
        self.assertIsInstance(error_stats, dict)


def run_integration_tests():
    """运行集成测试"""
    print("🔗 开始运行集成测试...")

    # 创建测试套件
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    print(f"\n📊 集成测试结果:")
    print(f"   运行测试数: {result.testsRun}")
    print(f"   失败数: {len(result.failures)}")
    print(f"   错误数: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
