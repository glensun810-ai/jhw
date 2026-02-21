"""
告警系统模块
P1 修复：恢复缺失的告警模块
"""

from wechat_backend.logging_config import api_logger
from enum import Enum
from typing import List, Optional, Callable
from datetime import datetime


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class AlertCondition:
    """告警条件"""
    
    def __init__(self, name: str, threshold: float, severity: AlertSeverity = AlertSeverity.MEDIUM):
        self.name = name
        self.threshold = threshold
        self.severity = severity
        self.callback: Optional[Callable] = None
    
    def check(self, value: float) -> bool:
        """检查是否触发告警"""
        return value >= self.threshold
    
    def trigger(self, value: float):
        """触发告警"""
        if self.callback:
            self.callback(self, value)
        api_logger.warning(f"Alert triggered: {self.name} (value: {value}, threshold: {self.threshold})")


class Alert:
    """告警"""
    
    def __init__(self, name: str, message: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
        self.name = name
        self.message = message
        self.severity = severity
        self.created_at = datetime.now()
        self.acknowledged = False
    
    def acknowledge(self):
        """确认告警"""
        self.acknowledged = True
        api_logger.info(f"Alert acknowledged: {self.name}")


class AlertSystem:
    """告警系统"""
    
    def __init__(self):
        self.conditions: List[AlertCondition] = []
        self.alerts: List[Alert] = []
        self.enabled = True
    
    def add_condition(self, condition: AlertCondition):
        """添加告警条件"""
        self.conditions.append(condition)
        api_logger.info(f"Alert condition added: {condition.name}")
    
    def check_conditions(self, metric_name: str, value: float):
        """检查所有条件"""
        if not self.enabled:
            return
        
        for condition in self.conditions:
            if condition.name == metric_name and condition.check(value):
                condition.trigger(value)
                self.create_alert(
                    name=condition.name,
                    message=f"{condition.name} exceeded threshold: {value} >= {condition.threshold}",
                    severity=condition.severity
                )
    
    def create_alert(self, name: str, message: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
        """创建告警"""
        alert = Alert(name, message, severity)
        self.alerts.append(alert)
        api_logger.warning(f"Alert created: {name} - {message}")
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃的告警"""
        return [a for a in self.alerts if not a.acknowledged]
    
    def enable(self):
        """启用告警系统"""
        self.enabled = True
        api_logger.info("Alert system enabled")
    
    def disable(self):
        """禁用告警系统"""
        self.enabled = False
        api_logger.info("Alert system disabled")


# 全局实例
_alert_system: Optional[AlertSystem] = None


def get_alert_system() -> AlertSystem:
    """获取告警系统实例"""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system


def init_default_alerts():
    """初始化默认告警"""
    alert_system = get_alert_system()
    
    # 添加默认告警条件
    alert_system.add_condition(AlertCondition(
        name='error_rate',
        threshold=0.1,
        severity=AlertSeverity.HIGH
    ))
    
    alert_system.add_condition(AlertCondition(
        name='response_time',
        threshold=5.0,
        severity=AlertSeverity.MEDIUM
    ))
    
    alert_system.add_condition(AlertCondition(
        name='cpu_usage',
        threshold=0.8,
        severity=AlertSeverity.HIGH
    ))
    
    api_logger.info('Default alerts initialized')


def start_alert_monitoring():
    """启动告警监控"""
    init_default_alerts()
    api_logger.info('Alert monitoring started')


__all__ = [
    'AlertSeverity',
    'AlertCondition',
    'Alert',
    'AlertSystem',
    'get_alert_system',
    'init_default_alerts',
    'start_alert_monitoring'
]
