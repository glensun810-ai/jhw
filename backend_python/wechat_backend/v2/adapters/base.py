"""
AI Adapter Base Abstract Class

This module defines the abstract base class for all AI platform adapters.
All concrete adapters must inherit from this class and implement abstract methods.

Author: System Architecture Team
Date: 2026-02-27
Version: 2.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator
import asyncio
import time
import logging

import aiohttp

from wechat_backend.v2.adapters.models import AIRequest, AIResponse, AIStreamChunk
from wechat_backend.v2.adapters.errors import (
    AIAdapterError,
    AIAuthenticationError,
    AIRateLimitError,
    AIQuotaExceededError,
    AITimeoutError,
    AIConnectionError,
    AIResponseError,
    AIModelNotFoundError,
    AIContentFilterError,
)
from wechat_backend.v2.services.retry_policy import RetryPolicy
from wechat_backend.v2.services.api_call_logger import APICallLogger
from wechat_backend.v2.config.ai_platforms import get_platform_config

logger = logging.getLogger(__name__)


class BaseAIAdapter(ABC):
    """
    AI Adapter Abstract Base Class

    All platform-specific adapters must inherit from this class and implement
    the abstract methods. This class provides common retry, logging, and error
    handling mechanisms.

    Responsibilities:
    1. Define standard interface for all AI adapters
    2. Provide common retry mechanism via RetryPolicy
    3. Provide common logging via APICallLogger
    4. Handle common error scenarios
    5. Manage API key retrieval from environment

    Example:
        >>> class DeepSeekAdapter(BaseAIAdapter):
        ...     def _get_api_key(self) -> str:
        ...         return os.getenv('DEEPSEEK_API_KEY')
        ...
        ...     def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        ...         return {'model': 'deepseek-chat', 'messages': [...]}
        ...
        ...     def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        ...         return AIResponse(content=..., model=..., ...)
    """

    def __init__(self, provider: str):
        """
        Initialize the adapter

        Args:
            provider: Platform name (e.g., 'deepseek')
        """
        self.provider = provider
        self.config = get_platform_config(provider)

        # Reuse phase-one infrastructure services
        self.retry_policy = RetryPolicy(
            max_retries=self.config.get('max_retries', 3),
            base_delay=self.config.get('retry_base_delay', 1.0),
            max_delay=self.config.get('retry_max_delay', 30.0),
            retryable_exceptions=[
                AITimeoutError,
                AIConnectionError,
                AIRateLimitError,
            ]
        )

        self.logger = APICallLogger()

        # Get API key from environment variable
        self.api_key = self._get_api_key()

        logger.info(
            "ai_adapter_initialized",
            extra={
                'event': 'ai_adapter_initialized',
                'provider': provider,
                'max_retries': self.retry_policy.max_retries,
            }
        )

    @abstractmethod
    def _get_api_key(self) -> str:
        """
        Get API key from environment variable

        Subclasses must implement this to retrieve the API key from
        the appropriate environment variable.

        Returns:
            str: API key

        Raises:
            ValueError: If API key is not set
        """
        pass

    @abstractmethod
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        Build platform-specific request payload

        Subclasses must implement this to convert the standardized
        AIRequest into the platform's specific format.

        Args:
            request: Standardized request

        Returns:
            Dict[str, Any]: Platform-specific request dictionary
        """
        pass

    @abstractmethod
    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        Parse platform-specific response

        Subclasses must implement this to convert the platform's raw
        response into the standardized AIResponse format.

        Args:
            response_data: Raw response from platform
            request: Original request (for logging)

        Returns:
            AIResponse: Standardized response

        Raises:
            AIResponseError: If response format is invalid
        """
        pass

    @abstractmethod
    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        Parse platform-specific error

        Subclasses must implement this to convert the platform's error
        response into the appropriate internal exception type.

        Args:
            response_data: Error response from platform
            status_code: HTTP status code

        Returns:
            AIAdapterError: Corresponding internal exception
        """
        pass

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers including authentication

        Returns:
            Dict[str, str]: Request headers
        """
        pass

    @abstractmethod
    def _get_api_url(self) -> str:
        """
        Get API endpoint URL

        Returns:
            str: API URL
        """
        pass

    @abstractmethod
    def parse_geo_data(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse GEO (Geographic/Emotional) data from response

        Extracts geographic distribution, sentiment analysis, and other
        structured data from the AI response content.

        Args:
            response: Standardized response containing AI-generated content

        Returns:
            Dict[str, Any]: Parsed GEO data with following structure:
                {
                    'brand': str,              # Brand name
                    'sentiment': str,          # positive/neutral/negative
                    'confidence': float,       # Confidence score (0-1)
                    'keywords': List[str],     # Extracted keywords
                    'regions': List[str],      # Mentioned regions
                    'raw_data': Dict           # Original parsed data
                }

        Note:
            Subclasses should implement JSON parsing logic based on
            the expected response format from their prompts.
        """
        pass

    async def send(self, request: AIRequest) -> AIResponse:
        """
        Send request with retry and logging

        This is the main method exposed to the business layer.
        Subclasses typically do not need to override this.

        Args:
            request: Standardized request

        Returns:
            AIResponse: Standardized response

        Raises:
            AIAdapterError: Various adapter-specific errors
        """
        start_time = time.time()

        # Prepare log context
        log_context = {
            'provider': self.provider,
            'model': request.model,
            'request_id': request.request_id,
        }

        try:
            # Execute request with retry policy
            response = await self.retry_policy.execute_async(
                self._send_single,
                request=request
            )

            # Record success log
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.log_api_call(
                provider=self.provider,
                request=request,
                response=response,
                latency_ms=latency_ms,
                success=True
            )

            logger.info(
                "ai_request_succeeded",
                extra={
                    'event': 'ai_request_succeeded',
                    'provider': self.provider,
                    'model': request.model,
                    'latency_ms': latency_ms,
                    'request_id': request.request_id,
                }
            )

            return response

        except AIAdapterError as e:
            # Record failure log
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.log_api_call(
                provider=self.provider,
                request=request,
                error=e,
                latency_ms=latency_ms,
                success=False
            )

            logger.warning(
                "ai_request_failed",
                extra={
                    'event': 'ai_request_failed',
                    'provider': self.provider,
                    'model': request.model,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'latency_ms': latency_ms,
                    'request_id': request.request_id,
                }
            )
            raise

        except Exception as e:
            # Wrap unknown exceptions
            latency_ms = int((time.time() - start_time) * 1000)
            wrapped_error = AIAdapterError(
                f"Unexpected error: {str(e)}",
                provider=self.provider,
                original_error=e
            )
            self.logger.log_api_call(
                provider=self.provider,
                request=request,
                error=wrapped_error,
                latency_ms=latency_ms,
                success=False
            )

            logger.error(
                "ai_request_unknown_error",
                extra={
                    'event': 'ai_request_unknown_error',
                    'provider': self.provider,
                    'model': request.model,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'latency_ms': latency_ms,
                    'request_id': request.request_id,
                }
            )
            raise wrapped_error

    async def _send_single(self, request: AIRequest) -> AIResponse:
        """
        Send single request (called by retry policy)

        Args:
            request: Standardized request

        Returns:
            AIResponse: Standardized response

        Raises:
            AIAdapterError: Various adapter-specific errors
        """
        # 1. Build request payload
        payload = self._build_request_payload(request)

        # 2. Get headers and URL
        headers = self._get_headers()
        url = self._get_api_url()

        # 3. Send HTTP request
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=request.timeout)
                ) as resp:

                    # 4. Read response
                    response_data = await resp.json()

                    # 5. Check HTTP status code
                    if resp.status >= 400:
                        error = self._parse_error(response_data, resp.status)
                        raise error

                    # 6. Parse response
                    return self._parse_response(response_data, request)

        except asyncio.TimeoutError:
            raise AITimeoutError(
                f"Request timeout after {request.timeout}s",
                provider=self.provider
            )
        except aiohttp.ClientConnectionError as e:
            raise AIConnectionError(
                f"Connection error: {str(e)}",
                provider=self.provider,
                original_error=e
            )
        except aiohttp.ClientError as e:
            raise AIAdapterError(
                f"HTTP client error: {str(e)}",
                provider=self.provider,
                original_error=e
            )

    async def send_stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        """
        Send streaming request (optional implementation)

        Subclasses can override this method to support streaming output.

        Args:
            request: Standardized request

        Yields:
            AIStreamChunk: Streaming response chunks

        Raises:
            NotImplementedError: If streaming is not supported
        """
        raise NotImplementedError(f"{self.provider} does not support streaming")

    def validate_response(self, response: AIResponse) -> bool:
        """
        Validate response validity

        Subclasses can override this method to add platform-specific
        validation logic.

        Args:
            response: Standardized response

        Returns:
            bool: Whether the response is valid
        """
        return response.is_success and response.content and len(response.content) > 0
