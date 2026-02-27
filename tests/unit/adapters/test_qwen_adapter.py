"""
Unit Tests for Qwen Adapter

Tests for:
- API key retrieval
- Request payload building
- Response parsing
- Error parsing
"""

import pytest
import os

from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.qwen_adapter import QwenAdapter
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
    """Create Qwen adapter for testing"""
    os.environ['QWEN_API_KEY'] = 'test-api-key'
    return QwenAdapter()


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables"""
    os.environ['QWEN_API_KEY'] = 'test-api-key'
    yield


class TestQwenAdapterInit:
    """Test QwenAdapter initialization"""

    def test_init(self):
        """Test adapter initialization"""
        adapter = QwenAdapter()
        assert adapter.provider == 'qwen'
        assert adapter.api_key == 'test-api-key'

    def test_init_missing_api_key(self):
        """Test initialization fails without API key"""
        original_key = os.environ.pop('QWEN_API_KEY', None)
        
        with pytest.raises(ValueError, match="QWEN_API_KEY"):
            QwenAdapter()
        
        if original_key:
            os.environ['QWEN_API_KEY'] = original_key


class TestQwenAdapterGetHeaders:
    """Test QwenAdapter request headers"""

    def test_get_headers(self, adapter):
        """Test getting request headers"""
        headers = adapter._get_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-api-key'
        assert headers['Content-Type'] == 'application/json'
        assert headers['X-DashScope-SSE'] == 'disable'


class TestQwenAdapterGetApiUrl:
    """Test QwenAdapter API URL"""

    def test_get_api_url_default(self, adapter):
        """Test getting default API URL"""
        url = adapter._get_api_url()
        assert url == 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'


class TestQwenAdapterBuildRequestPayload:
    """Test QwenAdapter request payload building"""

    def test_build_basic_payload(self, adapter):
        """Test building basic request payload"""
        request = AIRequest(prompt="Test prompt", model="qwen-turbo")
        payload = adapter._build_request_payload(request)
        
        assert payload['model'] == 'qwen-turbo'
        assert 'input' in payload
        assert 'messages' in payload['input']
        assert len(payload['input']['messages']) == 1
        assert payload['input']['messages'][0]['role'] == 'user'
        assert payload['input']['messages'][0]['content'] == 'Test prompt'
        assert 'parameters' in payload
        assert payload['parameters']['temperature'] == 0.7
        assert payload['parameters']['max_tokens'] == 2000
        assert payload['parameters']['result_format'] == 'message'

    def test_build_payload_with_messages(self, adapter):
        """Test building payload with existing messages"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        request = AIRequest(prompt="Test", model="qwen-turbo", messages=messages)
        payload = adapter._build_request_payload(request)
        
        assert payload['input']['messages'] == messages


class TestQwenAdapterParseResponse:
    """Test QwenAdapter response parsing"""

    def test_parse_successful_response(self, adapter):
        """Test parsing successful response"""
        mock_response = {
            'model': 'qwen-turbo',
            'request_id': 'req-789',
            'output': {
                'choices': [
                    {
                        'message': {'role': 'assistant', 'content': 'Test response'},
                        'finish_reason': 'stop',
                    }
                ]
            },
            'usage': {
                'input_tokens': 12,
                'output_tokens': 22,
                'total_tokens': 34,
            },
        }
        
        request = AIRequest(prompt="Test", model="qwen-turbo")
        response = adapter._parse_response(mock_response, request)
        
        assert isinstance(response, AIResponse)
        assert response.content == 'Test response'
        assert response.model == 'qwen-turbo'
        assert response.prompt_tokens == 12  # Qwen uses input_tokens
        assert response.completion_tokens == 22  # Qwen uses output_tokens
        assert response.total_tokens == 34
        assert response.finish_reason == 'stop'
        assert response.provider == 'qwen'
        assert response.request_id == 'req-789'

    def test_parse_response_no_choices(self, adapter):
        """Test parsing response with no choices raises error"""
        mock_response = {
            'model': 'qwen-turbo',
            'output': {},
        }
        request = AIRequest(prompt="Test", model="qwen-turbo")
        
        with pytest.raises(AIResponseError, match="No choices"):
            adapter._parse_response(mock_response, request)

    def test_parse_response_different_token_names(self, adapter):
        """Test that Qwen's token field names are correctly mapped"""
        mock_response = {
            'model': 'qwen-turbo',
            'output': {
                'choices': [
                    {
                        'message': {'content': 'Test'},
                        'finish_reason': 'stop',
                    }
                ]
            },
            'usage': {
                'input_tokens': 100,
                'output_tokens': 200,
                'total_tokens': 300,
            },
        }
        
        request = AIRequest(prompt="Test", model="qwen-turbo")
        response = adapter._parse_response(mock_response, request)
        
        # Verify Qwen's field names are mapped correctly
        assert response.prompt_tokens == 100
        assert response.completion_tokens == 200
        assert response.total_tokens == 300


class TestQwenAdapterParseError:
    """Test QwenAdapter error parsing"""

    def test_parse_authentication_error_by_status(self, adapter):
        """Test parsing 401 authentication error"""
        mock_error = {'code': 'InvalidApiKey', 'message': 'The API key is invalid'}
        
        error = adapter._parse_error(mock_error, 401)
        assert isinstance(error, AIAuthenticationError)

    def test_parse_authentication_error_by_code(self, adapter):
        """Test parsing authentication error by code"""
        mock_error = {'code': 'InvalidApiKey', 'message': 'Invalid key'}
        
        error = adapter._parse_error(mock_error, 400)
        assert isinstance(error, AIAuthenticationError)

    def test_parse_rate_limit_error_by_status(self, adapter):
        """Test parsing 429 rate limit error"""
        mock_error = {'code': 'Throttling', 'message': 'Rate limit exceeded'}
        
        error = adapter._parse_error(mock_error, 429)
        assert isinstance(error, AIRateLimitError)

    def test_parse_rate_limit_error_by_code(self, adapter):
        """Test parsing rate limit error by code"""
        mock_error = {'code': 'Throttling', 'message': 'Too many requests'}
        
        error = adapter._parse_error(mock_error, 400)
        assert isinstance(error, AIRateLimitError)

    def test_parse_model_not_found_error(self, adapter):
        """Test parsing model not found error"""
        mock_error = {'code': 'ModelNotFound', 'message': 'Model does not exist'}
        
        error = adapter._parse_error(mock_error, 404)
        assert isinstance(error, AIModelNotFoundError)

    def test_parse_content_filter_error(self, adapter):
        """Test parsing content filter error"""
        mock_error = {'code': 'ContentFilter', 'message': 'Content filtered'}
        
        error = adapter._parse_error(mock_error, 400)
        assert isinstance(error, AIContentFilterError)

    def test_parse_quota_exceeded_error(self, adapter):
        """Test parsing quota exceeded error"""
        mock_error = {'code': 'QuotaExceeded', 'message': 'Quota exceeded'}
        
        error = adapter._parse_error(mock_error, 429)
        assert isinstance(error, AIQuotaExceededError)

    def test_parse_generic_error(self, adapter):
        """Test parsing generic error"""
        mock_error = {'code': 'UnknownError', 'message': 'Something went wrong'}
        
        error = adapter._parse_error(mock_error, 500)
        assert isinstance(error, AIAdapterError)
        assert error.provider == 'qwen'
