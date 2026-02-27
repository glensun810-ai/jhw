"""
DeepSeek AI Adapter

Adapter for DeepSeek AI platform.

Official Documentation: https://platform.deepseek.com/api-docs/

Author: System Architecture Team
Date: 2026-02-27
Version: 2.0.0
"""

import os
import logging
from typing import Dict, Any, Optional

from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.errors import (
    AIAuthenticationError,
    AIRateLimitError,
    AIQuotaExceededError,
    AIResponseError,
    AIContentFilterError,
    AIModelNotFoundError,
    AIAdapterError,
)

logger = logging.getLogger(__name__)


class DeepSeekAdapter(BaseAIAdapter):
    """
    DeepSeek AI Adapter

    Supports DeepSeek chat and coder models.

    Features:
    1. Standard request/response format conversion
    2. Platform-specific error handling
    3. API key management from environment

    Example:
        >>> adapter = DeepSeekAdapter()
        >>> request = AIRequest(prompt="Hello", model="deepseek-chat")
        >>> response = await adapter.send(request)
        >>> print(response.content)
    """

    def __init__(self, provider: str = 'deepseek'):
        """
        Initialize DeepSeek adapter

        Args:
            provider: Provider name
        """
        super().__init__(provider)

    def _get_api_key(self) -> str:
        """
        Get DeepSeek API key from environment variable

        Returns:
            str: API key

        Raises:
            ValueError: If API key is not set
        """
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        return api_key

    def _get_api_url(self) -> str:
        """
        Get DeepSeek API endpoint URL

        Returns:
            str: API URL
        """
        return self.config.get('api_url', 'https://api.deepseek.com/v1/chat/completions')

    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers

        Returns:
            Dict[str, str]: Request headers with authentication
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        Build DeepSeek-specific request payload

        DeepSeek API format:
        {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "prompt"}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": false
        }

        Args:
            request: Standardized request

        Returns:
            Dict[str, Any]: Platform-specific request payload
        """
        messages = request.messages or []
        if not messages and request.prompt:
            messages = [{"role": "user", "content": request.prompt}]

        payload = {
            "model": request.model or "deepseek-chat",
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False,
        }

        # Remove None values
        return {k: v for k, v in payload.items() if v is not None}

    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        Parse DeepSeek response

        DeepSeek response format:
        {
            "id": "chatcmpl-xxx",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "deepseek-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "response text"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

        Args:
            response_data: Raw response from DeepSeek
            request: Original request

        Returns:
            AIResponse: Standardized response

        Raises:
            AIResponseError: If response format is invalid
        """
        try:
            # Extract response content
            choices = response_data.get('choices', [])
            if not choices:
                raise AIResponseError("No choices in response", provider=self.provider)

            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')

            # Extract usage
            usage = response_data.get('usage', {})

            # Extract finish reason
            finish_reason = first_choice.get('finish_reason')

            return AIResponse(
                content=content,
                model=response_data.get('model', request.model),
                latency_ms=0,  # Will be filled by upper layer
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                finish_reason=finish_reason,
                raw_response=response_data,
                provider=self.provider,
                request_id=response_data.get('id'),
            )

        except KeyError as e:
            raise AIResponseError(
                f"Missing field in response: {e}",
                provider=self.provider,
                original_error=e
            )

    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        Parse DeepSeek error response

        DeepSeek error format:
        {
            "error": {
                "message": "Invalid API key",
                "type": "invalid_request_error",
                "param": null,
                "code": "invalid_api_key"
            }
        }

        Args:
            response_data: Error response from DeepSeek
            status_code: HTTP status code

        Returns:
            AIAdapterError: Corresponding internal exception
        """
        error = response_data.get('error', {})
        message = error.get('message', 'Unknown error')
        error_code = error.get('code', '')
        error_type = error.get('type', '')

        # Map to internal exception based on status code and error code
        if status_code == 401:
            return AIAuthenticationError(message, provider=self.provider)
        elif status_code == 429:
            if 'rate' in message.lower():
                return AIRateLimitError(message, provider=self.provider)
            else:
                return AIQuotaExceededError(message, provider=self.provider)
        elif status_code == 404:
            return AIModelNotFoundError(message, provider=self.provider)
        elif status_code == 400 and 'content' in message.lower():
            return AIContentFilterError(message, provider=self.provider)
        else:
            return AIAdapterError(message, provider=self.provider)

    def parse_geo_data(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse GEO (Geographic/Emotional) data from DeepSeek response

        Expects the AI to return structured JSON data with brand analysis.
        Parses the response content to extract brand, sentiment, and geographic data.

        Args:
            response: Standardized response from DeepSeek

        Returns:
            Dict[str, Any]: Parsed GEO data with structure:
                {
                    'brand': str,
                    'sentiment': str,
                    'confidence': float,
                    'keywords': List[str],
                    'regions': List[str],
                    'raw_data': Dict
                }
        """
        import json

        default_result = {
            'brand': '',
            'sentiment': 'neutral',
            'confidence': 0.0,
            'keywords': [],
            'regions': [],
            'raw_data': {},
        }

        if not response.content:
            return default_result

        try:
            # Try to parse JSON from response content
            # AI may return markdown code blocks, so we extract JSON
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            content = content.strip()
            data = json.loads(content)

            # Extract standardized fields
            return {
                'brand': data.get('brand', data.get('brand_name', '')),
                'sentiment': data.get('sentiment', 'neutral'),
                'confidence': float(data.get('confidence', data.get('score', 0.0))),
                'keywords': data.get('keywords', data.get('tags', [])),
                'regions': data.get('regions', data.get('geo_data', {}).get('regions', [])),
                'raw_data': data,
            }

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Failed to parse GEO data from response: {e}")
            # Return content as-is in raw_data for manual processing
            default_result['raw_data'] = {'content': response.content}
            return default_result
