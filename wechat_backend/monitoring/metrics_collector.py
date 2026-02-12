"""
API指标收集器
收集API调用的各种性能和安全指标
"""

import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    API_CALL = "api_call"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    SECURITY_EVENT = "security_event"


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, retention_minutes: int = 60):
        """
        初始化指标收集器
        :param retention_minutes: 指标保留分钟数
        """
        self.retention_delta = timedelta(minutes=retention_minutes)
        self.metrics = defaultdict(lambda: deque(maxlen=10000))  # 限制每个指标最多存储10000条记录
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.lock = threading.Lock()
        self.start_time = datetime.utcnow()
        
    def record_api_call(self, 
                       platform: str, 
                       endpoint: str, 
                       status_code: int, 
                       response_time: float,
                       tokens_used: int = 0,
                       request_size: int = 0):
        """记录API调用指标"""
        timestamp = datetime.utcnow()
        metric_data = {
            'timestamp': timestamp,
            'platform': platform,
            'endpoint': endpoint,
            'status_code': status_code,
            'response_time': response_time,
            'tokens_used': tokens_used,
            'request_size': request_size
        }
        
        with self.lock:
            self.metrics[MetricType.API_CALL.value].append(metric_data)
            self.counters[f'api_calls_total:{platform}'] += 1
            self.counters[f'api_calls_by_status:{platform}:{status_code}'] += 1
            
            # 记录响应时间
            self.metrics[MetricType.RESPONSE_TIME.value].append({
                'timestamp': timestamp,
                'platform': platform,
                'response_time': response_time
            })
    
    def record_error(self, platform: str, error_type: str, error_message: str = ""):
        """记录错误指标"""
        timestamp = datetime.utcnow()
        with self.lock:
            self.counters[f'errors_total:{platform}:{error_type}'] += 1
            self.metrics[MetricType.ERROR_RATE.value].append({
                'timestamp': timestamp,
                'platform': platform,
                'error_type': error_type,
                'error_message': error_message
            })
    
    def record_security_event(self, event_type: str, severity: str, details: Dict[str, Any]):
        """记录安全事件"""
        timestamp = datetime.utcnow()
        event_data = {
            'timestamp': timestamp,
            'event_type': event_type,
            'severity': severity,
            'details': details
        }
        
        with self.lock:
            self.metrics[MetricType.SECURITY_EVENT.value].append(event_data)
            self.counters[f'security_events:{event_type}:{severity}'] += 1
            logger.warning(f"Security event recorded: {event_type} [{severity}] - {details}")
    
    def increment_counter(self, name: str, amount: int = 1):
        """增加计数器"""
        with self.lock:
            self.counters[name] += amount
    
    def set_gauge(self, name: str, value: float):
        """设置仪表盘值"""
        with self.lock:
            self.gauges[name] = value
    
    def get_api_call_stats(self, platform: str = None, hours: int = 1) -> Dict[str, Any]:
        """获取API调用统计信息"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.lock:
            api_calls = [m for m in self.metrics[MetricType.API_CALL.value] 
                        if m['timestamp'] >= cutoff_time and 
                        (platform is None or m['platform'] == platform)]
            
            if not api_calls:
                return {}
            
            total_calls = len(api_calls)
            successful_calls = len([c for c in api_calls if 200 <= c['status_code'] < 300])
            failed_calls = total_calls - successful_calls
            
            response_times = [c['response_time'] for c in api_calls]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0
            
            # 按状态码分组
            status_counts = defaultdict(int)
            for call in api_calls:
                status_counts[call['status_code']] += 1
            
            # 计算吞吐量 (calls per minute)
            duration_minutes = hours * 60
            throughput = total_calls / duration_minutes if duration_minutes > 0 else 0
            
            return {
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'failed_calls': failed_calls,
                'success_rate': successful_calls / total_calls if total_calls > 0 else 0,
                'average_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'min_response_time': min_response_time,
                'throughput_cpm': throughput,
                'status_codes': dict(status_counts),
                'time_period_hours': hours
            }
    
    def get_error_stats(self, platform: str = None, hours: int = 1) -> Dict[str, Any]:
        """获取错误统计信息"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.lock:
            errors = [e for e in self.metrics[MetricType.ERROR_RATE.value] 
                     if e['timestamp'] >= cutoff_time and 
                     (platform is None or e['platform'] == platform)]
            
            if not errors:
                return {'total_errors': 0, 'error_types': {}}
            
            error_types = defaultdict(int)
            for error in errors:
                error_types[error['error_type']] += 1
            
            return {
                'total_errors': len(errors),
                'error_rate': len(errors) / self.get_total_api_calls(platform, hours) if self.get_total_api_calls(platform, hours) > 0 else 0,
                'error_types': dict(error_types),
                'time_period_hours': hours
            }
    
    def get_total_api_calls(self, platform: str = None, hours: int = 1) -> int:
        """获取指定时间内API调用总数"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.lock:
            api_calls = [m for m in self.metrics[MetricType.API_CALL.value] 
                        if m['timestamp'] >= cutoff_time and 
                        (platform is None or m['platform'] == platform)]
            return len(api_calls)
    
    def get_security_events(self, hours: int = 1) -> List[Dict[str, Any]]:
        """获取安全事件"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.lock:
            events = [e for e in self.metrics[MetricType.SECURITY_EVENT.value] 
                     if e['timestamp'] >= cutoff_time]
            return events
    
    def get_counters(self) -> Dict[str, int]:
        """获取所有计数器"""
        with self.lock:
            return dict(self.counters)
    
    def get_gauges(self) -> Dict[str, float]:
        """获取所有仪表盘值"""
        with self.lock:
            return dict(self.gauges)
    
    def cleanup_old_metrics(self):
        """清理旧的指标数据"""
        cutoff_time = datetime.utcnow() - self.retention_delta
        
        with self.lock:
            for metric_type in self.metrics:
                self.metrics[metric_type] = deque(
                    [m for m in self.metrics[metric_type] if m['timestamp'] >= cutoff_time],
                    maxlen=10000
                )


# 全局指标收集器实例
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_api_call(platform: str, endpoint: str, status_code: int, response_time: float, **kwargs):
    """便捷函数：记录API调用"""
    collector = get_metrics_collector()
    collector.record_api_call(platform, endpoint, status_code, response_time, **kwargs)


def record_error(platform: str, error_type: str, error_message: str = ""):
    """便捷函数：记录错误"""
    collector = get_metrics_collector()
    collector.record_error(platform, error_type, error_message)


def record_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """便捷函数：记录安全事件"""
    collector = get_metrics_collector()
    collector.record_security_event(event_type, severity, details)
