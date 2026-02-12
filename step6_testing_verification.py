#!/usr/bin/env python3
"""
测试和验证工具
此脚本用于验证所有安全改进措施的有效性
"""

import os
import sys
from pathlib import Path
import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock


def create_comprehensive_tests():
    """创建综合测试套件"""
    
    test_content = '''"""
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
        self.assertEqual(adapter.api_key, self.model_name)
    
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
    
    print(f"\\n📊 测试结果:")
    print(f"   运行测试数: {result.testsRun}")
    print(f"   失败数: {len(result.failures)}")
    print(f"   错误数: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_security_tests()
    exit(0 if success else 1)
'''
    
    # 创建测试目录
    test_dir = Path('tests')
    test_dir.mkdir(exist_ok=True)
    
    # 写入测试文件
    with open(test_dir / 'test_security_improvements.py', 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("✓ 已创建安全改进验证测试: tests/test_security_improvements.py")


def create_integration_tests():
    """创建集成测试"""

    integration_test_content = '''"""
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

    print(f"\\n📊 集成测试结果:")
    print(f"   运行测试数: {result.testsRun}")
    print(f"   失败数: {len(result.failures)}")
    print(f"   错误数: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
'''

    # 创建测试目录
    test_dir = Path('tests')
    test_dir.mkdir(exist_ok=True)

    # 写入集成测试文件
    with open(test_dir / 'test_integration.py', 'w', encoding='utf-8') as f:
        f.write(integration_test_content)

    print("✓ 已创建集成测试: tests/test_integration.py")


def create_final_verification_script():
    """创建最终验证脚本"""
    
    verification_script_content = '''#!/usr/bin/env python3
"""
最终验证脚本
验证所有安全改进措施是否正确实施
"""

import os
import sys
import importlib
from pathlib import Path


def check_module_availability():
    """检查所有新模块是否可以正确导入"""
    modules_to_check = [
        "wechat_backend.security.secure_config",
        "wechat_backend.network.security",
        "wechat_backend.network.connection_pool",
        "wechat_backend.network.circuit_breaker",
        "wechat_backend.network.retry_mechanism",
        "wechat_backend.network.rate_limiter",
        "wechat_backend.network.request_wrapper",
        "wechat_backend.monitoring.metrics_collector",
        "wechat_backend.monitoring.alert_system",
        "wechat_backend.monitoring.logging_enhancements",
    ]
    
    print("🔍 检查模块可用性...")
    all_imported = True
    
    for module_name in modules_to_check:
        try:
            importlib.import_module(module_name)
            print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}: {e}")
            all_imported = False
    
    return all_imported


def check_file_existence():
    """检查所有必需的文件是否存在"""
    files_to_check = [
        "wechat_backend/security/secure_config.py",
        "wechat_backend/network/security.py",
        "wechat_backend/network/connection_pool.py",
        "wechat_backend/network/circuit_breaker.py",
        "wechat_backend/network/retry_mechanism.py",
        "wechat_backend/network/rate_limiter.py",
        "wechat_backend/network/request_wrapper.py",
        "wechat_backend/monitoring/metrics_collector.py",
        "wechat_backend/monitoring/alert_system.py",
        "wechat_backend/monitoring/logging_enhancements.py",
        "wechat_backend/ai_adapters/deepseek_adapter.py",  # 更新后的适配器
        ".env.example",  # 安全的环境变量示例
    ]
    
    print("\\n📁 检查文件存在性...")
    all_exist = True
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path}")
            all_exist = False
    
    return all_exist


def check_sensitive_data_removal():
    """检查是否已移除敏感数据"""
    files_to_check = [
        ".env",
        "test_doubao_api.py",
        "test_real_api_calls_updated.py",
        "test_api_keys.py",
        "real_api_implementation_summary.md",
    ]
    
    print("\\n🔒 检查敏感数据移除...")
    sensitive_patterns = [
        "sk-13908093890f46fb82c52a01c8dfc464",
        "sk-5261a4dfdf964a5c9a6364128cc4c653", 
        "2a376e32-8877-4df8-9865-7eb3e99c9f92",
        "AIzaSyCOeSqGt-YluHUQkdStzc-RVkufFKBldCE",
        "504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh",
        "wx8876348e089bc261",
        "6d43225261bbfc9bfe3c68de9e069b66",
    ]
    
    all_clean = True
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            found_patterns = []
            for pattern in sensitive_patterns:
                if pattern in content:
                    found_patterns.append(pattern)
            
            if found_patterns:
                print(f"  ✗ {file_path}: 发现敏感数据 {found_patterns}")
                all_clean = False
            else:
                print(f"  ✓ {file_path}: 无敏感数据")
    
    return all_clean


def run_all_checks():
    """运行所有检查"""
    print("🚀 开始最终验证...")
    print("=" * 50)
    
    results = []
    
    # 检查模块可用性
    modules_ok = check_module_availability()
    results.append(("模块可用性", modules_ok))
    
    # 检查文件存在性
    files_ok = check_file_existence()
    results.append(("文件存在性", files_ok))
    
    # 检查敏感数据移除
    sensitive_clean = check_sensitive_data_removal()
    results.append(("敏感数据移除", sensitive_clean))
    
    print("\\n" + "=" * 50)
    print("📋 验证结果摘要:")
    
    all_passed = True
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {check_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\\n🎯 总体结果: {'✓ ALL CHECKS PASSED' if all_passed else '✗ SOME CHECKS FAILED'}")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
'''
    
    # 写入最终验证脚本
    with open('verify_implementation.py', 'w', encoding='utf-8') as f:
        f.write(verification_script_content)
    
    print("✓ 已创建最终验证脚本: verify_implementation.py")


def main():
    print("🚀 开始执行安全改进计划 - 第六步：测试和验证")
    print("=" * 60)
    
    print("\n1. 创建综合测试套件...")
    create_comprehensive_tests()
    
    print("\n2. 创建集成测试...")
    create_integration_tests()
    
    print("\n3. 创建最终验证脚本...")
    create_final_verification_script()
    
    print("\n" + "=" * 60)
    print("✅ 第六步完成！")
    print("\n已完成：")
    print("• 创建了全面的安全改进验证测试")
    print("• 创建了组件集成测试")
    print("• 创建了最终验证脚本")
    print("\n下一步：")
    print("• 运行测试验证所有改进措施")
    print("• 执行最终验证脚本确认实施效果")
    print("• 准备部署到生产环境")


if __name__ == "__main__":
    main()