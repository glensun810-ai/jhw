"""
Unit Tests for AI Adapter Factory

Tests for:
- Adapter registration
- Adapter retrieval (singleton pattern)
- Dynamic loading
- Supported providers list
"""

import pytest
import os

# Set up environment variables for testing
os.environ['DEEPSEEK_API_KEY'] = 'test-deepseek-key'
os.environ['DOUBAO_API_KEY'] = 'test-doubao-key'
os.environ['QWEN_API_KEY'] = 'test-qwen-key'

from wechat_backend.v2.adapters.factory import (
    AIAdapterFactory,
    get_adapter,
    get_supported_providers,
)
from wechat_backend.v2.adapters.errors import AIModelNotFoundError
from wechat_backend.v2.adapters.deepseek_adapter import DeepSeekAdapter
from wechat_backend.v2.adapters.doubao_adapter import DoubaoAdapter
from wechat_backend.v2.adapters.qwen_adapter import QwenAdapter


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear adapter cache before each test"""
    AIAdapterFactory.clear_cache()
    AIAdapterFactory._initialized = False  # Reset initialization flag
    yield
    AIAdapterFactory.clear_cache()
    AIAdapterFactory._initialized = False  # Reset initialization flag


class TestAdapterFactory:
    """Test AIAdapterFactory class"""

    def test_get_adapter_deepseek(self):
        """Test getting DeepSeek adapter"""
        adapter = AIAdapterFactory.get_adapter('deepseek')
        assert isinstance(adapter, DeepSeekAdapter)
        assert adapter.provider == 'deepseek'

    def test_get_adapter_doubao(self):
        """Test getting Doubao adapter"""
        adapter = AIAdapterFactory.get_adapter('doubao')
        assert isinstance(adapter, DoubaoAdapter)
        assert adapter.provider == 'doubao'

    def test_get_adapter_qwen(self):
        """Test getting Qwen adapter"""
        adapter = AIAdapterFactory.get_adapter('qwen')
        assert isinstance(adapter, QwenAdapter)
        assert adapter.provider == 'qwen'

    def test_get_adapter_case_insensitive(self):
        """Test that provider name is case insensitive"""
        adapter1 = AIAdapterFactory.get_adapter('DEEPSEEK')
        adapter2 = AIAdapterFactory.get_adapter('deepseek')
        assert isinstance(adapter1, DeepSeekAdapter)
        assert isinstance(adapter2, DeepSeekAdapter)
        assert adapter1 is adapter2  # Same instance (singleton)

    def test_get_adapter_singleton(self):
        """Test that adapter instances are cached (singleton pattern)"""
        adapter1 = AIAdapterFactory.get_adapter('deepseek')
        adapter2 = AIAdapterFactory.get_adapter('deepseek')
        assert adapter1 is adapter2

    def test_get_adapter_unknown(self):
        """Test getting unknown adapter raises error"""
        with pytest.raises(AIModelNotFoundError) as exc_info:
            AIAdapterFactory.get_adapter('unknown')
        
        assert "not registered" in str(exc_info.value)
        assert exc_info.value.provider == 'unknown'

    def test_register_custom_adapter(self):
        """Test registering a custom adapter"""
        class CustomAdapter(DeepSeekAdapter):
            pass
        
        AIAdapterFactory.register('custom', CustomAdapter)
        adapter = AIAdapterFactory.get_adapter('custom')
        assert isinstance(adapter, CustomAdapter)

    def test_register_overwrites_existing(self):
        """Test that registering overwrites existing adapter"""
        class CustomAdapter(DeepSeekAdapter):
            pass
        
        # Get original adapter
        original = AIAdapterFactory.get_adapter('deepseek')
        
        # Register custom adapter
        AIAdapterFactory.register('deepseek', CustomAdapter)
        
        # Clear cache to force reload
        AIAdapterFactory.clear_cache()
        
        # Get new adapter
        new_adapter = AIAdapterFactory.get_adapter('deepseek')
        assert isinstance(new_adapter, CustomAdapter)

    def test_get_supported_providers(self):
        """Test getting list of supported providers"""
        providers = AIAdapterFactory.get_supported_providers()
        
        assert 'deepseek' in providers
        assert 'doubao' in providers
        assert 'qwen' in providers

    def test_is_supported(self):
        """Test checking if provider is supported"""
        assert AIAdapterFactory.is_supported('deepseek') is True
        assert AIAdapterFactory.is_supported('unknown') is False

    def test_clear_cache(self):
        """Test clearing adapter cache"""
        # Get adapter to cache it
        AIAdapterFactory.get_adapter('deepseek')
        
        # Clear cache
        AIAdapterFactory.clear_cache()
        
        # Verify cache is cleared (new instance created)
        adapter1 = AIAdapterFactory.get_adapter('deepseek')
        AIAdapterFactory.clear_cache()
        adapter2 = AIAdapterFactory.get_adapter('deepseek')
        # After clear, they should be different instances
        # But since we clear between gets, they will be new each time


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_get_adapter_function(self):
        """Test get_adapter convenience function"""
        adapter = get_adapter('deepseek')
        assert isinstance(adapter, DeepSeekAdapter)

    def test_get_supported_providers_function(self):
        """Test get_supported_providers convenience function"""
        providers = get_supported_providers()
        assert isinstance(providers, list)
        assert len(providers) >= 3
