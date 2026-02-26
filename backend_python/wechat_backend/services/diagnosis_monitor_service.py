"""
诊断监控服务
P2-020: 实时监控大盘 - 诊断成功率、完成率、错误分布

功能：
1. 记录每次诊断的执行指标
2. 聚合统计数据（按小时/天/周）
3. 提供监控数据 API
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from wechat_backend.logging_config import api_logger
import threading
import json

# 线程安全的锁
_metrics_lock = threading.Lock()

# 内存存储指标数据（生产环境应使用数据库或时序数据库）
# 结构：{date_str: {execution_id: metric_data}}
_diagnosis_metrics: Dict[str, Dict] = {}

# 指标保留天数
METRICS_RETENTION_DAYS = 30


class DiagnosisMetrics:
    """诊断指标记录"""
    
    def __init__(
        self,
        execution_id: str,
        user_id: str,
        total_tasks: int,
        completed_tasks: int,
        success: bool,
        duration_seconds: float,
        quota_exhausted_models: List[str] = None,
        error_type: str = None,
        error_message: str = None
    ):
        self.execution_id = execution_id
        self.user_id = user_id
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.success = success
        self.duration_seconds = duration_seconds
        self.quota_exhausted_models = quota_exhausted_models or []
        self.error_type = error_type
        self.error_message = error_message
        self.timestamp = datetime.now()
        self.completion_rate = (completed_tasks / max(total_tasks, 1)) * 100 if total_tasks > 0 else 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'execution_id': self.execution_id,
            'user_id': self.user_id,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'success': self.success,
            'duration_seconds': round(self.duration_seconds, 2),
            'completion_rate': round(self.completion_rate, 2),
            'quota_exhausted_models': self.quota_exhausted_models,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat(),
            'date': self.timestamp.strftime('%Y-%m-%d'),
            'hour': self.timestamp.hour
        }


def record_diagnosis_metric(
    execution_id: str,
    user_id: str,
    total_tasks: int,
    completed_tasks: int,
    success: bool,
    duration_seconds: float,
    quota_exhausted_models: List[str] = None,
    error_type: str = None,
    error_message: str = None
):
    """
    记录诊断指标
    
    参数：
        execution_id: 执行 ID
        user_id: 用户 ID
        total_tasks: 总任务数
        completed_tasks: 完成任务数
        success: 是否成功
        duration_seconds: 执行时长（秒）
        quota_exhausted_models: 配额用尽的模型列表
        error_type: 错误类型
        error_message: 错误信息
    """
    metric = DiagnosisMetrics(
        execution_id=execution_id,
        user_id=user_id,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        success=success,
        duration_seconds=duration_seconds,
        quota_exhausted_models=quota_exhausted_models,
        error_type=error_type,
        error_message=error_message
    )
    
    date_str = metric.timestamp.strftime('%Y-%m-%d')
    
    with _metrics_lock:
        if date_str not in _diagnosis_metrics:
            _diagnosis_metrics[date_str] = {}
        
        _diagnosis_metrics[date_str][execution_id] = metric.to_dict()
        
        api_logger.info(
            f"[P2-020 监控] 记录诊断指标：execution_id={execution_id}, "
            f"完成率={metric.completion_rate:.1f}%, "
            f"耗时={duration_seconds:.2f}s"
        )
    
    # 清理过期数据
    _cleanup_expired_metrics()


def get_monitoring_dashboard(period: str = 'today') -> Dict:
    """
    获取监控大盘数据
    
    参数：
        period: 时间周期 ('today', 'week', 'month')
    
    返回：
        监控数据字典
    """
    now = datetime.now()
    date_strings = []
    
    # 计算日期范围
    if period == 'today':
        date_strings = [now.strftime('%Y-%m-%d')]
    elif period == 'week':
        date_strings = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    elif period == 'month':
        date_strings = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    else:
        date_strings = [now.strftime('%Y-%m-%d')]
    
    # 收集所有指标
    all_metrics = []
    with _metrics_lock:
        for date_str in date_strings:
            if date_str in _diagnosis_metrics:
                all_metrics.extend(_diagnosis_metrics[date_str].values())
    
    if not all_metrics:
        return _empty_dashboard()
    
    # 计算统计数据
    total_diagnosis = len(all_metrics)
    successful_diagnosis = sum(1 for m in all_metrics if m['success'])
    failed_diagnosis = total_diagnosis - successful_diagnosis
    
    # 完成率统计
    completion_rates = [m['completion_rate'] for m in all_metrics]
    avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
    full_completion_count = sum(1 for rate in completion_rates if rate >= 100)
    partial_completion_count = sum(1 for rate in completion_rates if 0 < rate < 100)
    
    # 耗时统计
    durations = [m['duration_seconds'] for m in all_metrics]
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    
    # 配额用尽统计
    quota_exhausted_count = sum(1 for m in all_metrics if m['quota_exhausted_models'])
    all_exhausted_models = []
    for m in all_metrics:
        all_exhausted_models.extend(m['quota_exhausted_models'])
    
    # 错误类型分布
    error_distribution = {}
    for m in all_metrics:
        if m['error_type']:
            error_distribution[m['error_type']] = error_distribution.get(m['error_type'], 0) + 1
    
    # 按小时分布（今天）
    hourly_distribution = {}
    if period == 'today':
        for m in all_metrics:
            hour = str(m['hour'])
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
    
    return {
        'period': period,
        'total_diagnosis': total_diagnosis,
        'successful_diagnosis': successful_diagnosis,
        'failed_diagnosis': failed_diagnosis,
        'success_rate': round((successful_diagnosis / max(total_diagnosis, 1)) * 100, 2),
        
        'completion': {
            'avg_completion_rate': round(avg_completion_rate, 2),
            'full_completion_count': full_completion_count,
            'partial_completion_count': partial_completion_count,
            'full_completion_rate': round((full_completion_count / max(total_diagnosis, 1)) * 100, 2)
        },
        
        'performance': {
            'avg_duration_seconds': round(avg_duration, 2),
            'max_duration_seconds': round(max_duration, 2),
            'p95_duration_seconds': _calculate_percentile(durations, 95)
        },
        
        'quota': {
            'quota_exhausted_count': quota_exhausted_count,
            'quota_exhausted_rate': round((quota_exhausted_count / max(total_diagnosis, 1)) * 100, 2),
            'exhausted_models': list(set(all_exhausted_models))
        },
        
        'errors': {
            'error_distribution': error_distribution,
            'total_errors': sum(error_distribution.values())
        },
        
        'hourly_distribution': hourly_distribution,
        'updated_at': now.isoformat()
    }


def _calculate_percentile(data: List[float], percentile: int) -> float:
    """计算百分位数"""
    if not data:
        return 0
    
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    if index >= len(sorted_data):
        index = len(sorted_data) - 1
    
    return round(sorted_data[index], 2)


def _empty_dashboard() -> Dict:
    """返回空大盘数据"""
    return {
        'period': 'today',
        'total_diagnosis': 0,
        'successful_diagnosis': 0,
        'failed_diagnosis': 0,
        'success_rate': 0,
        'completion': {
            'avg_completion_rate': 0,
            'full_completion_count': 0,
            'partial_completion_count': 0,
            'full_completion_rate': 0
        },
        'performance': {
            'avg_duration_seconds': 0,
            'max_duration_seconds': 0,
            'p95_duration_seconds': 0
        },
        'quota': {
            'quota_exhausted_count': 0,
            'quota_exhausted_rate': 0,
            'exhausted_models': []
        },
        'errors': {
            'error_distribution': {},
            'total_errors': 0
        },
        'hourly_distribution': {},
        'updated_at': datetime.now().isoformat()
    }


def _cleanup_expired_metrics():
    """清理过期指标数据"""
    now = datetime.now()
    cutoff_date = now - timedelta(days=METRICS_RETENTION_DAYS)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    
    with _metrics_lock:
        dates_to_remove = [
            date_str for date_str in _diagnosis_metrics.keys()
            if date_str < cutoff_str
        ]
        
        for date_str in dates_to_remove:
            del _diagnosis_metrics[date_str]
        
        if dates_to_remove:
            api_logger.info(f"[P2-020 监控] 清理 {len(dates_to_remove)} 天的过期指标数据")


def get_recent_diagnosis_list(limit: int = 20) -> List[Dict]:
    """
    获取最近的诊断列表
    
    参数：
        limit: 返回数量限制
    
    返回：
        诊断列表
    """
    all_metrics = []
    
    with _metrics_lock:
        # 从最近的日期开始收集
        sorted_dates = sorted(_diagnosis_metrics.keys(), reverse=True)
        
        for date_str in sorted_dates:
            for execution_id, metric in _diagnosis_metrics[date_str].items():
                all_metrics.append(metric)
                
                if len(all_metrics) >= limit:
                    break
            
            if len(all_metrics) >= limit:
                break
    
    # 按时间戳排序
    all_metrics.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return all_metrics[:limit]


# 导出函数
__all__ = [
    'record_diagnosis_metric',
    'get_monitoring_dashboard',
    'get_recent_diagnosis_list'
]
