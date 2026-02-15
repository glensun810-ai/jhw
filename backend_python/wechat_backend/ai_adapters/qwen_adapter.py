import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager
from ...utils.ai_response_wrapper import log_detailed_response

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
        
        api_logger.info(f"QwenAdapter initialized for model: {model_name} with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Qwen API 发送请求
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
                        error_type=error_type.value if error_type else "UNKNOWN_ERROR",
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
                    error_type="REQUEST_EXCEPTION",
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log request exception to enhanced logger: {log_error}")
            
            record_error("qwen", "REQUEST_EXCEPTION", str(e))
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
                    error_type="UNEXPECTED_ERROR",
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log unexpected error to enhanced logger: {log_error}")
            
            record_error("qwen", "UNKNOWN_ERROR", str(e))
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
