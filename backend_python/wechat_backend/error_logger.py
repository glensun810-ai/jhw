"""
增强错误日志记录模块

功能：
- 记录完整的错误上下文信息
- 结构化日志格式
- 错误追踪 ID
- 性能影响分析

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import logging
import traceback
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from functools import wraps

from wechat_backend.error_codes import ErrorCodeDefinition, ErrorSeverity


@dataclass
class ErrorContext:
    """错误上下文信息"""
    error_code: str                           # 错误码
    error_message: str                        # 错误消息
    severity: str                             # 严重程度
    timestamp: str                            # 时间戳
    execution_id: Optional[str] = None        # 执行 ID
    user_id: Optional[str] = None             # 用户 ID
    request_id: Optional[str] = None          # 请求 ID
    trace_id: Optional[str] = None            # 追踪 ID
    module: Optional[str] = None              # 模块名称
    function: Optional[str] = None            # 函数名称
    file_path: Optional[str] = None           # 文件路径
    line_number: Optional[int] = None         # 行号
    stack_trace: Optional[str] = None         # 堆栈追踪
    request_params: Optional[Dict] = None     # 请求参数
    user_context: Optional[Dict] = None       # 用户上下文
    system_context: Optional[Dict] = None     # 系统上下文
    additional_info: Optional[Dict] = None    # 附加信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（过滤 None 值）"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class ErrorLogger:
    """增强错误日志记录器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化错误日志记录器
        
        Args:
            logger: 日志记录器实例，默认使用根日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def _generate_trace_id(self) -> str:
        """生成追踪 ID"""
        return f"trace_{uuid.uuid4().hex[:16]}"
    
    def _generate_request_id(self) -> str:
        """生成请求 ID"""
        return f"req_{uuid.uuid4().hex[:12]}"
    
    def _extract_stack_info(self, skip_frames: int = 2) -> Dict[str, Any]:
        """
        提取堆栈信息
        
        Args:
            skip_frames: 跳过的堆栈帧数（跳过本模块的帧）
            
        Returns:
            包含文件路径、函数名、行号等信息的字典
        """
        import sys
        exc_type, exc_value, exc_tb = sys.exc_info()
        
        if exc_tb is None:
            return {}
        
        # 获取调用者信息
        tb = exc_tb
        for _ in range(skip_frames):
            if tb.tb_next:
                tb = tb.tb_next
            else:
                break
        
        frame_info = {
            'file_path': tb.tb_frame.f_code.co_filename,
            'function': tb.tb_frame.f_code.co_name,
            'line_number': tb.tb_lineno,
        }
        
        # 获取完整堆栈追踪
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        return {
            **frame_info,
            'stack_trace': stack_trace
        }
    
    def log_error(
        self,
        error: Exception,
        error_code: ErrorCodeDefinition,
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
            error_code: 错误码定义
            execution_id: 执行 ID
            user_id: 用户 ID
            request_params: 请求参数
            user_context: 用户上下文
            system_context: 系统上下文
            additional_info: 附加信息
            log_level: 日志级别
            
        Returns:
            str: 追踪 ID（用于日志关联查询）
        """
        # 生成追踪 ID
        trace_id = self._generate_trace_id()
        request_id = self._generate_request_id()
        
        # 提取堆栈信息
        stack_info = self._extract_stack_info()
        
        # 构建错误上下文
        context = ErrorContext(
            error_code=error_code.code,
            error_message=str(error),
            severity=error_code.severity.value,
            timestamp=datetime.now().isoformat(),
            execution_id=execution_id,
            user_id=user_id,
            request_id=request_id,
            trace_id=trace_id,
            **stack_info,
            request_params=request_params,
            user_context=user_context,
            system_context=system_context,
            additional_info=additional_info
        )
        
        # 根据严重程度选择日志级别
        if error_code.severity == ErrorSeverity.CRITICAL:
            log_level = logging.CRITICAL
        elif error_code.severity == ErrorSeverity.ERROR:
            log_level = logging.ERROR
        elif error_code.severity == ErrorSeverity.WARNING:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # 记录结构化日志
        log_message = (
            f"[{error_code.code}] {context.error_message}\n"
            f"TraceID: {trace_id} | RequestID: {request_id}"
        )

        if execution_id:
            log_message += f" | ExecutionID: {execution_id}"

        # 使用正确的日志级别方法
        if log_level == logging.CRITICAL:
            self.logger.critical(log_message, extra={'error_context': context.to_dict()})
        elif log_level == logging.ERROR:
            self.logger.error(log_message, extra={'error_context': context.to_dict()})
        elif log_level == logging.WARNING:
            self.logger.warning(log_message, extra={'error_context': context.to_dict()})
        elif log_level == logging.INFO:
            self.logger.info(log_message, extra={'error_context': context.to_dict()})
        else:
            self.logger.debug(log_message, extra={'error_context': context.to_dict()})

        # 对于严重错误，额外记录完整 JSON
        if error_code.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]:
            self.logger.debug(f"Error Context JSON: {context.to_json()}")

        return trace_id
    
    def log_warning(
        self,
        message: str,
        error_code: Optional[ErrorCodeDefinition] = None,
        **kwargs
    ) -> str:
        """
        记录警告日志
        
        Args:
            message: 警告消息
            error_code: 错误码定义（可选）
            **kwargs: 其他参数传递给 log_error
            
        Returns:
            str: 追踪 ID
        """
        if error_code:
            # 创建一个临时异常
            error = Exception(message)
            return self.log_error(error, error_code, log_level=logging.WARNING, **kwargs)
        else:
            # 简单警告日志
            trace_id = self._generate_trace_id()
            self.logger.warning(f"[{trace_id}] {message}")
            return trace_id
    
    def log_info(
        self,
        message: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        记录信息日志
        
        Args:
            message: 信息消息
            context: 上下文信息
            **kwargs: 其他参数
            
        Returns:
            str: 追踪 ID
        """
        trace_id = self._generate_trace_id()
        
        if context:
            self.logger.info(f"[{trace_id}] {message}", extra={'context': context})
        else:
            self.logger.info(f"[{trace_id}] {message}")
        
        return trace_id


# 全局错误日志记录器实例
_error_logger: Optional[ErrorLogger] = None


def get_error_logger() -> ErrorLogger:
    """获取全局错误日志记录器"""
    global _error_logger
    if _error_logger is None:
        from wechat_backend.logging_config import api_logger
        _error_logger = ErrorLogger(api_logger)
    return _error_logger


# ==================== 装饰器 ====================

def log_errors(error_code: ErrorCodeDefinition):
    """
    错误日志装饰器
    
    自动记录函数执行过程中的错误，并附加完整的上下文信息
    
    Args:
        error_code: 错误码定义（可以是枚举值或 ErrorCodeDefinition）
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_logger = get_error_logger()
                
                # 尝试从参数中提取上下文信息
                execution_id = kwargs.get('execution_id')
                user_id = kwargs.get('user_id')
                
                # 处理枚举值
                from enum import Enum
                if isinstance(error_code, Enum):
                    error_code_def = error_code.value
                else:
                    error_code_def = error_code
                
                # 记录错误
                trace_id = error_logger.log_error(
                    error=e,
                    error_code=error_code_def,
                    execution_id=execution_id,
                    user_id=user_id,
                    additional_info={
                        'function': func.__name__,
                        'args': args,
                        'kwargs': kwargs
                    }
                )
                
                # 将 trace_id 附加到异常上，便于后续处理
                e.trace_id = trace_id  # type: ignore
                
                raise
        return wrapper
    return decorator


def log_diagnosis_errors(func):
    """
    诊断系统专用错误日志装饰器
    
    自动提取诊断相关的上下文信息
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_logger = get_error_logger()
            
            # 提取诊断相关上下文
            execution_id = kwargs.get('execution_id') or args[0] if args else None
            user_id = kwargs.get('user_id')
            brand_name = kwargs.get('brand_name')
            
            # 根据异常类型选择错误码
            from wechat_backend.error_codes import DiagnosisErrorCode
            
            if 'timeout' in str(e).lower():
                error_code = DiagnosisErrorCode.DIAGNOSIS_TIMEOUT.value
            elif 'validation' in str(e).lower() or '验证' in str(e).lower():
                error_code = DiagnosisErrorCode.DIAGNOSIS_RESULT_INVALID.value
            elif 'save' in str(e).lower() or '保存' in str(e).lower():
                error_code = DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED.value
            else:
                error_code = DiagnosisErrorCode.DIAGNOSIS_EXECUTION_FAILED.value
            
            # 记录错误
            trace_id = error_logger.log_error(
                error=e,
                error_code=error_code,
                execution_id=execution_id,
                user_id=user_id,
                user_context={
                    'brand_name': brand_name,
                },
                additional_info={
                    'function': func.__name__,
                }
            )
            
            e.trace_id = trace_id  # type: ignore
            raise
    return wrapper
