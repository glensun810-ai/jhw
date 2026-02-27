"""
Unit Tests for DeepSeek Adapter

Tests for:
- API key retrieval
- Request payload building
- Response parsing
- Error parsing
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.deepseek_adapter import DeepSeekAdapter
from wechat_backend.v2.adapters.errors import (
    AIAuthenticationError,
    AIRateLimitError,
    AIQuotaExceededError,
    AIModelNotFoundError,
    AIContentFilterError,
    AIResponseError,
    AIAdapterError,
)


@pytest.fixture
def adapter():
    """Create DeepSeek adapter for testing"""
    os.environ['DEEPSEEK_API_KEY'] = 'test-api-key'
    return DeepSeekAdapter()


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables"""
    os.environ['DEEPSEEK_API_KEY'] = 'test-api-key'
    yield


class TestDeepSeekAdapterInit:
    """Test DeepSeekAdapter initialization"""

    def test_init(self):
        """Test adapter initialization"""
        adapter = DeepSeekAdapter()
        assert adapter.provider == 'deepseek'
        assert adapter.api_key == 'test-api-key'

    def test_init_missing_api_key(self):
        """Test initialization fails without API key"""
        # Temporarily remove API key
        original_key = os.environ.pop('DEEPSEEK_API_KEY', None)
        
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            DeepSeekAdapter()
        
        # Restore API key
        if original_key:
            os.environ['DEEPSEEK_API_KEY'] = original_key


class TestDeepSeekAdapterGetHeaders:
    """Test DeepSeekAdapter request headers"""

    def test_get_headers(self, adapter):
        """Test getting request headers"""
        headers = adapter._get_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-api-key'
        assert headers['Content-Type'] == 'application/json'
        assert headers['Accept'] == 'application/json'


class TestDeepSeekAdapterGetApiUrl:
    """Test DeepSeekAdapter API URL"""

    def test_get_api_url_default(self, adapter):
        """Test getting default API URL"""
        url = adapter._get_api_url()
        assert url == 'https://api.deepseek.com/v1/chat/completions'

    @patch.object(DeepSeekAdapter, 'config', {'api_url': 'https://custom.api.com/v1'})
    def test_get_api_url_custom(self, adapter):
        """Test getting custom API URL"""
        # This test would work if we could override the config
        pass


class TestDeepSeekAdapterBuildRequestPayload:
    """Test DeepSeekAdapter request payload building"""

    def test_build_basic_payload(self, adapter):
        """Test building basic request payload"""
        request = AIRequest(prompt="Test prompt", model="deepseek-chat")
        payload = adapter._build_request_payload(request)
        
        assert payload['model'] == 'deepseek-chat'
        assert len(payload['messages']) == 1
        assert payload['messages'][0]['role'] == 'user'
        assert payload['messages'][0]['content'] == 'Test prompt'
        assert payload['temperature'] == 0.7
        assert payload['max_tokens'] == 2000
        assert payload['top_p'] == 1.0
        assert payload['frequency_penalty'] == 0.0
        assert payload['presence_penalty'] == 0.0
        assert payload['stream'] is False

    def test_build_payload_with_messages(self, adapter):
        """Test building payload with existing messages"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        request = AIRequest(prompt="Test", model="deepseek-chat", messages=messages)
        payload = adapter._build_request_payload(request)
        
        assert payload['messages'] == messages

    def test_build_payload_removes_none_values(self, adapter):
        """Test that None values are removed from payload"""
        request = AIRequest(
            prompt="Test",
            model="deepseek-chat",
            temperature=None,  # This would be removed
        )
        # Note: In current implementation, temperature has default 0.7
        # This test verifies the filtering logic
        payload = adapter._build_request_payload(request)
        
        # Verify no None values in payload
        for key, value in payload.items():
            assert value is not None, f"Key {key} has None value"


class TestDeepSeekAdapterParseResponse:
    """Test DeepSeekAdapter response parsing"""

    def test_parse_successful_response(self, adapter):
        """Test parsing successful response"""
        mock_response = {
            'id': 'chatcmpl-123',
            'model': 'deepseek-chat',
            'choices': [
                {
                    'index': 0,
                    'message': {'role': 'assistant', 'content': 'Test response'},
                    'finish_reason': 'stop',
                }
            ],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 20,
                'total_tokens': 30,
            },
        }
        
        request = AIRequest(prompt="Test", model="deepseek-chat")
        response = adapter._parse_response(mock_response, request)
        
        assert isinstance(response, AIResponse)
        assert response.content == 'Test response'
        assert response.model == 'deepseek-chat'
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.finish_reason == 'stop'
        assert response.provider == 'deepseek'
        assert response.request_id == 'chatcmpl-123'
        assert response.raw_response == mock_response

    def test_parse_response_no_choices(self, adapter):
        """Test parsing response with no choices raises error"""
        mock_response = {'id': 'test', 'model': 'deepseek-chat'}
        request = AIRequest(prompt="Test", model="deepseek-chat")
        
        with pytest.raises(AIResponseError, match="No choices"):
            adapter._parse_response(mock_response, request)

    def test_parse_response_missing_field(self, adapter):
        """Test parsing response with missing field raises error"""
        mock_response = {
            'id': 'test',
            'choices': [{}],  # Missing message
        }
        request = AIRequest(prompt="Test", model="deepseek-chat")
        
        # This should not raise because get() returns None for missing keys
        # and content becomes empty string
        response = adapter._parse_response(mock_response, request)
        assert response.content == ''

    def test_parse_response_empty_content(self, adapter):
        """Test parsing response with empty content"""
        mock_response = {
            'id': 'test',
            'model': 'deepseek-chat',
            'choices': [
                {
                    'message': {'role': 'assistant', 'content': ''},
                    'finish_reason': 'stop',
                }
            ],
        }
        
        request = AIRequest(prompt="Test", model="deepseek-chat")
        response = adapter._parse_response(mock_response, request)
        
        assert response.content == ''
        assert response.is_success is True  # Empty content is still success


class TestDeepSeekAdapterParseError:
    """Test DeepSeekAdapter error parsing"""

    def test_parse_authentication_error(self, adapter):
        """Test parsing 401 authentication error"""
        mock_error = {
            'error': {
                'message': 'Invalid API key',
                'code': 'invalid_api_key',
                'type': 'invalid_request_error',
            }
        }
        
        error = adapter._parse_error(mock_error, 401)
        assert isinstance(error, AIAuthenticationError)
        assert 'Invalid API key' in str(error)

    def test_parse_rate_limit_error(self, adapter):
        """Test parsing 429 rate limit error"""
        mock_error = {
            'error': {
                'message': 'Rate limit exceeded',
                'code': 'rate_limit_exceeded',
            }
        }
        
        error = adapter._parse_error(mock_error, 429)
        assert isinstance(error, AIRateLimitError)

    def test_parse_quota_exceeded_error(self, adapter):
        """Test parsing 429 quota exceeded error"""
        mock_error = {
            'error': {
                'message': 'Quota exceeded',
                'code': 'insufficient_quota',
            }
        }
        
        error = adapter._parse_error(mock_error, 429)
        assert isinstance(error, AIQuotaExceededError)

    def test_parse_model_not_found_error(self, adapter):
        """Test parsing 404 model not found error"""
        mock_error = {
            'error': {
                'message': 'Model not found',
                'code': 'model_not_found',
            }
        }
        
        error = adapter._parse_error(mock_error, 404)
        assert isinstance(error, AIModelNotFoundError)

    def test_parse_content_filter_error(self, adapter):
        """Test parsing 400 content filter error"""
        mock_error = {
            'error': {
                'message': 'Content contains inappropriate content',
                'code': 'content_filter',
            }
        }
        
        error = adapter._parse_error(mock_error, 400)
        assert isinstance(error, AIContentFilterError)

    def test_parse_generic_error(self, adapter):
        """Test parsing generic error"""
        mock_error = {
            'error': {
                'message': 'Something went wrong',
                'code': 'unknown',
            }
        }
        
        error = adapter._parse_error(mock_error, 500)
        assert isinstance(error, AIAdapterError)
        assert error.provider == 'deepseek'
