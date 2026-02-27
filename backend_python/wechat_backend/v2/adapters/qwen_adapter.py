"""
Qwen AI Adapter

Adapter for Qwen AI platform (Alibaba Cloud).

Official Documentation: https://help.aliyun.com/document_detail/613695.html

Author: System Architecture Team
Date: 2026-02-27
Version: 2.0.0
"""

import os
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


class QwenAdapter(BaseAIAdapter):
    """
    Qwen AI Adapter (Alibaba Cloud)

    Supports Qwen turbo, plus, and max models.

    Features:
    1. Standard request/response format conversion
    2. Platform-specific error handling
    3. API key management from environment
    4. Special handling for Qwen's different token field names

    Example:
        >>> adapter = QwenAdapter()
        >>> request = AIRequest(prompt="Hello", model="qwen-turbo")
        >>> response = await adapter.send(request)
        >>> print(response.content)
    """

    def __init__(self, provider: str = 'qwen'):
        """
        Initialize Qwen adapter

        Args:
            provider: Provider name
        """
        super().__init__(provider)

    def _get_api_key(self) -> str:
        """
        Get Qwen API key from environment variable

        Returns:
            str: API key

        Raises:
            ValueError: If API key is not set
        """
        api_key = os.getenv('QWEN_API_KEY')
        if not api_key:
            raise ValueError("QWEN_API_KEY environment variable not set")
        return api_key

    def _get_api_url(self) -> str:
        """
        Get Qwen API endpoint URL

        Returns:
            str: API URL
        """
        return self.config.get('api_url', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')

    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers (Qwen uses different authentication)

        Returns:
            Dict[str, str]: Request headers with authentication
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-SSE': 'disable',  # Disable streaming
        }

    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        Build Qwen-specific request payload

        Qwen API format:
        {
            "model": "qwen-turbo",
            "input": {
                "messages": [
                    {"role": "user", "content": "prompt"}
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 0.8,
                "result_format": "message"
            }
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
            "model": request.model or "qwen-turbo",
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "result_format": "message",
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
            }
        }

        return payload

    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        Parse Qwen response

        Qwen response format:
        {
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "response text"
                        },
                        "finish_reason": "stop"
                    }
                ]
            },
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30
            }
        }

        Args:
            response_data: Raw response from Qwen
            request: Original request

        Returns:
            AIResponse: Standardized response

        Raises:
            AIResponseError: If response format is invalid
        """
        try:
            output = response_data.get('output', {})
            choices = output.get('choices', [])

            if not choices:
                raise AIResponseError("No choices in response", provider=self.provider)

            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')

            usage = response_data.get('usage', {})

            # Qwen uses different token field names
            prompt_tokens = usage.get('input_tokens')
            completion_tokens = usage.get('output_tokens')
            total_tokens = usage.get('total_tokens')

            return AIResponse(
                content=content,
                model=response_data.get('model', request.model),
                latency_ms=0,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=first_choice.get('finish_reason'),
                raw_response=response_data,
                provider=self.provider,
                request_id=response_data.get('request_id'),
            )

        except KeyError as e:
            raise AIResponseError(
                f"Missing field in response: {e}",
                provider=self.provider,
                original_error=e
            )

    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        Parse Qwen error response

        Qwen error format:
        {
            "code": "InvalidApiKey",
            "message": "The API key is invalid",
            "request_id": "xxx"
        }

        Args:
            response_data: Error response from Qwen
            status_code: HTTP status code

        Returns:
            AIAdapterError: Corresponding internal exception
        """
        code = response_data.get('code', '')
        message = response_data.get('message', 'Unknown error')

        if status_code == 401 or 'InvalidApiKey' in code:
            return AIAuthenticationError(message, provider=self.provider)
        elif status_code == 429 or 'Throttling' in code:
            return AIRateLimitError(message, provider=self.provider)
        elif 'ModelNotFound' in code:
            return AIModelNotFoundError(message, provider=self.provider)
        elif 'ContentFilter' in code:
            return AIContentFilterError(message, provider=self.provider)
        elif 'QuotaExceeded' in code:
            return AIQuotaExceededError(message, provider=self.provider)
        else:
            return AIAdapterError(message, provider=self.provider)

    def parse_geo_data(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse GEO (Geographic/Emotional) data from Qwen response

        Expects the AI to return structured JSON data with brand analysis.
        Parses the response content to extract brand, sentiment, and geographic data.

        Args:
            response: Standardized response from Qwen

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
            default_result['raw_data'] = {'content': response.content}
            return default_result
