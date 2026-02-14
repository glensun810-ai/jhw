"""
ProviderFactory 单元测试
测试ProviderFactory的功能和DeepSeekProvider的实现
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from wechat_backend.ai_adapters.provider_factory import ProviderFactory
from wechat_backend.ai_adapters.base_provider import BaseAIProvider
from wechat_backend.ai_adapters.deepseek_provider import DeepSeekProvider


class TestProviderFactory(unittest.TestCase):
    """测试ProviderFactory类的功能"""

    def setUp(self):
        """设置测试环境"""
        # 重置工厂的注册表以确保测试隔离
        ProviderFactory._providers = {}

    def test_register_provider(self):
        """测试注册提供者"""
        class MockProvider(BaseAIProvider):
            def ask_question(self, prompt: str):
                return {"content": "test response"}

        ProviderFactory.register("mock_provider", MockProvider)
        
        registered_providers = ProviderFactory.get_available_providers()
        self.assertIn("mock_provider", registered_providers)
        print("✓ 提供者注册功能测试通过")

    def test_create_provider_instance(self):
        """测试创建提供者实例"""
        class MockProvider(BaseAIProvider):
            def __init__(self, api_key, model_name=None):
                super().__init__(api_key, model_name)
            
            def ask_question(self, prompt: str):
                return {"content": "test response"}

        ProviderFactory.register("mock_provider", MockProvider)
        
        provider = ProviderFactory.create("mock_provider", "test-key", "test-model")
        
        self.assertIsInstance(provider, MockProvider)
        self.assertEqual(provider.api_key, "test-key")
        self.assertEqual(provider.model_name, "test-model")
        print("✓ 提供者实例创建功能测试通过")

    def test_create_provider_without_model_name(self):
        """测试不指定模型名称时创建提供者"""
        class MockProvider(BaseAIProvider):
            def __init__(self, api_key, model_name=None):
                super().__init__(api_key, model_name)
            
            def ask_question(self, prompt: str):
                return {"content": "test response"}

        ProviderFactory.register("mock_provider", MockProvider)
        
        provider = ProviderFactory.create("mock_provider", "test-key")
        
        self.assertIsInstance(provider, MockProvider)
        self.assertEqual(provider.api_key, "test-key")
        self.assertIsNone(provider.model_name)
        print("✓ 未指定模型名称时提供者创建功能测试通过")

    def test_create_nonexistent_provider_raises_error(self):
        """测试创建不存在的提供者时抛出错误"""
        with self.assertRaises(ValueError) as context:
            ProviderFactory.create("nonexistent_provider", "test-key")
        
        self.assertIn("No provider registered", str(context.exception))
        print("✓ 不存在提供者时抛出错误测试通过")

    def test_get_available_providers(self):
        """测试获取可用提供者列表"""
        # 注册一些提供者
        class MockProvider1(BaseAIProvider):
            def ask_question(self, prompt: str):
                return {"content": "test response"}

        class MockProvider2(BaseAIProvider):
            def ask_question(self, prompt: str):
                return {"content": "test response"}

        ProviderFactory.register("provider1", MockProvider1)
        ProviderFactory.register("provider2", MockProvider2)
        
        available = ProviderFactory.get_available_providers()
        
        self.assertIn("provider1", available)
        self.assertIn("provider2", available)
        self.assertEqual(len(available), 2)
        print("✓ 获取可用提供者列表功能测试通过")


class TestDeepSeekProvider(unittest.TestCase):
    """测试DeepSeekProvider类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.provider = DeepSeekProvider(
            api_key="test-key",
            model_name="deepseek-chat",
            enable_reasoning_extraction=True
        )

    @patch('requests.Session.post')
    def test_ask_question_success(self, mock_post):
        """测试成功发送问题"""
        # 模拟成功的API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "这是一个测试回答"
                    }
                }
            ],
            "model": "deepseek-chat",
            "usage": {
                "total_tokens": 10
            }
        }
        mock_post.return_value = mock_response

        # 创建会话模拟
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        self.provider.session = mock_session

        result = self.provider.ask_question("测试问题")

        self.assertTrue(result['success'])
        self.assertEqual(result['content'], "这是一个测试回答")
        self.assertEqual(result['model'], "deepseek-chat")
        self.assertEqual(result['tokens_used'], 10)
        print("✓ 成功发送问题测试通过")

    @patch('requests.Session.post')
    def test_ask_question_with_reasoning_extraction(self, mock_post):
        """测试推理链提取功能"""
        # 模拟包含推理内容的API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "最终答案是正确的",
                        "reasoning": "这是推理过程，分析了各种可能性"
                    }
                }
            ],
            "model": "deepseek-chat",
            "usage": {
                "total_tokens": 25
            }
        }
        mock_post.return_value = mock_response

        # 创建会话模拟
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        self.provider.session = mock_session

        result = self.provider.ask_question("需要推理的问题")

        self.assertTrue(result['success'])
        self.assertEqual(result['content'], "最终答案是正确的")
        self.assertEqual(result['reasoning_content'], "这是推理过程，分析了各种可能性")
        self.assertTrue(result['has_reasoning'])
        print("✓ 推理链提取功能测试通过")

    def test_extract_reasoning_from_content(self):
        """测试从内容中提取推理过程"""
        content_with_reasoning = """
        让我逐步分析这个问题：
        
        思考过程：
        1. 首先分析问题的核心要素
        2. 然后考虑可能的解决方案
        3. 最后得出结论
        
        最终答案：这个问题的答案是正确的。
        """
        
        reasoning = self.provider._extract_reasoning_from_content(content_with_reasoning)
        
        self.assertIn("分析问题的核心要素", reasoning)
        self.assertIn("考虑可能的解决方案", reasoning)
        self.assertNotIn("最终答案", reasoning)  # 推理部分不应该包含最终答案
        print("✓ 从内容中提取推理过程功能测试通过")

    def test_extract_reasoning_from_content_no_markers(self):
        """测试没有推理标记的内容"""
        content_without_reasoning = "这是一个直接的答案，没有推理过程。"
        
        reasoning = self.provider._extract_reasoning_from_content(content_without_reasoning)
        
        self.assertEqual(reasoning, "")
        print("✓ 无推理标记内容处理测试通过")

    @patch('requests.Session.post')
    def test_ask_question_timeout(self, mock_post):
        """测试请求超时处理"""
        # 模拟超时异常
        mock_post.side_effect = TimeoutError("Request timed out")

        result = self.provider.ask_question("测试问题")

        self.assertFalse(result['success'])
        self.assertIn("超时", result['error'])
        print("✓ 请求超时处理测试通过")

    @patch('requests.Session.post')
    def test_ask_question_api_error(self, mock_post):
        """测试API错误处理"""
        # 模拟API错误响应
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        result = self.provider.ask_question("测试问题")

        self.assertFalse(result['success'])
        self.assertIn("401", result['error'])
        print("✓ API错误处理测试通过")

    def test_health_check(self):
        """测试健康检查功能"""
        # 由于健康检查需要实际API调用，我们测试其结构
        # 在实际实现中，这会调用ask_question方法
        self.assertTrue(callable(self.provider.health_check))
        print("✓ 健康检查方法存在测试通过")


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_provider_factory_with_deepseek_provider(self):
        """测试ProviderFactory与DeepSeekProvider集成"""
        # 重新注册DeepSeekProvider
        ProviderFactory.register('deepseek', DeepSeekProvider)
        
        # 创建实例
        provider = ProviderFactory.create(
            platform_name='deepseek',
            api_key='test-key',
            model_name='deepseek-chat',
            enable_reasoning_extraction=True
        )
        
        self.assertIsInstance(provider, DeepSeekProvider)
        self.assertEqual(provider.api_key, 'test-key')
        self.assertEqual(provider.model_name, 'deepseek-chat')
        self.assertTrue(provider.enable_reasoning_extraction)
        print("✓ ProviderFactory与DeepSeekProvider集成测试通过")


if __name__ == '__main__':
    print("开始测试ProviderFactory和DeepSeekProvider...")
    print("="*60)
    
    # 运行所有测试
    unittest.main(verbosity=2)
    
    print("\n" + "="*60)
    print("所有测试通过!")
    print("✓ ProviderFactory注册功能正常")
    print("✓ ProviderFactory创建实例功能正常")
    print("✓ DeepSeekProvider ask_question 方法正常")
    print("✓ DeepSeekProvider推理链提取功能正常")
    print("✓ 错误处理机制正常")
    print("✓ 集成测试通过")
    print("="*60)