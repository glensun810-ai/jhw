"""
统一后台服务管理器 - BackgroundServiceManager

功能：
1. 统一管理所有后台清理任务（SSE、缓存、导出文件等）
2. 避免并发写入数据库导致的 database is locked 错误
3. 提供统一的生命周期管理（启动、停止、重启）
4. 提供服务健康状态监控

设计原则：
- 单一调度线程，避免多个清理线程同时运行
- 任务错峰执行，避免同一时间并发操作数据库
- 统一异常处理，单个任务失败不影响其他任务
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from wechat_backend.logging_config import api_logger


class ServiceStatus(Enum):
    """服务状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ScheduledTask:
    """计划任务配置"""
    name: str
    func: Callable[[], Any]
    interval_seconds: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    enabled: bool = True


class BackgroundServiceManager:
    """
    统一后台服务管理器

    管理所有后台清理和维护任务，避免资源竞争和数据库锁定问题
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._status = ServiceStatus.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # 统计信息
        self._start_time: Optional[datetime] = None
        self._total_executions = 0
        self._total_errors = 0

    def register_task(
        self,
        name: str,
        func: Callable[[], Any],
        interval_seconds: int,
        enabled: bool = True
    ) -> 'BackgroundServiceManager':
        """
        注册计划任务

        Args:
            name: 任务名称
            func: 任务函数
            interval_seconds: 执行间隔（秒）
            enabled: 是否启用

        Returns:
            self（支持链式调用）
        """
        with self._lock:
            now = datetime.now()
            self._tasks[name] = ScheduledTask(
                name=name,
                func=func,
                interval_seconds=interval_seconds,
                next_run=now,  # 立即执行一次
                enabled=enabled
            )
            api_logger.info(f"[BackgroundService] 注册任务：{name} (interval={interval_seconds}s)")
        return self

    def unregister_task(self, name: str) -> bool:
        """
        注销计划任务

        Args:
            name: 任务名称

        Returns:
            是否成功注销
        """
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                api_logger.info(f"[BackgroundService] 注销任务：{name}")
                return True
            return False

    def enable_task(self, name: str) -> bool:
        """启用任务"""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = True
                api_logger.info(f"[BackgroundService] 启用任务：{name}")
                return True
            return False

    def disable_task(self, name: str) -> bool:
        """禁用任务"""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = False
                api_logger.info(f"[BackgroundService] 禁用任务：{name}")
                return True
            return False

    def start(self, stagger_seconds: int = 5):
        """
        启动后台服务管理器

        Args:
            stagger_seconds: 任务错峰间隔（秒），避免所有任务同时执行
        """
        with self._lock:
            if self._status == ServiceStatus.RUNNING:
                api_logger.warning("[BackgroundService] 服务已在运行中")
                return

            self._stop_event.clear()
            self._status = ServiceStatus.RUNNING
            self._start_time = datetime.now()
            
            # 设置任务的下次执行时间（错峰）
            now = datetime.now()
            for i, task in enumerate(self._tasks.values()):
                task.next_run = now.replace(second=0, microsecond=0)
                # 每个任务间隔 stagger_seconds 秒
                from datetime import timedelta
                task.next_run = task.next_run + timedelta(seconds=i * stagger_seconds)

        # 启动调度线程
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="BackgroundServiceManager"
        )
        self._thread.start()
        
        api_logger.info(
            f"[BackgroundService] 服务已启动，管理 {len(self._tasks)} 个任务，"
            f"错峰间隔 {stagger_seconds}秒"
        )

    def stop(self, timeout_seconds: float = 10.0):
        """
        停止后台服务管理器

        Args:
            timeout_seconds: 等待线程结束的超时时间
        """
        with self._lock:
            if self._status != ServiceStatus.RUNNING:
                return
            
            self._stop_event.set()
            self._status = ServiceStatus.STOPPED

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)
            if self._thread.is_alive():
                api_logger.warning("[BackgroundService] 停止超时，强制终止")
            else:
                api_logger.info("[BackgroundService] 服务已停止")

    def _scheduler_loop(self):
        """调度器主循环"""
        while not self._stop_event.is_set():
            try:
                self._execute_due_tasks()
            except Exception as e:
                api_logger.error(f"[BackgroundService] 调度器错误：{e}", exc_info=True)
            
            # 每秒检查一次
            self._stop_event.wait(1.0)

    def _execute_due_tasks(self):
        """执行到期的任务"""
        now = datetime.now()
        
        with self._lock:
            due_tasks = [
                task for task in self._tasks.values()
                if task.enabled and task.next_run and task.next_run <= now
            ]
        
        # 按 next_run 时间排序，确保顺序执行
        due_tasks.sort(key=lambda t: t.next_run or now)
        
        for task in due_tasks:
            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask):
        """执行单个任务"""
        try:
            api_logger.debug(f"[BackgroundService] 执行任务：{task.name}")
            task.func()
            
            with self._lock:
                task.run_count += 1
                task.last_run = datetime.now()
                task.next_run = datetime.now().replace(second=0, microsecond=0)
                from datetime import timedelta
                task.next_run = task.next_run + timedelta(seconds=task.interval_seconds)
                self._total_executions += 1
                
        except Exception as e:
            api_logger.error(
                f"[BackgroundService] 任务执行失败：{task.name}, 错误：{e}",
                exc_info=True
            )
            with self._lock:
                task.error_count += 1
                task.last_error = str(e)
                self._total_errors += 1

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        with self._lock:
            tasks_status = {}
            for name, task in self._tasks.items():
                tasks_status[name] = {
                    'enabled': task.enabled,
                    'run_count': task.run_count,
                    'error_count': task.error_count,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'last_error': task.last_error,
                    'interval_seconds': task.interval_seconds
                }
            
            return {
                'status': self._status.value,
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                'total_tasks': len(self._tasks),
                'enabled_tasks': sum(1 for t in self._tasks.values() if t.enabled),
                'total_executions': self._total_executions,
                'total_errors': self._total_errors,
                'tasks': tasks_status
            }


# =============================================================================
# 全局单例
# =============================================================================

_service_manager: Optional[BackgroundServiceManager] = None
_manager_lock = threading.Lock()


def get_background_service_manager() -> BackgroundServiceManager:
    """获取全局后台服务管理器"""
    global _service_manager
    if _service_manager is None:
        with _manager_lock:
            if _service_manager is None:
                _service_manager = BackgroundServiceManager()
    return _service_manager


def reset_background_service_manager():
    """重置全局后台服务管理器（用于测试）"""
    global _service_manager
    with _manager_lock:
        if _service_manager:
            _service_manager.stop()
        _service_manager = None


# =============================================================================
# 预定义的清理任务函数
# =============================================================================

def create_sse_cleanup_task(sse_manager_getter: Callable) -> Callable:
    """
    创建 SSE 清理任务

    Args:
        sse_manager_getter: 获取 SSE 管理器的函数

    Returns:
        清理任务函数
    """
    def cleanup():
        try:
            manager = sse_manager_getter()
            if manager:
                manager.cleanup_inactive()
                api_logger.debug("[BackgroundService] SSE 清理完成")
        except Exception as e:
            api_logger.error(f"[BackgroundService] SSE 清理失败：{e}")
    
    return cleanup


def create_export_cleanup_task(export_service_getter: Callable, max_age_hours: int = 24) -> Callable:
    """
    创建导出文件清理任务

    Args:
        export_service_getter: 获取导出服务的函数
        max_age_hours: 保留最大小时数

    Returns:
        清理任务函数
    """
    def cleanup():
        try:
            service = export_service_getter()
            if service:
                cleaned = service.cleanup_old_tasks(max_age_hours)
                api_logger.info(f"[BackgroundService] 导出文件清理：移除 {cleaned} 个旧任务")
        except Exception as e:
            api_logger.error(f"[BackgroundService] 导出文件清理失败：{e}")
    
    return cleanup


def create_cache_maintenance_task(cache_maintenance_func: Callable) -> Callable:
    """
    创建缓存维护任务

    Args:
        cache_maintenance_func: 缓存维护函数

    Returns:
        维护任务函数
    """
    def maintenance():
        try:
            cache_maintenance_func()
            api_logger.debug("[BackgroundService] 缓存维护完成")
        except Exception as e:
            api_logger.error(f"[BackgroundService] 缓存维护失败：{e}")
    
    return maintenance


# =============================================================================
# 初始化函数
# =============================================================================

def initialize_background_services():
    """
    初始化所有后台服务

    应该在 app.py 启动时调用，替代各个独立的清理线程
    """
    manager = get_background_service_manager()
    
    # 注册 SSE 清理任务（每 60 秒）
    try:
        from wechat_backend.services.sse_service_v2 import get_sse_manager
        manager.register_task(
            name="sse_cleanup",
            func=create_sse_cleanup_task(get_sse_manager),
            interval_seconds=60,
            enabled=True
        )
    except Exception as e:
        api_logger.warning(f"[BackgroundService] 注册 SSE 清理任务失败：{e}")
    
    # 注册导出文件清理任务（每小时）
    try:
        from wechat_backend.services.async_export_service import get_async_export_service
        manager.register_task(
            name="export_cleanup",
            func=create_export_cleanup_task(get_async_export_service, max_age_hours=24),
            interval_seconds=3600,  # 1 小时
            enabled=True
        )
    except Exception as e:
        api_logger.warning(f"[BackgroundService] 注册导出清理任务失败：{e}")
    
    # 注册缓存维护任务（每 5 分钟）
    try:
        from wechat_backend.cache.api_cache import _cleanup_expired_entries
        manager.register_task(
            name="cache_maintenance",
            func=create_cache_maintenance_task(_cleanup_expired_entries),
            interval_seconds=300,  # 5 分钟
            enabled=True
        )
    except Exception as e:
        api_logger.warning(f"[BackgroundService] 注册缓存维护任务失败：{e}")
    
    # 启动服务管理器（任务错峰 10 秒）
    manager.start(stagger_seconds=10)
    
    api_logger.info("✅ 统一后台服务管理器已启动")
    
    return manager
