"""
工作流管理器单元测试
测试Webhook功能和重试机制
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime, timedelta
from wechat_backend.ai_adapters.workflow_manager import WorkflowManager, WebhookManager, TaskPriority


class TestWebhookManager(unittest.TestCase):
    """测试WebhookManager类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.webhook_manager = WebhookManager()

    @patch('requests.Session.post')
    def test_send_webhook_success(self, mock_post):
        """测试Webhook发送成功"""
        # 模拟成功的HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 测试数据
        webhook_url = "https://example.com/webhook"
        payload = {"test": "data"}
        task_id = "test_task_123"

        # 执行测试
        result = self.webhook_manager.send_webhook(webhook_url, payload, task_id)

        # 验证结果
        self.assertTrue(result)
        mock_post.assert_called_once_with(
            webhook_url,
            json=payload,
            timeout=30
        )

    @patch('requests.Session.post')
    def test_send_webhook_non_success_status(self, mock_post):
        """测试Webhook收到非成功状态码"""
        # 模拟非成功状态码的响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        # 测试数据
        webhook_url = "https://example.com/webhook"
        payload = {"test": "data"}
        task_id = "test_task_123"

        # 执行测试
        result = self.webhook_manager.send_webhook(webhook_url, payload, task_id)

        # 验证结果
        self.assertFalse(result)

    @patch('requests.Session.post')
    def test_send_webhook_timeout(self, mock_post):
        """测试Webhook请求超时"""
        # 模拟超时异常
        mock_post.side_effect = TimeoutError("Request timed out")

        # 测试数据
        webhook_url = "https://example.com/webhook"
        payload = {"test": "data"}
        task_id = "test_task_123"

        # 执行测试 - 应该捕获异常并返回False
        with patch.object(self.webhook_manager.circuit_breaker, 'call') as mock_call:
            # 让call方法直接执行内部函数，避免电路断路器的复杂逻辑
            def call_func(func, *args, **kwargs):
                return func(*args, **kwargs)
            mock_call.side_effect = call_func
            
            result = self.webhook_manager.send_webhook(webhook_url, payload, task_id)

        # 验证结果
        self.assertFalse(result)

    @patch('requests.Session.post')
    def test_send_webhook_request_exception(self, mock_post):
        """测试Webhook请求异常"""
        # 模拟请求异常
        mock_post.side_effect = Exception("Network error")

        # 测试数据
        webhook_url = "https://example.com/webhook"
        payload = {"test": "data"}
        task_id = "test_task_123"

        # 执行测试
        with patch.object(self.webhook_manager.circuit_breaker, 'call') as mock_call:
            # 让call方法直接执行内部函数
            def call_func(func, *args, **kwargs):
                return func(*args, **kwargs)
            mock_call.side_effect = call_func
            
            result = self.webhook_manager.send_webhook(webhook_url, payload, task_id)

        # 验证结果
        self.assertFalse(result)


class TestWorkflowManager(unittest.TestCase):
    """测试WorkflowManager类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.workflow_manager = WorkflowManager()

    def test_create_task_package(self):
        """测试创建任务包功能"""
        # 测试数据
        evidence_fragment = "测试证据片段"
        associated_url = "https://example.com"
        source_name = "测试信源"
        risk_level = "High"
        brand_name = "测试品牌"
        intervention_script = "测试干预脚本"
        source_meta = {"platform": "test", "category": "security"}
        webhook_url = "https://example.com/webhook"

        # 执行测试
        task_package = self.workflow_manager.create_task_package(
            evidence_fragment, associated_url, source_name, 
            risk_level, brand_name, intervention_script, source_meta, webhook_url
        )

        # 验证结果
        self.assertIsInstance(task_package, dict)
        self.assertIn('task_type', task_package)
        self.assertIn('evidence_data', task_package)
        self.assertIn('delivery_instructions', task_package)
        self.assertEqual(task_package['task_type'], 'negative_evidence_intervention')
        self.assertEqual(task_package['evidence_data']['evidence_fragment'], evidence_fragment)
        self.assertEqual(task_package['delivery_instructions']['webhook_url'], webhook_url)

    def test_priority_to_number_conversion(self):
        """测试优先级到数字的转换"""
        # 测试各种优先级
        self.assertEqual(self.workflow_manager._priority_to_number(TaskPriority.LOW), 4)
        self.assertEqual(self.workflow_manager._priority_to_number(TaskPriority.MEDIUM), 3)
        self.assertEqual(self.workflow_manager._priority_to_number(TaskPriority.HIGH), 2)
        self.assertEqual(self.workflow_manager._priority_to_number(TaskPriority.CRITICAL), 1)

    @patch.object(WebhookManager, 'send_webhook')
    def test_dispatch_task(self, mock_send_webhook):
        """测试任务分发功能"""
        # 模拟Webhook发送成功
        mock_send_webhook.return_value = True

        # 测试数据
        evidence_fragment = "测试证据片段"
        associated_url = "https://example.com"
        source_name = "测试信源"
        risk_level = "High"
        brand_name = "测试品牌"
        intervention_script = "测试干预脚本"
        source_meta = {"platform": "test", "category": "security"}
        webhook_url = "https://example.com/webhook"

        # 执行测试
        task_id = self.workflow_manager.dispatch_task(
            evidence_fragment, associated_url, source_name, 
            risk_level, brand_name, intervention_script, source_meta, webhook_url
        )

        # 验证结果
        self.assertIsInstance(task_id, str)
        self.assertTrue(task_id.startswith('wf_'))


class TestRetryMechanism(unittest.TestCase):
    """测试重试机制"""

    def test_calculate_retry_delay_basic(self):
        """测试基本重试延迟计算"""
        workflow_manager = WorkflowManager()

        # 测试第一次重试（retry_count=0）
        delay = workflow_manager._calculate_retry_delay(0)
        self.assertGreaterEqual(delay, 30)  # 基础延迟30秒
        self.assertLessEqual(delay, 40)  # 加上抖动不超过40秒

        # 测试第二次重试（retry_count=1）
        delay = workflow_manager._calculate_retry_delay(1)
        self.assertGreaterEqual(delay, 60)  # 30*2=60秒
        self.assertLessEqual(delay, 70)  # 加上抖动不超过70秒

        # 测试第三次重试（retry_count=2）
        delay = workflow_manager._calculate_retry_delay(2)
        self.assertGreaterEqual(delay, 120)  # 30*2^2=120秒
        self.assertLessEqual(delay, 130)  # 加上抖动不超过130秒

    def test_calculate_retry_delay_maximum_limit(self):
        """测试重试延迟的最大限制"""
        workflow_manager = WorkflowManager()

        # 测试大量重试次数，验证延迟不会超过最大限制（3600秒）
        delay = workflow_manager._calculate_retry_delay(10)  # 大量重试
        self.assertLessEqual(delay, 3600)  # 不应超过1小时


def test_webhook_retry_simulation():
    """模拟Webhook重试场景测试"""
    print("测试Webhook重试机制模拟...")
    
    # 创建工作流管理器
    workflow_manager = WorkflowManager()
    
    # 模拟Webhook发送失败的情况
    with patch.object(WebhookManager, 'send_webhook') as mock_send_webhook:
        # 让前两次调用失败，第三次成功
        call_count = 0
        def mock_behavior(url, payload, task_id):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False  # 前两次失败
            else:
                return True   # 第三次成功
        
        mock_send_webhook.side_effect = mock_behavior
        
        # 创建任务包
        task_package = workflow_manager.create_task_package(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试干预脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://example.com/webhook"
        )
        
        # 模拟处理任务（这会触发重试逻辑）
        task_data = {
            'task_id': 'test_task_123',
            'task_package': task_package,
            'webhook_url': 'https://example.com/webhook',
            'retry_count': 0,
            'max_retries': 3
        }
        
        # 处理任务（会触发重试）
        workflow_manager._process_task(task_data)
        
        # 验证调用次数
        print(f"Webhook调用次数: {call_count}")
        assert call_count == 3, f"期望调用3次，实际调用{call_count}次"
        print("✓ 重试机制正常工作，失败后进行了重试")
    
    print("Webhook重试机制模拟测试完成！")


if __name__ == '__main__':
    # 运行单元测试
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # 运行模拟测试
    test_webhook_retry_simulation()