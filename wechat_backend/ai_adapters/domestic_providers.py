"""
Specific AI Provider Implementations for GEO Content Quality Validator
Includes providers for domestic models like DeepSeek, Doubao, Yuanbao, etc.
"""
import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Optional
from .base_adapter import AIClient, AIResponse, AIPlatformType
from ..logging_config import api_logger


class DeepSeekProvider(AIClient):
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

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the DeepSeek API"""
        import requests
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
    
    def _extract_sources(self, content: str) -> List[str]:
        """Extract potential sources from the content"""
        # This is a simple implementation - in reality, DeepSeek might not provide direct sources
        # unless specifically prompted to do so
        sources = []
        # Look for URLs in the content
        import re
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        sources.extend(urls)
        return sources
    
    def validate_config(self) -> bool:
        """Validate the configuration for DeepSeek API"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("DeepSeek API key is not configured")
            return False
        
        # Test the API key by making a simple request
        # This would normally be done synchronously, but for now we'll return True
        # A full implementation would make a test call
        return True
    
    def get_provider_type(self) -> AIProviderType:
        """Get the type of AI provider"""
        return AIProviderType.DEEPSEEK


class DoubaoProvider(AIClient):
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

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """Send a prompt to the Doubao API"""
        import requests
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
                api_logger.error(f"Doubao API error for model {self.model_name}: {error_msg}")

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
            api_logger.error(f"Unexpected error when calling Doubao API for model {self.model_name}: {str(e)}")
            return AIResponse(
                success=False,
                error_message=str(e),
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
    
    def _extract_sources_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """Extract sources from Doubao response (placeholder implementation)"""
        sources = []
        # In a real implementation, this would extract sources from the response
        # which might include web search results or citations
        return sources
    
    def validate_config(self) -> bool:
        """Validate the configuration for Doubao API"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("Doubao API key is not configured")
            return False
        
        return True
    
    def get_provider_type(self) -> AIProviderType:
        """Get the type of AI provider"""
        return AIProviderType.DOUBAO


class YuanbaoProvider(AIClient):
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
    
    async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
        """Query the Yuanbao API"""
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
            await self.initialize_session()
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",  # Placeholder URL
                headers=self.headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                response_data = await response.json()
                
                if response.status == 200:
                    # Extract the content from the response
                    content = response_data['choices'][0]['message']['content']
                    
                    # Extract token usage if available
                    usage = response_data.get('usage', {})
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                    
                    # Extract sources (placeholder)
                    sources = self._extract_sources_from_response(response_data)
                    
                    api_logger.info(f"Successfully received response from Yuanbao API for model: {self.model_name}")
                    
                    return StandardAIResponse(
                        content=content,
                        sources=sources,
                        usage={
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'total_tokens': total_tokens
                        },
                        latency=latency,
                        success=True,
                        provider=self.provider_name,
                        model=self.model_name,
                        metadata=response_data
                    )
                else:
                    # Handle API error
                    error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status}')
                    api_logger.error(f"Yuanbao API error for model {self.model_name}: {error_msg}")
                    
                    return StandardAIResponse(
                        content="",
                        sources=[],
                        usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                        latency=latency,
                        success=False,
                        error_message=error_msg,
                        provider=self.provider_name,
                        model=self.model_name
                    )
        
        except asyncio.TimeoutError:
            api_logger.error(f"Timeout error when calling Yuanbao API for model: {self.model_name}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message="Request timed out",
                provider=self.provider_name,
                model=self.model_name
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Yuanbao API for model {self.model_name}: {str(e)}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message=str(e),
                provider=self.provider_name,
                model=self.model_name
            )
    
    def _extract_sources_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """Extract sources from Yuanbao response (placeholder implementation)"""
        sources = []
        # In a real implementation, this would extract sources from the response
        return sources
    
    def validate_config(self) -> bool:
        """Validate the configuration for Yuanbao API"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("Yuanbao API key is not configured")
            return False
        
        return True
    
    def get_provider_type(self) -> AIProviderType:
        """Get the type of AI provider"""
        return AIProviderType.YUANBAO


class QwenProvider(BaseAIProvider):
    """AI Provider for Qwen (Alibaba Tongyi) API"""
    
    def __init__(self, api_key: str, model_name: str = "qwen-max", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)
        
        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
        """Query the Qwen API"""
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
            await self.initialize_session()
            
            async with self.session.post(
                f"{self.base_url}/services/aigc/text-generation/generation",
                headers=self.headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                response_data = await response.json()
                
                if response.status == 200:
                    # Extract the content from the response
                    content = response_data['output']['text']
                    
                    # Extract token usage if available
                    usage = response_data.get('usage', {})
                    input_tokens = usage.get('input_tokens', 0)
                    output_tokens = usage.get('output_tokens', 0)
                    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                    
                    # Extract sources (placeholder)
                    sources = self._extract_sources_from_response(response_data)
                    
                    api_logger.info(f"Successfully received response from Qwen API for model: {self.model_name}")
                    
                    return StandardAIResponse(
                        content=content,
                        sources=sources,
                        usage={
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'total_tokens': total_tokens
                        },
                        latency=latency,
                        success=True,
                        provider=self.provider_name,
                        model=self.model_name,
                        metadata=response_data
                    )
                else:
                    # Handle API error
                    error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status}')
                    api_logger.error(f"Qwen API error for model {self.model_name}: {error_msg}")
                    
                    return StandardAIResponse(
                        content="",
                        sources=[],
                        usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                        latency=latency,
                        success=False,
                        error_message=error_msg,
                        provider=self.provider_name,
                        model=self.model_name
                    )
        
        except asyncio.TimeoutError:
            api_logger.error(f"Timeout error when calling Qwen API for model: {self.model_name}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message="Request timed out",
                provider=self.provider_name,
                model=self.model_name
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Qwen API for model {self.model_name}: {str(e)}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message=str(e),
                provider=self.provider_name,
                model=self.model_name
            )
    
    def _extract_sources_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """Extract sources from Qwen response (placeholder implementation)"""
        sources = []
        # In a real implementation, this would extract sources from the response
        return sources
    
    def validate_config(self) -> bool:
        """Validate the configuration for Qwen API"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("Qwen API key is not configured")
            return False
        
        return True
    
    def get_provider_type(self) -> AIProviderType:
        """Get the type of AI provider"""
        return AIProviderType.QWEN


class ErnieProvider(BaseAIProvider):
    """AI Provider for Ernie (Baidu) API"""
    
    def __init__(self, api_key: str, model_name: str = "ernie-bot-4.5", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        # Note: This is a placeholder - actual Ernie API details would be different
        self.base_url = kwargs.get('base_url', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)
        
        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
        """Query the Ernie API"""
        start_time = time.time()
        
        # For Baidu ERNIE, we need to get access token first
        access_token = await self._get_access_token()
        if not access_token:
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message="Failed to get access token",
                provider=self.provider_name,
                model=self.model_name
            )
        
        # Prepare the request payload
        payload = {
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }
        
        try:
            await self.initialize_session()
            
            async with self.session.post(
                f"{self.base_url}/wenxinworkshop/chat/{self.model_name}?access_token={access_token}",
                headers=self.headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                response_data = await response.json()
                
                if response.status == 200 and 'result' in response_data:
                    # Extract the content from the response
                    content = response_data['result']
                    
                    # Extract token usage if available
                    usage = response_data.get('usage', {})
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                    
                    # Extract sources (Baidu ERNIE might provide references)
                    sources = self._extract_sources_from_response(response_data)
                    
                    api_logger.info(f"Successfully received response from Ernie API for model: {self.model_name}")
                    
                    return StandardAIResponse(
                        content=content,
                        sources=sources,
                        usage={
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'total_tokens': total_tokens
                        },
                        latency=latency,
                        success=True,
                        provider=self.provider_name,
                        model=self.model_name,
                        metadata=response_data
                    )
                else:
                    # Handle API error
                    error_msg = response_data.get('error_msg', f'HTTP {response.status}')
                    api_logger.error(f"Ernie API error for model {self.model_name}: {error_msg}")
                    
                    return StandardAIResponse(
                        content="",
                        sources=[],
                        usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                        latency=latency,
                        success=False,
                        error_message=error_msg,
                        provider=self.provider_name,
                        model=self.model_name
                    )
        
        except asyncio.TimeoutError:
            api_logger.error(f"Timeout error when calling Ernie API for model: {self.model_name}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message="Request timed out",
                provider=self.provider_name,
                model=self.model_name
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Ernie API for model {self.model_name}: {str(e)}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message=str(e),
                provider=self.provider_name,
                model=self.model_name
            )
    
    async def _get_access_token(self) -> Optional[str]:
        """Get access token for Baidu ERNIE API"""
        # This is a placeholder implementation
        # In a real implementation, you would exchange API key/secret for access token
        return self.api_key  # Simplified for this example
    
    def _extract_sources_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """Extract sources from Ernie response (placeholder implementation)"""
        sources = []
        # In a real implementation, this would extract sources from the response
        # which might include references to Baidu Baike or other sources
        return sources
    
    def validate_config(self) -> bool:
        """Validate the configuration for Ernie API"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("Ernie API key is not configured")
            return False
        
        return True
    
    def get_provider_type(self) -> AIProviderType:
        """Get the type of AI provider"""
        return AIProviderType.WENXIN


class KimiProvider(BaseAIProvider):
    """AI Provider for Kimi (Moonshot) API"""
    
    def __init__(self, api_key: str, model_name: str = "moonshot-v1-8k", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        # Note: This is a placeholder - actual Kimi API details would be different
        self.base_url = kwargs.get('base_url', 'https://api.moonshot.cn/v1')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 1000)
        
        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
        """Query the Kimi API"""
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
            await self.initialize_session()
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",  # Placeholder URL
                headers=self.headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                response_data = await response.json()
                
                if response.status == 200:
                    # Extract the content from the response
                    content = response_data['choices'][0]['message']['content']
                    
                    # Extract token usage if available
                    usage = response_data.get('usage', {})
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                    
                    # Extract sources (Kimi might provide long context references)
                    sources = self._extract_sources_from_response(response_data)
                    
                    api_logger.info(f"Successfully received response from Kimi API for model: {self.model_name}")
                    
                    return StandardAIResponse(
                        content=content,
                        sources=sources,
                        usage={
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'total_tokens': total_tokens
                        },
                        latency=latency,
                        success=True,
                        provider=self.provider_name,
                        model=self.model_name,
                        metadata=response_data
                    )
                else:
                    # Handle API error
                    error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status}')
                    api_logger.error(f"Kimi API error for model {self.model_name}: {error_msg}")
                    
                    return StandardAIResponse(
                        content="",
                        sources=[],
                        usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                        latency=latency,
                        success=False,
                        error_message=error_msg,
                        provider=self.provider_name,
                        model=self.model_name
                    )
        
        except asyncio.TimeoutError:
            api_logger.error(f"Timeout error when calling Kimi API for model: {self.model_name}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message="Request timed out",
                provider=self.provider_name,
                model=self.model_name
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling Kimi API for model {self.model_name}: {str(e)}")
            return StandardAIResponse(
                content="",
                sources=[],
                usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                latency=time.time() - start_time,
                success=False,
                error_message=str(e),
                provider=self.provider_name,
                model=self.model_name
            )
    
    def _extract_sources_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """Extract sources from Kimi response (placeholder implementation)"""
        sources = []
        # In a real implementation, this would extract sources from the response
        # which might include long context references
        return sources
    
    def validate_config(self) -> bool:
        """Validate the configuration for Kimi API"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("Kimi API key is not configured")
            return False
        
        return True
    
    def get_provider_type(self) -> AIProviderType:
        """Get the type of AI provider"""
        return AIProviderType.KIMI