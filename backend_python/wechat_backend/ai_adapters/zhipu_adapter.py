import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from ..config_manager import Config as PlatformConfigManager
from ..circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.ai_response_wrapper import log_detailed_response

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
        
        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(platform_name="zhipu", model_name=model_name)
        
        api_logger.info(f"ZhipuAdapter initialized for model: {model_name} with unified request wrapper and circuit breaker")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Zhipu API 发送请求
        """
        # 使用电路断路器保护API调用
        try:
            response = self.circuit_breaker.call(self._make_request_internal, prompt, **kwargs)
            return response
        except CircuitBreakerOpenError as e:
            error_message = f"Zhipu 服务暂时不可用（熔断器开启）: {e}"
            api_logger.warning(error_message)
            
            # Log failed response to enhanced logger with context
            try:
                execution_id = kwargs.get('execution_id', 'unknown')
                log_detailed_response(
                    question=prompt,  # 使用原始prompt
                    response="",  # No content in case of failure
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVICE_UNAVAILABLE,
                    latency_ms=0,  # No latency since no actual request was made
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log failed response to enhanced logger: {log_error}")
            
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.SERVICE_UNAVAILABLE,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=0.0
            )

    def _make_request_internal(self, prompt: str, **kwargs) -> AIResponse:
        """
        实际的API请求逻辑
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
                
                # Log response to enhanced logger with context
                try:
                    execution_id = kwargs.get('execution_id', 'unknown')
                    log_detailed_response(
                        question=prompt,
                        response=content,
                        platform=self.platform_type.value,
                        model=self.model_name,
                        success=True,
                        latency_ms=int(latency * 1000),  # Convert to milliseconds
                        tokens_used=tokens_used,
                        execution_id=execution_id,
                        **kwargs  # Pass any additional context from kwargs
                    )
                except Exception as log_error:
                    # Don't let logging errors affect the main response
                    api_logger.warning(f"Failed to log response to enhanced logger: {log_error}")
                
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
                
                # Log failed response to enhanced logger with context
                try:
                    execution_id = kwargs.get('execution_id', 'unknown')
                    log_detailed_response(
                        question=prompt,
                        response="",  # No content in case of failure
                        platform=self.platform_type.value,
                        model=self.model_name,
                        success=False,
                        error_message=error_message,
                        error_type=error_type if error_type else AIErrorType.UNKNOWN_ERROR,
                        latency_ms=int(latency * 1000),  # Convert to milliseconds
                        execution_id=execution_id,
                        **kwargs  # Pass any additional context from kwargs
                    )
                except Exception as log_error:
                    # Don't let logging errors affect the main response
                    api_logger.warning(f"Failed to log failed response to enhanced logger: {log_error}")
                
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

            # Log failed response to enhanced logger with context
            try:
                execution_id = kwargs.get('execution_id', 'unknown')
                log_detailed_response(
                    question=prompt,
                    response="",  # No content in case of failure
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=error_type if error_type else AIErrorType.REQUEST_EXCEPTION,
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log request exception to enhanced logger: {log_error}")

            # Re-raise the exception to trigger circuit breaker for connection-related errors
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                raise e

            record_error("zhipu", error_type, str(e))
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
            
            # Log failed response to enhanced logger with context
            try:
                execution_id = kwargs.get('execution_id', 'unknown')
                log_detailed_response(
                    question=prompt,
                    response="",  # No content in case of failure
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.UNEXPECTED_ERROR,
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log unexpected error to enhanced logger: {log_error}")
            
            # Re-raise the exception to trigger circuit breaker for critical errors
            if isinstance(e, (ConnectionError, TimeoutError)):
                raise e
            
            record_error("zhipu", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
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
