"""
Synchronous AI Provider Implementations for GEO Content Quality Validator
Includes providers for domestic models like DeepSeek, Doubao, Qwen, etc.
"""
import requests
import time
from typing import List, Dict, Any
from wechat_backend.ai_adapters.enhanced_base import EnhancedAIClient, AIResponse, AIPlatformType
from wechat_backend.logging_config import api_logger


class DeepSeekProvider(EnhancedAIClient):
    """AI Provider for DeepSeek API"""

    def __init__(self, api_key: str, model_name: str = "deepseek-chat", **kwargs):
        super().__init__(AIPlatformType.DEEPSEEK, model_name, api_key)
        self.base_url = kwargs.get('base_url', 'https://api.deepseek.com/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)

        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the DeepSeek API"""
        start_time = time.time()

        # Prepare the request payload
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,  # For now, using non-streaming responses
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)
            )
            latency = time.time() - start_time
            response_data = response.json()

            if response.status_code == 200:
                # Extract the content from the response
                content = response_data['choices'][0]['message']['content']

                # Extract token usage if available
                usage = response_data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)

                api_logger.info(f"Successfully received response from DeepSeek API for model: {self.model_name}")

                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=total_tokens,
                    latency=latency,
                    metadata=response_data
                )
            else:
                # Handle API error
                error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                api_logger.error(f"DeepSeek API error for model {self.model_name}: {error_msg}")

                return AIResponse(
                    success=False,
                    error_message=error_msg,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling DeepSeek API for model: {self.model_name}")
            return AIResponse(
                success=False,
                error_message="Request timed out",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling DeepSeek API for model {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )


class DoubaoProvider(EnhancedAIClient):
    """AI Provider for Doubao (ByteDance) API"""

    def __init__(self, api_key: str, model_name: str = "doubao-pro-128k", **kwargs):
        super().__init__(AIPlatformType.DOUBAO, model_name, api_key)
        # Note: This is a placeholder - actual Doubao API details would be different
        self.base_url = kwargs.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)

        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the Doubao API"""
        start_time = time.time()

        # Prepare the request payload
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",  # Placeholder URL
                headers=self.headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)
            )
            latency = time.time() - start_time
            response_data = response.json()

            if response.status_code == 200:
                # Extract the content from the response
                content = response_data['choices'][0]['message']['content']

                # Extract token usage if available
                usage = response_data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)

                api_logger.info(f"Successfully received response from Doubao API for model: {self.model_name}")

                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=total_tokens,
                    latency=latency,
                    metadata=response_data
                )
            else:
                # Handle API error
                error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                api_logger.error(f"Doubao API error for model: {self.model_name}: {error_msg}")

                return AIResponse(
                    success=False,
                    error_message=error_msg,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling Doubao API for model: {self.model_name}")
            return AIResponse(
                success=False,
                error_message="Request timed out",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Doubao API for model: {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )


class QwenProvider(EnhancedAIClient):
    """AI Provider for Qwen (Alibaba Tongyi) API"""

    def __init__(self, api_key: str, model_name: str = "qwen-max", **kwargs):
        super().__init__(AIPlatformType.QWEN, model_name, api_key)
        self.base_url = kwargs.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)

        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the Qwen API"""
        start_time = time.time()

        # Prepare the request payload
        payload = {
            'model': self.model_name,
            'input': {
                'messages': [{'role': 'user', 'content': prompt}]
            },
            'parameters': {
                'temperature': kwargs.get('temperature', self.temperature),
                'max_tokens': kwargs.get('max_tokens', self.max_tokens)
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/services/aigc/text-generation/generation",
                headers=self.headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)
            )
            latency = time.time() - start_time
            response_data = response.json()

            if response.status_code == 200:
                # Extract the content from the response
                content = response_data['output']['text']

                # Extract token usage if available
                usage = response_data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)

                api_logger.info(f"Successfully received response from Qwen API for model: {self.model_name}")

                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=total_tokens,
                    latency=latency,
                    metadata=response_data
                )
            else:
                # Handle API error
                error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                api_logger.error(f"Qwen API error for model: {self.model_name}: {error_msg}")

                return AIResponse(
                    success=False,
                    error_message=error_msg,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling Qwen API for model: {self.model_name}")
            return AIResponse(
                success=False,
                error_message="Request timed out",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Qwen API for model: {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )


class YuanbaoProvider(EnhancedAIClient):
    """AI Provider for Yuanbao (Tencent HunYuan) API"""

    def __init__(self, api_key: str, model_name: str = "hunyuan-pro", **kwargs):
        super().__init__(AIPlatformType.YUANBAO, model_name, api_key)
        # Note: This is a placeholder - actual Yuanbao API details would be different
        self.base_url = kwargs.get('base_url', 'https://hunyuan.cloud.tencent.com/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)

        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the Yuanbao API"""
        start_time = time.time()

        # Prepare the request payload
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",  # Placeholder URL
                headers=self.headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)
            )
            latency = time.time() - start_time
            response_data = response.json()

            if response.status_code == 200:
                # Extract the content from the response
                content = response_data['choices'][0]['message']['content']

                # Extract token usage if available
                usage = response_data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)

                api_logger.info(f"Successfully received response from Yuanbao API for model: {self.model_name}")

                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=total_tokens,
                    latency=latency,
                    metadata=response_data
                )
            else:
                # Handle API error
                error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                api_logger.error(f"Yuanbao API error for model: {self.model_name}: {error_msg}")

                return AIResponse(
                    success=False,
                    error_message=error_msg,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling Yuanbao API for model: {self.model_name}")
            return AIResponse(
                success=False,
                error_message="Request timed out",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Yuanbao API for model: {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )


class ErnieProvider(EnhancedAIClient):
    """AI Provider for Ernie (Baidu) API"""

    def __init__(self, api_key: str, model_name: str = "ernie-bot-4.5", **kwargs):
        super().__init__(AIPlatformType.WENXIN, model_name, api_key)
        # Note: This is a placeholder - actual Ernie API details would be different
        self.base_url = kwargs.get('base_url', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)

        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json'
        }

    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the Ernie API"""
        start_time = time.time()

        # For Baidu ERNIE, we need to get access token first
        access_token = self._get_access_token()
        if not access_token:
            return AIResponse(
                success=False,
                error_message="Failed to get access token",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )

        # Prepare the request payload
        payload = {
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }

        try:
            response = requests.post(
                f"{self.base_url}/wenxinworkshop/chat/{self.model_name}?access_token={access_token}",
                headers=self.headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)
            )
            latency = time.time() - start_time
            response_data = response.json()

            if response.status_code == 200 and 'result' in response_data:
                # Extract the content from the response
                content = response_data['result']

                # Extract token usage if available
                usage = response_data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)

                api_logger.info(f"Successfully received response from Ernie API for model: {self.model_name}")

                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=total_tokens,
                    latency=latency,
                    metadata=response_data
                )
            else:
                # Handle API error
                error_msg = response_data.get('error_msg', f'HTTP {response.status_code}')
                api_logger.error(f"Ernie API error for model {self.model_name}: {error_msg}")

                return AIResponse(
                    success=False,
                    error_message=error_msg,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling Ernie API for model: {self.model_name}")
            return AIResponse(
                success=False,
                error_message="Request timed out",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Ernie API for model: {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )

    def _get_access_token(self):
        """Get access token for Baidu API - placeholder implementation"""
        # In a real implementation, you would fetch the access token from Baidu
        # using your API key and secret
        return "fake_access_token"  # Placeholder


class KimiProvider(EnhancedAIClient):
    """AI Provider for Kimi (Moonshot AI) API"""

    def __init__(self, api_key: str, model_name: str = "moonshot-v1-8k", **kwargs):
        super().__init__(AIPlatformType.KIMI, model_name, api_key)
        self.base_url = kwargs.get('base_url', 'https://api.moonshot.cn/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)

        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the Kimi API"""
        start_time = time.time()

        # Prepare the request payload
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)
            )
            latency = time.time() - start_time
            response_data = response.json()

            if response.status_code == 200:
                # Extract the content from the response
                content = response_data['choices'][0]['message']['content']

                # Extract token usage if available
                usage = response_data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)

                api_logger.info(f"Successfully received response from Kimi API for model: {self.model_name}")

                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=total_tokens,
                    latency=latency,
                    metadata=response_data
                )
            else:
                # Handle API error
                error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                api_logger.error(f"Kimi API error for model: {self.model_name}: {error_msg}")

                return AIResponse(
                    success=False,
                    error_message=error_msg,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling Kimi API for model: {self.model_name}")
            return AIResponse(
                success=False,
                error_message="Request timed out",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Kimi API for model: {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )