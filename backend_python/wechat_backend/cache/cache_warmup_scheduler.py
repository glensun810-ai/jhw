"""
定时任务调度器

功能：
- cron 表达式解析
- 定时任务调度
- 后台调度线程
- 任务执行管理

参考：P2-7: 智能缓存预热未实现
"""

import sys
import time
import threading
import re
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from wechat_backend.logging_config import api_logger
from config.config_cache_warmup import cache_warmup_config


class CronParser:
    """
    Cron 表达式解析器
    
    支持格式：分 时 日 月 周
    例如：0 3 * * * 表示每天凌晨 3 点
    """
    
    @staticmethod
    def parse(expression: str) -> Dict[str, Any]:
        """
        解析 cron 表达式
        
        Args:
            expression: cron 表达式
            
        Returns:
            解析后的字典
        """
        parts = expression.strip().split()
        
        if len(parts) != 5:
            raise ValueError(f"无效的 cron 表达式：{expression}")
        
        return {
            'minute': CronParser._parse_field(parts[0], 0, 59),
            'hour': CronParser._parse_field(parts[1], 0, 23),
            'day': CronParser._parse_field(parts[2], 1, 31),
            'month': CronParser._parse_field(parts[3], 1, 12),
            'weekday': CronParser._parse_field(parts[4], 0, 6),  # 0=Sunday
        }
    
    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """解析 cron 字段"""
        if field == '*':
            return list(range(min_val, max_val + 1))
        
        values = []
        for part in field.split(','):
            if '-' in part:
                # 范围：1-5
                start, end = map(int, part.split('-'))
                values.extend(range(start, end + 1))
            elif '/' in part:
                # 步长：*/5 或 0-30/5
                range_part, step = part.split('/')
                if range_part == '*':
                    start, end = min_val, max_val
                else:
                    start, end = map(int, range_part.split('-')) if '-' in range_part else (int(range_part), max_val)
                values.extend(range(start, end + 1, int(step)))
            else:
                # 单个值：5
                values.append(int(part))
        
        return [v for v in values if min_val <= v <= max_val]
    
    @staticmethod
    def get_next_run_time(cron_config: Dict[str, Any], from_time: datetime = None) -> datetime:
        """
        计算下次运行时间
        
        Args:
            cron_config: 解析后的 cron 配置
            from_time: 起始时间
            
        Returns:
            下次运行时间
        """
        if from_time is None:
            from_time = datetime.now()
        
        # 从下一分钟开始查找
        candidate = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # 最多查找一年
        max_iterations = 366 * 24 * 60
        
        for _ in range(max_iterations):
            if CronParser._matches(candidate, cron_config):
                return candidate
            candidate += timedelta(minutes=1)
        
        raise ValueError("无法找到匹配的运行时间")
    
    @staticmethod
    def _matches(dt: datetime, cron_config: Dict[str, Any]) -> bool:
        """检查时间是否匹配 cron 配置"""
        return (
            dt.minute in cron_config['minute'] and
            dt.hour in cron_config['hour'] and
            dt.day in cron_config['day'] and
            dt.month in cron_config['month'] and
            dt.weekday() in cron_config['weekday']
        )


class TaskScheduler:
    """
    任务调度器
    
    功能：
    1. cron 表达式调度
    2. 间隔调度
    3. 后台线程执行
    4. 任务管理
    """
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        api_logger.info("任务调度器初始化")
    
    def add_cron_task(self, name: str, func: Callable, cron_expression: str):
        """
        添加 cron 任务
        
        Args:
            name: 任务名称
            func: 任务函数
            cron_expression: cron 表达式
        """
        cron_config = CronParser.parse(cron_expression)
        next_run = CronParser.get_next_run_time(cron_config)
        
        self._tasks[name] = {
            'name': name,
            'func': func,
            'type': 'cron',
            'cron_config': cron_config,
            'cron_expression': cron_expression,
            'next_run': next_run,
            'last_run': None,
            'run_count': 0,
            'enabled': True,
        }
        
        api_logger.info(f"添加 cron 任务：{name}, cron={cron_expression}, 下次运行={next_run}")
    
    def add_interval_task(self, name: str, func: Callable, interval_minutes: int):
        """
        添加间隔任务
        
        Args:
            name: 任务名称
            func: 任务函数
            interval_minutes: 间隔分钟数
        """
        next_run = datetime.now() + timedelta(minutes=interval_minutes)
        
        self._tasks[name] = {
            'name': name,
            'func': func,
            'type': 'interval',
            'interval_minutes': interval_minutes,
            'next_run': next_run,
            'last_run': None,
            'run_count': 0,
            'enabled': True,
        }
        
        api_logger.info(f"添加间隔任务：{name}, interval={interval_minutes}分钟")
    
    def remove_task(self, name: str):
        """移除任务"""
        if name in self._tasks:
            del self._tasks[name]
            api_logger.info(f"移除任务：{name}")
    
    def enable_task(self, name: str):
        """启用任务"""
        if name in self._tasks:
            self._tasks[name]['enabled'] = True
            api_logger.info(f"启用任务：{name}")
    
    def disable_task(self, name: str):
        """禁用任务"""
        if name in self._tasks:
            self._tasks[name]['enabled'] = False
            api_logger.info(f"禁用任务：{name}")
    
    def start(self):
        """启动调度器"""
        if self._running:
            api_logger.warning("调度器已在运行中")
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run, daemon=True)
        self._scheduler_thread.start()
        
        api_logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5.0)
        
        api_logger.info("任务调度器已停止")
    
    def _run(self):
        """调度器主循环"""
        api_logger.info("调度器主循环启动")
        
        while self._running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                api_logger.error(f"调度器执行失败：{e}")
            
            # 每分钟检查一次
            time.sleep(60)
    
    def _check_and_run_tasks(self):
        """检查并执行到期的任务"""
        now = datetime.now()
        
        with self._lock:
            for name, task in list(self._tasks.items()):
                if not task['enabled']:
                    continue
                
                if now >= task['next_run']:
                    self._run_task(name, task)
    
    def _run_task(self, name: str, task: Dict[str, Any]):
        """执行任务"""
        try:
            api_logger.info(f"执行任务：{name}")
            
            # 执行任务函数
            task['func']()
            
            # 更新任务状态
            task['last_run'] = datetime.now()
            task['run_count'] += 1
            
            # 计算下次运行时间
            if task['type'] == 'cron':
                task['next_run'] = CronParser.get_next_run_time(
                    task['cron_config'],
                    task['last_run']
                )
            elif task['type'] == 'interval':
                task['next_run'] = task['last_run'] + timedelta(
                    minutes=task['interval_minutes']
                )
            
            api_logger.info(
                f"任务执行完成：{name}, "
                f"下次运行={task['next_run']}"
            )
            
        except Exception as e:
            api_logger.error(f"任务执行失败：{name}, 错误：{e}")
            
            # 即使失败也更新下次运行时间
            if task['type'] == 'interval':
                task['next_run'] = datetime.now() + timedelta(
                    minutes=task['interval_minutes']
                )
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        tasks_status = []
        
        for name, task in self._tasks.items():
            tasks_status.append({
                'name': name,
                'type': task['type'],
                'enabled': task['enabled'],
                'last_run': task['last_run'].isoformat() if task['last_run'] else None,
                'next_run': task['next_run'].isoformat() if task['next_run'] else None,
                'run_count': task['run_count'],
            })
        
        return {
            'running': self._running,
            'tasks': tasks_status,
        }
    
    def get_tasks(self) -> List[str]:
        """获取任务列表"""
        return list(self._tasks.keys())


# 全局调度器实例
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器实例"""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = TaskScheduler()
    
    return _scheduler


def start_scheduler():
    """启动调度器"""
    get_scheduler().start()


def stop_scheduler():
    """停止调度器"""
    get_scheduler().stop()


def get_scheduler_status() -> Dict[str, Any]:
    """获取调度器状态"""
    return get_scheduler().get_status()
