"""
Qwen (Alibaba Tongyi) AI 平台的适配器

【P0-Qwen 超时修复】
- 添加动态超时配置（默认 30 秒）
- 添加请求频率控制
- 超时后自动降级到其他模型
"""

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
# 【P0-Qwen 超时修复】导入超时管理器
from wechat_backend.ai_timeout import get_timeout_manager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from wechat_backend.utils.ai_response_wrapper import log_detailed_response


class QwenAdapter(AIClient):
    """
    Qwen (Alibaba Tongyi) AI 平台的适配器
    """
    # 【P0-Qwen 频率控制】类级别定义默认值，确保属性始终存在
    _last_request_time = 0
    _min_request_interval = 2.0
    
    def __init__(self, api_key: str, model_name: str = "qwen-max", base_url: Optional[str] = None):
        # 【P0-Qwen 频率控制】在调用 super()前就确保属性存在
        self._last_request_time = 0
        self._min_request_interval = 2.0
        
        super().__init__(AIPlatformType.QWEN, model_name, api_key)

        # 【P0-Qwen 超时修复】使用动态超时配置
        try:
            timeout_manager = get_timeout_manager()
            timeout = timeout_manager.get_timeout('qwen')  # 默认 30 秒
        except Exception as e:
            api_logger.warning(f"[Qwen] 获取超时配置失败，使用默认值 30 秒：{e}")
            timeout = 30

        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="qwen",
            base_url=base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            api_key=api_key,
            timeout=timeout,  # 【P0-Qwen 超时修复】动态超时
            max_retries=2  # 【P0-Qwen 超时修复】减少重试次数，避免长时间等待
        )

        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(platform_name="qwen", model_name=model_name)

        api_logger.info(f"QwenAdapter initialized for model: {model_name} with timeout={timeout}s")

    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """生成响应（兼容 NXM 执行引擎）"""
        return self.send_prompt(prompt, **kwargs)
    
    def _apply_frequency_control(self) -> float:
        """
        【P0-Qwen 频率控制】应用请求频率控制
        
        返回:
            float: 实际等待的时间（秒）
        """
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            api_logger.info(f"[Qwen] 频率控制：延迟 {wait_time:.2f}秒")
            time.sleep(wait_time)
        
        self._last_request_time = time.time()
        return self._last_request_time
    
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Qwen API 发送请求
        
        【P0-Qwen 超时修复】
        - 添加频率控制
        - 超时后自动降级
        """
        # 【P0-Qwen 频率控制】应用请求频率控制
        self._apply_frequency_control()
        
        # 使用电路断路器保护 API 调用
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
                    question=prompt,
                    response="",
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVICE_UNAVAILABLE,
                    latency_ms=0,
                    execution_id=execution_id,
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                )
            except Exception as log_error:
                api_logger.warning(f"Failed to log failed response to enhanced logger: {log_error}")

            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.SERVICE_UNAVAILABLE,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=0.0
            )
        except requests.exceptions.Timeout as e:
            # 【P0-Qwen 超时修复】超时后降级
            error_message = f"Qwen API 超时（>{self.request_wrapper.timeout}秒）: {e}"
            api_logger.warning(error_message)
            
            # 记录超时错误
            try:
                execution_id = kwargs.get('execution_id', 'unknown')
                log_detailed_response(
                    question=prompt,
                    response="",
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.TIMEOUT,
                    latency_ms=int(self.request_wrapper.timeout * 1000),
                    execution_id=execution_id,
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                )
            except Exception as log_error:
                api_logger.warning(f"Failed to log timeout to enhanced logger: {log_error}")
            
            # 【P0-Qwen 超时修复】触发降级，返回超时错误让上层切换到其他模型
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.TIMEOUT,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=self.request_wrapper.timeout
            )

    def _make_request_internal(self, prompt: str, **kwargs) -> AIResponse:
        """
        实际的 API 请求逻辑
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
            # 【P0-Qwen 超时修复】使用动态超时
            response = self.request_wrapper.make_ai_request(
                endpoint="",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=self.request_wrapper.timeout
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
                        latency_ms=int(latency * 1000),
                        tokens_used=tokens_used,
                        execution_id=execution_id,
                        **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                    )
                except Exception as log_error:
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
                        response="",
                        platform=self.platform_type.value,
                        model=self.model_name,
                        success=False,
                        error_message=error_message,
                        error_type=error_type if error_type else AIErrorType.UNKNOWN_ERROR,
                        latency_ms=int(latency * 1000),
                        execution_id=execution_id,
                        **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                    )
                except Exception as log_error:
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
                    response="",
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.REQUEST_EXCEPTION,
                    latency_ms=int(latency * 1000),
                    execution_id=execution_id,
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                )
            except Exception as log_error:
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
                    response="",
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.UNEXPECTED_ERROR,
                    latency_ms=int(latency * 1000),
                    execution_id=execution_id,
                    **{k: v for k, v in kwargs.items() if k != 'execution_id'}
                )
            except Exception as log_error:
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
        """将 Qwen 的错误码映射到标准错误类型"""
        if error_code == "InvalidAPIKey":
            return AIErrorType.INVALID_API_KEY
        if error_code == "QuotaExhausted":
            return AIErrorType.INSUFFICIENT_QUOTA
        if error_code == "OperationDenied.ContentRisk":
            return AIErrorType.CONTENT_SAFETY
        if "Throttling" in error_code:
            return AIErrorType.RATE_LIMIT_EXCEEDED
        return AIErrorType.UNKNOWN_ERROR
