#!/usr/bin/env python3
"""
测试豆包(Doubao) API集成
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
from wechat_backend.ai_adapters.base_adapter import AIResponse, AIPlatformType


class TestDoubaoIntegration(unittest.TestCase):
    """豆包API集成测试"""

    def setUp(self):
        """测试前准备"""
        self.api_key = os.getenv('DOUBAO_API_KEY', 'fake-api-key-for-testing')
        self.model_name = 'ep-20240520111905-bavcb'
        self.adapter = DoubaoAdapter(self.api_key, self.model_name)

    def test_adapter_initialization(self):
        """测试适配器初始化"""
        self.assertEqual(self.adapter.platform_type, AIPlatformType.DOUBAO)
        self.assertEqual(self.adapter.model_name, self.model_name)
        self.assertEqual(self.adapter.api_key, self.api_key)

    @patch('wechat_backend.network.request_wrapper.UnifiedRequestWrapper._make_request')
    def test_send_prompt_success(self, mock_request):
        """测试成功发送提示词"""
        # 模拟成功的API响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "这是一个测试回复"
                    }
                }
            ],
            "usage": {
                "total_tokens": 10
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # 发送提示词
        response = self.adapter.send_prompt("测试提示词")

        # 验证响应
        self.assertTrue(response.success)
        self.assertEqual(response.content, "这是一个测试回复")
        self.assertEqual(response.tokens_used, 10)
        self.assertEqual(response.model, self.model_name)
        self.assertEqual(response.platform, "doubao")

    @patch('wechat_backend.network.request_wrapper.UnifiedRequestWrapper._make_request')
    def test_send_prompt_failure(self, mock_request):
        """测试发送提示词失败"""
        from wechat_backend.ai_adapters.base_adapter import AIErrorType

        # 模拟失败的API响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid API key"
            }
        }
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_request.return_value = mock_response

        # 发送提示词
        response = self.adapter.send_prompt("测试提示词")

        # 验证响应
        self.assertFalse(response.success)
        self.assertIsNotNone(response.error_message)
        self.assertEqual(response.error_type, AIErrorType.UNKNOWN_ERROR)

    @patch('wechat_backend.network.request_wrapper.UnifiedRequestWrapper._make_request')
    def test_send_prompt_no_choices(self, mock_request):
        """测试API返回无选择项的情况"""
        # 模拟API返回无选择项
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": []
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # 发送提示词
        response = self.adapter.send_prompt("测试提示词")

        # 验证响应
        self.assertFalse(response.success)
        self.assertIsNotNone(response.error_message)

    def test_error_mapping(self):
        """测试错误消息映射"""
        from wechat_backend.ai_adapters.base_adapter import AIErrorType

        # 测试各种错误情况
        error_mappings = [
            ("Invalid API key", AIErrorType.INVALID_API_KEY.value),
            ("Authentication failed", AIErrorType.INVALID_API_KEY.value),
            ("Insufficient quota", AIErrorType.INSUFFICIENT_QUOTA.value),
            ("Credit exceeded", AIErrorType.INSUFFICIENT_QUOTA.value),
            ("Content policy violation", AIErrorType.CONTENT_SAFETY.value),
            ("Safety check failed", AIErrorType.CONTENT_SAFETY.value),
            ("Unknown error", AIErrorType.UNKNOWN_ERROR.value)
        ]

        for error_msg, expected_type in error_mappings:
            mapped_type = self.adapter._map_error_message(error_msg)
            self.assertEqual(mapped_type.value, expected_type,
                           f"Failed for error message: {error_msg}")


def run_integration_test():
    """运行集成测试"""
    print("🔍 开始测试豆包(Doubao) API集成...")
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDoubaoIntegration)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果摘要
    print(f"\n📊 测试结果摘要:")
    print(f"   运行测试数: {result.testsRun}")
    print(f"   失败数: {len(result.failures)}")
    print(f"   错误数: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, trace in result.failures:
            print(f"   - {test}: {trace}")
    
    if result.errors:
        print("\n❌ 错误的测试:")
        for test, trace in result.errors:
            print(f"   - {test}: {trace}")
    
    success = result.wasSuccessful()
    print(f"\n{'✅ 所有测试通过!' if success else '❌ 部分测试失败!'}")
    
    return success


def test_real_api_connection():
    """测试与真实API的连接"""
    print("\n🌐 测试与真实豆包API的连接...")
    
    api_key = os.getenv('DOUBAO_API_KEY')
    if not api_key or api_key == 'fake-api-key-for-testing':
        print("⚠️ 未设置真实的DOUBAO_API_KEY，跳过真实API测试")
        return False
    
    try:
        adapter = DoubaoAdapter(api_key, 'ep-20240520111905-bavcb')
        response = adapter.send_prompt("你好，请简单介绍自己，用一句话回答。")
        
        if response.success:
            print(f"✅ 真实API连接成功!")
            print(f"   响应: {response.content[:100]}...")
            return True
        else:
            print(f"❌ 真实API连接失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ 真实API连接异常: {e}")
        return False


def main():
    """主函数"""
    print("🚀 豆包(Doubao) API集成测试")
    print("="*50)
    
    # 运行单元测试
    unit_test_success = run_integration_test()
    
    # 运行真实API测试（如果API密钥存在）
    real_api_success = test_real_api_connection()
    
    print("\n" + "="*50)
    print("📋 最终测试报告:")
    print(f"   单元测试: {'✅ 通过' if unit_test_success else '❌ 失败'}")
    print(f"   真实API测试: {'✅ 通过' if real_api_success else '❌ 失败或跳过'}")
    
    overall_success = unit_test_success  # 真实API测试可能因缺少密钥而跳过
    print(f"\n   总体结果: {'✅ 成功' if overall_success else '❌ 失败'}")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)