"""
错误处理工具模块

提供统一的错误响应格式，包括错误消息、建议和详情

作者：首席全栈工程师
日期：2026-03-05
版本：1.0
"""

from flask import jsonify
from wechat_backend.logging_config import api_logger
from functools import wraps


# 错误代码和建议映射表
ERROR_REGISTRY = {
    # 认证相关错误
    'AUTH_REQUIRED': {
        'message': '认证信息已过期',
        'suggestion': ['请重新登录', '清除缓存后重试'],
        'http_status': 401
    },
    'AUTH_INVALID': {
        'message': '认证信息无效',
        'suggestion': ['请检查 Token 是否正确', '重新登录后重试'],
        'http_status': 401
    },
    'AUTH_FORBIDDEN': {
        'message': '无权访问此资源',
        'suggestion': ['请联系管理员获取权限', '检查用户角色配置'],
        'http_status': 403
    },
    
    # 验证相关错误
    'VALIDATION_ERROR': {
        'message': '输入数据格式错误',
        'suggestion': ['请检查品牌名称是否正确', '确认已选择 AI 模型', '验证问题格式是否完整'],
        'http_status': 400
    },
    'MISSING_PARAMETER': {
        'message': '缺少必需参数',
        'suggestion': ['请检查请求参数是否完整'],
        'http_status': 400
    },
    'INVALID_PARAMETER': {
        'message': '参数值无效',
        'suggestion': ['请检查参数格式和取值范围'],
        'http_status': 400
    },
    
    # AI 平台相关错误
    'AI_SERVICE_UNAVAILABLE': {
        'message': 'AI 平台暂时不可用',
        'suggestion': ['请稍后重试', '尝试更换其他 AI 模型', '检查 AI 平台状态'],
        'http_status': 503
    },
    'AI_API_KEY_MISSING': {
        'message': 'AI API 密钥未配置',
        'suggestion': ['请联系管理员配置 API 密钥', '检查环境变量设置'],
        'http_status': 500
    },
    'AI_API_KEY_INVALID': {
        'message': 'AI API 密钥无效',
        'suggestion': ['请联系管理员更新 API 密钥', '检查密钥是否过期'],
        'http_status': 401
    },
    'AI_RATE_LIMIT_EXCEEDED': {
        'message': 'AI 平台请求过于频繁',
        'suggestion': ['请等待 1 分钟后重试', '减少并发请求数量'],
        'http_status': 429
    },
    'AI_TIMEOUT': {
        'message': 'AI 平台响应超时',
        'suggestion': ['请稍后重试', '尝试使用其他 AI 模型', '检查网络连接'],
        'http_status': 504
    },
    'AI_RESPONSE_PARSE_ERROR': {
        'message': 'AI 响应解析失败',
        'suggestion': ['请重试', '检查 AI 模型返回格式'],
        'http_status': 500
    },
    
    # 任务执行相关错误
    'TASK_EXECUTION_FAILED': {
        'message': '任务执行失败',
        'suggestion': ['查看历史记录', '重新发起诊断', '减少 AI 模型数量'],
        'http_status': 500
    },
    'TASK_TIMEOUT': {
        'message': '任务执行超时',
        'suggestion': ['请重试', '减少问题数量', '减少 AI 模型数量'],
        'http_status': 408
    },
    'TASK_NOT_FOUND': {
        'message': '任务不存在',
        'suggestion': ['请检查执行 ID 是否正确', '重新发起诊断任务'],
        'http_status': 404
    },
    
    # 数据库相关错误
    'DATABASE_ERROR': {
        'message': '数据库操作失败',
        'suggestion': ['请联系技术支持', '提供错误发生时间'],
        'http_status': 500
    },
    'DATABASE_CONNECTION_ERROR': {
        'message': '数据库连接失败',
        'suggestion': ['请稍后重试', '联系技术支持'],
        'http_status': 503
    },
    
    # 系统相关错误
    'INTERNAL_SERVER_ERROR': {
        'message': '服务器内部错误',
        'suggestion': ['请稍后重试', '联系技术支持'],
        'http_status': 500
    },
    'SERVICE_UNAVAILABLE': {
        'message': '服务暂时不可用',
        'suggestion': ['请稍后重试', '检查系统维护公告'],
        'http_status': 503
    },
}


def create_error_response(error_code=None, message=None, suggestion=None, details=None, 
                          http_status=None, original_error=None):
    """
    创建统一的错误响应
    
    Args:
        error_code: 错误代码（预定义代码或自定义）
        message: 错误消息（可选，如果未提供则使用预定义消息）
        suggestion: 用户建议（可选，字符串或列表）
        details: 详细错误信息（可选，用于调试）
        http_status: HTTP 状态码（可选，如果未提供则使用预定义状态码）
        original_error: 原始异常对象（用于日志记录）
    
    Returns:
        tuple: (jsonify_response, http_status)
    """
    # 获取预定义的错误信息
    error_info = ERROR_REGISTRY.get(error_code, {})
    
    # 使用提供的参数或预定义值
    final_message = message or error_info.get('message', '操作失败')
    final_suggestion = suggestion or error_info.get('suggestion', ['请稍后重试'])
    final_status = http_status or error_info.get('http_status', 500)
    
    # 构建响应数据
    response_data = {
        'error': final_message,
        'error_code': error_code or 'UNKNOWN_ERROR',
        'suggestion': final_suggestion
    }
    
    # 添加详细信息（仅在开发环境或明确提供时）
    if details:
        if isinstance(details, str):
            response_data['details'] = details
        elif isinstance(details, list):
            response_data['details'] = details
        elif isinstance(details, dict):
            response_data['details'].update(details)
    
    # 记录错误日志
    if original_error:
        api_logger.error(f"Error [{error_code or 'UNKNOWN'}]: {str(original_error)}")
    else:
        api_logger.warning(f"Error response created: {final_message}")
    
    return jsonify(response_data), final_status


def handle_ai_platform_error(error, platform_name='AI 平台'):
    """
    处理 AI 平台相关错误
    
    Args:
        error: 异常对象
        platform_name: AI 平台名称
    
    Returns:
        tuple: (jsonify_response, http_status)
    """
    error_msg = str(error).lower()
    
    # 根据错误类型返回不同的响应
    if 'timeout' in error_msg or 'timed out' in error_msg:
        return create_error_response(
            error_code='AI_TIMEOUT',
            message=f'{platform_name}响应超时',
            original_error=error
        )
    elif 'connection' in error_msg or 'network' in error_msg:
        return create_error_response(
            error_code='AI_SERVICE_UNAVAILABLE',
            message=f'{platform_name}连接失败',
            original_error=error
        )
    elif 'api key' in error_msg or 'authentication' in error_msg:
        return create_error_response(
            error_code='AI_API_KEY_INVALID',
            message=f'{platform_name}认证失败',
            original_error=error
        )
    elif 'rate limit' in error_msg or 'too many requests' in error_msg:
        return create_error_response(
            error_code='AI_RATE_LIMIT_EXCEEDED',
            message=f'{platform_name}请求受限',
            original_error=error
        )
    else:
        return create_error_response(
            error_code='AI_SERVICE_UNAVAILABLE',
            message=f'{platform_name}暂时不可用',
            original_error=error
        )


def handle_validation_error(field_name, message):
    """
    处理验证错误
    
    Args:
        field_name: 字段名称
        message: 错误消息
    
    Returns:
        tuple: (jsonify_response, http_status)
    """
    return create_error_response(
        error_code='VALIDATION_ERROR',
        message=message,
        details={'field': field_name},
        suggestion=[
            f'请检查 {field_name} 字段',
            '参考 API 文档确认格式要求'
        ]
    )


def handle_database_error(error, operation='数据库操作'):
    """
    处理数据库错误
    
    Args:
        error: 异常对象
        operation: 操作类型
    
    Returns:
        tuple: (jsonify_response, http_status)
    """
    error_msg = str(error).lower()
    
    if 'connection' in error_msg or 'connect' in error_msg:
        return create_error_response(
            error_code='DATABASE_CONNECTION_ERROR',
            message='数据库连接失败',
            original_error=error
        )
    else:
        return create_error_response(
            error_code='DATABASE_ERROR',
            message=f'{operation}失败',
            original_error=error
        )


def create_success_response(data=None, message='操作成功', code='SUCCESS'):
    """
    创建统一的成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        code: 成功代码
    
    Returns:
        tuple: (jsonify_response, http_status)
    """
    response_data = {
        'status': 'success',
        'message': message,
        'code': code
    }
    
    if data is not None:
        response_data['data'] = data
    
    return jsonify(response_data), 200


# 装饰器：自动错误处理
def handle_errors(default_error_code='INTERNAL_SERVER_ERROR'):
    """
    错误处理装饰器
    
    Args:
        default_error_code: 默认错误代码
    
    Returns:
        decorator function
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                api_logger.error(f"Unhandled error in {f.__name__}: {str(e)}")
                return create_error_response(
                    error_code=default_error_code,
                    original_error=e
                )[0], ERROR_REGISTRY.get(default_error_code, {}).get('http_status', 500)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


# 装饰器：API 异常处理（兼容旧代码）
def handle_api_exceptions(f):
    """
    API 异常处理装饰器（向后兼容）
    
    自动捕获 API 处理过程中的异常并返回结构化错误响应
    
    Args:
        f: 被装饰的函数
    
    Returns:
        wrapper function
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            api_logger.error(f"API exception in {f.__name__}: {str(e)}")
            error_msg = str(e).lower()
            
            # 根据错误类型返回相应的响应
            if 'timeout' in error_msg:
                return create_error_response(
                    error_code='AI_TIMEOUT',
                    message='AI 平台响应超时',
                    suggestion=['请稍后重试', '尝试使用其他 AI 模型', '检查网络连接'],
                    details={'error': str(e)}
                )[0], 504
            elif 'api key' in error_msg or 'authentication' in error_msg:
                return create_error_response(
                    error_code='AI_API_KEY_INVALID',
                    message='AI API 密钥无效',
                    suggestion=['请联系管理员更新 API 密钥', '检查密钥是否过期'],
                    details={'error': str(e)}
                )[0], 401
            elif 'rate limit' in error_msg or 'too many requests' in error_msg:
                return create_error_response(
                    error_code='AI_RATE_LIMIT_EXCEEDED',
                    message='AI 平台请求过于频繁',
                    suggestion=['请等待 1 分钟后重试', '减少并发请求数量'],
                    details={'error': str(e)}
                )[0], 429
            elif 'validation' in error_msg or 'invalid' in error_msg:
                return create_error_response(
                    error_code='VALIDATION_ERROR',
                    message='输入数据格式错误',
                    suggestion=['请检查品牌名称是否正确', '确认已选择 AI 模型', '验证问题格式是否完整'],
                    details={'error': str(e)}
                )[0], 400
            else:
                return create_error_response(
                    error_code='TASK_EXECUTION_FAILED',
                    message='诊断执行失败',
                    suggestion=['查看历史记录', '重新发起诊断', '减少 AI 模型数量'],
                    details={'error': str(e)}
                )[0], 500
    return wrapper
