"""
调试管理器
P1 修复：恢复缺失的调试模块
"""

from wechat_backend.logging_config import api_logger


class DebugManager:
    """调试管理器类"""
    
    def __init__(self):
        self.debug_mode = False
    
    def log(self, message, **kwargs):
        """记录调试日志"""
        if self.debug_mode:
            api_logger.debug(f"[DEBUG] {message}", **kwargs)
    
    def enable(self):
        """启用调试模式"""
        self.debug_mode = True
        api_logger.info("Debug mode enabled")
    
    def disable(self):
        """禁用调试模式"""
        self.debug_mode = False
        api_logger.info("Debug mode disabled")


# 全局实例
_debug_manager = None


def get_debug_manager():
    """获取调试管理器实例"""
    global _debug_manager
    if _debug_manager is None:
        _debug_manager = DebugManager()
    return _debug_manager


__all__ = [
    'DebugManager',
    'get_debug_manager',
    'debug_log',
    'ai_io_log',
    'status_flow_log',
    'exception_log'
]


# =============================================================================
# 兼容旧代码的函数
# =============================================================================

def debug_log(*args, **kwargs):
    """
    调试日志（兼容旧代码）
    
    Args:
        *args: 位置参数（消息部分）
        **kwargs: 额外参数
    """
    message = ' '.join(str(arg) for arg in args)
    api_logger.debug(f"[DEBUG] {message}", **kwargs)


def ai_io_log(*args, **kwargs):
    """
    AI I/O 日志

    Args:
        *args: 位置参数（消息部分）
        **kwargs: 额外参数
    """
    message = ' '.join(str(arg) for arg in args)
    api_logger.info(f"[AI I/O] {message}", **kwargs)


def debug_log_ai_io(tag, execution_id, content, message=""):
    """
    AI I/O 调试日志（4 个参数版本）
    
    Args:
        tag (str): 标签/模块名
        execution_id (str): 执行 ID
        content (str): 内容（prompt 或 response 摘要）
        message (str): 额外消息
    """
    api_logger.debug(f"[AI I/O] [{tag}] [ID:{execution_id}] {message}: {content}")


def status_flow_log(*args, **kwargs):
    """
    状态流日志
    
    Args:
        *args: 位置参数（消息部分）
        **kwargs: 额外参数
    """
    message = ' '.join(str(arg) for arg in args)
    api_logger.debug(f"[STATUS] {message}", **kwargs)


def exception_log(*args, **kwargs):
    """
    异常日志
    
    Args:
        *args: 位置参数（消息部分）
        **kwargs: 额外参数
    """
    message = ' '.join(str(arg) for arg in args)
    api_logger.error(f"[EXCEPTION] {message}", **kwargs)
