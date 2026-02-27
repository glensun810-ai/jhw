"""
Configuration Package

This package provides configuration management for:
- AI platform settings (API endpoints, timeouts, retry policies)
- Feature flags
- Environment-based configuration overrides

Usage:
    from wechat_backend.v2.config import get_platform_config, get_all_platforms
    
    config = get_platform_config('deepseek')
    platforms = get_all_platforms()
"""

from wechat_backend.v2.config.ai_platforms import (
    get_platform_config,
    get_all_platforms,
    is_platform_configured,
    get_platform_models,
    is_model_supported,
    DEFAULT_CONFIGS,
)

__all__ = [
    'get_platform_config',
    'get_all_platforms',
    'is_platform_configured',
    'get_platform_models',
    'is_model_supported',
    'DEFAULT_CONFIGS',
]
