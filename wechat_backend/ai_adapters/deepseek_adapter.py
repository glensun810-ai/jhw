import requests
import time
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType # 引入 AIErrorType
from config_manager import Config as PlatformConfigManager

class DeepSeekAdapter(AIClient):
    """
    DeepSeek AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.DEEPSEEK, model_name, api_key)
        self.base_url = base_url or "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        api_logger.info(f"DeepSeekAdapter initialized for model: {model_name}")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 DeepSeek API 发送请求
        """
        messages = [{"role": "user", "content": prompt}]
        
        platform_config_manager = PlatformConfigManager()
        deepseek_config = platform_config_manager.get_platform_config('deepseek')
        
        temperature = kwargs.get('temperature', deepseek_config.default_temperature if deepseek_config else 0.7)
        max_tokens = kwargs.get('max_tokens', deepseek_config.default_max_tokens if deepseek_config else 1000)
        timeout = kwargs.get('timeout', deepseek_config.timeout if deepseek_config else 30)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        start_time = time.time()
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=timeout)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            response_data = response.json()
            
            latency = time.time() - start_time
            
            if response_data and response_data.get("choices"):
                content = response_data["choices"][0]["message"]["content"]
                tokens_used = response_data["usage"]["total_tokens"]
                api_logger.info(f"DeepSeek response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=tokens_used,
                    latency=latency,
                    metadata=response_data
                )
            else:
                error_message = response_data.get("error", {}).get("message", "Unknown DeepSeek API error")
                error_type = AIErrorType.UNKNOWN_ERROR # 默认错误类型
                if "invalid_api_key" in error_message.lower():
                    error_type = AIErrorType.INVALID_API_KEY
                elif "rate limit" in error_message.lower():
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED

                api_logger.error(f"DeepSeek API returned no choices: {error_message}")
                return AIResponse(success=False, error_message=error_message, error_type=error_type, model=self.model_name, platform=self.platform_type.value, latency=latency)

        except requests.exceptions.RequestException as e:
            error_message = f"DeepSeek API request failed: {e}"
            error_type = AIErrorType.UNKNOWN_ERROR
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code == 401:
                    error_type = AIErrorType.INVALID_API_KEY
                elif e.response.status_code == 429:
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED

            api_logger.error(error_message)
            return AIResponse(success=False, error_message=error_message, error_type=error_type, model=self.model_name, platform=self.platform_type.value, latency=time.time() - start_time)
        except Exception as e:
            error_message = f"An unexpected error occurred with DeepSeek API: {e}"
            api_logger.error(error_message)
            return AIResponse(success=False, error_message=error_message, error_type=AIErrorType.UNKNOWN_ERROR, model=self.model_name, platform=self.platform_type.value, latency=time.time() - start_time)
