"""
DeepSeek AI Platform Adapter
Implements the AIClient interface for DeepSeek API
"""
import time
import requests
from typing import Dict, Any, Optional
from .base import AIClient, AIResponse, AIPlatformType
from ..logging_config import api_logger


class DeepSeekAdapter(AIClient):
    """
    Adapter for DeepSeek AI platform
    Implements the AIClient interface to provide standardized access to DeepSeek API
    """
    
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", **kwargs):
        """
        Initialize the DeepSeek adapter
        
        Args:
            api_key: DeepSeek API key
            model_name: Name of the DeepSeek model to use (default: deepseek-chat)
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model_name, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://api.deepseek.com/v1')
        self.timeout = kwargs.get('timeout', 30)
        
        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        Send a prompt to DeepSeek API and return a standardized response
        
        Args:
            prompt: The input prompt to send
            **kwargs: Additional parameters for the API call
            
        Returns:
            AIResponse: Standardized response object
        """
        start_time = time.time()
        
        # Prepare the request payload
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False  # For now, using non-streaming responses
        }
        
        # Add any additional parameters passed in kwargs
        temperature = kwargs.get('temperature')
        if temperature is not None:
            payload['temperature'] = temperature
            
        max_tokens = kwargs.get('max_tokens')
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        
        try:
            api_logger.info(f"Sending request to DeepSeek API for model: {self.model_name}")
            
            # Make the API request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            # Calculate latency
            latency = time.time() - start_time
            
            if response.status_code == 200:
                # Parse the response
                data = response.json()
                
                # Extract the content from the response
                content = data['choices'][0]['message']['content']
                
                # Extract token usage if available
                usage = data.get('usage', {})
                tokens_used = usage.get('total_tokens')
                prompt_tokens = usage.get('prompt_tokens')
                completion_tokens = usage.get('completion_tokens')
                
                api_logger.info(f"Successfully received response from DeepSeek API for model: {self.model_name}")
                
                return AIResponse(
                    content=content,
                    model=self.model_name,
                    platform=self.platform_name,
                    tokens_used=tokens_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=tokens_used,
                    latency=latency,
                    metadata=data,
                    success=True
                )
            else:
                # Handle API error
                error_data = response.json() if response.content else {'error': 'Unknown error'}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                
                api_logger.error(f"DeepSeek API error for model {self.model_name}: {error_msg}")
                
                return AIResponse(
                    content="",
                    model=self.model_name,
                    platform=self.platform_name,
                    latency=latency,
                    metadata=error_data,
                    success=False,
                    error_message=error_msg
                )
                
        except requests.exceptions.Timeout:
            api_logger.error(f"Timeout error when calling DeepSeek API for model: {self.model_name}")
            return AIResponse(
                content="",
                model=self.model_name,
                platform=self.platform_name,
                latency=latency,
                success=False,
                error_message="Request timed out"
            )
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Request error when calling DeepSeek API for model {self.model_name}: {str(e)}")
            return AIResponse(
                content="",
                model=self.model_name,
                platform=self.platform_name,
                latency=latency,
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            api_logger.error(f"Unexpected error when calling DeepSeek API for model {self.model_name}: {str(e)}")
            return AIResponse(
                content="",
                model=self.model_name,
                platform=self.platform_name,
                success=False,
                error_message=str(e)
            )
    
    def validate_config(self) -> bool:
        """
        Validate the configuration for DeepSeek API
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        if not self.api_key or len(self.api_key.strip()) == 0:
            api_logger.error("DeepSeek API key is not configured")
            return False
        
        # Test the API key by making a simple request
        try:
            test_payload = {
                'model': self.model_name,
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 5
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=test_payload,
                timeout=10
            )
            
            is_valid = response.status_code in [200, 400]  # 400 means API key is valid but request is bad
            if is_valid:
                api_logger.info("DeepSeek API configuration validated successfully")
            else:
                api_logger.error(f"DeepSeek API configuration validation failed with status: {response.status_code}")
            
            return is_valid
        except Exception as e:
            api_logger.error(f"Error validating DeepSeek API configuration: {str(e)}")
            return False
    
    def get_platform_type(self) -> AIPlatformType:
        """
        Get the type of AI platform this adapter supports
        
        Returns:
            AIPlatformType: The type of AI platform
        """
        return AIPlatformType.DEEPSEEK