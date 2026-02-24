import time
import requests
from typing import Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from wechat_backend.monitoring.metrics_collector import record_api_call, record_error
from wechat_backend.monitoring.logging_enhancements import log_api_request, log_api_response
from wechat_backend.config_manager import ConfigurationManager as PlatformConfigManager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from wechat_backend.utils.ai_response_wrapper import log_detailed_response


class QwenAdapter(AIClient):
    """
    Qwen (Alibaba Tongyi) AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "qwen-max", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.QWEN, model_name, api_key)
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="qwen",
            base_url=base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(platform_name="qwen", model_name=model_name)
        
        api_logger.info(f"QwenAdapter initialized for model: {model_name} with unified request wrapper and circuit breaker")

    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """生成响应（兼容 NXM 执行引擎）"""
        return self.send_prompt(prompt, **kwargs)
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Qwen API 发送请求
        """
        # 使用电路断路器保护API调用
        try:
            response = self.circuit_breaker.call(self._make_request_internal, prompt, **kwargs)
            return response
        except CircuitBreakerOpenError as e:
            error_message = f"Qwen 服务暂时不可用（熔断器开启）: {e}"
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
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
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
        qwen_config = platform_config_manager.get_platform_config('qwen')

        temperature = kwargs.get('temperature', qwen_config.default_temperature if qwen_config else 0.7)

        payload = {
            "model": self.model_name,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": temperature,
            }
        }

        start_time = time.time()
        try:
            # 使用统一请求封装器发送请求
            response = self.request_wrapper.make_ai_request(
                endpoint="",  # Qwen API endpoint is specified in base_url
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            if response_data and response_data.get("output"):
                content = response_data["output"]["text"]
                tokens_used = response_data["usage"]["total_tokens"] if response_data.get("usage") else 0
                api_logger.info(f"Qwen response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
                
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
                        # 避免重复传递 execution_id
                        **{k: v for k, v in kwargs.items() if k != 'execution_id'}
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
                error_code = response_data.get("code", "")
                error_message = response_data.get("message", "Unknown Qwen API error")
                error_type = self._map_error_code(error_code)

                api_logger.error(f"Qwen API returned no output: {error_code} - {error_message}")
                
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
                        **{k: v for k, v in kwargs.items() if k != 'execution_id'}
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
            error_message = f"Qwen API request failed: {e}"
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
                    error_type=AIErrorType.REQUEST_EXCEPTION,
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log request exception to enhanced logger: {log_error}")

            record_error("qwen", "REQUEST_EXCEPTION", str(e))

            # Re-raise the exception to trigger circuit breaker for connection-related errors
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                raise e

            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with Qwen API: {e}"
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
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log unexpected error to enhanced logger: {log_error}")

            record_error("qwen", "UNKNOWN_ERROR", str(e))

            # Re-raise the exception to trigger circuit breaker for critical errors
            if isinstance(e, (ConnectionError, TimeoutError)):
                raise e

            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_error_code(self, error_code: str) -> AIErrorType:
        """将Qwen的错误码映射到标准错误类型"""
        if error_code == "InvalidAPIKey":
            return AIErrorType.INVALID_API_KEY
        if error_code == "QuotaExhausted":
            return AIErrorType.INSUFFICIENT_QUOTA
        if error_code == "OperationDenied.ContentRisk":
            return AIErrorType.CONTENT_SAFETY
        if "Throttling" in error_code:
            return AIErrorType.RATE_LIMIT_EXCEEDED
        return AIErrorType.UNKNOWN_ERROR