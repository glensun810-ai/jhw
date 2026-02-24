"""
异常处理装饰器模块

提供统一的异常处理机制，自动捕获并转换异常为友好的 API 响应
"""

from functools import wraps
from flask import jsonify, request
from typing import Callable, Optional, Dict, Any
import traceback

from wechat_backend.logging_config import api_logger
from wechat_backend.exceptions import (
    BaseAPIException,
    ValidationError,
    AIPlatformError,
    AIConfigError,
    TaskExecutionError,
    TaskTimeoutError,
    NotFoundError,
    AuthenticationError,
    PermissionError,
    DatabaseError,
    RateLimitError
)


def handle_api_exceptions(f: Callable) -> Callable:
    """
    API 异常处理装饰器
    
    自动捕获各种异常并转换为统一的 JSON 响应格式
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        # 已定义的异常类型，直接返回
        except ValidationError as e:
            api_logger.warning(f"验证错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except AIConfigError as e:
            api_logger.warning(f"AI 配置错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except AIPlatformError as e:
            api_logger.error(f"AI 平台错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except TaskTimeoutError as e:
            api_logger.warning(f"任务超时：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except TaskExecutionError as e:
            api_logger.error(f"任务执行错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except NotFoundError as e:
            api_logger.warning(f"资源未找到：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except AuthenticationError as e:
            api_logger.warning(f"认证错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except PermissionError as e:
            api_logger.warning(f"权限错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except RateLimitError as e:
            api_logger.warning(f"频率限制：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        except DatabaseError as e:
            api_logger.error(f"数据库错误：{e.message}")
            return jsonify(e.to_dict()), e.status_code
        
        # 未预期的异常，记录详细日志并返回通用错误
        except Exception as e:
            # 记录完整堆栈信息
            error_traceback = traceback.format_exc()
            api_logger.error(f"未预期错误：{str(e)}\n{error_traceback}")
            
            # 生产环境不暴露详细错误信息
            return jsonify({
                'error': '系统繁忙，请稍后重试',
                'code': 'INTERNAL_ERROR',
                'status_code': 500,
                'details': {
                    'type': type(e).__name__
                }
            }), 500
    
    return decorated_function


def exception_to_dict(e: Exception) -> Dict[str, Any]:
    """
    将异常转换为字典格式
    
    用于在异步线程中捕获异常后传递给前端
    """
    if isinstance(e, BaseAPIException):
        return e.to_dict()
    
    # 常见异常类型映射
    error_mapping = {
        'ValidationError': {'code': 'VALIDATION_ERROR', 'status_code': 400},
        'TimeoutError': {'code': 'TASK_TIMEOUT_ERROR', 'status_code': 408},
        'ConnectionError': {'code': 'AI_PLATFORM_ERROR', 'status_code': 503},
        'KeyError': {'code': 'AI_CONFIG_ERROR', 'status_code': 400},
        'ValueError': {'code': 'VALIDATION_ERROR', 'status_code': 400},
    }
    
    error_type = type(e).__name__
    mapping = error_mapping.get(error_type, {'code': 'UNKNOWN_ERROR', 'status_code': 500})
    
    return {
        'error': str(e),
        'code': mapping['code'],
        'status_code': mapping['status_code'],
        'details': {
            'type': error_type
        }
    }
