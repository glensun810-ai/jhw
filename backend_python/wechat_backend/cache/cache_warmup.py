"""
缓存预热核心模块

功能：
- 缓存预热器
- 预热任务执行
- 预热进度跟踪
- 预热指标统计

参考：P2-7: 智能缓存预热未实现
"""

import time
import threading
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from wechat_backend.logging_config import api_logger, db_logger
from config.config_cache_warmup import CacheWarmupConfig, cache_warmup_config


class CacheWarmupMetrics:
    """缓存预热指标"""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_tasks: int = 0
        self.completed_tasks: int = 0
        self.failed_tasks: int = 0
        self.cached_items: int = 0
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        duration = 0
        if self.start_time:
            if self.end_time:
                duration = self.end_time - self.start_time
            else:
                duration = time.time() - self.start_time
        
        return {
            'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'duration_seconds': round(duration, 2),
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'cached_items': self.cached_items,
            'success_rate': round(self.completed_tasks / self.total_tasks * 100, 2) if self.total_tasks > 0 else 0,
            'errors': self.errors[-10:],  # 只保留最近 10 个错误
        }


class CacheWarmupEngine:
    """
    缓存预热器
    
    功能：
    1. 执行预热任务
    2. 跟踪预热进度
    3. 统计预热指标
    4. 支持并发预热
    """
    
    def __init__(self):
        self._running = False
        self._current_metrics: Optional[CacheWarmupMetrics] = None
        self._last_metrics: Optional[CacheWarmupMetrics] = None
        self._warmup_tasks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
        api_logger.info("缓存预热器初始化")
    
    def register_task(self, name: str, func: Callable):
        """
        注册预热任务
        
        Args:
            name: 任务名称
            func: 预热函数
        """
        self._warmup_tasks[name] = func
        api_logger.debug(f"注册预热任务：{name}")
    
    def execute_warmup(self, tasks: List[str] = None, concurrent: bool = False) -> CacheWarmupMetrics:
        """
        执行缓存预热
        
        Args:
            tasks: 要执行的任务列表（None 表示执行所有注册的任务）
            concurrent: 是否并发执行
            
        Returns:
            预热指标
        """
        if not cache_warmup_config.is_warmup_enabled():
            api_logger.info("缓存预热未启用，跳过")
            metrics = CacheWarmupMetrics()
            metrics.errors.append("缓存预热未启用")
            return metrics
        
        with self._lock:
            if self._running:
                api_logger.warning("缓存预热正在执行中，跳过本次请求")
                metrics = CacheWarmupMetrics()
                metrics.errors.append("预热正在执行中")
                return metrics
            
            self._running = True
        
        # 初始化指标
        metrics = CacheWarmupMetrics()
        self._current_metrics = metrics
        metrics.start_time = time.time()
        
        # 确定要执行的任务
        if tasks is None:
            tasks = list(self._warmup_tasks.keys())
        
        metrics.total_tasks = len(tasks)
        
        api_logger.info(f"开始执行缓存预热，任务数：{len(tasks)}, 并发：{concurrent}")
        
        try:
            if concurrent and cache_warmup_config.CONCURRENT_WARMUP_ENABLED:
                # 并发执行
                self._execute_concurrent(tasks, metrics)
            else:
                # 顺序执行
                self._execute_sequential(tasks, metrics)
            
        except Exception as e:
            api_logger.error(f"缓存预热执行失败：{e}")
            metrics.errors.append(str(e))
        
        finally:
            metrics.end_time = time.time()
            self._running = False
            self._last_metrics = metrics
            self._current_metrics = None
            
            api_logger.info(
                f"缓存预热完成：耗时 {metrics.end_time - metrics.start_time:.2f}s, "
                f"成功 {metrics.completed_tasks}/{metrics.total_tasks}"
            )
        
        return metrics
    
    def _execute_sequential(self, tasks: List[str], metrics: CacheWarmupMetrics):
        """顺序执行预热任务"""
        for task_name in tasks:
            if not self._running:
                break
            
            self._execute_single_task(task_name, metrics)
    
    def _execute_concurrent(self, tasks: List[str], metrics: CacheWarmupMetrics):
        """并发执行预热任务"""
        thread_count = min(
            cache_warmup_config.WARMUP_THREAD_COUNT,
            len(tasks)
        )
        
        # 创建线程池
        threads = []
        task_queue = list(tasks)
        task_lock = threading.Lock()
        
        def worker():
            while True:
                with task_lock:
                    if not task_queue:
                        break
                    task_name = task_queue.pop(0)
                
                self._execute_single_task(task_name, metrics)
        
        # 启动线程
        for _ in range(thread_count):
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=cache_warmup_config.WARMUP_TIMEOUT_SECONDS)
    
    def _execute_single_task(self, task_name: str, metrics: CacheWarmupMetrics):
        """执行单个预热任务"""
        if task_name not in self._warmup_tasks:
            api_logger.warning(f"未知的预热任务：{task_name}")
            metrics.failed_tasks += 1
            metrics.errors.append(f"未知任务：{task_name}")
            return
        
        func = self._warmup_tasks[task_name]
        
        try:
            if cache_warmup_config.WARMUP_VERBOSE_LOGGING:
                api_logger.info(f"执行预热任务：{task_name}")
            
            # 执行预热函数
            result = func()
            
            # 更新指标
            metrics.completed_tasks += 1
            if isinstance(result, int):
                metrics.cached_items += result
            else:
                metrics.cached_items += 1
            
            if cache_warmup_config.WARMUP_VERBOSE_LOGGING:
                api_logger.info(f"预热任务完成：{task_name}")
                
        except Exception as e:
            api_logger.error(f"预热任务失败：{task_name}, 错误：{e}")
            metrics.failed_tasks += 1
            metrics.errors.append(f"{task_name}: {str(e)}")
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """获取当前预热指标"""
        if self._current_metrics:
            return self._current_metrics.to_dict()
        return None
    
    def get_last_metrics(self) -> Optional[Dict[str, Any]]:
        """获取上次预热指标"""
        if self._last_metrics:
            return self._last_metrics.to_dict()
        return None
    
    def is_running(self) -> bool:
        """检查是否正在执行预热"""
        return self._running
    
    def get_status(self) -> Dict[str, Any]:
        """获取预热器状态"""
        return {
            'running': self._running,
            'registered_tasks': list(self._warmup_tasks.keys()),
            'current_metrics': self.get_current_metrics(),
            'last_metrics': self.get_last_metrics(),
        }


# 全局预热器实例
_warmup_engine: Optional[CacheWarmupEngine] = None


def get_warmup_engine() -> CacheWarmupEngine:
    """获取预热器实例"""
    global _warmup_engine
    
    if _warmup_engine is None:
        _warmup_engine = CacheWarmupEngine()
    
    return _warmup_engine


def register_warmup_task(name: str, func: Callable):
    """
    注册预热任务（便捷函数）
    
    Args:
        name: 任务名称
        func: 预热函数
    """
    get_warmup_engine().register_task(name, func)


def execute_warmup(tasks: List[str] = None, concurrent: bool = True) -> Dict[str, Any]:
    """
    执行缓存预热（便捷函数）
    
    Args:
        tasks: 要执行的任务列表
        concurrent: 是否并发执行
        
    Returns:
        预热指标字典
    """
    engine = get_warmup_engine()
    metrics = engine.execute_warmup(tasks, concurrent)
    return metrics.to_dict()


def get_warmup_status() -> Dict[str, Any]:
    """获取预热状态"""
    return get_warmup_engine().get_status()
