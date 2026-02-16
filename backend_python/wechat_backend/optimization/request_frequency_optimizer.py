"""
API请求频率优化模块
用于控制和优化AI平台API请求频率，避免过度请求导致的问题
"""

import time
import threading
from typing import Dict, Optional
from collections import defaultdict
from enum import Enum

from ..logging_config import api_logger


class RequestPriority(Enum):
    """请求优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class RequestFrequencyOptimizer:
    """API请求频率优化器"""
    
    def __init__(self):
        self.request_times = defaultdict(list)  # 记录每个平台的请求时间
        self.lock = threading.Lock()
        self.global_min_interval = 1.0  # 全局最小间隔（秒）
        self.platform_intervals = {      # 各平台特定最小间隔
            'doubao': 2.0,               # 豆包需要较长间隔
            'qwen': 1.5,                # 通义千问
            'zhipu': 1.5,               # 智谱AI
            'deepseek': 1.0,            # DeepSeek
            'deepseekr1': 1.5,          # DeepSeek R1
            'chatgpt': 1.0,             # ChatGPT
            'gemini': 1.2               # Gemini
        }
        
    def should_delay_request(self, platform: str, priority: RequestPriority = RequestPriority.MEDIUM) -> float:
        """
        判断是否需要延迟请求以及延迟多久
        
        Args:
            platform: AI平台名称
            priority: 请求优先级
            
        Returns:
            float: 需要延迟的时间（秒），0表示无需延迟
        """
        with self.lock:
            # 获取平台特定的最小间隔
            min_interval = self.platform_intervals.get(platform.lower(), self.global_min_interval)
            
            # 对于低优先级请求，适当增加间隔
            if priority == RequestPriority.LOW:
                min_interval *= 1.5
            elif priority == RequestPriority.HIGH:
                min_interval *= 0.8  # 高优先级请求可以稍微缩短间隔
                
            # 获取该平台最近的请求时间
            recent_requests = self.request_times[platform]
            
            if not recent_requests:
                # 没有历史请求，可以直接执行
                self.request_times[platform].append(time.time())
                return 0.0
            
            # 获取最后一次请求时间
            last_request_time = recent_requests[-1]
            time_since_last = time.time() - last_request_time
            
            if time_since_last < min_interval:
                # 需要延迟
                delay_needed = min_interval - time_since_last
                # 记录这次虚拟的"计划"请求时间
                self.request_times[platform].append(time.time() + delay_needed)
                return delay_needed
            else:
                # 不需要延迟，记录实际请求时间
                self.request_times[platform].append(time.time())
                return 0.0
    
    def cleanup_old_records(self, max_age_seconds: int = 300):  # 5分钟
        """清理过期的请求记录"""
        with self.lock:
            current_time = time.time()
            for platform, times in self.request_times.items():
                # 保留最近的请求记录
                recent_times = [t for t in times if current_time - t <= max_age_seconds]
                self.request_times[platform] = recent_times
    
    def get_current_frequency(self, platform: str, window_seconds: int = 60) -> float:
        """获取指定平台在指定时间窗口内的请求频率（次/分钟）"""
        with self.lock:
            current_time = time.time()
            recent_requests = [
                t for t in self.request_times[platform] 
                if current_time - t <= window_seconds
            ]
            return len(recent_requests) / (window_seconds / 60.0)  # 转换为每分钟的频率
    
    def force_reset_platform(self, platform: str):
        """强制重置指定平台的请求计数"""
        with self.lock:
            self.request_times[platform] = []


# 全局实例
request_frequency_optimizer = RequestFrequencyOptimizer()


def optimize_request_frequency(platform: str, priority: RequestPriority = RequestPriority.MEDIUM):
    """
    优化API请求频率的装饰器
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 检查是否需要延迟
            delay_time = request_frequency_optimizer.should_delay_request(platform, priority)
            
            if delay_time > 0:
                api_logger.info(f"Delaying request to {platform} for {delay_time:.2f}s due to frequency control")
                time.sleep(delay_time)
            
            # 执行原始函数
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_platform_frequency_info(platform: str) -> Dict:
    """获取平台频率信息"""
    return {
        'frequency_per_minute': request_frequency_optimizer.get_current_frequency(platform),
        'last_request_time': request_frequency_optimizer.request_times[platform][-1] if request_frequency_optimizer.request_times[platform] else None,
        'total_recent_requests': len(request_frequency_optimizer.request_times[platform])
    }


def cleanup_frequency_records():
    """清理过期的频率记录"""
    request_frequency_optimizer.cleanup_old_records()