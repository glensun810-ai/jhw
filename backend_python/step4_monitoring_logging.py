#!/usr/bin/env python3
"""
监控和日志改进工具
此脚本用于实现API调用指标收集、响应时间监控和安全事件告警
"""

import os
import sys
from pathlib import Path
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import json
import atexit


def create_metrics_collector():
    """创建指标收集器模块"""
    
    metrics_content = '''"""
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
'''
    
    # 获取监控目录
    monitoring_dir = Path('wechat_backend/monitoring')
    monitoring_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入指标收集器模块
    with open(monitoring_dir / 'metrics_collector.py', 'w', encoding='utf-8') as f:
        f.write(metrics_content)
    
    # 创建__init__.py文件
    with open(monitoring_dir / '__init__.py', 'w', encoding='utf-8') as f:
        f.write('"""监控模块初始化"""')
    
    print("✓ 已创建指标收集器模块: wechat_backend/monitoring/metrics_collector.py")


def create_alert_system():
    """创建告警系统模块"""
    
    alert_system_content = '''"""
告警系统
基于指标数据实现安全事件和性能问题的告警
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCondition:
    """告警条件"""
    
    def __init__(self, 
                 metric_name: str, 
                 threshold: float, 
                 comparison: str = ">",
                 time_window_minutes: int = 5,
                 consecutive_violations: int = 1):
        """
        初始化告警条件
        :param metric_name: 指标名称
        :param threshold: 阈值
        :param comparison: 比较操作符 (> >= < <= == !=)
        :param time_window_minutes: 时间窗口（分钟）
        :param consecutive_violations: 连续违规次数才触发告警
        """
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
        self.time_window_minutes = time_window_minutes
        self.consecutive_violations = consecutive_violations
        self.violation_count = 0
        self.last_evaluation = None
    
    def evaluate(self, current_value: float) -> bool:
        """评估当前值是否满足告警条件"""
        # 检查比较条件
        condition_met = False
        if self.comparison == ">":
            condition_met = current_value > self.threshold
        elif self.comparison == ">=":
            condition_met = current_value >= self.threshold
        elif self.comparison == "<":
            condition_met = current_value < self.threshold
        elif self.comparison == "<=":
            condition_met = current_value <= self.threshold
        elif self.comparison == "==":
            condition_met = current_value == self.threshold
        elif self.comparison == "!=":
            condition_met = current_value != self.threshold
        else:
            logger.warning(f"未知的比较操作符: {self.comparison}")
            return False
        
        # 更新违规计数
        if condition_met:
            self.violation_count += 1
        else:
            self.violation_count = 0
        
        self.last_evaluation = datetime.utcnow()
        
        # 检查是否达到连续违规次数
        return self.violation_count >= self.consecutive_violations


class Alert:
    """告警实体"""
    
    def __init__(self, 
                 name: str, 
                 condition: AlertCondition, 
                 severity: AlertSeverity,
                 description: str = "",
                 notification_targets: List[str] = None):
        """
        初始化告警
        :param name: 告警名称
        :param condition: 告警条件
        :param severity: 严重程度
        :param description: 描述
        :param notification_targets: 通知目标列表
        """
        self.name = name
        self.condition = condition
        self.severity = severity
        self.description = description
        self.notification_targets = notification_targets or []
        self.active = False
        self.triggered_at = None
        self.last_notified_at = None
        self.suppression_duration_minutes = 15  # 告警抑制时间
    
    def check_condition(self, current_value: float) -> bool:
        """检查告警条件是否满足"""
        return self.condition.evaluate(current_value)
    
    def trigger(self):
        """触发告警"""
        if not self.active:
            self.active = True
            self.triggered_at = datetime.utcnow()
            logger.warning(f"告警触发: {self.name} [{self.severity.value}] - {self.description}")
            return True
        return False
    
    def should_notify(self) -> bool:
        """检查是否应该发送通知（考虑抑制时间）"""
        if not self.active:
            return False
        
        if self.last_notified_at is None:
            return True
        
        time_since_last_notification = datetime.utcnow() - self.last_notified_at
        return time_since_last_notification >= timedelta(minutes=self.suppression_duration_minutes)
    
    def notify(self):
        """发送通知"""
        if self.should_notify():
            self.last_notified_at = datetime.utcnow()
            # 这里可以集成实际的通知系统（邮件、短信、Slack等）
            logger.info(f"发送告警通知: {self.name} -> {self.notification_targets}")
    
    def deactivate(self):
        """停用告警"""
        self.active = False
        self.triggered_at = None


class AlertSystem:
    """告警系统"""
    
    def __init__(self):
        self.alerts = {}
        self.callbacks = []  # 告警触发时的回调函数
        self.is_running = False
        self.thread = None
        self.check_interval = 30  # 检查间隔（秒）
        self.lock = threading.Lock()
    
    def add_alert(self, alert: Alert):
        """添加告警"""
        with self.lock:
            self.alerts[alert.name] = alert
            logger.info(f"添加告警: {alert.name}")
    
    def remove_alert(self, alert_name: str):
        """移除告警"""
        with self.lock:
            if alert_name in self.alerts:
                del self.alerts[alert_name]
                logger.info(f"移除告警: {alert_name}")
    
    def add_callback(self, callback: Callable[[Alert, float], None]):
        """添加告警回调函数"""
        self.callbacks.append(callback)
    
    def evaluate_alerts(self, metric_values: Dict[str, float]):
        """评估所有告警"""
        triggered_alerts = []
        
        with self.lock:
            for alert_name, alert in self.alerts.items():
                if alert_name in metric_values:
                    current_value = metric_values[alert_name]
                    if alert.check_condition(current_value):
                        if alert.trigger():
                            triggered_alerts.append((alert, current_value))
                            
                            # 执行回调
                            for callback in self.callbacks:
                                try:
                                    callback(alert, current_value)
                                except Exception as e:
                                    logger.error(f"告警回调执行失败: {e}")
                    
                    # 如果告警被触发，发送通知
                    if alert.active and alert.should_notify():
                        alert.notify()
        
        return triggered_alerts
    
    def start_monitoring(self):
        """启动监控线程"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("告警监控已启动")
    
    def stop_monitoring(self):
        """停止监控线程"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("告警监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        from .metrics_collector import get_metrics_collector
        
        while self.is_running:
            try:
                # 获取最新的指标值
                collector = get_metrics_collector()
                counters = collector.get_counters()
                gauges = collector.get_gauges()
                
                # 合并指标值
                all_metrics = {**counters, **gauges}
                
                # 评估告警
                self.evaluate_alerts(all_metrics)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"告警监控循环出错: {e}")
                time.sleep(self.check_interval)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃的告警"""
        with self.lock:
            return [alert for alert in self.alerts.values() if alert.active]


# 全局告警系统实例
_alert_system = None


def get_alert_system() -> AlertSystem:
    """获取告警系统实例"""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system


def add_alert(name: str, condition: AlertCondition, severity: AlertSeverity, **kwargs):
    """便捷函数：添加告警"""
    alert = Alert(name, condition, severity, **kwargs)
    system = get_alert_system()
    system.add_alert(alert)


def start_alert_monitoring():
    """便捷函数：启动告警监控"""
    system = get_alert_system()
    system.start_monitoring()


def stop_alert_monitoring():
    """便捷函数：停止告警监控"""
    system = get_alert_system()
    system.stop_monitoring()
'''
    
    # 获取监控目录
    monitoring_dir = Path('wechat_backend/monitoring')
    
    # 写入告警系统模块
    with open(monitoring_dir / 'alert_system.py', 'w', encoding='utf-8') as f:
        f.write(alert_system_content)
    
    print("✓ 已创建告警系统模块: wechat_backend/monitoring/alert_system.py")


def create_logging_enhancements():
    """创建日志增强模块"""
    
    logging_enhancements_content = '''"""
增强日志系统
提供结构化日志记录和安全审计功能
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
from enum import Enum

# 定义专门的日志记录器
audit_logger = logging.getLogger("audit")
security_logger = logging.getLogger("security")
api_logger = logging.getLogger("api")


class LogEventType(Enum):
    """日志事件类型"""
    API_CALL = "api_call"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    SECURITY_EVENT = "security_event"
    SYSTEM_ERROR = "system_error"


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_structured(self, level: int, event_type: LogEventType, message: str, **kwargs):
        """记录结构化日志"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "message": message,
            "details": kwargs
        }
        
        self.logger.log(level, json.dumps(log_entry, ensure_ascii=False))
    
    def info(self, event_type: LogEventType, message: str, **kwargs):
        """信息级别日志"""
        self._log_structured(logging.INFO, event_type, message, **kwargs)
    
    def warning(self, event_type: LogEventType, message: str, **kwargs):
        """警告级别日志"""
        self._log_structured(logging.WARNING, event_type, message, **kwargs)
    
    def error(self, event_type: LogEventType, message: str, **kwargs):
        """错误级别日志"""
        self._log_structured(logging.ERROR, event_type, message, **kwargs)
    
    def critical(self, event_type: LogEventType, message: str, **kwargs):
        """严重级别日志"""
        self._log_structured(logging.CRITICAL, event_type, message, **kwargs)


class AuditLogger(StructuredLogger):
    """审计日志记录器"""
    
    def __init__(self):
        super().__init__("audit")
    
    def log_api_access(self, user_id: str, ip_address: str, endpoint: str, method: str, status_code: int):
        """记录API访问"""
        self.info(
            LogEventType.API_CALL,
            "API访问记录",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            method=method,
            status_code=status_code
        )
    
    def log_authentication(self, username: str, success: bool, ip_address: str = None, reason: str = None):
        """记录身份验证"""
        self.info(
            LogEventType.AUTHENTICATION,
            f"身份验证{'成功' if success else '失败'}",
            username=username,
            success=success,
            ip_address=ip_address,
            reason=reason
        )
    
    def log_authorization(self, user_id: str, resource: str, action: str, granted: bool, reason: str = None):
        """记录授权"""
        self.info(
            LogEventType.AUTHORIZATION,
            f"授权{'通过' if granted else '拒绝'}",
            user_id=user_id,
            resource=resource,
            action=action,
            granted=granted,
            reason=reason
        )
    
    def log_data_access(self, user_id: str, resource: str, action: str, success: bool):
        """记录数据访问"""
        self.info(
            LogEventType.DATA_ACCESS,
            f"数据访问{'成功' if success else '失败'}",
            user_id=user_id,
            resource=resource,
            action=action,
            success=success
        )
    
    def log_config_change(self, user_id: str, config_key: str, old_value: str, new_value: str):
        """记录配置变更"""
        self.info(
            LogEventType.CONFIG_CHANGE,
            "配置变更",
            user_id=user_id,
            config_key=config_key,
            old_value=old_value,
            new_value=new_value
        )


class SecurityLogger(StructuredLogger):
    """安全日志记录器"""
    
    def __init__(self):
        super().__init__("security")
    
    def log_security_event(self, event_type: str, severity: str, description: str, **details):
        """记录安全事件"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            f"安全事件: {description}",
            event_type=event_type,
            severity=severity,
            **details
        )
    
    def log_potential_attack(self, attack_type: str, ip_address: str, user_agent: str = None, **details):
        """记录潜在攻击"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            f"检测到潜在{attack_type}攻击",
            attack_type=attack_type,
            ip_address=ip_address,
            user_agent=user_agent,
            **details
        )
    
    def log_brute_force_attempt(self, username: str, ip_address: str, attempts: int):
        """记录暴力破解尝试"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            "暴力破解尝试",
            username=username,
            ip_address=ip_address,
            attempts=attempts
        )
    
    def log_unauthorized_access(self, user_id: str, resource: str, ip_address: str):
        """记录未授权访问"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            "未授权访问尝试",
            user_id=user_id,
            resource=resource,
            ip_address=ip_address
        )
    
    def log_privilege_escalation(self, user_id: str, attempted_privilege: str, ip_address: str):
        """记录权限提升尝试"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            "权限提升尝试",
            user_id=user_id,
            attempted_privilege=attempted_privilege,
            ip_address=ip_address
        )


class APILogger(StructuredLogger):
    """API日志记录器"""
    
    def __init__(self):
        super().__init__("api")
    
    def log_request(self, 
                   method: str, 
                   endpoint: str, 
                   user_id: str = None, 
                   ip_address: str = None, 
                   request_size: int = 0):
        """记录API请求"""
        self.info(
            LogEventType.API_CALL,
            "API请求接收",
            method=method,
            endpoint=endpoint,
            user_id=user_id,
            ip_address=ip_address,
            request_size=request_size
        )
    
    def log_response(self, 
                    endpoint: str, 
                    status_code: int, 
                    response_time: float, 
                    response_size: int = 0,
                    user_id: str = None):
        """记录API响应"""
        self.info(
            LogEventType.API_CALL,
            "API响应发送",
            endpoint=endpoint,
            status_code=status_code,
            response_time=response_time,
            response_size=response_size,
            user_id=user_id
        )
    
    def log_error(self, 
                  endpoint: str, 
                  status_code: int, 
                  error_message: str, 
                  user_id: str = None,
                  traceback_info: str = None):
        """记录API错误"""
        self.error(
            LogEventType.SYSTEM_ERROR,
            "API错误",
            endpoint=endpoint,
            status_code=status_code,
            error_message=error_message,
            user_id=user_id,
            traceback=traceback_info
        )


# 全局日志记录器实例
_audit_logger = None
_security_logger = None
_api_logger = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志记录器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_security_logger() -> SecurityLogger:
    """获取安全日志记录器"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger


def get_api_logger() -> APILogger:
    """获取API日志记录器"""
    global _api_logger
    if _api_logger is None:
        _api_logger = APILogger()
    return _api_logger


# 便捷函数
def log_api_access(user_id: str, ip_address: str, endpoint: str, method: str, status_code: int):
    """便捷函数：记录API访问"""
    logger = get_audit_logger()
    logger.log_api_access(user_id, ip_address, endpoint, method, status_code)


def log_security_event(event_type: str, severity: str, description: str, **details):
    """便捷函数：记录安全事件"""
    logger = get_security_logger()
    logger.log_security_event(event_type, severity, description, **details)


def log_api_request(method: str, endpoint: str, user_id: str = None, ip_address: str = None, request_size: int = 0):
    """便捷函数：记录API请求"""
    logger = get_api_logger()
    logger.log_request(method, endpoint, user_id, ip_address, request_size)


def log_api_response(endpoint: str, status_code: int, response_time: float, response_size: int = 0, user_id: str = None):
    """便捷函数：记录API响应"""
    logger = get_api_logger()
    logger.log_response(endpoint, status_code, response_time, response_size, user_id)
'''
    
    # 获取监控目录
    monitoring_dir = Path('wechat_backend/monitoring')
    
    # 写入日志增强模块
    with open(monitoring_dir / 'logging_enhancements.py', 'w', encoding='utf-8') as f:
        f.write(logging_enhancements_content)
    
    print("✓ 已创建日志增强模块: wechat_backend/monitoring/logging_enhancements.py")


def update_ai_adapters_with_monitoring():
    """更新AI适配器以使用监控功能"""
    
    # 更新DeepSeek适配器以使用监控功能
    updated_deepseek_adapter = '''import time
import requests
from typing import Dict, Any, Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.security import get_http_client
from ..network.connection_pool import get_session_for_url
from ..network.circuit_breaker import get_circuit_breaker
from ..network.retry_mechanism import SmartRetryHandler
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager


class DeepSeekAdapter(AIClient):
    """
    DeepSeek AI 平台适配器
    用于将 DeepSeek API 接入 GEO 内容质量验证系统
    支持两种模式：普通对话模式（deepseek-chat）和搜索/推理模式（deepseek-reasoner）
    包含内部 Prompt 约束逻辑，可配置是否启用中文回答及事实性约束
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.deepseek.com/v1",
        enable_chinese_constraint: bool = True  # 新增参数：是否启用中文约束
    ):
        """
        初始化 DeepSeek 适配器

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-chat"
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示搜索/推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_chinese_constraint: 是否启用中文回答约束，默认为 True
        """
        super().__init__(AIPlatformType.DEEPSEEK, model_name, api_key)
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_chinese_constraint = enable_chinese_constraint  # 存储中文约束开关

        # 初始化弹性组件
        self.circuit_breaker = get_circuit_breaker(f"deepseek_{model_name}")
        self.retry_handler = SmartRetryHandler(max_attempts=3, base_delay=1.0)

        # 初始化监控组件
        self.platform_name = "deepseek"
        
        api_logger.info(f"DeepSeekAdapter initialized for model: {model_name} with resilience and monitoring features")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示到 DeepSeek 并返回标准化响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含 DeepSeek 响应的统一数据结构
        """
        # 记录请求开始时间以计算延迟
        start_time = time.time()

        def _make_request():
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 如果启用了中文约束，在原始 prompt 基础上添加约束指令
            # 这样做不会影响上层传入的原始 prompt，仅在发送给 AI 时附加约束
            processed_prompt = prompt
            if self.enable_chinese_constraint:
                constraint_instruction = (
                    "请严格按照以下要求作答：\\n"
                    "1. 必须使用中文回答\\n"
                    "2. 基于事实和公开信息作答\\n"
                    "3. 避免在不确定时胡编乱造\\n"
                    "4. 输出结构清晰（分点或分段）\\n\\n"
                )
                processed_prompt = constraint_instruction + prompt

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 根据模式构建不同的请求体
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 搜索/推理模式 (reasoner): 适用于需要深度分析和推理的问题
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": processed_prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # 如果是推理模式，添加额外参数
            if self.mode == "reasoner":
                payload["reasoner"] = "search"  # 启用搜索推理能力

            # 记录API请求
            log_api_request(
                method="POST",
                endpoint=f"{self.base_url}/chat/completions",
                request_size=len(str(payload))
            )

            # 使用连接池发送请求到 DeepSeek API
            session = get_session_for_url(f"{self.base_url}/chat/completions")
            response = session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)  # 设置请求超时时间为30秒
            )

            # 计算请求延迟
            response_time = time.time() - start_time

            # 记录API响应
            log_api_response(
                endpoint=f"{self.base_url}/chat/completions",
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content)
            )

            # 检查响应状态码
            if response.status_code != 200:
                raise requests.HTTPError(f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}")

            # 解析响应数据
            response_data = response.json()

            # 提取所需信息
            content = ""
            usage = {}

            # 从响应中提取实际回答文本
            choices = response_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

            # 从响应中提取使用情况信息
            usage = response_data.get("usage", {})

            # 记录成功指标
            record_api_call(
                platform=self.platform_name,
                endpoint="chat/completions",
                status_code=response.status_code,
                response_time=response_time,
                tokens_used=usage.get("total_tokens", 0)
            )

            # 返回成功的 AIResponse，包含模式信息
            return AIResponse(
                success=True,
                content=content,
                model=response_data.get("model", self.model_name),
                platform=self.platform_type.value,
                tokens_used=usage.get("total_tokens", 0),
                latency=response_time,
                metadata=response_data
            )

        try:
            # 使用断路器包装请求
            response = self.circuit_breaker.call(_make_request)
            return response
        except Exception as e:
            # 记录延迟
            response_time = time.time() - start_time
            
            # 根据错误类型确定错误类别
            error_type = self._map_request_exception(e) if isinstance(e, requests.RequestException) else AIErrorType.UNKNOWN_ERROR
            
            # 记录错误指标
            error_category = str(error_type).split('.')[-1]  # 获取错误类型名称
            record_error(self.platform_name, error_category, str(e))
            
            # 返回错误响应
            return AIResponse(
                success=False,
                error_message=f"请求失败: {str(e)}",
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=response_time
            )

    def _map_request_exception(self, e: requests.RequestException) -> AIErrorType:
        """将请求异常映射到标准错误类型"""
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                return AIErrorType.INVALID_API_KEY
            elif status_code == 429:
                return AIErrorType.RATE_LIMIT_EXCEEDED
            elif status_code >= 500:
                return AIErrorType.SERVER_ERROR
            elif status_code == 403:
                return AIErrorType.INVALID_API_KEY
        return AIErrorType.UNKNOWN_ERROR

    def health_check(self) -> bool:
        """
        检查 DeepSeek 客户端的健康状态
        通过发送一个简单的测试请求来验证连接

        Returns:
            bool: 客户端是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.send_prompt("你好，请回复'正常'。")
            return test_response.success
        except Exception:
            return False
'''
    
    # 更新AI适配器
    ai_adapters_dir = Path('wechat_backend/ai_adapters')
    
    # 保存更新后的DeepSeek适配器
    with open(ai_adapters_dir / 'deepseek_adapter.py', 'w', encoding='utf-8') as f:
        f.write(updated_deepseek_adapter)
    
    print("✓ 已更新DeepSeek适配器以使用监控功能")


def main():
    print("🚀 开始执行安全改进计划 - 第四步：监控和日志改进")
    print("=" * 60)
    
    print("\n1. 创建指标收集器模块...")
    create_metrics_collector()
    
    print("\n2. 创建告警系统模块...")
    create_alert_system()
    
    print("\n3. 创建日志增强模块...")
    create_logging_enhancements()
    
    print("\n4. 更新AI适配器以使用监控功能...")
    update_ai_adapters_with_monitoring()
    
    print("\n" + "=" * 60)
    print("✅ 第四步完成！")
    print("\n已完成：")
    print("• 创建了指标收集器，用于收集API性能数据")
    print("• 创建了告警系统，支持基于阈值的告警")
    print("• 创建了增强日志系统，支持结构化日志记录")
    print("• 更新了AI适配器以使用新的监控功能")
    print("\n下一步：")
    print("• 部署监控系统到生产环境")
    print("• 配置告警阈值和通知渠道")
    print("• 开始收集和分析监控数据")


if __name__ == "__main__":
    main()