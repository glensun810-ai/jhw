import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from ..config_manager import Config as PlatformConfigManager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.ai_response_wrapper import log_detailed_response

class GeminiAdapter(AIClient):
    """
    Google Gemini AI 平台的适配器 - 使用 REST API 避免 Python 版本兼容性问题
    """
    def __init__(self, api_key: str, model_name: str = "gemini-pro", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.GEMINI, model_name, api_key)

        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="gemini",
            base_url=base_url or f"https://generativelanguage.googleapis.com/v1beta/models",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )

        api_logger.info(f"GeminiAdapter initialized for model: {model_name} using REST API with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Gemini API 发送请求 - 使用 REST API
        """
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": kwargs.get('temperature', 0.7),
                "maxOutputTokens": kwargs.get('max_tokens', 2048)
            }
        }

        start_time = time.time()
        try:
            # 使用统一请求封装器发送请求
            url_suffix = f"/{self.model_name}:generateContent?key={self.api_key}"
            response = self.request_wrapper.make_ai_request(
                endpoint=url_suffix,
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            # 解析响应
            candidates = response_data.get("candidates", [])
            if candidates:
                content = candidates[0]["content"]["parts"][0]["text"]

                # 估算 token 数量
                tokens_used = len(prompt.split()) + len(content.split())

                api_logger.info(f"Gemini response success. Tokens: ~{tokens_used}, Latency: {latency:.2f}s")
                
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
                error_details = response_data.get("error", {})
                error_message = error_details.get("message", "Unknown Gemini API error")
                error_type = self._map_error_code(error_details.get("code", 0))

                api_logger.error(f"Gemini API returned no candidates: {error_message}")
                
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
            latency = time.time() - start_time
            error_message = f"Gemini API request failed: {e}"
            error_type = AIErrorType.UNKNOWN_ERROR

            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 400:
                    error_type = AIErrorType.CONTENT_SAFETY  # Often safety issues return 400
                elif status_code == 401 or status_code == 403:
                    error_type = AIErrorType.INVALID_API_KEY
                elif status_code == 429:
                    error_type = AIErrorType.INSUFFICIENT_QUOTA  # Quota issues often return 429
                elif status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR

            api_logger.error(error_message)
            
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
            
            record_error("gemini", error_type.value, str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )
        except Exception as e:
            latency = time.time() - start_time
            error_message = f"An unexpected error occurred with Gemini API: {e}"
            api_logger.error(error_message)
            
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
            
            record_error("gemini", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_error_code(self, error_code: int) -> AIErrorType:
        """将Gemini的错误码映射到标准错误类型"""
        if error_code == 3:  # Invalid argument (often means invalid API key)
            return AIErrorType.INVALID_API_KEY
        if error_code == 7:  # Permission denied
            return AIErrorType.INVALID_API_KEY
        if error_code == 8:  # Resource exhausted (quota)
            return AIErrorType.INSUFFICIENT_QUOTA
        if error_code == 10:  # Failed precondition (could be safety)
            return AIErrorType.CONTENT_SAFETY
        if error_code == 13:  # Internal server error
            return AIErrorType.SERVER_ERROR
        if error_code == 14:  # Service unavailable
            return AIErrorType.SERVER_ERROR
        return AIErrorType.UNKNOWN_ERROR
