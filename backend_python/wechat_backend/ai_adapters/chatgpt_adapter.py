import time
import requests
from typing import Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.monitoring.metrics_collector import record_api_call, record_error
from wechat_backend.monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from wechat_backend.utils.ai_response_wrapper import log_detailed_response

class ChatGPTAdapter(AIClient):
    """
    ChatGPT (OpenAI) AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.CHATGPT, model_name, api_key)
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="chatgpt",
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"ChatGPTAdapter initialized for model: {model_name} with unified request wrapper")

    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """生成响应（兼容 NXM 执行引擎）"""
        return self.send_prompt(prompt, **kwargs)
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 ChatGPT API 发送请求
        """
        messages = [{"role": "user", "content": prompt}]

        platform_config_manager = PlatformConfigManager()
        chatgpt_config = platform_config_manager.get_platform_config('chatgpt')

        temperature = kwargs.get('temperature', chatgpt_config.default_temperature if chatgpt_config else 0.7)
        max_tokens = kwargs.get('max_tokens', chatgpt_config.default_max_tokens if chatgpt_config else 1000)
        timeout = kwargs.get('timeout', chatgpt_config.timeout if chatgpt_config else 30)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
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
                api_logger.info(f"ChatGPT response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
                
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
                error_message = response_data.get("error", {}).get("message", "Unknown ChatGPT API error")
                error_type = self._map_error_message(error_message)
                api_logger.error(f"ChatGPT API returned no choices: {error_message}")
                
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
            error_message = f"ChatGPT API request failed: {e}"
            error_type = AIErrorType.UNKNOWN_ERROR
            latency = time.time() - start_time
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    error_type = AIErrorType.INVALID_API_KEY
                elif status_code == 429:
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED
                elif status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR
                elif status_code == 403:
                    error_type = AIErrorType.INVALID_API_KEY

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
            
            record_error("chatgpt", error_type.value, str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=error_type, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with ChatGPT API: {e}"
            latency = time.time() - start_time
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
            
            record_error("chatgpt", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=AIErrorType.UNKNOWN_ERROR, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )

    def _map_error_message(self, error_message: str) -> AIErrorType:
        """将ChatGPT的错误信息映射到标准错误类型"""
        error_message_lower = error_message.lower()
        if "incorrect api key" in error_message_lower:
            return AIErrorType.INVALID_API_KEY
        if "quota" in error_message_lower:
            return AIErrorType.INSUFFICIENT_QUOTA
        if "content policy" in error_message_lower:
            return AIErrorType.CONTENT_SAFETY
        return AIErrorType.UNKNOWN_ERROR
