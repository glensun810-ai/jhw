"""
日志模块
P1 修复：恢复缺失的日志模块
"""

from wechat_backend.logging_config import api_logger

# 调试开关
ENABLE_DEBUG_AI_CODE = True


def debug_log_ai_io(tag, execution_id, content, message=""):
    """
    AI I/O 调试日志

    Args:
        tag (str): 标签/模块名
        execution_id (str): 执行 ID
        content (str): 内容（prompt 或 response 摘要）
        message (str): 额外消息
    """
    if ENABLE_DEBUG_AI_CODE:
        api_logger.debug(f"[AI I/O] [{tag}] [ID:{execution_id}] {message}: {content}")


def debug_log_exception(tag, execution_id, error_message):
    """
    异常调试日志

    Args:
        tag (str): 标签/模块名
        execution_id (str): 执行 ID
        error_message (str): 错误消息
    """
    if ENABLE_DEBUG_AI_CODE:
        api_logger.error(f"[EXCEPTION] [{tag}] [ID:{execution_id}] {error_message}")


def debug_log_status_flow(tag, execution_id, message):
    """
    状态流调试日志

    Args:
        tag (str): 标签/模块名
        execution_id (str): 执行 ID
        message (str): 状态消息
    """
    if ENABLE_DEBUG_AI_CODE:
        api_logger.debug(f"[STATUS] [{tag}] [ID:{execution_id}] {message}")


def debug_log_debug_log(tag, execution_id, message):
    """
    通用调试日志

    Args:
        tag (str): 标签/模块名
        execution_id (str): 执行 ID
        message (str): 调试消息
    """
    if ENABLE_DEBUG_AI_CODE:
        api_logger.debug(f"[DEBUG] [{tag}] [ID:{execution_id}] {message}")


__all__ = [
    'debug_log_ai_io',
    'debug_log_exception',
    'debug_log_status_flow',
    'debug_log_debug_log',
    'ENABLE_DEBUG_AI_CODE'
]
