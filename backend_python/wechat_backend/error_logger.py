"""
增强错误日志记录模块

功能：
- 记录完整的错误上下文信息
- 结构化日志格式
- 错误追踪 ID
- 错误码统一处理（兼容枚举、元组、字符串）

@author: 系统架构组
@date: 2026-03-02
@version: 2.0.0 (P1 架构修复)
"""

import logging
import traceback
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from functools import wraps

from wechat_backend.error_codes import ErrorCode, get_error_message


class ErrorSeverity:
    """错误严重程度"""
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


def _get_severity_from_error_code(error_code) -> str:
    """从错误码获取严重程度

    Args:
        error_code: 错误码（ErrorCode 枚举或字符串）

    Returns:
        str: 严重程度
    """
    if hasattr(error_code, 'http_status'):
        http_status = error_code.http_status
        if http_status >= 500:
            return ErrorSeverity.CRITICAL
        elif http_status >= 400:
            return ErrorSeverity.ERROR
        elif http_status >= 300:
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.INFO
    return ErrorSeverity.ERROR


@dataclass
class ErrorContext:
    """错误上下文信息"""
    error_code: str
    error_message: str
    severity: str
    timestamp: str
    execution_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None
    request_params: Optional[Dict] = None
    user_context: Optional[Dict] = None
    system_context: Optional[Dict] = None
    additional_info: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（过滤 None 值）"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class ErrorLogger:
    """增强错误日志记录器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def _generate_trace_id(self) -> str:
        return f"trace_{uuid.uuid4().hex[:16]}"

    def _generate_request_id(self) -> str:
        return f"req_{uuid.uuid4().hex[:12]}"

    def _extract_stack_info(self, skip_frames: int = 2) -> Dict[str, Any]:
        import sys
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_tb is None:
            return {}

        tb = exc_tb
        for _ in range(skip_frames):
            if tb.tb_next:
                tb = tb.tb_next
            else:
                break

        return {
            'file_path': tb.tb_frame.f_code.co_filename,
            'function': tb.tb_frame.f_code.co_name,
            'line_number': tb.tb_lineno,
            'stack_trace': ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        }

    def _normalize_error_code(self, error_code) -> Tuple[str, str]:
        """
        【P1 架构修复 - 2026-03-11】统一错误码处理，兼容多种类型

        支持类型：
        1. ErrorCode 枚举（如 ErrorCode.AI_SERVICE_UNAVAILABLE）
        2. Enum 值（如 DiagnosisErrorCode.DIAGNOSIS_EXECUTION_FAILED）
        3. 元组 ('code', 'message', http_status)
        4. 字符串

        Args:
            error_code: 错误码（多种类型）

        Returns:
            Tuple[str, str]: (错误码字符串，严重程度)
        """
        from enum import Enum

        # 情况 1: None
        if error_code is None:
            return 'UNKNOWN_ERROR', ErrorSeverity.ERROR

        # 情况 2: ErrorCode 枚举（有 code 和 http_status 属性）
        if hasattr(error_code, 'code') and hasattr(error_code, 'http_status'):
            return error_code.code, _get_severity_from_error_code(error_code)

        # 情况 3: Enum 包装（如 error_code.value 是 ErrorCode）
        if isinstance(error_code, Enum):
            value = error_code.value if hasattr(error_code, 'value') else error_code
            if hasattr(value, 'code'):
                return value.code, _get_severity_from_error_code(value)
            # 如果 value 是元组
            if isinstance(value, (tuple, list)) and len(value) >= 1:
                return value[0], ErrorSeverity.ERROR
            return str(value), ErrorSeverity.ERROR

        # 情况 4: 元组 ('code', 'message', status)
        if isinstance(error_code, (tuple, list)) and len(error_code) >= 1:
            return error_code[0], ErrorSeverity.ERROR

        # 情况 5: 字符串
        if isinstance(error_code, str):
            return error_code, ErrorSeverity.ERROR

        # 情况 6: 其他类型，转为字符串
        return str(error_code), ErrorSeverity.ERROR

    def _build_error_context(
        self,
        error: Exception,
        error_code: str,
        severity: str,
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_params: Optional[Dict] = None,
        user_context: Optional[Dict] = None,
        system_context: Optional[Dict] = None,
        additional_info: Optional[Dict] = None,
        stack_info: Optional[Dict] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> ErrorContext:
        """构建错误上下文"""
        return ErrorContext(
            error_code=error_code,
            error_message=str(error),
            severity=severity,
            timestamp=datetime.now().isoformat(),
            execution_id=execution_id,
            user_id=user_id,
            request_id=request_id,
            trace_id=trace_id,
            **(stack_info or {}),
            request_params=request_params,
            user_context=user_context,
            system_context=system_context,
            additional_info=additional_info
        )

    def log_error(
        self,
        error: Exception,
        error_code,
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_params: Optional[Dict] = None,
        user_context: Optional[Dict] = None,
        system_context: Optional[Dict] = None,
        additional_info: Optional[Dict] = None,
        log_level: int = logging.ERROR
    ) -> str:
        """
        记录错误日志（带完整上下文）

        Args:
            error: 异常对象
            error_code: 错误码（支持 ErrorCode 枚举、元组、字符串）
            execution_id: 执行 ID
            user_id: 用户 ID
            request_params: 请求参数
            user_context: 用户上下文
            system_context: 系统上下文
            additional_info: 附加信息
            log_level: 日志级别

        Returns:
            str: 追踪 ID
        """
        trace_id = self._generate_trace_id()
        request_id = self._generate_request_id()
        stack_info = self._extract_stack_info()

        # 【P1 架构修复】统一错误码处理
        error_code_str, severity = self._normalize_error_code(error_code)

        context = self._build_error_context(
            error=error,
            error_code=error_code_str,
            severity=severity,
            execution_id=execution_id,
            user_id=user_id,
            request_params=request_params,
            user_context=user_context,
            system_context=system_context,
            additional_info=additional_info,
            stack_info=stack_info,
            request_id=request_id,
            trace_id=trace_id
        )

        # 根据严重程度选择日志级别
        if severity == ErrorSeverity.CRITICAL:
            log_level = logging.CRITICAL
        elif severity == ErrorSeverity.ERROR:
            log_level = logging.ERROR
        elif severity == ErrorSeverity.WARNING:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        log_message = (
            f"[{error_code_str}] {context.error_message}\n"
            f"TraceID: {trace_id} | RequestID: {request_id}"
        )
        if execution_id:
            log_message += f" | ExecutionID: {execution_id}"

        if log_level == logging.CRITICAL:
            self.logger.critical(log_message, extra={'error_context': context.to_dict()})
        elif log_level == logging.ERROR:
            self.logger.error(log_message, extra={'error_context': context.to_dict()})
        elif log_level == logging.WARNING:
            self.logger.warning(log_message, extra={'error_context': context.to_dict()})
        else:
            self.logger.info(log_message, extra={'error_context': context.to_dict()})

        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]:
            self.logger.debug(f"Error Context JSON: {context.to_json()}")

        return trace_id

    def log_warning(self, message: str, error_code: Optional = None, **kwargs) -> str:
        if error_code:
            error = Exception(message)
            return self.log_error(error, error_code, log_level=logging.WARNING, **kwargs)
        trace_id = self._generate_trace_id()
        self.logger.warning(f"[{trace_id}] {message}")
        return trace_id

    def log_info(self, message: str, context: Optional[Dict] = None, **kwargs) -> str:
        trace_id = self._generate_trace_id()
        if context:
            self.logger.info(f"[{trace_id}] {message}", extra={'context': context})
        else:
            self.logger.info(f"[{trace_id}] {message}")
        return trace_id


# 全局实例
_error_logger: Optional[ErrorLogger] = None


def get_error_logger() -> ErrorLogger:
    global _error_logger
    if _error_logger is None:
        from wechat_backend.logging_config import api_logger
        _error_logger = ErrorLogger(api_logger)
    return _error_logger
