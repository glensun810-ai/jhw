"""
AI 调用超时处理模块

P1-014 新增：为 AI 调用添加超时保护，防止单个 AI 失败阻塞整个流程
"""

import asyncio
import aiohttp
from typing import Callable, Any, Optional
from functools import wraps
import time

from wechat_backend.logging_config import api_logger


class AITimeoutError(Exception):
    """AI 调用超时异常"""
    def __init__(self, model_name: str, timeout: int):
        self.model_name = model_name
        self.timeout = timeout
        super().__init__(f"AI 调用超时：{model_name} (超时 {timeout}秒)")


class AICallError(Exception):
    """AI 调用失败异常"""
    def __init__(self, model_name: str, message: str):
        self.model_name = model_name
        self.message = message
        super().__init__(f"AI 调用失败：{model_name} - {message}")


async def call_with_timeout(
    func: Callable,
    *args,
    timeout: int = 30,
    model_name: str = "unknown",
    **kwargs
) -> Any:
    """
    为 AI 调用添加超时保护
    
    参数:
    - func: 要执行的异步函数
    - timeout: 超时时间（秒）
    - model_name: 模型名称（用于日志）
    - args, kwargs: 传递给 func 的参数
    
    返回:
    - func 的返回值
    
    异常:
    - AITimeoutError: 超时时抛出
    - AICallError: 其他错误时抛出
    """
    try:
        # 使用 asyncio.wait_for 添加超时
        return await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        api_logger.error(f"[AI 超时] {model_name} 调用超时 ({timeout}秒)")
        raise AITimeoutError(model_name, timeout)
    except Exception as e:
        api_logger.error(f"[AI 错误] {model_name} 调用失败：{e}")
        raise AICallError(model_name, str(e))


def sync_call_with_timeout(
    func: Callable,
    *args,
    timeout: int = 30,
    model_name: str = "unknown",
    **kwargs
) -> Any:
    """
    为同步 AI 调用添加超时保护
    
    BUG-002 修复：使用 run_until_complete 而非 await
    
    参数:
    - func: 要执行的同步函数
    - timeout: 超时时间（秒）
    - model_name: 模型名称（用于日志）
    - args, kwargs: 传递给 func 的参数
    
    返回:
    - func 的返回值
    
    异常:
    - AITimeoutError: 超时时抛出
    - AICallError: 其他错误时抛出
    """
    import asyncio
    from asyncio import TimeoutError
    
    # BUG-002 修复：创建新的事件循环，使用 run_until_complete
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        
        # 使用 run_until_complete 而非 await
        result = loop.run_until_complete(
            asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: func(*args, **kwargs)
                ),
                timeout=timeout
            )
        )
        return result
        
    except TimeoutError:
        api_logger.error(f"[AI 超时] {model_name} 调用超时 ({timeout}秒)")
        raise AITimeoutError(model_name, timeout)
    except Exception as e:
        api_logger.error(f"[AI 错误] {model_name} 调用失败：{e}")
        raise AICallError(model_name, str(e))
    finally:
        # 清理事件循环
        loop.close()
        asyncio.set_event_loop(None)


def timeout_decorator(timeout: int = 30, model_name: str = "unknown"):
    """
    超时装饰器
    
    用法:
    @timeout_decorator(timeout=30, model_name="doubao")
    async def call_ai(...):
        ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await call_with_timeout(
                func,
                *args,
                timeout=timeout,
                model_name=model_name,
                **kwargs
            )
        return wrapper
    return decorator


class AITimeoutManager:
    """
    AI 超时管理器
    
    BUG-007 修复：添加线程锁，确保多线程安全
    
    统一管理所有 AI 调用的超时配置
    
    超时配置说明:
    - 整体执行超时：由 execute_nxm_test 的 timeout_seconds 参数控制（默认 300 秒）
    - 单个 AI 超时：由本管理器控制（默认 30 秒/模型）
    - 关系：单个 AI 超时 < 整体执行超时，确保单个失败不影响整体
    """
    
    # 默认超时配置（秒）
    DEFAULT_TIMEOUTS = {
        'deepseek': 30,
        'deepseekr1': 30,
        'qwen': 30,
        'doubao': 30,
        'chatgpt': 30,
        'gemini': 30,
        'zhipu': 30,
        'wenxin': 30,
        'default': 30
    }
    
    # BUG-007 修复：线程锁
    _lock = None
    
    @classmethod
    def _get_lock(cls):
        """获取线程锁（延迟初始化）"""
        if cls._lock is None:
            import threading
            cls._lock = threading.Lock()
        return cls._lock
    
    @classmethod
    def get_timeout(cls, model_name: str) -> int:
        """获取指定模型的超时配置（线程安全）"""
        # 读操作不需要锁，因为字典读取是原子操作
        return cls.DEFAULT_TIMEOUTS.get(model_name, cls.DEFAULT_TIMEOUTS['default'])
    
    @classmethod
    def set_timeout(cls, model_name: str, timeout: int):
        """设置指定模型的超时配置（线程安全）"""
        # BUG-007 修复：写操作需要锁
        with cls._get_lock():
            cls.DEFAULT_TIMEOUTS[model_name] = timeout
    
    @classmethod
    def get_all_timeouts(cls) -> dict:
        """获取所有超时配置（线程安全）"""
        # BUG-007 修复：返回副本，避免并发修改
        with cls._get_lock():
            return cls.DEFAULT_TIMEOUTS.copy()


# 单例实例
_timeout_manager = None
_timeout_manager_lock = None

def get_timeout_manager() -> AITimeoutManager:
    """
    获取超时管理器单例（线程安全）
    
    BUG-007 修复：使用双重检查锁定模式
    """
    global _timeout_manager, _timeout_manager_lock
    
    # 第一次检查（不需要锁）
    if _timeout_manager is not None:
        return _timeout_manager
    
    # 延迟初始化锁
    import threading
    if _timeout_manager_lock is None:
        _timeout_manager_lock = threading.Lock()
    
    # 加锁
    with _timeout_manager_lock:
        # 第二次检查（需要锁）
        if _timeout_manager is None:
            _timeout_manager = AITimeoutManager()
        
        return _timeout_manager
