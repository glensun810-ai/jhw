"""
AI Adapter Error Definitions

This module defines the exception hierarchy for AI adapter error handling.
All platform-specific errors are mapped to these internal exception types.
"""

from typing import Optional


class AIAdapterError(Exception):
    """Base exception for AI adapter errors"""

    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class AIAuthenticationError(AIAdapterError):
    """Authentication error (invalid API Key)"""
    pass


class AIRateLimitError(AIAdapterError):
    """Rate limit error"""
    pass


class AIQuotaExceededError(AIAdapterError):
    """Quota exceeded error"""
    pass


class AITimeoutError(AIAdapterError):
    """Timeout error"""
    pass


class AIConnectionError(AIAdapterError):
    """Connection error"""
    pass


class AIResponseError(AIAdapterError):
    """Response format error"""
    pass


class AIModelNotFoundError(AIAdapterError):
    """Model not found error"""
    pass


class AIContentFilterError(AIAdapterError):
    """Content filtered error"""
    pass


# Error code mapping (for converting platform-specific errors to internal errors)
# Format: ('provider', 'platform_error_code'): InternalErrorClass
ERROR_CODE_MAPPING = {
    # DeepSeek
    ('deepseek', 'invalid_api_key'): AIAuthenticationError,
    ('deepseek', 'insufficient_quota'): AIQuotaExceededError,
    ('deepseek', 'model_not_found'): AIModelNotFoundError,
    
    # Doubao
    ('doubao', 'InvalidApiKey'): AIAuthenticationError,
    ('doubao', 'Throttling'): AIRateLimitError,
    ('doubao', 'QuotaExceeded'): AIQuotaExceededError,
    
    # Qwen
    ('qwen', 'InvalidApiKey'): AIAuthenticationError,
    ('qwen', 'Throttling'): AIRateLimitError,
    ('qwen', 'ModelNotFound'): AIModelNotFoundError,
    ('qwen', 'ContentFilter'): AIContentFilterError,
    ('qwen', 'QuotaExceeded'): AIQuotaExceededError,
}
