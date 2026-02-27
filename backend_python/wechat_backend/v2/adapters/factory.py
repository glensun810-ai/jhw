"""
AI Adapter Factory

This module provides the factory for creating AI adapter instances.
It supports dynamic loading and singleton pattern for efficiency.

Author: System Architecture Team
Date: 2026-02-27
Version: 2.0.0
"""

from typing import Dict, Type, Optional
import importlib
import logging

from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.errors import AIModelNotFoundError

logger = logging.getLogger(__name__)


class AIAdapterFactory:
    """
    AI Adapter Factory

    Responsible for creating adapter instances based on provider names.
    Supports dynamic loading and singleton pattern.

    Features:
    1. Adapter registration and discovery
    2. Singleton pattern for adapter instances
    3. Dynamic loading from modules
    4. Support for custom adapters

    Example:
        >>> # Get adapter instance
        >>> adapter = AIAdapterFactory.get_adapter('deepseek')
        >>>
        >>> # Register custom adapter
        >>> AIAdapterFactory.register('custom', CustomAdapter)
        >>>
        >>> # Get supported providers
        >>> providers = AIAdapterFactory.get_supported_providers()
    """

    _adapters: Dict[str, Type[BaseAIAdapter]] = {}
    _instances: Dict[str, BaseAIAdapter] = {}
    _initialized: bool = False

    @classmethod
    def _initialize_default_adapters(cls):
        """Initialize default adapters (deepseek, doubao, qwen)"""
        if cls._initialized:
            return
        
        # Pre-register known adapters for dynamic loading
        for provider in ['deepseek', 'doubao', 'qwen']:
            cls._try_import_adapter(provider)
        
        cls._initialized = True

    @classmethod
    def register(cls, provider: str, adapter_class: Type[BaseAIAdapter]):
        """
        Register an adapter class

        Args:
            provider: Platform name
            adapter_class: Adapter class

        Example:
            >>> AIAdapterFactory.register('deepseek', DeepSeekAdapter)
        """
        provider_key = provider.lower()
        cls._adapters[provider_key] = adapter_class

        # Clear cached instance to use new class
        if provider_key in cls._instances:
            del cls._instances[provider_key]

        logger.info(
            "adapter_registered",
            extra={
                'event': 'adapter_registered',
                'provider': provider,
                'adapter_class': adapter_class.__name__,
            }
        )

    @classmethod
    def get_adapter(cls, provider: str) -> BaseAIAdapter:
        """
        Get adapter instance (singleton pattern)

        Args:
            provider: Platform name

        Returns:
            BaseAIAdapter: Adapter instance

        Raises:
            AIModelNotFoundError: If provider is not registered

        Example:
            >>> adapter = AIAdapterFactory.get_adapter('deepseek')
        """
        # Initialize default adapters on first call
        cls._initialize_default_adapters()
        
        provider_key = provider.lower()

        # Return cached instance
        if provider_key in cls._instances:
            return cls._instances[provider_key]

        # Get adapter class
        adapter_class = cls._adapters.get(provider_key)
        if not adapter_class:
            # Try dynamic import
            cls._try_import_adapter(provider_key)
            adapter_class = cls._adapters.get(provider_key)

        if not adapter_class:
            raise AIModelNotFoundError(
                f"AI provider '{provider}' not registered",
                provider=provider
            )

        # Create and cache instance
        instance = adapter_class(provider_key)
        cls._instances[provider_key] = instance

        logger.info(
            "adapter_created",
            extra={
                'event': 'adapter_created',
                'provider': provider,
                'adapter_class': adapter_class.__name__,
            }
        )

        return instance

    @classmethod
    def _try_import_adapter(cls, provider: str):
        """
        Try to dynamically import adapter module

        Supports lazy loading to avoid importing all adapters upfront.

        Args:
            provider: Platform name
        """
        try:
            module_name = f"wechat_backend.v2.adapters.{provider}_adapter"
            module = importlib.import_module(module_name)

            # Look for adapter class (typically named {Provider}Adapter)
            class_name = f"{provider.capitalize()}Adapter"
            if hasattr(module, class_name):
                adapter_class = getattr(module, class_name)
                cls.register(provider, adapter_class)

                logger.debug(
                    "adapter_dynamically_loaded",
                    extra={
                        'event': 'adapter_dynamically_loaded',
                        'provider': provider,
                        'module': module_name,
                    }
                )
        except (ImportError, AttributeError) as e:
            logger.debug(
                "adapter_import_failed",
                extra={
                    'event': 'adapter_import_failed',
                    'provider': provider,
                    'error': str(e),
                }
            )
            pass  # Ignore import errors, will throw exception later

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """
        Get list of all registered providers

        Returns:
            list[str]: List of provider names

        Example:
            >>> providers = AIAdapterFactory.get_supported_providers()
            >>> print(providers)
            ['deepseek', 'doubao', 'qwen']
        """
        # Initialize default adapters
        cls._initialize_default_adapters()
        
        return list(cls._adapters.keys())

    @classmethod
    def clear_cache(cls):
        """
        Clear cached instances

        Mainly used for testing to reset state.
        """
        cls._instances.clear()

        logger.info(
            "adapter_cache_cleared",
            extra={
                'event': 'adapter_cache_cleared',
            }
        )

    @classmethod
    def is_supported(cls, provider: str) -> bool:
        """
        Check if provider is supported

        Args:
            provider: Platform name

        Returns:
            bool: True if supported

        Example:
            >>> AIAdapterFactory.is_supported('deepseek')
            True
        """
        return provider.lower() in cls.get_supported_providers()


# Convenience functions
def get_adapter(provider: str) -> BaseAIAdapter:
    """
    Get adapter instance (shortcut)

    Args:
        provider: Platform name

    Returns:
        BaseAIAdapter: Adapter instance
    """
    return AIAdapterFactory.get_adapter(provider)


def get_supported_providers() -> list[str]:
    """
    Get supported providers (shortcut)

    Returns:
        list[str]: List of provider names
    """
    return AIAdapterFactory.get_supported_providers()
