"""
Unit Tests for Doubao Adapter

Tests for:
- API key retrieval
- Request payload building
- Response parsing
- Error parsing
"""

import pytest
import os

from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.doubao_adapter import DoubaoAdapter
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
    """Create Doubao adapter for testing"""
    os.environ['DOUBAO_API_KEY'] = 'test-api-key'
    return DoubaoAdapter()


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables"""
    os.environ['DOUBAO_API_KEY'] = 'test-api-key'
    yield


class TestDoubaoAdapterInit:
    """Test DoubaoAdapter initialization"""

    def test_init(self):
        """Test adapter initialization"""
        adapter = DoubaoAdapter()
        assert adapter.provider == 'doubao'
        assert adapter.api_key == 'test-api-key'

    def test_init_missing_api_key(self):
        """Test initialization fails without API key"""
        original_key = os.environ.pop('DOUBAO_API_KEY', None)
        
        with pytest.raises(ValueError, match="DOUBAO_API_KEY"):
            DoubaoAdapter()
        
        if original_key:
            os.environ['DOUBAO_API_KEY'] = original_key


class TestDoubaoAdapterGetHeaders:
    """Test DoubaoAdapter request headers"""

    def test_get_headers(self, adapter):
        """Test getting request headers"""
        headers = adapter._get_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-api-key'
        assert headers['Content-Type'] == 'application/json'


class TestDoubaoAdapterGetApiUrl:
    """Test DoubaoAdapter API URL"""

    def test_get_api_url_default(self, adapter):
        """Test getting default API URL"""
        url = adapter._get_api_url()
        assert url == 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'


class TestDoubaoAdapterBuildRequestPayload:
    """Test DoubaoAdapter request payload building"""

    def test_build_basic_payload(self, adapter):
        """Test building basic request payload"""
        request = AIRequest(prompt="Test prompt", model="doubao-lite-32k")
        payload = adapter._build_request_payload(request)
        
        assert payload['model'] == 'doubao-lite-32k'
        assert len(payload['messages']) == 1
        assert payload['messages'][0]['role'] == 'user'
        assert payload['messages'][0]['content'] == 'Test prompt'
        assert payload['temperature'] == 0.7
        assert payload['max_tokens'] == 2000

    def test_build_payload_with_messages(self, adapter):
        """Test building payload with existing messages"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        request = AIRequest(prompt="Test", model="doubao-lite-32k", messages=messages)
        payload = adapter._build_request_payload(request)
        
        assert payload['messages'] == messages


class TestDoubaoAdapterParseResponse:
    """Test DoubaoAdapter response parsing"""

    def test_parse_successful_response(self, adapter):
        """Test parsing successful response"""
        mock_response = {
            'id': 'chatcmpl-456',
            'model': 'doubao-lite-32k',
            'choices': [
                {
                    'index': 0,
                    'message': {'role': 'assistant', 'content': 'Test response'},
                    'finish_reason': 'stop',
                }
            ],
            'usage': {
                'prompt_tokens': 15,
                'completion_tokens': 25,
                'total_tokens': 40,
            },
        }
        
        request = AIRequest(prompt="Test", model="doubao-lite-32k")
        response = adapter._parse_response(mock_response, request)
        
        assert isinstance(response, AIResponse)
        assert response.content == 'Test response'
        assert response.model == 'doubao-lite-32k'
        assert response.prompt_tokens == 15
        assert response.completion_tokens == 25
        assert response.total_tokens == 40
        assert response.finish_reason == 'stop'
        assert response.provider == 'doubao'
        assert response.request_id == 'chatcmpl-456'

    def test_parse_response_no_choices(self, adapter):
        """Test parsing response with no choices raises error"""
        mock_response = {'id': 'test', 'model': 'doubao-lite-32k'}
        request = AIRequest(prompt="Test", model="doubao-lite-32k")
        
        with pytest.raises(AIResponseError, match="No choices"):
            adapter._parse_response(mock_response, request)


class TestDoubaoAdapterParseError:
    """Test DoubaoAdapter error parsing"""

    def test_parse_authentication_error(self, adapter):
        """Test parsing 401 authentication error"""
        mock_error = {'error': {'message': 'Invalid API key'}}
        
        error = adapter._parse_error(mock_error, 401)
        assert isinstance(error, AIAuthenticationError)

    def test_parse_rate_limit_error(self, adapter):
        """Test parsing 429 rate limit error"""
        mock_error = {'error': {'message': 'Rate limit exceeded'}}
        
        error = adapter._parse_error(mock_error, 429)
        assert isinstance(error, AIRateLimitError)

    def test_parse_model_not_found_error(self, adapter):
        """Test parsing 404 model not found error"""
        mock_error = {'error': {'message': 'Model not found'}}
        
        error = adapter._parse_error(mock_error, 404)
        assert isinstance(error, AIModelNotFoundError)

    def test_parse_content_filter_error(self, adapter):
        """Test parsing 400 content filter error (English)"""
        mock_error = {'error': {'message': 'Content contains inappropriate content'}}
        
        error = adapter._parse_error(mock_error, 400)
        assert isinstance(error, AIContentFilterError)

    def test_parse_content_filter_error_chinese(self, adapter):
        """Test parsing 400 content filter error (Chinese)"""
        mock_error = {'error': {'message': '内容包含敏感信息'}}
        
        error = adapter._parse_error(mock_error, 400)
        assert isinstance(error, AIContentFilterError)

    def test_parse_generic_error(self, adapter):
        """Test parsing generic error"""
        mock_error = {'error': {'message': 'Unknown error'}}
        
        error = adapter._parse_error(mock_error, 500)
        assert isinstance(error, AIAdapterError)
        assert error.provider == 'doubao'
