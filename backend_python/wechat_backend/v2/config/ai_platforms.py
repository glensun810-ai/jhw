"""
AI Platform Configuration Management

This module manages configuration for all AI platforms including:
- API endpoints
- Timeout settings
- Retry policies
- Rate limits
- Supported models

Author: System Architecture Team
Date: 2026-02-27
Version: 2.0.0
"""

from typing import Dict, Any
import os


# Default platform configurations
DEFAULT_CONFIGS = {
    'deepseek': {
        'api_url': 'https://api.deepseek.com/v1/chat/completions',
        'max_retries': 3,
        'retry_base_delay': 1.0,
        'retry_max_delay': 30.0,
        'timeout': 60,
        'rate_limit': 10,  # Requests per minute
        'models': ['deepseek-chat', 'deepseek-coder'],
    },
    'doubao': {
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'max_retries': 3,
        'retry_base_delay': 1.0,
        'retry_max_delay': 30.0,
        'timeout': 60,
        'rate_limit': 20,
        'models': ['doubao-lite-32k', 'doubao-pro-32k'],
    },
    'qwen': {
        'api_url': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        'max_retries': 3,
        'retry_base_delay': 1.0,
        'retry_max_delay': 30.0,
        'timeout': 60,
        'rate_limit': 15,
        'models': ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    },
}


def get_platform_config(provider: str) -> Dict[str, Any]:
    """
    Get platform configuration

    Supports environment variable overrides for all configuration options.

    Environment variable format: AI_{PROVIDER}_{CONFIG_KEY}
    Example: AI_DEEPSEEK_TIMEOUT=120

    Args:
        provider: Platform name (e.g., 'deepseek')

    Returns:
        Dict[str, Any]: Platform configuration dictionary
    """
    config = DEFAULT_CONFIGS.get(provider.lower(), {}).copy()

    # Override from environment variables
    env_prefix = f"AI_{provider.upper()}_"
    for key in config.keys():
        env_key = env_prefix + key.upper()
        if env_key in os.environ:
            value = os.environ[env_key]
            # Try to convert to appropriate type
            if isinstance(config[key], int):
                try:
                    config[key] = int(value)
                except ValueError:
                    pass
            elif isinstance(config[key], float):
                try:
                    config[key] = float(value)
                except ValueError:
                    pass
            elif isinstance(config[key], bool):
                config[key] = value.lower() in ('true', '1', 'yes')
            else:
                config[key] = value

    return config


def get_all_platforms() -> list[str]:
    """
    Get all configured platforms

    Returns:
        list[str]: List of platform names
    """
    return list(DEFAULT_CONFIGS.keys())


def is_platform_configured(provider: str) -> bool:
    """
    Check if platform is configured (API Key exists)

    Args:
        provider: Platform name

    Returns:
        bool: True if API key is configured
    """
    env_var = f"{provider.upper()}_API_KEY"
    return env_var in os.environ


def get_platform_models(provider: str) -> list[str]:
    """
    Get supported models for a platform

    Args:
        provider: Platform name

    Returns:
        list[str]: List of model names
    """
    config = get_platform_config(provider)
    return config.get('models', [])


def is_model_supported(provider: str, model: str) -> bool:
    """
    Check if a model is supported by a platform

    Args:
        provider: Platform name
        model: Model name

    Returns:
        bool: True if model is supported
    """
    models = get_platform_models(provider)
    return model in models
