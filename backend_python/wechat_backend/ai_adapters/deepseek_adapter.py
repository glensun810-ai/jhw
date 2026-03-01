import time
import requests
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from wechat_backend.utils.ai_response_wrapper import log_detailed_response

# Flask context handling for async logging
try:
    from flask import current_app
    _FLASK_AVAILABLE = True
except ImportError:
    _FLASK_AVAILABLE = False
    current_app = None


class DeepSeekAdapter(AIClient):
    """
    DeepSeek AI 平台适配器
    用于将 DeepSeek API 接入 GEO 内容质量验证系统
    支持两种模式：普通对话模式（deepseek-chat）和搜索/推理模式（deepseek-reasoner）
    包含内部 Prompt 约束逻辑，可配置是否启用中文回答及事实性约束
    """

    def _safe_log_response(self, **log_kwargs):
        """
        安全地记录日志，处理 Flask 应用上下文

        在异步调用或后台任务中，Flask 的 g 对象和 request 上下文可能不可用，
        需要显式创建应用上下文来访问 current_app

        Args:
            **log_kwargs: 传递给 log_detailed_response 的参数
        """
        try:
            if _FLASK_AVAILABLE and current_app is not None:
                # 检查是否已经在应用上下文中
                try:
                    # 如果已经在上下文中，直接记录
                    _ = current_app.name
                    log_detailed_response(**log_kwargs)
                except RuntimeError:
                    # Working outside of application context, create one
                    with current_app.app_context():
                        log_detailed_response(**log_kwargs)
            else:
                # Flask 不可用，直接记录（会降级为匿名日志）
                log_detailed_response(**log_kwargs)
        except Exception as log_error:
            # 不要让日志错误影响主流程
            api_logger.warning(f"Failed to log response: {log_error}")

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.deepseek.com/v1",
        enable_chinese_constraint: bool = True  # 新增参数：是否启用中文约束
    ):
        """
        初始化 DeepSeek 适配器

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-chat"
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示搜索/推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_chinese_constraint: 是否启用中文回答约束，默认为 True
        """
        super().__init__(AIPlatformType.DEEPSEEK, model_name, api_key)
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_chinese_constraint = enable_chinese_constraint  # 存储中文约束开关

        # 初始化统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="deepseek",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )

        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(platform_name="deepseek", model_name=model_name)

        api_logger.info(f"DeepSeekAdapter initialized for model: {model_name} with unified request wrapper and circuit breaker")

    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """生成响应（兼容 NXM 执行引擎）"""
        return self.send_prompt(prompt, **kwargs)
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示到 DeepSeek 并返回标准化响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含 DeepSeek 响应的统一数据结构
        """
        # 记录请求开始时间以计算延迟
        start_time = time.time()

        # 使用电路断路器保护 API 调用
        try:
            response = self.circuit_breaker.call(self._make_request_internal, prompt, **kwargs)
            return response
        except CircuitBreakerOpenError as e:
            error_message = f"DeepSeek 服务暂时不可用（熔断器开启）: {e}"
            api_logger.warning(error_message)

            # Log failed response to enhanced logger with context
            execution_id = kwargs.get('execution_id', 'unknown')
            self._safe_log_response(
                question=prompt,  # 使用原始 prompt
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
        实际的 API 请求逻辑
        """
        # 记录请求开始时间以计算延迟
        start_time = time.time()

        try:
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 如果启用了中文约束，在原始 prompt 基础上添加约束指令
            # 这样做不会影响上层传入的原始 prompt，仅在发送给 AI 时附加约束
            processed_prompt = prompt
            if self.enable_chinese_constraint:
                constraint_instruction = (
                    "请严格按照以下要求作答：\n"
                    "1. 必须使用中文回答\n"
                    "2. 基于事实和公开信息作答\n"
                    "3. 避免在不确定时胡编乱造\n"
                    "4. 输出结构清晰（分点或分段）\n\n"
                )
                processed_prompt = constraint_instruction + prompt

            # 根据模式构建不同的请求体
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 搜索/推理模式 (reasoner): 适用于需要深度分析和推理的问题
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": processed_prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # 如果是推理模式，添加额外参数
            if self.mode == "reasoner":
                payload["reasoner"] = "search"  # 启用搜索推理能力

            # 使用统一请求封装器发送请求到 DeepSeek API
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=processed_prompt,
                model=self.model_name,
                json=payload,
                timeout=kwargs.get('timeout', 30)  # 设置请求超时时间为 30 秒
            )

            # 计算请求延迟
            latency = time.time() - start_time

            # 检查响应状态码
            if response.status_code != 200:
                error_message = f"API 请求失败，状态码：{response.status_code}, 响应：{response.text}"

                # Log failed response to enhanced logger with context
                execution_id = kwargs.get('execution_id', 'unknown')
                self._safe_log_response(
                    question=prompt,  # 使用原始 prompt
                    response="",  # No content in case of failure
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVER_ERROR,
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )

                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVER_ERROR,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

            # 解析响应数据
            response_data = response.json()

            # 提取所需信息
            content = ""
            usage = {}

            # 从响应中提取实际回答文本
            choices = response_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

            # 从响应中提取使用情况信息
            usage = response_data.get("usage", {})

            # Log response to enhanced logger with context
            execution_id = kwargs.get('execution_id', 'unknown')
            self._safe_log_response(
                question=prompt,  # 使用原始 prompt，而不是 processed_prompt
                response=content,
                platform=self.platform_type.value,
                model=response_data.get("model", self.model_name),
                success=True,
                latency_ms=int(latency * 1000),  # Convert to milliseconds
                tokens_used=usage.get("total_tokens", 0),
                execution_id=execution_id,
                **kwargs  # Pass any additional context from kwargs
            )

            # 返回成功的 AIResponse，包含模式信息
            return AIResponse(
                success=True,
                content=content,
                model=response_data.get("model", self.model_name),
                platform=self.platform_type.value,
                tokens_used=usage.get("total_tokens", 0),
                latency=latency,
                metadata=response_data
            )

        except requests.exceptions.Timeout:
            # 处理请求超时异常
            latency = time.time() - start_time

            # Log failed response to enhanced logger with context
            execution_id = kwargs.get('execution_id', 'unknown')
            self._safe_log_response(
                question=prompt,  # 使用原始 prompt
                response="",  # No content in case of failure
                platform=self.platform_type.value,
                model=self.model_name,
                success=False,
                error_message="请求超时",
                error_type=AIErrorType.SERVER_ERROR,
                latency_ms=int(latency * 1000),  # Convert to milliseconds
                execution_id=execution_id,
                **kwargs  # Pass any additional context from kwargs
            )

            # Re-raise the exception to trigger circuit breaker
            raise requests.exceptions.Timeout("Request timed out")

        except requests.exceptions.RequestException as e:
            # 处理其他请求相关异常
            latency = time.time() - start_time
            error_type = self._map_request_exception(e)

            # Log failed response to enhanced logger with context
            execution_id = kwargs.get('execution_id', 'unknown')
            self._safe_log_response(
                question=prompt,  # 使用原始 prompt
                response="",  # No content in case of failure
                platform=self.platform_type.value,
                model=self.model_name,
                success=False,
                error_message=f"请求异常：{str(e)}",
                error_type=error_type if error_type else AIErrorType.UNKNOWN_ERROR,
                latency_ms=int(latency * 1000),  # Convert to milliseconds
                execution_id=execution_id,
                **kwargs  # Pass any additional context from kwargs
            )

            # Re-raise the exception to trigger circuit breaker for connection-related errors
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                raise e

            return AIResponse(
                success=False,
                error_message=f"请求异常：{str(e)}",
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except ValueError as e:
            # 处理 API Key 验证等值错误
            latency = time.time() - start_time

            # Log failed response to enhanced logger with context
            execution_id = kwargs.get('execution_id', 'unknown')
            self._safe_log_response(
                question=prompt,  # 使用原始 prompt
                response="",  # No content in case of failure
                platform=self.platform_type.value,
                model=self.model_name,
                success=False,
                error_message=str(e),
                error_type=AIErrorType.INVALID_API_KEY,
                latency_ms=int(latency * 1000),  # Convert to milliseconds
                execution_id=execution_id,
                **kwargs  # Pass any additional context from kwargs
            )

            return AIResponse(
                success=False,
                error_message=str(e),
                error_type=AIErrorType.INVALID_API_KEY,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except Exception as e:
            # 处理其他未预期的异常
            latency = time.time() - start_time

            # Log failed response to enhanced logger with context
            execution_id = kwargs.get('execution_id', 'unknown')
            self._safe_log_response(
                question=prompt,  # 使用原始 prompt
                response="",  # No content in case of failure
                platform=self.platform_type.value,
                model=self.model_name,
                success=False,
                error_message=f"未知错误：{str(e)}",
                error_type=AIErrorType.UNKNOWN_ERROR,
                latency_ms=int(latency * 1000),  # Convert to milliseconds
                execution_id=execution_id,
                **kwargs  # Pass any additional context from kwargs
            )

            # Re-raise the exception to trigger circuit breaker for critical errors
            if isinstance(e, (ConnectionError, TimeoutError)):
                raise e

            return AIResponse(
                success=False,
                error_message=f"未知错误：{str(e)}",
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_request_exception(self, e: requests.RequestException) -> AIErrorType:
        """将请求异常映射到标准错误类型"""
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                return AIErrorType.INVALID_API_KEY
            elif status_code == 429:
                return AIErrorType.RATE_LIMIT_EXCEEDED
            elif status_code >= 500:
                return AIErrorType.SERVER_ERROR
            elif status_code == 403:
                return AIErrorType.INVALID_API_KEY
        return AIErrorType.UNKNOWN_ERROR

    def health_check(self) -> bool:
        """
        检查 DeepSeek 客户端的健康状态
        通过发送一个简单的测试请求来验证连接

        Returns:
            bool: 客户端是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.send_prompt("你好，请回复'正常'。")
            return test_response.success
        except Exception:
            return False
