#!/usr/bin/env python3
"""
Unit tests for AIJudgeClient with dynamic parameters
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_judge_module import AIJudgeClient, JudgeResult, ConfidenceLevel


class TestAIJudgeClientDynamicParameters(unittest.TestCase):
    """Unit tests for AIJudgeClient with dynamic parameters"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock the lazy imports to avoid actual API calls
        self.patcher = patch.dict('ai_judge_module.__dict__', {
            'AIAdapterFactory': MagicMock(),
            'api_logger': MagicMock()
        })
        self.mock_dict = self.patcher.start()

        # Mock the config manager - import from config_manager module
        with patch('ai_judge_module.PlatformConfigManager') as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.get_platform_config.return_value = None
            mock_config.return_value = mock_config_instance

    def tearDown(self):
        """Clean up after each test method."""
        self.patcher.stop()

    def test_init_with_valid_parameters(self):
        """Test initialization with valid parameters"""
        client = AIJudgeClient(
            judge_platform="qwen",
            judge_model="qwen-max",
            api_key="test-key-123"
        )
        
        self.assertEqual(client.judge_platform, "qwen")
        self.assertEqual(client.judge_model, "qwen-max")
        self.assertEqual(client.api_key, "test-key-123")
        # Should have tried to create an adapter with the provided parameters
        if client.ai_client is not None:  # If initialization didn't fail
            pass  # The adapter creation is mocked, so we just check the attributes are set

    def test_init_with_none_parameters(self):
        """Test initialization with None parameters (should use defaults)"""
        # Temporarily set environment variables to known values for testing
        original_env = os.environ.copy()
        os.environ['JUDGE_LLM_PLATFORM'] = 'test-platform'
        os.environ['JUDGE_LLM_MODEL'] = 'test-model'
        os.environ['JUDGE_LLM_API_KEY'] = 'test-api-key'
        
        try:
            client = AIJudgeClient(
                judge_platform=None,
                judge_model=None,
                api_key=None
            )
            
            # Should use environment variables when parameters are None
            self.assertEqual(client.judge_platform, "test-platform")
            self.assertEqual(client.judge_model, "test-model")
            self.assertEqual(client.api_key, "test-api-key")
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_init_with_partial_parameters(self):
        """Test initialization with partial parameters"""
        # Set up environment variables
        original_env = os.environ.copy()
        os.environ['JUDGE_LLM_PLATFORM'] = 'env-platform'
        os.environ['JUDGE_LLM_MODEL'] = 'env-model'
        os.environ['JUDGE_LLM_API_KEY'] = 'env-api-key'
        
        try:
            # Only provide judge_platform, others should come from env or defaults
            client = AIJudgeClient(
                judge_platform="provided-platform",  # This should override env
                judge_model=None,  # Should use env value
                api_key=None       # Should use env value
            )
            
            self.assertEqual(client.judge_platform, "provided-platform")
            self.assertEqual(client.judge_model, "env-model")  # From env
            self.assertEqual(client.api_key, "env-api-key")    # From env
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_init_without_any_parameters(self):
        """Test initialization without any parameters (should use defaults)"""
        # Set up environment variables
        original_env = os.environ.copy()
        os.environ['JUDGE_LLM_PLATFORM'] = 'default-platform'
        os.environ['JUDGE_LLM_MODEL'] = 'default-model'
        os.environ['JUDGE_LLM_API_KEY'] = 'default-api-key'
        
        try:
            client = AIJudgeClient()  # No parameters provided
            
            self.assertEqual(client.judge_platform, "default-platform")
            self.assertEqual(client.judge_model, "default-model")
            self.assertEqual(client.api_key, "default-api-key")
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_init_with_empty_string_parameters(self):
        """Test initialization with empty string parameters"""
        client = AIJudgeClient(
            judge_platform="",
            judge_model="",
            api_key=""
        )
        
        # Empty strings should be used as-is
        self.assertEqual(client.judge_platform, "")
        self.assertEqual(client.judge_model, "")
        self.assertEqual(client.api_key, "")

    def test_backward_compatibility(self):
        """Test that the old initialization still works (backward compatibility)"""
        # This should work the same way as before our changes
        try:
            client = AIJudgeClient()
            # Should not raise an exception
            self.assertIsNotNone(client)
        except Exception as e:
            self.fail(f"Backward compatibility broken: {e}")

    @patch('ai_judge_module.AIAdapterFactory')
    def test_adapter_creation_with_dynamic_params(self, mock_factory):
        """Test that the adapter is created with the correct dynamic parameters"""
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        client = AIJudgeClient(
            judge_platform="test-platform",
            judge_model="test-model",
            api_key="test-key"
        )
        
        # Verify that the factory was called with the correct parameters
        mock_factory.create.assert_called_once_with("test-platform", "test-key", "test-model")

    def test_evaluate_response_skipped_when_no_client(self):
        """Test that evaluate_response returns None when no client is available"""
        # Create a client without a valid ai_client (simulate failure)
        client = AIJudgeClient()
        client.ai_client = None  # Simulate initialization failure
        
        result = client.evaluate_response("test-brand", "test-question", "test-answer")
        
        # Should return None when ai_client is None
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()