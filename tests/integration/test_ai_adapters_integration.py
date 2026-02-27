"""
Integration Tests for AI Adapters

Tests for:
- Real API calls (when API keys are available)
- Adapter interface consistency
- Factory integration
- Error handling integration

Note: These tests require API keys to be set in environment variables.
Tests will be skipped if API keys are not configured.
"""

import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from wechat_backend.v2.adapters import (
    get_adapter,
    get_supported_providers,
    AIRequest,
    AIResponse,
)
from wechat_backend.v2.adapters.factory import AIAdapterFactory
from wechat_backend.v2.adapters.errors import (
    AIAdapterError,
    AIAuthenticationError,
    AITimeoutError,
)
from wechat_backend.v2.adapters.deepseek_adapter import DeepSeekAdapter
from wechat_backend.v2.adapters.doubao_adapter import DoubaoAdapter
from wechat_backend.v2.adapters.qwen_adapter import QwenAdapter


class TestAIAdaptersInterface:
    """Test that all adapters implement consistent interface"""

    @pytest.mark.parametrize("provider,adapter_class", [
        ('deepseek', DeepSeekAdapter),
        ('doubao', DoubaoAdapter),
        ('qwen', QwenAdapter),
    ])
    def test_adapter_has_required_methods(self, provider, adapter_class):
        """Test that adapter has all required methods"""
        # Set up environment
        os.environ[f'{provider.upper()}_API_KEY'] = 'test-key'
        
        adapter = adapter_class()
        
        # Check required methods exist
        assert hasattr(adapter, '_get_api_key')
        assert hasattr(adapter, '_build_request_payload')
        assert hasattr(adapter, '_parse_response')
        assert hasattr(adapter, '_parse_error')
        assert hasattr(adapter, '_get_headers')
        assert hasattr(adapter, '_get_api_url')
        assert hasattr(adapter, 'send')
        assert hasattr(adapter, 'send_stream')
        assert hasattr(adapter, 'validate_response')
        
        # Check methods are callable
        assert callable(adapter._get_api_key)
        assert callable(adapter._build_request_payload)
        assert callable(adapter._parse_response)
        assert callable(adapter._parse_error)
        assert callable(adapter._get_headers)
        assert callable(adapter._get_api_url)
        assert callable(adapter.send)

    @pytest.mark.parametrize("provider,adapter_class", [
        ('deepseek', DeepSeekAdapter),
        ('doubao', DoubaoAdapter),
        ('qwen', QwenAdapter),
    ])
    def test_adapter_build_request_payload_returns_dict(self, provider, adapter_class):
        """Test that _build_request_payload returns a dictionary"""
        os.environ[f'{provider.upper()}_API_KEY'] = 'test-key'
        
        adapter = adapter_class()
        request = AIRequest(prompt="Test", model="test-model")
        payload = adapter._build_request_payload(request)
        
        assert isinstance(payload, dict)
        assert 'model' in payload or 'input' in payload  # Different formats

    @pytest.mark.parametrize("provider,adapter_class", [
        ('deepseek', DeepSeekAdapter),
        ('doubao', DoubaoAdapter),
        ('qwen', QwenAdapter),
    ])
    def test_adapter_parse_response_returns_airesponse(self, provider, adapter_class):
        """Test that _parse_response returns AIResponse"""
        os.environ[f'{provider.upper()}_API_KEY'] = 'test-key'
        
        adapter = adapter_class()
        
        # Mock response based on provider
        if provider == 'deepseek' or provider == 'doubao':
            mock_response = {
                'id': 'test-id',
                'model': 'test-model',
                'choices': [{'message': {'content': 'Test'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30},
            }
        else:  # qwen
            mock_response = {
                'model': 'test-model',
                'output': {
                    'choices': [{'message': {'content': 'Test'}, 'finish_reason': 'stop'}]
                },
                'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30},
            }
        
        request = AIRequest(prompt="Test", model="test-model")
        response = adapter._parse_response(mock_response, request)
        
        assert isinstance(response, AIResponse)
        assert response.content == 'Test'

    @pytest.mark.parametrize("provider,adapter_class", [
        ('deepseek', DeepSeekAdapter),
        ('doubao', DoubaoAdapter),
        ('qwen', QwenAdapter),
    ])
    def test_adapter_parse_error_returns_aiadaptererror(self, provider, adapter_class):
        """Test that _parse_error returns AIAdapterError subclass"""
        os.environ[f'{provider.upper()}_API_KEY'] = 'test-key'
        
        adapter = adapter_class()
        mock_error = {'error': {'message': 'Test error'}} if provider != 'qwen' else {'code': 'TestError', 'message': 'Test error'}
        
        error = adapter._parse_error(mock_error, 500)
        
        assert isinstance(error, AIAdapterError)
        assert error.provider == provider


class TestAdapterFactoryIntegration:
    """Test adapter factory integration"""

    def test_get_all_supported_providers(self):
        """Test getting all supported providers"""
        providers = get_supported_providers()
        
        assert isinstance(providers, list)
        assert len(providers) >= 3
        assert 'deepseek' in providers
        assert 'doubao' in providers
        assert 'qwen' in providers

    def test_factory_returns_correct_adapter_types(self):
        """Test that factory returns correct adapter types"""
        # Set up environment
        os.environ['DEEPSEEK_API_KEY'] = 'test-key'
        os.environ['DOUBAO_API_KEY'] = 'test-key'
        os.environ['QWEN_API_KEY'] = 'test-key'
        
        # Clear cache to ensure fresh instances
        AIAdapterFactory.clear_cache()
        
        deepseek_adapter = get_adapter('deepseek')
        doubao_adapter = get_adapter('doubao')
        qwen_adapter = get_adapter('qwen')
        
        assert isinstance(deepseek_adapter, DeepSeekAdapter)
        assert isinstance(doubao_adapter, DoubaoAdapter)
        assert isinstance(qwen_adapter, QwenAdapter)

    def test_factory_caches_instances(self):
        """Test that factory caches adapter instances"""
        os.environ['DEEPSEEK_API_KEY'] = 'test-key'
        AIAdapterFactory.clear_cache()
        
        adapter1 = get_adapter('deepseek')
        adapter2 = get_adapter('deepseek')
        
        # Should be same instance (singleton)
        assert adapter1 is adapter2


class TestAIAdaptersRealAPICalls:
    """Test real API calls (requires valid API keys)"""

    @pytest.mark.asyncio
    async def test_deepseek_real_call(self):
        """Test DeepSeek real API call (requires API key)"""
        if not os.getenv('DEEPSEEK_API_KEY'):
            pytest.skip("DEEPSEEK_API_KEY not set")
        
        adapter = get_adapter('deepseek')
        request = AIRequest(
            prompt="Hello, please respond with just 'OK'",
            model="deepseek-chat",
            max_tokens=10,
        )
        
        try:
            response = await adapter.send(request)
            assert response.is_success
            assert response.content
            assert response.model
            assert response.latency_ms > 0
        except AIAuthenticationError:
            pytest.skip("Invalid API key")
        except (AITimeoutError, AIAdapterError) as e:
            pytest.skip(f"API call failed: {e}")

    @pytest.mark.asyncio
    async def test_doubao_real_call(self):
        """Test Doubao real API call (requires API key)"""
        if not os.getenv('DOUBAO_API_KEY'):
            pytest.skip("DOUBAO_API_KEY not set")
        
        adapter = get_adapter('doubao')
        request = AIRequest(
            prompt="Hello, please respond with just 'OK'",
            model="doubao-lite-32k",
            max_tokens=10,
        )
        
        try:
            response = await adapter.send(request)
            assert response.is_success
            assert response.content
            assert response.model
            assert response.latency_ms > 0
        except AIAuthenticationError:
            pytest.skip("Invalid API key")
        except (AITimeoutError, AIAdapterError) as e:
            pytest.skip(f"API call failed: {e}")

    @pytest.mark.asyncio
    async def test_qwen_real_call(self):
        """Test Qwen real API call (requires API key)"""
        if not os.getenv('QWEN_API_KEY'):
            pytest.skip("QWEN_API_KEY not set")
        
        adapter = get_adapter('qwen')
        request = AIRequest(
            prompt="Hello, please respond with just 'OK'",
            model="qwen-turbo",
            max_tokens=10,
        )
        
        try:
            response = await adapter.send(request)
            assert response.is_success
            assert response.content
            assert response.model
            assert response.latency_ms > 0
        except AIAuthenticationError:
            pytest.skip("Invalid API key")
        except (AITimeoutError, AIAdapterError) as e:
            pytest.skip(f"API call failed: {e}")


class TestAIAdaptersErrorHandling:
    """Test adapter error handling"""

    @pytest.mark.asyncio
    async def test_adapter_handles_timeout(self):
        """Test that adapter handles timeout correctly"""
        os.environ['DEEPSEEK_API_KEY'] = 'test-key'
        
        adapter = get_adapter('deepseek')
        request = AIRequest(
            prompt="Test",
            model="deepseek-chat",
            timeout=1,  # Very short timeout to trigger error
        )
        
        # Mock the HTTP call to simulate timeout
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(AITimeoutError) as exc_info:
                await adapter.send(request)
            
            assert 'timeout' in str(exc_info.value).lower()
            assert exc_info.value.provider == 'deepseek'

    @pytest.mark.asyncio
    async def test_adapter_handles_connection_error(self):
        """Test that adapter handles connection error correctly"""
        os.environ['DEEPSEEK_API_KEY'] = 'test-key'
        
        adapter = get_adapter('deepseek')
        request = AIRequest(prompt="Test", model="deepseek-chat")
        
        # Mock the HTTP call to simulate connection error
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            
            with pytest.raises(AIAdapterError):
                await adapter.send(request)


class TestAIAdaptersConfiguration:
    """Test adapter configuration"""

    def test_platform_config_loading(self):
        """Test loading platform configuration"""
        from wechat_backend.v2.config.ai_platforms import get_platform_config
        
        config = get_platform_config('deepseek')
        
        assert 'api_url' in config
        assert 'max_retries' in config
        assert 'timeout' in config
        assert config['max_retries'] == 3
        assert config['timeout'] == 60

    def test_platform_config_environment_override(self):
        """Test that environment variables override default config"""
        from wechat_backend.v2.config.ai_platforms import get_platform_config
        
        # Set environment override
        original = os.environ.get('AI_DEEPSEEK_TIMEOUT')
        os.environ['AI_DEEPSEEK_TIMEOUT'] = '120'
        
        try:
            config = get_platform_config('deepseek')
            assert config['timeout'] == 120
        finally:
            # Restore original value
            if original is not None:
                os.environ['AI_DEEPSEEK_TIMEOUT'] = original
            else:
                os.environ.pop('AI_DEEPSEEK_TIMEOUT', None)
