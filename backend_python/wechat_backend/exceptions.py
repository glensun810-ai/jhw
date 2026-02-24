"""
自定义异常模块

提供统一的异常处理机制，便于前端理解和处理错误
"""

from typing import Optional, Dict, Any


class BaseAPIException(Exception):
    """基础 API 异常类"""
    
    def __init__(
        self, 
        message: str, 
        code: str = 'UNKNOWN_ERROR',
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于返回给前端"""
        return {
            'error': self.message,
            'code': self.code,
            'status_code': self.status_code,
            'details': self.details
        }


class ValidationError(BaseAPIException):
    """输入验证错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code='VALIDATION_ERROR',
            status_code=400,
            details=details
        )


class AIPlatformError(BaseAPIException):
    """AI 平台调用错误"""
    
    def __init__(
        self, 
        message: str, 
        platform: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code='AI_PLATFORM_ERROR',
            status_code=503,
            details={
                'platform': platform,
                **(details or {})
            }
        )


class AIConfigError(BaseAPIException):
    """AI 配置错误（如 API Key 缺失）"""
    
    def __init__(self, message: str, platform: Optional[str] = None):
        super().__init__(
            message=message,
            code='AI_CONFIG_ERROR',
            status_code=400,
            details={'platform': platform}
        )


class TaskExecutionError(BaseAPIException):
    """任务执行错误"""
    
    def __init__(
        self, 
        message: str, 
        execution_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code='TASK_EXECUTION_ERROR',
            status_code=500,
            details={
                'execution_id': execution_id,
                **(details or {})
            }
        )


class TaskTimeoutError(BaseAPIException):
    """任务超时错误"""
    
    def __init__(
        self, 
        message: str, 
        execution_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ):
        super().__init__(
            message=message,
            code='TASK_TIMEOUT_ERROR',
            status_code=408,
            details={
                'execution_id': execution_id,
                'timeout_seconds': timeout_seconds
            }
        )


class NotFoundError(BaseAPIException):
    """资源未找到错误"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(
            message=message,
            code='NOT_FOUND_ERROR',
            status_code=404,
            details={'resource_type': resource_type}
        )


class AuthenticationError(BaseAPIException):
    """认证错误"""
    
    def __init__(self, message: str = '认证失败，请重新登录'):
        super().__init__(
            message=message,
            code='AUTHENTICATION_ERROR',
            status_code=401
        )


class PermissionError(BaseAPIException):
    """权限错误"""
    
    def __init__(self, message: str = '权限不足，无法执行此操作'):
        super().__init__(
            message=message,
            code='PERMISSION_ERROR',
            status_code=403
        )


class DatabaseError(BaseAPIException):
    """数据库错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code='DATABASE_ERROR',
            status_code=500,
            details=details
        )


class RateLimitError(BaseAPIException):
    """请求频率限制错误"""
    
    def __init__(self, message: str = '请求过于频繁，请稍后再试'):
        super().__init__(
            message=message,
            code='RATE_LIMIT_ERROR',
            status_code=429
        )
