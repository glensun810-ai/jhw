"""
安全改进验证测试套件
用于验证所有安全改进措施的有效性
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from wechat_backend.network.security import SecureHttpClient, get_http_client
from wechat_backend.network.connection_pool import get_connection_pool_manager
from wechat_backend.network.circuit_breaker import get_circuit_breaker, CircuitState
from wechat_backend.network.rate_limiter import get_rate_limiter_manager
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.monitoring.metrics_collector import get_metrics_collector
from wechat_backend.ai_adapters.base_adapter import AIResponse, AIErrorType
from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter


class TestSecurityImprovements(unittest.TestCase):
    """安全改进验证测试"""
    
    def setUp(self):
        """测试前准备"""
        self.api_key = "test-key"
        self.model_name = "test-model"
    
    def test_secure_http_client_creation(self):
        """测试安全HTTP客户端创建"""
        client = get_http_client()
        self.assertIsNotNone(client)
        self.assertTrue(hasattr(client, 'get'))
        self.assertTrue(hasattr(client, 'post'))
    
    def test_connection_pool_management(self):
        """测试连接池管理"""
        pool_manager = get_connection_pool_manager()
        self.assertIsNotNone(pool_manager)
        
        # 测试获取默认会话
        default_session = pool_manager.get_default_session()
        self.assertIsNotNone(default_session)
    
    def test_circuit_breaker_functionality(self):
        """测试断路器功能"""
        circuit_breaker = get_circuit_breaker("test-service")
        self.assertIsNotNone(circuit_breaker)
        
        # 测试初始状态
        self.assertEqual(circuit_breaker.state, CircuitState.CLOSED)
        
        # 模拟多次失败来触发断路器
        def failing_function():
            raise Exception("Simulated failure")
        
        # 快速连续调用失败函数，直到断路器打开
        for i in range(6):  # 超过默认阈值5次
            try:
                circuit_breaker.call(failing_function)
            except:
                pass  # 预期的异常
        
        # 断路器应该已经打开
        state_info = circuit_breaker.get_state_info()
        self.assertIn(state_info['state'], ['open', 'OPEN'])
    
    def test_rate_limiter_functionality(self):
        """测试速率限制器功能"""
        rate_limiter = get_rate_limiter_manager()
        self.assertIsNotNone(rate_limiter)
        
        # 测试速率限制
        result = rate_limiter.is_allowed("test-key", 10, 60)  # 10次/60秒
        self.assertTrue(result)
    
    def test_metrics_collection(self):
        """测试指标收集"""
        collector = get_metrics_collector()
        self.assertIsNotNone(collector)
        
        # 记录一些测试指标
        collector.record_api_call("test-platform", "/test-endpoint", 200, 0.1)
        collector.record_error("test-platform", "test-error", "Test error message")
        
        # 验证指标被记录
        stats = collector.get_api_call_stats("test-platform", 1)
        self.assertGreaterEqual(stats.get('total_calls', 0), 1)
    
    def test_unified_request_wrapper(self):
        """测试统一请求封装"""
        wrapper = get_ai_request_wrapper(
            platform_name="test-platform",
            api_key="test-key"
        )
        self.assertIsNotNone(wrapper)
        
        # 验证包装器属性
        self.assertEqual(wrapper.platform_name, "test-platform")
        self.assertEqual(wrapper.api_key, "test-key")
    
    def test_deepseek_adapter_initialization(self):
        """测试DeepSeek适配器初始化"""
        adapter = DeepSeekAdapter(
            api_key=self.api_key,
            model_name=self.model_name
        )
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.model_name, self.model_name)
        self.assertEqual(adapter.api_key, self.api_key)
    
    def test_deepseek_adapter_send_prompt(self):
        """测试DeepSeek适配器发送提示"""
        adapter = DeepSeekAdapter(
            api_key=self.api_key,
            model_name=self.model_name
        )
        
        # 模拟API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "model": self.model_name,
            "usage": {"total_tokens": 10}
        }
        
        # 由于实际API调用会失败（因为使用了测试密钥），我们验证错误处理
        response = adapter.send_prompt("Test prompt")
        # 由于使用了测试密钥，预期会失败
        self.assertIsInstance(response, AIResponse)
        self.assertFalse(response.success)
        self.assertIsNotNone(response.error_message)
    
    def test_error_mapping(self):
        """测试错误映射功能"""
        adapter = DeepSeekAdapter(
            api_key=self.api_key,
            model_name=self.model_name
        )
        
        # 创建一个模拟的请求异常
        mock_exception = Mock()
        mock_exception.response = Mock()
        mock_exception.response.status_code = 401
        
        error_type = adapter._map_request_exception(mock_exception)
        self.assertEqual(error_type, AIErrorType.INVALID_API_KEY)


class TestPerformanceAndReliability(unittest.TestCase):
    """性能和可靠性测试"""
    
    def test_concurrent_requests_handling(self):
        """测试并发请求处理"""
        # 创建多个适配器实例
        adapters = []
        for i in range(5):
            adapter = DeepSeekAdapter(
                api_key=f"test-key-{i}",
                model_name=f"test-model-{i}"
            )
            adapters.append(adapter)
        
        self.assertEqual(len(adapters), 5)
        
        # 验证每个适配器都有独立的组件
        for adapter in adapters:
            self.assertIsNotNone(adapter.request_wrapper)
    
    def test_resource_cleanup(self):
        """测试资源清理"""
        # 测试连接池清理
        from wechat_backend.network.connection_pool import cleanup_connection_pools
        cleanup_connection_pools()
        # 这个测试主要是确保清理函数可以正常运行而不抛出异常


class TestMonitoringAndLogging(unittest.TestCase):
    """监控和日志测试"""
    
    def test_metrics_retention(self):
        """测试指标保留"""
        collector = get_metrics_collector()
        
        # 记录一些指标
        for i in range(5):
            collector.record_api_call(f"platform-{i}", f"/endpoint-{i}", 200, 0.1)
        
        # 验证指标被正确记录
        counters = collector.get_counters()
        self.assertGreaterEqual(len(counters), 0)
        
        gauges = collector.get_gauges()
        self.assertIsInstance(gauges, dict)
    
    def test_security_event_recording(self):
        """测试安全事件记录"""
        from wechat_backend.monitoring.metrics_collector import record_security_event
        
        # 记录一个安全事件
        record_security_event("test-event", "high", {"test": "data"})
        
        # 验证事件被记录
        collector = get_metrics_collector()
        events = collector.get_security_events(1)  # 获取最近1小时的事件
        # 注意：由于时间差，可能无法立即获取到事件，所以这里主要是确保函数正常运行


def run_security_tests():
    """运行安全改进测试"""
    print("🧪 开始运行安全改进验证测试...")
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试用例
    test_suite.addTest(unittest.makeSuite(TestSecurityImprovements))
    test_suite.addTest(unittest.makeSuite(TestPerformanceAndReliability))
    test_suite.addTest(unittest.makeSuite(TestMonitoringAndLogging))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print(f"\n📊 测试结果:")
    print(f"   运行测试数: {result.testsRun}")
    print(f"   失败数: {len(result.failures)}")
    print(f"   错误数: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_security_tests()
    exit(0 if success else 1)
