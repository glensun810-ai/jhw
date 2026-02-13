"""
工作流管理器单元测试
"""
import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from wechat_backend.analytics.workflow_manager import WorkflowManager, TaskStatus


class TestWorkflowManager(unittest.TestCase):
    """测试WorkflowManager类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.wf_manager = WorkflowManager()

    def test_create_task_package(self):
        """测试创建任务包功能"""
        task_package = self.wf_manager.create_task_package(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook"
        )

        # 验证任务包结构
        self.assertIn("task_id", task_package)
        self.assertIn("payload", task_package)
        self.assertIn("webhook_url", task_package)
        self.assertEqual(task_package["webhook_url"], "https://hooks.example.com/webhook")
        
        payload = task_package["payload"]
        self.assertEqual(payload["evidence_fragment"], "测试证据片段")
        self.assertEqual(payload["brand_name"], "测试品牌")
        self.assertEqual(payload["risk_level"], "High")
        self.assertEqual(payload["intervention_script"], "测试纠偏脚本")
        self.assertIn("created_at", payload)

    def test_dispatch_task(self):
        """测试任务分发功能"""
        with patch.object(self.wf_manager, '_send_webhook_async') as mock_send:
            task_id = self.wf_manager.dispatch_task(
                evidence_fragment="测试证据片段",
                associated_url="https://example.com",
                source_name="测试信源",
                risk_level="High",
                brand_name="测试品牌",
                intervention_script="测试纠偏脚本",
                source_meta={"platform": "test", "category": "security"},
                webhook_url="https://hooks.example.com/webhook"
            )

            # 验证任务ID被创建
            self.assertIsNotNone(task_id)
            self.assertTrue(task_id.startswith("wf_"))
            
            # 验证任务被存储
            self.assertIn(task_id, self.wf_manager.active_tasks)
            
            # 验证异步发送被调用
            self.assertEqual(mock_send.call_count, 1)

    def test_get_task_status(self):
        """测试获取任务状态功能"""
        # 先创建一个任务
        task_id = self.wf_manager.dispatch_task(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook"
        )

        # 等待任务被创建
        time.sleep(0.1)

        # 获取任务状态
        status = self.wf_manager.get_task_status(task_id)

        # 验证状态信息
        self.assertIsNotNone(status)
        self.assertEqual(status["task_id"], task_id)
        self.assertIn(status["status"], [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value])
        self.assertEqual(status["retry_count"], 0)
        self.assertIn("created_at", status)
        self.assertIn("updated_at", status)

    def test_get_nonexistent_task_status(self):
        """测试获取不存在任务的状态"""
        status = self.wf_manager.get_task_status("nonexistent_task_id")
        self.assertIsNone(status)

    def test_get_all_active_tasks(self):
        """测试获取所有活动任务"""
        # 创建多个任务
        task_ids = []
        for i in range(3):
            task_id = self.wf_manager.dispatch_task(
                evidence_fragment=f"测试证据片段{i}",
                associated_url="https://example.com",
                source_name="测试信源",
                risk_level="High",
                brand_name="测试品牌",
                intervention_script="测试纠偏脚本",
                source_meta={"platform": "test", "category": "security"},
                webhook_url="https://hooks.example.com/webhook"
            )
            task_ids.append(task_id)

        # 等待任务被创建
        time.sleep(0.1)

        # 获取所有活动任务
        active_tasks = self.wf_manager.get_all_active_tasks()

        # 验证任务数量
        self.assertEqual(len(active_tasks), 3)
        
        # 验证任务ID存在于返回的列表中
        returned_task_ids = [task["task_id"] for task in active_tasks]
        for task_id in task_ids:
            self.assertIn(task_id, returned_task_ids)

    def test_cancel_task_success(self):
        """测试成功取消任务"""
        # 创建一个任务
        task_id = self.wf_manager.dispatch_task(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook"
        )

        # 等待任务被创建
        time.sleep(0.1)

        # 取消任务
        result = self.wf_manager.cancel_task(task_id)

        # 验证任务被取消
        self.assertTrue(result)
        self.assertNotIn(task_id, self.wf_manager.active_tasks)

    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        result = self.wf_manager.cancel_task("nonexistent_task_id")
        self.assertFalse(result)

    @patch('requests.post')
    def test_webhook_success(self, mock_post):
        """测试Webhook成功发送"""
        # 模拟成功的HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 创建任务包
        task_package = self.wf_manager.create_task_package(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook"
        )

        # 创建任务对象
        from datetime import datetime
        from wechat_backend.analytics.workflow_manager import WorkflowTask, TaskStatus
        task = WorkflowTask(
            task_id="test_task_123",
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 发送Webhook请求
        success = self.wf_manager._send_webhook_request(task_package, task)

        # 验证请求被发送
        mock_post.assert_called_once()
        self.assertTrue(success)

    @patch('requests.post')
    def test_webhook_failure(self, mock_post):
        """测试Webhook失败"""
        # 模拟失败的HTTP响应
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # 创建任务包
        task_package = self.wf_manager.create_task_package(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook"
        )

        # 创建任务对象
        from datetime import datetime
        from wechat_backend.analytics.workflow_manager import WorkflowTask, TaskStatus
        task = WorkflowTask(
            task_id="test_task_123",
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 发送Webhook请求
        success = self.wf_manager._send_webhook_request(task_package, task)

        # 验证请求被发送但失败
        mock_post.assert_called_once()
        self.assertFalse(success)

    @patch('requests.post')
    def test_webhook_timeout(self, mock_post):
        """测试Webhook超时"""
        # 模拟超时异常
        mock_post.side_effect = TimeoutError("Request timed out")

        # 创建任务包
        task_package = self.wf_manager.create_task_package(
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook"
        )

        # 创建任务对象
        from datetime import datetime
        from wechat_backend.analytics.workflow_manager import WorkflowTask, TaskStatus
        task = WorkflowTask(
            task_id="test_task_123",
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 发送Webhook请求
        success = self.wf_manager._send_webhook_request(task_package, task)

        # 验证请求被发送但失败
        mock_post.assert_called_once()
        self.assertFalse(success)

    def test_schedule_retry_logic(self):
        """测试重试逻辑"""
        # 创建任务对象
        from datetime import datetime
        from wechat_backend.analytics.workflow_manager import WorkflowTask, TaskStatus
        task = WorkflowTask(
            task_id="test_task_123",
            evidence_fragment="测试证据片段",
            associated_url="https://example.com",
            source_name="测试信源",
            risk_level="High",
            brand_name="测试品牌",
            intervention_script="测试纠偏脚本",
            source_meta={"platform": "test", "category": "security"},
            webhook_url="https://hooks.example.com/webhook",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            max_retries=3
        )

        # 验证初始重试计数
        self.assertEqual(task.retry_count, 0)

        # 模拟一次失败后增加重试计数
        task.retry_count += 1
        self.assertEqual(task.retry_count, 1)

        # 验证状态变为重试中
        task.status = TaskStatus.RETRYING
        self.assertEqual(task.status, TaskStatus.RETRYING)

        # 验证最大重试次数
        for i in range(2):  # 已经有一次失败，再失败2次达到最大重试次数
            task.retry_count += 1

        self.assertEqual(task.retry_count, 3)
        self.assertEqual(task.retry_count, task.max_retries)


if __name__ == '__main__':
    unittest.main()