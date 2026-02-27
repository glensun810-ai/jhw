"""
Base AI Adapter Tests

Tests for the abstract base adapter class functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.errors import AIAdapterError


class ConcreteAdapter(BaseAIAdapter):
    """Concrete implementation for testing base class"""
    
    def _get_api_key(self) -> str:
        return "test-key"
    
    def _build_request_payload(self, request: AIRequest) -> dict:
        return {"prompt": request.prompt}
    
    def _parse_response(self, response_data: dict, request: AIRequest) -> AIResponse:
        return AIResponse(
            content="test response",
            model=request.model,
            latency_ms=100
        )
    
    def _parse_error(self, response_data: dict, status_code: int) -> AIAdapterError:
        return AIAdapterError("test error", provider=self.provider)
    
    def _get_headers(self) -> dict:
        return {"Authorization": "Bearer test-key"}
    
    def _get_api_url(self) -> str:
        return "https://api.test.com/v1"
    
    def parse_geo_data(self, response: AIResponse) -> dict:
        return {"brand": "test", "sentiment": "neutral"}


class TestBaseAIAdapter:
    """Test suite for BaseAIAdapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create a concrete adapter instance for testing"""
        return ConcreteAdapter(provider="test")
    
    def test_adapter_initialization(self, adapter):
        """Test adapter initializes correctly"""
        assert adapter.provider == "test"
        assert adapter.config is not None
        assert adapter.retry_policy is not None
        assert adapter.logger is not None
    
    def test_validate_response_success(self, adapter):
        """Test validate_response with valid response"""
        response = AIResponse(
            content="Valid response content",
            model="test-model",
            latency_ms=100
        )
        assert adapter.validate_response(response) is True
    
    def test_validate_response_empty_content(self, adapter):
        """Test validate_response with empty content"""
        response = AIResponse(
            content="",
            model="test-model",
            latency_ms=100
        )
        assert adapter.validate_response(response) is False
    
    def test_validate_response_none_content(self, adapter):
        """Test validate_response with None content"""
        response = AIResponse(
            content=None,
            model="test-model",
            latency_ms=100
        )
        assert adapter.validate_response(response) is False
    
    def test_validate_response_with_error(self, adapter):
        """Test validate_response with error field set"""
        response = AIResponse(
            content="Some content",
            model="test-model",
            latency_ms=100,
            error="Some error occurred"
        )
        # Should still be True if content exists (error is separate concern)
        assert adapter.validate_response(response) is True
    
    def test_ai_request_to_dict(self):
        """Test AIRequest serialization"""
        request = AIRequest(
            prompt="Test prompt " * 20,  # Long prompt
            model="test-model",
            temperature=0.8,
            max_tokens=1000
        )
        result = request.to_dict()
        
        assert result['model'] == "test-model"
        assert result['temperature'] == 0.8
        assert result['max_tokens'] == 1000
        assert 'prompt_preview' in result
        assert len(result['prompt_preview']) <= 103  # 100 + "..."
    
    def test_ai_response_to_dict(self):
        """Test AIResponse serialization"""
        response = AIResponse(
            content="Response content " * 20,
            model="test-model",
            latency_ms=1500,
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            provider="test-provider"
        )
        result = response.to_dict()
        
        assert result['model'] == "test-model"
        assert result['latency_ms'] == 1500
        assert result['prompt_tokens'] == 100
        assert result['completion_tokens'] == 200
        assert result['total_tokens'] == 300
        assert result['provider'] == "test-provider"
        assert 'content_preview' in result
    
    def test_ai_response_is_success(self):
        """Test AIResponse is_success property"""
        # Success case
        response = AIResponse(
            content="Success",
            model="test-model",
            latency_ms=100
        )
        assert response.is_success is True
        
        # Error case
        response.error = "Test error"
        assert response.is_success is False
    
    def test_ai_response_text_length(self):
        """Test AIResponse text_length property"""
        response = AIResponse(
            content="Hello World",
            model="test-model",
            latency_ms=100
        )
        assert response.text_length == 11
        
        # Empty content
        response.content = ""
        assert response.text_length == 0
        
        # None content
        response.content = None
        assert response.text_length == 0
    
    @pytest.mark.asyncio
    async def test_send_stream_not_implemented(self, adapter):
        """Test that streaming raises NotImplementedError by default"""
        request = AIRequest(prompt="test", model="test-model")
        
        with pytest.raises(NotImplementedError):
            async for chunk in adapter.send_stream(request):
                pass
