import requests
import time
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from config_manager import Config as PlatformConfigManager

class ZhipuAdapter(AIClient):
    """
    Zhipu AI (ChatGLM) 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "glm-4", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.ZHIPU, model_name, api_key)
        # 智谱AI v4 API 地址
        self.base_url = base_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        api_logger.info(f"ZhipuAdapter initialized for model: {model_name}")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Zhipu AI API 发送请求
        """
        messages = [{"role": "user", "content": prompt}]
        
        platform_config_manager = PlatformConfigManager()
        zhipu_config = platform_config_manager.get_platform_config('zhipu')
        
        temperature = kwargs.get('temperature', zhipu_config.default_temperature if zhipu_config else 0.7)
        # 智谱通常支持较大的 max_tokens，这里设个默认值
        max_tokens = kwargs.get('max_tokens', zhipu_config.default_max_tokens if zhipu_config else 2048)
        timeout = kwargs.get('timeout', zhipu_config.timeout if zhipu_config else 60)

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
            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time
            
            if response_data and response_data.get("choices"):
                content = response_data["choices"][0]["message"]["content"]
                usage = response_data.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)
                
                api_logger.info(f"Zhipu AI response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
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
                error_message = response_data.get("error", {}).get("message", "Unknown Zhipu AI error")
                error_type = self._map_error_message(error_message)
                api_logger.error(f"Zhipu AI API returned no choices: {error_message}")
                return AIResponse(success=False, error_message=error_message, error_type=error_type, model=self.model_name, platform=self.platform_type.value, latency=latency)

        except requests.exceptions.RequestException as e:
            error_message = f"Zhipu AI API request failed: {e}"
            error_type = AIErrorType.UNKNOWN_ERROR
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code == 401:
                    error_type = AIErrorType.INVALID_API_KEY
                elif e.response.status_code == 429:
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED
                elif e.response.status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR

            api_logger.error(error_message)
            return AIResponse(success=False, error_message=error_message, error_type=error_type, model=self.model_name, platform=self.platform_type.value, latency=time.time() - start_time)
        except Exception as e:
            error_message = f"An unexpected error occurred with Zhipu AI API: {e}"
            api_logger.error(error_message)
            return AIResponse(success=False, error_message=error_message, error_type=AIErrorType.UNKNOWN_ERROR, model=self.model_name, platform=self.platform_type.value, latency=time.time() - start_time)

    def _map_error_message(self, error_message: str) -> AIErrorType:
        """将智谱AI的错误信息映射到标准错误类型"""
        error_message_lower = error_message.lower()
        if "invalid api key" in error_message_lower or "authentication failed" in error_message_lower:
            return AIErrorType.INVALID_API_KEY
        if "balance" in error_message_lower or "quota" in error_message_lower:
            return AIErrorType.INSUFFICIENT_QUOTA
        if "sensitive" in error_message_lower or "content" in error_message_lower:
            return AIErrorType.CONTENT_SAFETY
        return AIErrorType.UNKNOWN_ERROR
