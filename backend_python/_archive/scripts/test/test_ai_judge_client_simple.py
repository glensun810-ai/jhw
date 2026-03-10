#!/usr/bin/env python3
"""
Unit tests for AIJudgeClient with dynamic parameters - Simplified version
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

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_init_with_valid_parameters(self, mock_factory, mock_getenv):
        """Test initialization with valid parameters"""
        # Mock the environment variables to return defaults
        mock_getenv.side_effect = lambda x, default: default
        
        # Mock the adapter creation
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        client = AIJudgeClient(
            judge_platform="qwen",
            judge_model="qwen-max",
            api_key="test-key-123"
        )
        
        self.assertEqual(client.judge_platform, "qwen")
        self.assertEqual(client.judge_model, "qwen-max")
        self.assertEqual(client.api_key, "test-key-123")

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_init_with_none_parameters(self, mock_factory, mock_getenv):
        """Test initialization with None parameters (should use defaults)"""
        # Set up environment variables to return specific values
        def getenv_side_effect(key, default):
            if key == 'JUDGE_LLM_PLATFORM':
                return 'env-platform'
            elif key == 'JUDGE_LLM_MODEL':
                return 'env-model'
            elif key == 'JUDGE_LLM_API_KEY':
                return 'env-api-key'
            return default
        
        mock_getenv.side_effect = getenv_side_effect
        
        # Mock the adapter creation
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        client = AIJudgeClient(
            judge_platform=None,
            judge_model=None,
            api_key=None
        )
        
        # Should use environment variables when parameters are None
        self.assertEqual(client.judge_platform, "env-platform")
        self.assertEqual(client.judge_model, "env-model")
        self.assertEqual(client.api_key, "env-api-key")

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_init_with_partial_parameters(self, mock_factory, mock_getenv):
        """Test initialization with partial parameters"""
        # Set up environment variables
        def getenv_side_effect(key, default):
            if key == 'JUDGE_LLM_PLATFORM':
                return 'env-platform'
            elif key == 'JUDGE_LLM_MODEL':
                return 'env-model'
            elif key == 'JUDGE_LLM_API_KEY':
                return 'env-api-key'
            return default
        
        mock_getenv.side_effect = getenv_side_effect
        
        # Mock the adapter creation
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        # Only provide judge_platform, others should come from env
        client = AIJudgeClient(
            judge_platform="provided-platform",  # This should override env
            judge_model=None,  # Should use env value
            api_key=None       # Should use env value
        )
        
        self.assertEqual(client.judge_platform, "provided-platform")
        self.assertEqual(client.judge_model, "env-model")  # From env
        self.assertEqual(client.api_key, "env-api-key")    # From env

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_init_without_any_parameters(self, mock_factory, mock_getenv):
        """Test initialization without any parameters (should use defaults)"""
        # Set up environment variables
        def getenv_side_effect(key, default):
            if key == 'JUDGE_LLM_PLATFORM':
                return 'default-platform'
            elif key == 'JUDGE_LLM_MODEL':
                return 'default-model'
            elif key == 'JUDGE_LLM_API_KEY':
                return 'default-api-key'
            return default
        
        mock_getenv.side_effect = getenv_side_effect
        
        # Mock the adapter creation
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        client = AIJudgeClient()  # No parameters provided
        
        self.assertEqual(client.judge_platform, "default-platform")
        self.assertEqual(client.judge_model, "default-model")
        self.assertEqual(client.api_key, "default-api-key")

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_init_with_empty_string_parameters(self, mock_factory, mock_getenv):
        """Test initialization with empty string parameters"""
        # Mock the environment variables
        mock_getenv.side_effect = lambda x, default: default
        
        # Mock the adapter creation
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        client = AIJudgeClient(
            judge_platform="",
            judge_model="",
            api_key=""
        )
        
        # Empty strings should be used as-is
        self.assertEqual(client.judge_platform, "")
        self.assertEqual(client.judge_model, "")
        self.assertEqual(client.api_key, "")

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_backward_compatibility(self, mock_factory, mock_getenv):
        """Test that the old initialization still works (backward compatibility)"""
        # Mock the environment variables
        mock_getenv.side_effect = lambda x, default: default
        
        # Mock the adapter creation
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        # This should work the same way as before our changes
        try:
            client = AIJudgeClient()
            # Should not raise an exception
            self.assertIsNotNone(client)
        except Exception as e:
            self.fail(f"Backward compatibility broken: {e}")

    @patch('ai_judge_module.os.getenv')
    @patch('ai_judge_module.AIAdapterFactory')
    def test_adapter_creation_with_dynamic_params(self, mock_factory, mock_getenv):
        """Test that the adapter is created with the correct dynamic parameters"""
        # Mock the environment variables
        mock_getenv.side_effect = lambda x, default: default
        
        # Mock the adapter
        mock_adapter = MagicMock()
        mock_factory.create.return_value = mock_adapter
        
        client = AIJudgeClient(
            judge_platform="test-platform",
            judge_model="test-model",
            api_key="test-key"
        )
        
        # Verify that the factory was called with the correct parameters
        mock_factory.create.assert_called_once_with("test-platform", "test-key", "test-model")

    @patch('ai_judge_module.os.getenv')
    def test_evaluate_response_method_exists(self, mock_getenv):
        """Test that evaluate_response method exists and can be called"""
        # Mock the environment variables
        mock_getenv.side_effect = lambda x, default: default
        
        # Create a client without adapter to test method existence
        client = AIJudgeClient()
        client.ai_client = None  # Simulate failed initialization
        
        # Method should exist and handle None client gracefully
        result = client.evaluate_response("test-brand", "test-question", "test-answer")
        
        # Should return None when ai_client is None
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()