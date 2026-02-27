"""
AI Adapter 增强基类

提取各 AI Adapter 的公共方法，减少代码重复。

主要功能：
1. 统一的错误处理
2. 统一的日志记录
3. 统一的响应解析
4. 电路断路器集成
5. 请求包装器集成

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import (
    AIClient, 
    AIResponse, 
    AIPlatformType, 
    AIErrorType
)
from wechat_backend.ai_adapters.constants import (
    RetryConfig,
    TimeoutConfig,
    ErrorConfig,
    ResponseConfig,
)
from wechat_backend.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError


class EnhancedAIClient(AIClient, ABC):
    """
    增强的 AI 客户端基类
    
    提供通用的错误处理、日志记录和响应解析逻辑
    """

    def __init__(
        self,
        platform_type: AIPlatformType,
        model_name: str,
        api_key: str,
        base_url: str,
        timeout: int = TimeoutConfig.TOTAL_TIMEOUT,
        max_retries: int = RetryConfig.MAX_RETRIES
    ):
        """
        初始化增强的 AI 客户端

        Args:
            platform_type: 平台类型
            model_name: 模型名称
            api_key: API 密钥
            base_url: API 基础 URL
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        super().__init__(platform_type, model_name, api_key)
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(
            platform_name=platform_type.value,
            model_name=model_name
        )
        
        api_logger.info(
            f"EnhancedAIClient initialized for {platform_type.value}/{model_name}"
        )

    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """生成响应（兼容 NXM 执行引擎）"""
        return self.send_prompt(prompt, **kwargs)

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示并获取响应（带电路断路器保护）

        Args:
            prompt: 提示文本
            **kwargs: 额外参数

        Returns:
            AIResponse: 标准化响应
        """
        try:
            # 使用电路断路器保护 API 调用
            response = self.circuit_breaker.call(
                self._make_request_internal, 
                prompt, 
                **kwargs
            )
            return response
            
        except CircuitBreakerOpenError as e:
            # 电路断路器打开时的处理
            return self._handle_circuit_breaker_error(prompt, e, **kwargs)
            
        except Exception as e:
            # 其他异常处理
            return self._handle_general_error(prompt, e, **kwargs)

    @abstractmethod
    def _make_request_internal(
        self, 
        prompt: str, 
        **kwargs
    ) -> AIResponse:
        """
        实际的 API 请求逻辑（子类实现）

        Args:
            prompt: 提示文本
            **kwargs: 额外参数

        Returns:
            AIResponse: 标准化响应
        """
        pass

    def _handle_circuit_breaker_error(
        self, 
        prompt: str, 
        error: CircuitBreakerOpenError,
        **kwargs
    ) -> AIResponse:
        """
        处理电路断路器错误

        Args:
            prompt: 原始提示
            error: 电路断路器错误
            **kwargs: 额外参数

        Returns:
            AIResponse: 错误响应
        """
        error_message = f"{self.platform_type.value} 服务暂时不可用（熔断器开启）: {error}"
        api_logger.warning(error_message)

        self._log_enhanced_error(
            prompt=prompt,
            error_message=error_message,
            error_type=AIErrorType.SERVICE_UNAVAILABLE,
            **kwargs
        )

        return AIResponse(
            success=False,
            error_message=error_message,
            error_type=AIErrorType.SERVICE_UNAVAILABLE,
            model=self.model_name,
            platform=self.platform_type.value,
            latency=0.0
        )

    def _handle_general_error(
        self, 
        prompt: str, 
        error: Exception,
        **kwargs
    ) -> AIResponse:
        """
        处理一般错误

        Args:
            prompt: 原始提示
            error: 异常对象
            **kwargs: 额外参数

        Returns:
            AIResponse: 错误响应
        """
        error_message = f"{self.platform_type.value} 请求失败：{error}"
        api_logger.error(error_message)

        error_type = self._classify_error(error)
        
        self._log_enhanced_error(
            prompt=prompt,
            error_message=error_message,
            error_type=error_type,
            **kwargs
        )

        return AIResponse(
            success=False,
            error_message=error_message,
            error_type=error_type,
            model=self.model_name,
            platform=self.platform_type.value,
            latency=0.0
        )

    def _classify_error(self, error: Exception) -> AIErrorType:
        """
        分类错误类型

        Args:
            error: 异常对象

        Returns:
            AIErrorType: 错误类型
        """
        error_str = str(error).upper()
        
        # 检查是否为可重试错误
        for retryable_type in ErrorConfig.RETRYABLE_ERROR_TYPES:
            if retryable_type in error_str:
                return AIErrorType.SERVER_ERROR
        
        # 默认未知错误
        return AIErrorType.UNKNOWN_ERROR

    def _log_enhanced_error(
        self,
        prompt: str,
        error_message: str,
        error_type: AIErrorType,
        **kwargs
    ) -> None:
        """
        记录增强的错误日志

        Args:
            prompt: 原始提示
            error_message: 错误消息
            error_type: 错误类型
            **kwargs: 额外参数
        """
        try:
            from wechat_backend.utils.ai_response_wrapper import log_detailed_response
            
            execution_id = kwargs.get('execution_id', 'unknown')
            log_detailed_response(
                question=prompt,
                response="",
                platform=self.platform_type.value,
                model=self.model_name,
                success=False,
                error_message=error_message,
                error_type=error_type,
                latency_ms=0,
                execution_id=execution_id,
                **{k: v for k, v in kwargs.items() if k != 'execution_id'}
            )
        except Exception as log_error:
            api_logger.warning(
                f"Failed to log error to enhanced logger: {log_error}"
            )

    def _log_enhanced_success(
        self,
        prompt: str,
        content: str,
        tokens_used: int,
        latency: float,
        **kwargs
    ) -> None:
        """
        记录增强的成功日志

        Args:
            prompt: 原始提示
            content: 响应内容
            tokens_used: 使用的 token 数
            latency: 延迟（秒）
            **kwargs: 额外参数
        """
        try:
            from wechat_backend.utils.ai_response_wrapper import log_detailed_response
            
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
            api_logger.warning(
                f"Failed to log success to enhanced logger: {log_error}"
            )

    def _validate_response(
        self, 
        response_data: Dict[str, Any],
        required_fields: list = None
    ) -> bool:
        """
        验证响应数据

        Args:
            response_data: 响应数据
            required_fields: 必需字段列表

        Returns:
            bool: 是否有效
        """
        if not response_data:
            return False
            
        if required_fields:
            for field in required_fields:
                if field not in response_data:
                    api_logger.warning(
                        f"Missing required field: {field}"
                    )
                    return False
                    
        return True

    def _truncate_content(
        self, 
        content: str, 
        max_length: int = ResponseConfig.MAX_RESPONSE_LENGTH
    ) -> str:
        """
        截断超长内容

        Args:
            content: 原始内容
            max_length: 最大长度

        Returns:
            str: 截断后的内容
        """
        if len(content) <= max_length:
            return content
            
        return content[:max_length] + "... [truncated]"

    def _calculate_tokens(
        self, 
        content: str,
        estimation_ratio: float = 0.75
    ) -> int:
        """
        估算 token 数量（当 API 未提供时）

        Args:
            content: 内容
            estimation_ratio: 估算比例

        Returns:
            int: 估算的 token 数
        """
        # 简单估算：中文字符算 1 个 token，英文单词算 1 个 token
        chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
        english_chars = len(content) - chinese_chars
        english_words = english_chars / 5  # 平均 5 个字符一个单词
        
        return int((chinese_chars + english_words) * estimation_ratio)
