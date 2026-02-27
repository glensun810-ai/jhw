"""
v2 自定义异常模块

所有 v2 代码必须使用这些自定义异常类，禁止直接使用 Exception。

异常层级:
    DiagnosisError (基础异常)
    ├── DiagnosisTimeoutError (超时异常)
    ├── DiagnosisValidationError (验证异常)
    ├── DiagnosisStateError (状态异常)
    ├── AIPlatformError (AI 平台异常)
    ├── DataPersistenceError (数据持久化异常)
    └── DatabaseError (数据库异常)
"""

from typing import Optional, Dict, Any


class DiagnosisError(Exception):
    """诊断系统基础异常类
    
    Attributes:
        message: 错误消息
        error_code: 错误代码
        status_code: HTTP 状态码
        details: 详细错误信息
    """
    
    error_code: str = 'DIAGNOSIS_ERROR'
    status_code: int = 500
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
        }


class DiagnosisTimeoutError(DiagnosisError):
    """诊断任务执行超时异常"""
    
    error_code = 'DIAGNOSIS_TIMEOUT'
    status_code = 408
    
    def __init__(
        self,
        message: str = '诊断任务执行超时',
        execution_id: Optional[str] = None,
        elapsed_time: Optional[int] = None,
        max_allowed: int = 600,
    ):
        details = {
            'execution_id': execution_id,
            'elapsed_time': elapsed_time,
            'max_allowed': max_allowed,
        }
        super().__init__(message, details)


class DiagnosisValidationError(DiagnosisError):
    """数据验证异常"""
    
    error_code = 'DATA_VALIDATION_ERROR'
    status_code = 400
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        details = {
            'field': field,
            'value': value,
        }
        super().__init__(message, details)


class DiagnosisStateError(DiagnosisError):
    """状态机异常"""
    
    error_code = 'STATE_ERROR'
    status_code = 400
    
    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        event: Optional[str] = None,
        allowed_events: Optional[list] = None,
    ):
        details = {
            'current_state': current_state,
            'event': event,
            'allowed_events': allowed_events or [],
        }
        super().__init__(message, details)


class AIPlatformError(DiagnosisError):
    """AI 平台调用异常"""
    
    error_code = 'AI_PLATFORM_ERROR'
    status_code = 502
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        model: Optional[str] = None,
        original_error: Optional[str] = None,
    ):
        details = {
            'platform': platform,
            'model': model,
            'original_error': original_error,
        }
        super().__init__(message, details)


class DataPersistenceError(DiagnosisError):
    """数据持久化异常"""
    
    error_code = 'DATA_PERSISTENCE_ERROR'
    status_code = 500
    
    def __init__(
        self,
        message: str,
        execution_id: Optional[str] = None,
        original_error: Optional[str] = None,
    ):
        details = {
            'execution_id': execution_id,
            'original_error': original_error,
        }
        super().__init__(message, details)


class DatabaseError(DiagnosisError):
    """数据库操作异常"""
    
    error_code = 'DATABASE_ERROR'
    status_code = 500
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        original_error: Optional[str] = None,
    ):
        details = {
            'operation': operation,
            'original_error': original_error,
        }
        super().__init__(message, details)


class DeadLetterQueueError(DiagnosisError):
    """死信队列相关异常"""
    
    error_code = 'DEAD_LETTER_QUEUE_ERROR'
    status_code = 500


class RetryExhaustedError(DiagnosisError):
    """重试耗尽异常"""
    
    error_code = 'RETRY_EXHAUSTED'
    status_code = 500
    
    def __init__(self, original_error: Exception, retry_count: int):
        self.original_error = original_error
        self.retry_count = retry_count
        super().__init__(
            f"Retry exhausted after {retry_count} attempts. "
            f"Original error: {original_error}"
        )


class RepositoryError(DiagnosisError):
    """仓库操作异常"""

    error_code = 'REPOSITORY_ERROR'
    status_code = 500

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        original_error: Optional[str] = None,
    ):
        details = {
            'operation': operation,
            'original_error': original_error,
        }
        super().__init__(message, details)


# ==================== 统计算法异常类 ====================

class AnalyticsError(DiagnosisError):
    """统计算法基础异常类
    
    所有统计算法模块的异常都继承自此类
    
    Attributes:
        message: 错误消息
        error_code: 错误代码
        status_code: HTTP 状态码
        details: 详细错误信息
    """

    error_code = 'ANALYTICS_ERROR'
    status_code = 500


class AnalyticsDataError(AnalyticsError):
    """统计数据验证异常
    
    当输入数据格式错误或缺少必要字段时抛出
    """

    error_code = 'ANALYTICS_DATA_ERROR'
    status_code = 400

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected_type: Optional[str] = None,
    ):
        details = {
            'field': field,
            'value': str(value) if value is not None else None,
            'expected_type': expected_type,
        }
        super().__init__(message, details)


class AnalyticsConfigurationError(AnalyticsError):
    """统计算法配置异常
    
    当配置参数无效或冲突时抛出
    """

    error_code = 'ANALYTICS_CONFIGURATION_ERROR'
    status_code = 400

    def __init__(
        self,
        message: str,
        parameter: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        suggestion: Optional[str] = None,
    ):
        details = {
            'parameter': parameter,
            'invalid_value': str(invalid_value) if invalid_value is not None else None,
            'suggestion': suggestion,
        }
        super().__init__(message, details)


class AnalyticsProcessingError(AnalyticsError):
    """统计算法处理异常
    
    当分析处理过程中发生错误时抛出
    """

    error_code = 'ANALYTICS_PROCESSING_ERROR'
    status_code = 500

    def __init__(
        self,
        message: str,
        analyzer_name: Optional[str] = None,
        original_error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = {
            'analyzer_name': analyzer_name,
            'original_error': original_error,
            'context': context or {},
        }
        super().__init__(message, details)
