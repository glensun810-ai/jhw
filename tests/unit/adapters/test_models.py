"""
Unit Tests for AI Request/Response Models

Tests for:
- AIRequest dataclass
- AIResponse dataclass
- AIStreamChunk dataclass
- AIProvider enum
"""

import pytest
from datetime import datetime

from wechat_backend.v2.adapters.models import (
    AIRequest,
    AIResponse,
    AIStreamChunk,
    AIProvider,
)


class TestAIRequest:
    """Test AIRequest dataclass"""

    def test_create_basic_request(self):
        """Test creating a basic request with required fields"""
        request = AIRequest(prompt="Test prompt", model="deepseek-chat")
        
        assert request.prompt == "Test prompt"
        assert request.model == "deepseek-chat"
        assert request.temperature == 0.7  # Default
        assert request.max_tokens == 2000  # Default
        assert request.top_p == 1.0  # Default
        assert request.frequency_penalty == 0.0  # Default
        assert request.presence_penalty == 0.0  # Default
        assert request.timeout == 60  # Default
        assert request.messages is None
        assert request.request_id is None

    def test_create_request_with_all_options(self):
        """Test creating a request with all optional parameters"""
        request = AIRequest(
            prompt="Test prompt",
            model="deepseek-chat",
            temperature=0.9,
            max_tokens=1000,
            top_p=0.8,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            request_id="test-123",
            timeout=120,
            messages=[{"role": "user", "content": "Hello"}],
        )
        
        assert request.temperature == 0.9
        assert request.max_tokens == 1000
        assert request.top_p == 0.8
        assert request.frequency_penalty == 0.5
        assert request.presence_penalty == 0.3
        assert request.request_id == "test-123"
        assert request.timeout == 120
        assert len(request.messages) == 1

    def test_to_dict(self):
        """Test converting request to dictionary"""
        request = AIRequest(
            prompt="Test prompt",
            model="deepseek-chat",
            request_id="test-123",
        )
        
        result = request.to_dict()
        
        assert result['model'] == 'deepseek-chat'
        assert result['temperature'] == 0.7
        assert result['max_tokens'] == 2000
        assert result['request_id'] == 'test-123'
        assert 'prompt_preview' in result

    def test_to_dict_long_prompt(self):
        """Test prompt preview truncation for long prompts"""
        long_prompt = "A" * 200
        request = AIRequest(prompt=long_prompt, model="deepseek-chat")
        
        result = request.to_dict()
        
        assert len(result['prompt_preview']) == 103  # 100 + "..."
        assert result['prompt_preview'].endswith('...')


class TestAIResponse:
    """Test AIResponse dataclass"""

    def test_create_basic_response(self):
        """Test creating a basic response"""
        response = AIResponse(
            content="Test content",
            model="deepseek-chat",
            latency_ms=1234,
        )
        
        assert response.content == "Test content"
        assert response.model == "deepseek-chat"
        assert response.latency_ms == 1234
        assert response.prompt_tokens is None
        assert response.completion_tokens is None
        assert response.total_tokens is None
        assert response.finish_reason is None
        assert response.error is None
        assert response.error_code is None
        assert response.provider is None
        assert response.request_id is None
        assert isinstance(response.timestamp, datetime)

    def test_create_full_response(self):
        """Test creating a response with all fields"""
        raw_response = {'id': 'test-id', 'choices': []}
        response = AIResponse(
            content="Test content",
            model="deepseek-chat",
            latency_ms=1234,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            finish_reason="stop",
            raw_response=raw_response,
            error=None,
            error_code=None,
            request_id="test-id",
            provider="deepseek",
        )
        
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.raw_response == raw_response
        assert response.request_id == "test-id"
        assert response.provider == "deepseek"

    def test_is_success(self):
        """Test is_success property"""
        # Success case
        response = AIResponse(content="Test", model="test", latency_ms=100)
        assert response.is_success is True
        
        # Error case
        response_with_error = AIResponse(
            content="Test",
            model="test",
            latency_ms=100,
            error="Some error",
        )
        assert response_with_error.is_success is False

    def test_text_length(self):
        """Test text_length property"""
        response = AIResponse(content="Hello World", model="test", latency_ms=100)
        assert response.text_length == 11
        
        # Empty content
        empty_response = AIResponse(content="", model="test", latency_ms=100)
        assert empty_response.text_length == 0
        
        # None content
        none_response = AIResponse(content=None, model="test", latency_ms=100)
        assert none_response.text_length == 0

    def test_to_dict(self):
        """Test converting response to dictionary"""
        response = AIResponse(
            content="Test content",
            model="deepseek-chat",
            latency_ms=1234,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            finish_reason="stop",
            provider="deepseek",
        )
        
        result = response.to_dict()
        
        assert result['model'] == 'deepseek-chat'
        assert result['latency_ms'] == 1234
        assert result['prompt_tokens'] == 10
        assert result['completion_tokens'] == 20
        assert result['total_tokens'] == 30
        assert result['finish_reason'] == 'stop'
        assert result['provider'] == 'deepseek'
        assert 'content_preview' in result

    def test_to_dict_long_content(self):
        """Test content preview truncation for long content"""
        long_content = "B" * 200
        response = AIResponse(content=long_content, model="test", latency_ms=100)
        
        result = response.to_dict()
        
        assert len(result['content_preview']) == 103  # 100 + "..."
        assert result['content_preview'].endswith('...')


class TestAIStreamChunk:
    """Test AIStreamChunk dataclass"""

    def test_create_basic_chunk(self):
        """Test creating a basic chunk"""
        chunk = AIStreamChunk(content="Test chunk")
        
        assert chunk.content == "Test chunk"
        assert chunk.is_finished is False
        assert chunk.finish_reason is None
        assert chunk.index == 0

    def test_create_finished_chunk(self):
        """Test creating a finished chunk"""
        chunk = AIStreamChunk(
            content="Final chunk",
            is_finished=True,
            finish_reason="stop",
            index=5,
        )
        
        assert chunk.is_finished is True
        assert chunk.finish_reason == "stop"
        assert chunk.index == 5


class TestAIProvider:
    """Test AIProvider enum"""

    def test_provider_values(self):
        """Test enum values"""
        assert AIProvider.DEEPSEEK.value == 'deepseek'
        assert AIProvider.DOUBAO.value == 'doubao'
        assert AIProvider.QWEN.value == 'qwen'

    def test_provider_comparison(self):
        """Test enum comparison"""
        assert AIProvider.DEEPSEEK == 'deepseek'
        assert AIProvider.DOUBAO == 'doubao'
        assert AIProvider.QWEN == 'qwen'
