"""
诊断系统监控告警模块

功能：
1. 监控 API 调用失败率
2. 监控数据完整性（brand 字段为空比例）
3. 监控诊断任务成功率
4. 超过阈值时发送告警

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from pathlib import Path
from wechat_backend.logging_config import api_logger, db_logger
from wechat_backend.monitoring.enhanced_alert_manager import EnhancedAlertManager


# 监控配置
MONITORING_CONFIG = {
    # 失败率告警阈值
    'failure_rate_threshold': 0.1,  # 10%
    'failure_rate_window': 3600,     # 1 小时窗口（秒）
    
    # 数据完整性告警阈值
    'empty_brand_threshold': 0.01,   # 1%
    'empty_brand_window': 1800,      # 30 分钟窗口（秒）
    
    # 诊断成功率告警阈值
    'success_rate_threshold': 0.9,   # 90%
    'success_rate_window': 7200,     # 2 小时窗口（秒）
    
    # 告警抑制配置
    'alert_suppression_window': 600,  # 10 分钟内相同告警只发送一次
}


class DiagnosisMetrics:
    """诊断指标收集器"""
    
    def __init__(self):
        # 执行记录：execution_id -> {timestamp, success, error_type, brand_empty}
        self.executions: Dict[str, Dict[str, Any]] = {}
        
        # 按时间窗口统计
        self.failure_counts: Dict[int, int] = defaultdict(int)  # 每分钟失败数
        self.total_counts: Dict[int, int] = defaultdict(int)    # 每分钟总数
        self.empty_brand_counts: Dict[int, int] = defaultdict(int)  # 每分钟 brand 为空数
        
        # 告警历史
        self.alert_history: List[Dict[str, Any]] = []
        
        # 最后告警时间（用于抑制）
        self.last_alert_time: Dict[str, datetime] = {}
    
    def record_execution(
        self,
        execution_id: str,
        success: bool,
        error_type: Optional[str] = None,
        brand_empty: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录一次诊断执行
        
        参数:
            execution_id: 执行 ID
            success: 是否成功
            error_type: 错误类型
            brand_empty: brand 字段是否为空
            metadata: 其他元数据
        """
        timestamp = time.time()
        minute_key = int(timestamp // 60)  # 按分钟聚合
        
        self.executions[execution_id] = {
            'timestamp': timestamp,
            'success': success,
            'error_type': error_type,
            'brand_empty': brand_empty,
            'metadata': metadata or {}
        }
        
        # 更新统计
        self.total_counts[minute_key] += 1
        
        if not success:
            self.failure_counts[minute_key] += 1
        
        if brand_empty:
            self.empty_brand_counts[minute_key] += 1
        
        # 清理旧数据（保留 2 小时）
        self._cleanup_old_data(max_age=7200)
    
    def _cleanup_old_data(self, max_age: int = 7200):
        """清理旧数据"""
        current_time = time.time()
        cutoff_time = current_time - max_age
        
        # 清理执行记录
        expired_ids = [
            eid for eid, data in self.executions.items()
            if data['timestamp'] < cutoff_time
        ]
        for eid in expired_ids:
            del self.executions[eid]
        
        # 清理分钟级统计
        cutoff_minute = int(cutoff_time // 60)
        for minute_key in list(self.total_counts.keys()):
            if minute_key < cutoff_minute:
                del self.total_counts[minute_key]
                self.failure_counts.pop(minute_key, None)
                self.empty_brand_counts.pop(minute_key, None)
    
    def get_failure_rate(self, window: int = 3600) -> float:
        """
        获取失败率
        
        参数:
            window: 时间窗口（秒）
        
        返回:
            失败率 (0-1)
        """
        current_time = time.time()
        cutoff_time = current_time - window
        cutoff_minute = int(cutoff_time // 60)
        
        total = sum(
            count for minute, count in self.total_counts.items()
            if minute >= cutoff_minute
        )
        failures = sum(
            count for minute, count in self.failure_counts.items()
            if minute >= cutoff_minute
        )
        
        return failures / total if total > 0 else 0.0
    
    def get_empty_brand_rate(self, window: int = 1800) -> float:
        """
        获取 brand 字段为空的比例
        
        参数:
            window: 时间窗口（秒）
        
        返回:
            空 brand 比例 (0-1)
        """
        current_time = time.time()
        cutoff_time = current_time - window
        cutoff_minute = int(cutoff_time // 60)
        
        total = sum(
            count for minute, count in self.total_counts.items()
            if minute >= cutoff_minute
        )
        empty_brands = sum(
            count for minute, count in self.empty_brand_counts.items()
            if minute >= cutoff_minute
        )
        
        return empty_brands / total if total > 0 else 0.0
    
    def get_success_rate(self, window: int = 7200) -> float:
        """
        获取成功率
        
        参数:
            window: 时间窗口（秒）
        
        返回:
            成功率 (0-1)
        """
        return 1.0 - self.get_failure_rate(window)
    
    def should_send_alert(self, alert_type: str) -> bool:
        """
        检查是否应该发送告警（避免告警风暴）
        
        参数:
            alert_type: 告警类型
        
        返回:
            是否应该发送
        """
        if alert_type not in self.last_alert_time:
            return True
        
        suppression_window = MONITORING_CONFIG['alert_suppression_window']
        time_since_last = (datetime.now() - self.last_alert_time[alert_type]).total_seconds()
        
        return time_since_last > suppression_window
    
    def record_alert_sent(self, alert_type: str):
        """记录告警已发送"""
        self.last_alert_time[alert_type] = datetime.now()
        
        self.alert_history.append({
            'alert_type': alert_type,
            'timestamp': datetime.now().isoformat(),
        })
        
        # 保留最近 100 条告警
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]


# 全局监控实例
_diagnosis_monitor: Optional[DiagnosisMetrics] = None
_alert_manager: Optional[EnhancedAlertManager] = None


def get_diagnosis_monitor() -> DiagnosisMetrics:
    """获取诊断监控实例"""
    global _diagnosis_monitor
    if _diagnosis_monitor is None:
        _diagnosis_monitor = DiagnosisMetrics()
    return _diagnosis_monitor


def get_alert_manager() -> EnhancedAlertManager:
    """获取告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = EnhancedAlertManager()
    return _alert_manager


# 【P3 修复 - 2026-03-07】监控装饰器
def monitor_diagnosis_execution(func):
    """
    诊断执行监控装饰器
    
    用法:
        @monitor_diagnosis_execution
        async def execute_diagnosis(...):
            pass
    """
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        monitor = get_diagnosis_monitor()
        alert_mgr = get_alert_manager()
        
        # 生成或获取 execution_id
        execution_id = kwargs.get('execution_id') or args[0] if args else 'unknown'
        
        try:
            # 执行诊断
            result = await func(*args, **kwargs)
            
            # 记录成功执行
            success = result.get('success', False) if isinstance(result, dict) else True
            brand_empty = _check_brand_empty(result)
            
            monitor.record_execution(
                execution_id=execution_id,
                success=success,
                error_type=None if success else result.get('error_code'),
                brand_empty=brand_empty
            )
            
            # 检查告警
            _check_alerts(monitor, alert_mgr)
            
            return result
            
        except Exception as e:
            # 记录失败执行
            monitor.record_execution(
                execution_id=execution_id,
                success=False,
                error_type=type(e).__name__,
                brand_empty=False
            )
            
            # 检查告警
            _check_alerts(monitor, alert_mgr)
            
            raise
    
    return wrapper


def _check_brand_empty(result: Dict[str, Any]) -> bool:
    """检查结果中 brand 字段是否为空"""
    if not result or not isinstance(result, dict):
        return False
    
    # 检查单个结果
    if 'data' in result:
        data = result['data']
        if isinstance(data, dict):
            brand = data.get('brand', '')
            return brand == '' or brand is None
        
        # 检查结果列表
        if isinstance(data, list):
            empty_count = sum(
                1 for item in data
                if isinstance(item, dict) and (not item.get('brand') or item.get('brand') == '')
            )
            return empty_count > len(data) * 0.1  # 超过 10% 为空
    
    return False


def _check_alerts(monitor: DiagnosisMetrics, alert_mgr: EnhancedAlertManager):
    """检查并发送告警"""
    
    # 1. 检查失败率
    failure_rate = monitor.get_failure_rate()
    threshold = MONITORING_CONFIG['failure_rate_threshold']
    
    if failure_rate > threshold:
        alert_type = 'diagnosis_failure_rate'
        if monitor.should_send_alert(alert_type):
            alert_mgr.send_alert(
                title='诊断失败率过高',
                message=f'当前失败率：{failure_rate:.1%}, 阈值：{threshold:.1%}',
                severity='error',
                metric_name='diagnosis_failure_rate',
                current_value=failure_rate,
                threshold=threshold
            )
            monitor.record_alert_sent(alert_type)
    
    # 2. 检查空 brand 比例
    empty_brand_rate = monitor.get_empty_brand_rate()
    empty_threshold = MONITORING_CONFIG['empty_brand_threshold']
    
    if empty_brand_rate > empty_threshold:
        alert_type = 'empty_brand_rate'
        if monitor.should_send_alert(alert_type):
            alert_mgr.send_alert(
                title='brand 字段为空比例过高',
                message=f'当前空 brand 比例：{empty_brand_rate:.1%}, 阈值：{empty_threshold:.1%}',
                severity='critical',
                metric_name='empty_brand_rate',
                current_value=empty_brand_rate,
                threshold=empty_threshold
            )
            monitor.record_alert_sent(alert_type)
    
    # 3. 检查成功率
    success_rate = monitor.get_success_rate()
    success_threshold = MONITORING_CONFIG['success_rate_threshold']
    
    if success_rate < success_threshold:
        alert_type = 'diagnosis_success_rate'
        if monitor.should_send_alert(alert_type):
            alert_mgr.send_alert(
                title='诊断成功率过低',
                message=f'当前成功率：{success_rate:.1%}, 阈值：{success_threshold:.1%}',
                severity='warning',
                metric_name='diagnosis_success_rate',
                current_value=success_rate,
                threshold=success_threshold
            )
            monitor.record_alert_sent(alert_type)


# 【P3 修复 - 2026-03-07】便捷的监控记录函数
def record_diagnosis_result(
    execution_id: str,
    success: bool,
    error_type: Optional[str] = None,
    brand_empty: bool = False,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    记录诊断执行结果
    
    用法:
        record_diagnosis_result(
            execution_id='xxx',
            success=True,
            brand_empty=False
        )
    """
    monitor = get_diagnosis_monitor()
    alert_mgr = get_alert_manager()
    
    monitor.record_execution(
        execution_id=execution_id,
        success=success,
        error_type=error_type,
        brand_empty=brand_empty,
        metadata=metadata
    )
    
    _check_alerts(monitor, alert_mgr)


# 【P3 修复 - 2026-03-07】获取监控报告
def get_monitoring_report(window: int = 3600) -> Dict[str, Any]:
    """
    获取监控报告
    
    参数:
        window: 时间窗口（秒）
    
    返回:
        监控报告字典
    """
    monitor = get_diagnosis_monitor()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'window_seconds': window,
        'failure_rate': monitor.get_failure_rate(window),
        'success_rate': monitor.get_success_rate(window),
        'empty_brand_rate': monitor.get_empty_brand_rate(window // 2),
        'total_executions': sum(monitor.total_counts.values()),
        'total_failures': sum(monitor.failure_counts.values()),
        'alert_history': monitor.alert_history[-10:],
    }
