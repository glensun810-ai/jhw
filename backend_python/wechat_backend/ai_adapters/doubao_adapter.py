import os
import time
import requests
import statistics
from typing import Optional
from requests.adapters import HTTPAdapter
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager
from ..circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.debug_manager import ai_io_log, exception_log, debug_log

# Import the new DEBUG_AI_CODE logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from backend_python.utils.logger import debug_log_ai_io, debug_log_exception, ENABLE_DEBUG_AI_CODE

# Import the enhanced AI response logger
from ...utils.ai_response_wrapper import log_detailed_response


class DoubaoAdapter(AIClient):
    """
    Doubao AI 平台的适配器，带有健康检查和连接池功能
    """
    def __init__(self, api_key: str, model_name: str = None, base_url: Optional[str] = None):
        # 从配置管理器获取默认模型ID，如果没有传入则使用默认值
        if model_name is None:
            platform_config_manager = PlatformConfigManager()
            doubao_config = platform_config_manager.get_platform_config('doubao')
            if doubao_config and hasattr(doubao_config, 'default_model'):
                model_name = doubao_config.default_model
            else:
                model_name = os.getenv('DOUBAO_MODEL_ID', 'Doubao-pro')  # 使用通用模型名作为默认值

        super().__init__(AIPlatformType.DOUBAO, model_name, api_key)

        # 创建连接池以复用HTTP连接
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,      # 连接池大小
            pool_maxsize=20,         # 最大连接数
            max_retries=0,           # 重试由断路器控制
            pool_block=True          # 池满时阻塞
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

        # 初始化延迟统计
        self.latency_history = []

        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(platform_name="doubao", model_name=model_name)

        debug_log("AI_ADAPTER_INIT", f"DoubaoAdapter initialized for model: {model_name} with connection pooling and circuit breaker")

        # 执行健康检查
        self._health_check()

    def _health_check(self):
        """启动时验证API连通性"""
        try:
            # 发送一个极简请求，token计数为1
            minimal_prompt = "ping"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": minimal_prompt}],
                "max_tokens": 1  # 只生成1个token，快速响应
            }

            debug_log("HEALTH_CHECK", f"Performing health check for Doubao API with model: {self.model_name}")

            start = time.time()
            response = self.session.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers=headers,
                json=payload,
                timeout=30  # 偞康检查超时增加到30秒
            )
            latency = time.time() - start

            if response.status_code == 200:
                debug_log("HEALTH_CHECK", f"Doubao health check passed, latency: {latency:.2f}s")
            else:
                exception_log(f"Doubao health check failed: {response.status_code}, response: {response.text[:200]}...")
        except Exception as e:
            exception_log(f"Doubao health check failed: {e}")
            # 不抛出异常，只是记录警告
            debug_log("HEALTH_CHECK", "Doubao service may be unavailable at startup")

    def _get_headers(self):
        """统一管理请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Doubao API 发送请求 (带熔断保护和延迟统计)
        """
        # Extract execution_id from kwargs if available for DEBUG_AI_CODE logging
        execution_id = kwargs.get('execution_id', 'unknown')

        # Log AI I/O with DEBUG_AI_CODE logging
        if ENABLE_DEBUG_AI_CODE:
            debug_log_ai_io("DOUBAO_ADAPTER", execution_id, prompt[:50] + "...", "AI processing request") # #DEBUG_CLEAN

        # Also keep the original debug logging
        ai_io_log(f"Sending prompt to Doubao API. Prompt preview: {prompt[:50]}...")

        # 使用电路断路器保护API调用
        try:
            response = self.circuit_breaker.call(self._make_request_internal, prompt, **kwargs)
            ai_io_log(f"Doubao API response received. Response preview: {response.content[:100] if response.content else 'None'}")

            # Log the response with DEBUG_AI_CODE logging
            if ENABLE_DEBUG_AI_CODE:
                response_preview = response.content[:100] if response.content else 'None'
                debug_log_ai_io("DOUBAO_ADAPTER", execution_id, prompt[:50] + "...", response_preview) # #DEBUG_CLEAN

            return response
        except CircuitBreakerOpenError as e:
            exception_log(f"Doubao API 熔断中: {e}")

            # Log exception with DEBUG_AI_CODE logging
            if ENABLE_DEBUG_AI_CODE:
                import traceback
                error_msg = f"CircuitBreakerOpenError: {str(e)}\n{traceback.format_exc()}"
                debug_log_exception("DOUBAO_ADAPTER", execution_id, error_msg) # #DEBUG_CLEAN

            # 返回一个响应表示服务暂时不可用
            return AIResponse(
                success=False,
                error_message="Doubao 服务暂时不可用，请稍后重试",
                error_type=AIErrorType.SERVICE_UNAVAILABLE,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=0.0
            )

    def _make_request_internal(self, prompt: str, **kwargs) -> AIResponse:
        """
        实际的API请求逻辑
        """
        # Extract execution_id from kwargs for DEBUG_AI_CODE logging
        execution_id = kwargs.get('execution_id', 'unknown')

        messages = [{"role": "user", "content": prompt}]

        platform_config_manager = PlatformConfigManager()
        doubao_config = platform_config_manager.get_platform_config('doubao')

        temperature = kwargs.get('temperature', doubao_config.default_temperature if doubao_config else 0.7)
        max_tokens = kwargs.get('max_tokens', doubao_config.default_max_tokens if doubao_config else 1000)
        timeout = kwargs.get('timeout', doubao_config.timeout if doubao_config else 60)

        # Prepare payload for Doubao API
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()
        try:
            # 使用会话发送请求以复用连接
            debug_log("AI_IO", f"Making request to Doubao API with payload: {payload}")

            # Log with DEBUG_AI_CODE system
            if ENABLE_DEBUG_AI_CODE:
                debug_log_ai_io("DOUBAO_ADAPTER_INTERNAL", execution_id, str(payload)[:100], "Sending request to API") # #DEBUG_CLEAN

            response = self.session.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=timeout
            )

            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            # 记录延迟历史
            self.latency_history.append(latency)
            if len(self.latency_history) > 20:
                self.latency_history.pop(0)

            # 计算p95延迟
            if len(self.latency_history) >= 10:
                sorted_latencies = sorted(self.latency_history)
                p95_idx = int(len(sorted_latencies) * 0.95)
                if p95_idx >= len(sorted_latencies):
                    p95_idx = len(sorted_latencies) - 1
                p95 = sorted_latencies[p95_idx]
                debug_log("AI_IO", f"Doubao latency stats - current: {latency:.2f}s, p95: {p95:.2f}s")
            else:
                debug_log("AI_IO", f"Doubao response success. Latency: {latency:.2f}s")

            # Attempt to extract content - try multiple possible response structures
            content = None
            tokens_used = 0

            # Try standard OpenAI format first
            if response_data and "choices" in response_data and len(response_data["choices"]) > 0:
                if "message" in response_data["choices"][0]:
                    content = response_data["choices"][0]["message"]["content"]
                elif "delta" in response_data["choices"][0]:
                    # Handle streaming response format
                    content = response_data["choices"][0]["delta"].get("content", "")

                tokens_used = response_data.get("usage", {}).get("total_tokens", 0)
            # Try alternative formats
            elif "result" in response_data:
                content = response_data["result"]
            elif "response" in response_data:
                content = response_data["response"]
            elif "data" in response_data and isinstance(response_data["data"], str):
                content = response_data["data"]
            elif "content" in response_data:
                content = response_data["content"]

            if content is not None:
                debug_log("AI_IO", f"Doubao API response processed successfully. Content preview: {content[:100]}")

                # Log with DEBUG_AI_CODE system
                if ENABLE_DEBUG_AI_CODE:
                    debug_log_ai_io("DOUBAO_ADAPTER_INTERNAL", execution_id, str(payload)[:100], content[:100]) # #DEBUG_CLEAN

                # Log response to enhanced logger with context
                try:
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
                error_message = response_data.get("error", {}).get("message", "Unknown Doubao API error") or str(response_data)
                error_type = self._map_error_message(error_message)

                # Log with DEBUG_AI_CODE system for errors
                if ENABLE_DEBUG_AI_CODE:
                    debug_log_exception("DOUBAO_ADAPTER_INTERNAL", execution_id, f"Doubao API returned no content: {error_message}") # #DEBUG_CLEAN

                # Log failed response to enhanced logger with context
                try:
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

                exception_log(f"Doubao API returned no content: {error_message}")
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=error_type,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            # This catches all requests-related exceptions including timeouts
            error_message = f"Doubao API request failed: {e}"
            exception_log(error_message)
            latency = time.time() - start_time

            # Log exception with DEBUG_AI_CODE system
            if ENABLE_DEBUG_AI_CODE:
                import traceback
                error_msg = f"requests.exceptions.RequestException: {str(e)}\n{traceback.format_exc()}"
                debug_log_exception("DOUBAO_ADAPTER_INTERNAL", execution_id, error_msg) # #DEBUG_CLEAN

            # Log failed response to enhanced logger with context
            try:
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

            # Check if this is a timeout or connection error that should trigger circuit breaker
            should_propagate = isinstance(e, (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectTimeout,
                ConnectionError,
                TimeoutError
            ))

            if should_propagate:
                # This is an exception that should trigger the circuit breaker
                # So we re-raise it to be caught by the circuit breaker's call method
                debug_log("EXCEPTION", f"Propagating exception to circuit breaker: {type(e).__name__}")
                raise e
            else:
                # This is an HTTP error that shouldn't trigger circuit breaker (e.g., 401, 429, 500)
                error_type = AIErrorType.UNKNOWN_ERROR
                if isinstance(e, requests.exceptions.HTTPError):
                    if e.response is not None:
                        status_code = e.response.status_code
                        if status_code == 401:
                            error_type = AIErrorType.INVALID_API_KEY
                        elif status_code == 404:
                            # 404错误通常表示API端点不存在或API密钥错误
                            error_type = AIErrorType.INVALID_API_KEY
                            error_message = f"Doubao API endpoint not found (404). Check API endpoint and credentials: {e.response.text}"

                            # Log 404 error with DEBUG_AI_CODE system
                            if ENABLE_DEBUG_AI_CODE:
                                debug_log_exception("DOUBAO_ADAPTER_INTERNAL", execution_id, f"Doubao 404 Error: {e.response.text}") # #DEBUG_CLEAN

                            # Log 404 error to enhanced logger
                            try:
                                log_detailed_response(
                                    question=prompt,
                                    response="",  # No content in case of failure
                                    platform=self.platform_type.value,
                                    model=self.model_name,
                                    success=False,
                                    error_message=error_message,
                                    error_type=error_type.value,
                                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                                    execution_id=execution_id,
                                    **kwargs  # Pass any additional context from kwargs
                                )
                            except Exception as log_error:
                                # Don't let logging errors affect the main response
                                api_logger.warning(f"Failed to log 404 error to enhanced logger: {log_error}")

                            exception_log(f"Doubao 404 Error - This usually indicates an incorrect API key or endpoint: {e.response.text}")
                        elif status_code == 429:
                            error_type = AIErrorType.RATE_LIMIT_EXCEEDED
                        elif status_code >= 500:
                            error_type = AIErrorType.SERVER_ERROR
                        else:
                            error_message = f"Doubao API HTTP {status_code}: {e.response.text}"

                record_error("doubao", error_type.value, str(e))
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=error_type,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )
        except Exception as e:
            error_message = f"An unexpected error occurred with Doubao API: {e}"
            exception_log(error_message)
            latency = time.time() - start_time

            # Log exception with DEBUG_AI_CODE system
            if ENABLE_DEBUG_AI_CODE:
                import traceback
                error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
                debug_log_exception("DOUBAO_ADAPTER_INTERNAL", execution_id, error_msg) # #DEBUG_CLEAN

            # Log failed response to enhanced logger with context
            try:
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

            # For non-requests exceptions, check if it's a timeout-related error
            should_propagate = isinstance(e, (ConnectionError, TimeoutError))

            if should_propagate:
                debug_log("EXCEPTION", f"Propagating exception to circuit breaker: {type(e).__name__}")
                raise e
            else:
                record_error("doubao", "UNKNOWN_ERROR", str(e))
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.UNKNOWN_ERROR,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

    def _map_error_message(self, error_message: str) -> AIErrorType:
        """将Doubao的错误信息映射到标准错误类型"""
        error_message_lower = error_message.lower()
        if "invalid api" in error_message_lower or "authentication" in error_message_lower or "unauthorized" in error_message_lower or "api key" in error_message_lower:
            return AIErrorType.INVALID_API_KEY
        if "quota" in error_message_lower or "credit" in error_message_lower or "exceeded" in error_message_lower:
            return AIErrorType.INSUFFICIENT_QUOTA
        if "content" in error_message_lower and ("policy" in error_message_lower or "safety" in error_message_lower):
            return AIErrorType.CONTENT_SAFETY
        if "safety" in error_message_lower or "policy" in error_message_lower:
            return AIErrorType.CONTENT_SAFETY
        if "rate limit" in error_message_lower or "too many requests" in error_message_lower:
            return AIErrorType.RATE_LIMIT_EXCEEDED
        if "not found" in error_message_lower or "404" in error_message_lower:
            return AIErrorType.INVALID_API_KEY  # 404通常意味着API密钥或端点错误
        return AIErrorType.UNKNOWN_ERROR

    def get_latency_stats(self) -> dict:
        """获取延迟统计信息"""
        if not self.latency_history:
            return {
                'avg_latency': 0,
                'min_latency': 0,
                'max_latency': 0,
                'p95_latency': 0,
                'sample_size': 0
            }
        
        return {
            'avg_latency': statistics.mean(self.latency_history),
            'min_latency': min(self.latency_history),
            'max_latency': max(self.latency_history),
            'p95_latency': statistics.quantiles(self.latency_history, n=20)[-1] if len(self.latency_history) >= 10 else 0,
            'sample_size': len(self.latency_history)
        }

    def __del__(self):
        """清理会话连接"""
        if hasattr(self, 'session'):
            self.session.close()
            api_logger.info("DoubaoAdapter session closed")