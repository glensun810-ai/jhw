import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager

class ZhipuAdapter(AIClient):
    """
    Zhipu AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "glm-4", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.ZHIPU, model_name, api_key)
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="zhipu",
            base_url=base_url or "https://open.bigmodel.cn/api/paas/v4",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"ZhipuAdapter initialized for model: {model_name} with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Zhipu API 发送请求
        """
        messages = [{"role": "user", "content": prompt}]

        platform_config_manager = PlatformConfigManager()
        zhipu_config = platform_config_manager.get_platform_config('zhipu')

        temperature = kwargs.get('temperature', zhipu_config.default_temperature if zhipu_config else 0.7)
        max_tokens = kwargs.get('max_tokens', zhipu_config.default_max_tokens if zhipu_config else 1000)
        timeout = kwargs.get('timeout', zhipu_config.timeout if zhipu_config else 30)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()
        try:
            # 使用统一请求封装器发送请求
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=timeout
            )

            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            if response_data and response_data.get("choices"):
                content = response_data["choices"][0]["message"]["content"]
                tokens_used = response_data["usage"]["total_tokens"] if response_data.get("usage") else 0
                api_logger.info(f"Zhipu response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
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
                error_message = response_data.get("error", {}).get("message", "Unknown Zhipu API error")
                error_type = self._map_error_message(error_message)
                api_logger.error(f"Zhipu API returned no choices: {error_message}")
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=error_type,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            error_message = f"Zhipu API request failed: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            error_type = AIErrorType.UNKNOWN_ERROR
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    error_type = AIErrorType.INVALID_API_KEY
                elif status_code == 429:
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED
                elif status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR

            record_error("zhipu", error_type.value, str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with Zhipu API: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            record_error("zhipu", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self_model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_error_message(self, error_message: str) -> AIErrorType:
        """将Zhipu的错误信息映射到标准错误类型"""
        error_message_lower = error_message.lower()
        if "invalid api" in error_message_lower:
            return AIErrorType.INVALID_API_KEY
        if "quota" in error_message_lower or "balance" in error_message_lower:
            return AIErrorType.INSUFFICIENT_QUOTA
        if "content" in error_message_lower and "policy" in error_message_lower:
            return AIErrorType.CONTENT_SAFETY
        return AIErrorType.UNKNOWN_ERROR
