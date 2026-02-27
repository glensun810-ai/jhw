"""
超时管理服务

为诊断任务提供超时保护机制，确保任务不会无限期执行。

核心功能:
1. 为每个诊断任务启动 10 分钟超时计时器
2. 超时后自动触发状态流转到 TIMEOUT 状态
3. 任务完成后自动取消计时器
4. 线程安全的计时器管理

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import threading
import logging
from datetime import datetime
from typing import Dict, Callable, Optional
from wechat_backend.v2.exceptions import DiagnosisTimeoutError
from wechat_backend.logging_config import api_logger

logger = logging.getLogger(__name__)


class TimeoutManager:
    """
    超时管理器
    
    职责:
    1. 管理所有诊断任务的超时计时器
    2. 超时后调用回调函数
    3. 提供计时器状态查询
    4. 线程安全的计时器操作
    
    使用示例:
        >>> manager = TimeoutManager()
        >>> def on_timeout(execution_id):
        ...     print(f"Task {execution_id} timed out")
        >>> manager.start_timer("exec-123", on_timeout, timeout_seconds=600)
        >>> manager.cancel_timer("exec-123")
    """
    
    # ==================== 常量定义 ====================
    
    MAX_EXECUTION_TIME: int = 600  # 最大执行时间：10 分钟（秒）
    
    def __init__(self):
        """
        初始化超时管理器
        
        Attributes:
            timers: 执行 ID 到计时器的映射
            start_times: 执行 ID 到开始时间的映射
            timeouts: 执行 ID 到超时时间的映射
            lock: 线程锁，保护共享数据
        """
        self._timers: Dict[str, threading.Timer] = {}
        self._start_times: Dict[str, datetime] = {}
        self._timeouts: Dict[str, int] = {}  # 记录每个计时器的超时时间
        self._lock: threading.Lock = threading.Lock()
        
        api_logger.info(
            "timeout_manager_initialized",
            extra={
                'event': 'timeout_manager_initialized',
                'max_execution_time': self.MAX_EXECUTION_TIME,
            }
        )
    
    def start_timer(
        self,
        execution_id: str,
        on_timeout: Callable[[str], None],
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """
        启动超时计时器
        
        Args:
            execution_id: 任务执行 ID
            on_timeout: 超时回调函数，接收 execution_id 参数
            timeout_seconds: 超时时间（秒），默认使用 MAX_EXECUTION_TIME
            
        Raises:
            ValueError: 如果 execution_id 已存在计时器
            TypeError: 如果 on_timeout 不是可调用对象
            
        Example:
            >>> manager = TimeoutManager()
            >>> manager.start_timer("exec-123", lambda eid: print(f"{eid} timeout"))
        """
        if not callable(on_timeout):
            raise TypeError("on_timeout must be a callable")
        
        timeout = timeout_seconds if timeout_seconds is not None else self.MAX_EXECUTION_TIME
        
        with self._lock:
            # 检查是否已存在计时器
            if execution_id in self._timers:
                api_logger.warning(
                    "timeout_timer_already_exists",
                    extra={
                        'event': 'timeout_timer_already_exists',
                        'execution_id': execution_id,
                    }
                )
                raise ValueError(f"Timer already exists for execution_id: {execution_id}")
            
            # 记录开始时间
            self._start_times[execution_id] = datetime.now()
            self._timeouts[execution_id] = timeout
            
            def timeout_handler() -> None:
                """超时处理函数"""
                try:
                    api_logger.warning(
                        "timeout_triggered",
                        extra={
                            'event': 'timeout_triggered',
                            'execution_id': execution_id,
                            'timeout_seconds': timeout,
                        }
                    )
                    on_timeout(execution_id)
                except Exception as e:
                    api_logger.error(
                        "timeout_handler_error",
                        extra={
                            'event': 'timeout_handler_error',
                            'execution_id': execution_id,
                            'error': str(e),
                            'error_type': type(e).__name__,
                        }
                    )
                finally:
                    # 清理资源
                    self._cleanup(execution_id)
            
            # 创建并启动计时器
            timer = threading.Timer(timeout, timeout_handler)
            timer.daemon = True  # 设置为守护线程，主线程退出时自动清理
            self._timers[execution_id] = timer
            timer.start()
            
            api_logger.info(
                "timeout_timer_started",
                extra={
                    'event': 'timeout_timer_started',
                    'execution_id': execution_id,
                    'timeout_seconds': timeout,
                    'max_execution_time': self.MAX_EXECUTION_TIME,
                }
            )
    
    def cancel_timer(self, execution_id: str) -> bool:
        """
        取消超时计时器
        
        Args:
            execution_id: 任务执行 ID
            
        Returns:
            bool: 是否成功取消（False 表示计时器不存在或已触发）
            
        Example:
            >>> manager.cancel_timer("exec-123")
            True
        """
        with self._lock:
            if execution_id not in self._timers:
                api_logger.debug(
                    "timeout_timer_not_found",
                    extra={
                        'event': 'timeout_timer_not_found',
                        'execution_id': execution_id,
                    }
                )
                return False
            
            timer = self._timers[execution_id]
            timer.cancel()
            
            self._cleanup(execution_id)
            
            api_logger.info(
                "timeout_timer_cancelled",
                extra={
                    'event': 'timeout_timer_cancelled',
                    'execution_id': execution_id,
                }
            )
            return True
    
    def get_remaining_time(self, execution_id: str) -> int:
        """
        获取剩余时间（秒）
        
        Args:
            execution_id: 任务执行 ID
            
        Returns:
            int: 剩余秒数，0 表示已超时或不存在
            
        Example:
            >>> manager.get_remaining_time("exec-123")
            580
        """
        with self._lock:
            if execution_id not in self._start_times:
                return 0
            
            # 使用该计时器的自定义超时时间
            timeout = self._timeouts.get(execution_id, self.MAX_EXECUTION_TIME)
            
            elapsed = (datetime.now() - self._start_times[execution_id]).total_seconds()
            remaining = max(0, timeout - int(elapsed))
            return remaining
    
    def is_timer_active(self, execution_id: str) -> bool:
        """
        检查计时器是否活跃
        
        Args:
            execution_id: 任务执行 ID
            
        Returns:
            bool: True 表示计时器存在且活跃
            
        Example:
            >>> manager.is_timer_active("exec-123")
            True
        """
        with self._lock:
            return execution_id in self._timers
    
    def _cleanup(self, execution_id: str) -> None:
        """
        清理计时器资源（内部方法）
        
        Args:
            execution_id: 任务执行 ID
        """
        if execution_id in self._timers:
            del self._timers[execution_id]
        
        if execution_id in self._start_times:
            del self._start_times[execution_id]
        
        if execution_id in self._timeouts:
            del self._timeouts[execution_id]
        
        api_logger.debug(
            "timeout_timer_cleaned",
            extra={
                'event': 'timeout_timer_cleaned',
                'execution_id': execution_id,
            }
        )
    
    def get_active_timers_count(self) -> int:
        """
        获取活跃的计时器数量
        
        Returns:
            int: 活跃计时器数量
        """
        with self._lock:
            return len(self._timers)
    
    def cancel_all_timers(self) -> int:
        """
        取消所有计时器
        
        Returns:
            int: 取消的计时器数量
        """
        with self._lock:
            count = len(self._timers)
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
            self._start_times.clear()
            
            api_logger.info(
                "timeout_all_timers_cancelled",
                extra={
                    'event': 'timeout_all_timers_cancelled',
                    'count': count,
                }
            )
            return count
