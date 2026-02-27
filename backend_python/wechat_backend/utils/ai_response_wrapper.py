#!/usr/bin/env python3
"""
AI响应日志记录包装器
用于在AI适配器中统一记录响应到增强版日志系统
"""

from typing import Optional, Dict, Any
from wechat_backend.utils.ai_response_logger_v3 import log_ai_response
from wechat_backend.security.auth import get_current_user_id


def get_execution_context():
    """
    获取当前执行上下文信息
    """
    # 从Flask g对象获取上下文信息
    try:
        from flask import g, request
        context = {}

        # 获取请求相关信息
        if request:
            context['request_id'] = getattr(request, 'id', None)
            context['request_method'] = request.method
            context['request_url'] = request.url
            context['remote_addr'] = request.remote_addr

        # 获取用户相关信息
        user_id = get_current_user_id()
        if user_id:
            context['user_id'] = user_id

        return context
    except Exception as e:
        api_logger.error(f"Error getting execution context: {e}", exc_info=True)
        # 如果无法获取上下文，返回空字典
        return {}


def log_ai_response_with_context(
    question: str,
    response: str,
    platform: str,
    model: str,
    success: bool = True,
    error_message: Optional[str] = None,
    error_type: Optional[str] = None,
    latency_ms: Optional[int] = None,
    tokens_used: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    brand: Optional[str] = None,
    competitor: Optional[str] = None,
    execution_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,  # 优先使用传入的用户ID
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    使用上下文信息记录AI响应

    Args:
        question: 问题内容
        response: 响应内容
        platform: 平台名称
        model: 模型名称
        success: 是否成功
        error_message: 错误消息
        error_type: 错误类型
        latency_ms: 延迟（毫秒）
        tokens_used: 使用的总token数
        prompt_tokens: 输入token数
        completion_tokens: 输出token数
        brand: 品牌名称
        competitor: 竞品名称
        execution_id: 执行ID
        session_id: 会话ID
        user_id: 用户ID（如果未提供，则尝试从上下文中获取）
        metadata: 额外元数据
        **kwargs: 其他参数
    """
    # 如果没有提供用户ID，尝试从当前请求上下文获取
    if not user_id:
        user_id = get_current_user_id()
        if not user_id:
            # 如果无法获取用户ID，使用执行ID或标记为匿名
            user_id = execution_id or 'anonymous'

    # 如果metadata为空，初始化为空字典
    if metadata is None:
        metadata = {}

    # 添加执行上下文信息
    context_info = get_execution_context()
    if context_info:
        metadata.update(context_info)

    # 调用增强版日志记录器（修正函数名）
    return log_ai_response(
        question=question,
        response=response,
        platform=platform,
        model=model,
        success=success,
        error_message=error_message,
        error_type=error_type,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        brand=brand,
        competitor=competitor,
        execution_id=execution_id,
        session_id=session_id,
        user_id=user_id,
        metadata=metadata,
        **kwargs
    )


def get_enhanced_logger():
    """获取增强版日志记录器实例"""
    from utils.ai_response_logger_enhanced import get_enhanced_logger
    return get_enhanced_logger()


def get_user_responses(user_id: str, **kwargs):
    """获取特定用户的响应记录"""
    logger = get_enhanced_logger()
    return logger.get_user_responses(user_id, **kwargs)


def get_system_responses(**kwargs):
    """获取系统级别的响应记录"""
    logger = get_enhanced_logger()
    return logger.get_system_responses(**kwargs)


def get_user_statistics(user_id: str, **kwargs):
    """获取特定用户的统计信息"""
    logger = get_enhanced_logger()
    return logger.get_user_statistics(user_id, **kwargs)


def get_all_users_statistics(**kwargs):
    """获取所有用户的统计信息"""
    logger = get_enhanced_logger()
    return logger.get_all_users_statistics(**kwargs)


# 便捷函数
def log_detailed_response(
    question: str,
    response: str,
    platform: str,
    model: str,
    user_id: Optional[str] = None,
    **kwargs
):
    """
    记录详细响应信息的便捷函数
    """
    return log_ai_response_with_context(
        question=question,
        response=response,
        platform=platform,
        model=model,
        user_id=user_id,
        **kwargs
    )