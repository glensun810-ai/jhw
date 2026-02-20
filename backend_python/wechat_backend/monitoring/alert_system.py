"""
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
        from wechat_backend.monitoring.metrics_collector import get_metrics_collector
        
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
