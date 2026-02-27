"""
监控告警配置模块

功能：
- 监控指标定义
- 告警规则配置
- 告警通知
- 监控仪表板数据

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from wechat_backend.logging_config import api_logger


class AlertLevel(Enum):
    """告警级别"""
    INFO = 'info'           # 信息
    WARNING = 'warning'     # 警告
    ERROR = 'error'         # 错误
    CRITICAL = 'critical'   # 严重


class MetricType(Enum):
    """指标类型"""
    COUNTER = 'counter'     # 计数器
    GAUGE = 'gauge'         # 仪表
    HISTOGRAM = 'histogram' # 直方图


@dataclass
class AlertRule:
    """告警规则"""
    name: str                           # 规则名称
    metric: str                         # 监控指标
    condition: Callable[[Any], bool]    # 条件函数
    level: AlertLevel                   # 告警级别
    message: str                        # 告警消息
    cooldown: int = 300                 # 冷却时间（秒）
    enabled: bool = True                # 是否启用
    last_triggered: Optional[datetime] = None


@dataclass
class Alert:
    """告警"""
    rule_name: str
    level: AlertLevel
    message: str
    metric_value: Any
    triggered_at: datetime
    context: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    指标收集器
    
    收集和存储监控指标
    """
    
    def __init__(self):
        """初始化指标收集器"""
        self._metrics: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self.logger = api_logger
    
    def increment(self, name: str, value: int = 1, labels: Dict = None) -> None:
        """
        增加计数器
        
        参数:
            name: 指标名称
            value: 增加的值
            labels: 标签
        """
        key = self._make_key(name, labels)
        
        if key not in self._metrics:
            self._metrics[key] = 0
        
        self._metrics[key] += value
        self._timestamps[key] = datetime.now()
    
    def set(self, name: str, value: Any, labels: Dict = None) -> None:
        """
        设置指标值
        
        参数:
            name: 指标名称
            value: 指标值
            labels: 标签
        """
        key = self._make_key(name, labels)
        self._metrics[key] = value
        self._timestamps[key] = datetime.now()
    
    def get(self, name: str, labels: Dict = None) -> Optional[Any]:
        """
        获取指标值
        
        参数:
            name: 指标名称
            labels: 标签
            
        返回:
            指标值
        """
        key = self._make_key(name, labels)
        return self._metrics.get(key)
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有指标
        
        返回:
            所有指标字典
        """
        return self._metrics.copy()
    
    def _make_key(self, name: str, labels: Dict = None) -> str:
        """
        生成指标键
        
        参数:
            name: 指标名称
            labels: 标签
            
        返回:
            指标键
        """
        if not labels:
            return name
        
        labels_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{labels_str}}}"
    
    def reset(self, name: str = None, labels: Dict = None) -> None:
        """
        重置指标
        
        参数:
            name: 指标名称（可选，不传则重置所有）
            labels: 标签
        """
        if name is None:
            self._metrics.clear()
            self._timestamps.clear()
        else:
            key = self._make_key(name, labels)
            if key in self._metrics:
                del self._metrics[key]
            if key in self._timestamps:
                del self._timestamps[key]


class AlertManager:
    """
    告警管理器
    
    管理告警规则和告警通知
    """
    
    def __init__(self):
        """初始化告警管理器"""
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._callbacks: List[Callable[[Alert], None]] = []
        self.logger = api_logger
    
    def add_rule(self, rule: AlertRule) -> None:
        """
        添加告警规则
        
        参数:
            rule: 告警规则
        """
        self._rules[rule.name] = rule
        self.logger.info("alert_rule_added", extra={
            'event': 'alert_rule_added',
            'rule_name': rule.name,
            'level': rule.level.value,
            'timestamp': datetime.now().isoformat()
        })
    
    def remove_rule(self, name: str) -> bool:
        """
        移除告警规则
        
        参数:
            name: 规则名称
            
        返回:
            是否移除成功
        """
        if name in self._rules:
            del self._rules[name]
            return True
        return False
    
    def add_callback(self, callback: Callable[[Alert], None]) -> None:
        """
        添加告警回调
        
        参数:
            callback: 回调函数
        """
        self._callbacks.append(callback)
    
    def check_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        检查告警规则
        
        参数:
            metrics: 指标字典
            
        返回:
            触发的告警列表
        """
        triggered_alerts = []
        now = datetime.now()
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            # 检查冷却时间
            if rule.last_triggered:
                cooldown_end = rule.last_triggered.timestamp() + rule.cooldown
                if now.timestamp() < cooldown_end:
                    continue
            
            # 获取指标值
            metric_value = metrics.get(rule.metric)
            if metric_value is None:
                continue
            
            # 检查条件
            try:
                if rule.condition(metric_value):
                    alert = Alert(
                        rule_name=rule.name,
                        level=rule.level,
                        message=rule.message,
                        metric_value=metric_value,
                        triggered_at=now
                    )
                    
                    self._alerts.append(alert)
                    triggered_alerts.append(alert)
                    rule.last_triggered = now
                    
                    # 通知回调
                    for callback in self._callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            self.logger.error("alert_callback_failed", extra={
                                'event': 'alert_callback_failed',
                                'rule_name': rule.name,
                                'error': str(e),
                                'timestamp': now.isoformat()
                            })
                    
                    self.logger.warning("alert_triggered", extra={
                        'event': 'alert_triggered',
                        'rule_name': rule.name,
                        'level': rule.level.value,
                        'message': rule.message,
                        'metric_value': metric_value,
                        'timestamp': now.isoformat()
                    })
            except Exception as e:
                self.logger.error("rule_check_failed", extra={
                    'event': 'rule_check_failed',
                    'rule_name': rule.name,
                    'error': str(e),
                    'timestamp': now.isoformat()
                })
        
        return triggered_alerts
    
    def get_alerts(self, limit: int = 100) -> List[Alert]:
        """
        获取告警列表
        
        参数:
            limit: 最大返回数量
            
        返回:
            告警列表
        """
        return self._alerts[-limit:]
    
    def clear_alerts(self) -> None:
        """清空告警"""
        self._alerts.clear()


# 预定义的告警规则
DEFAULT_ALERT_RULES = [
    AlertRule(
        name='high_error_rate',
        metric='error_rate',
        condition=lambda x: x > 0.05,  # 错误率 > 5%
        level=AlertLevel.ERROR,
        message='系统错误率超过 5%',
        cooldown=300
    ),
    AlertRule(
        name='high_latency',
        metric='avg_latency',
        condition=lambda x: x > 10.0,  # 平均延迟 > 10 秒
        level=AlertLevel.WARNING,
        message='系统平均响应时间超过 10 秒',
        cooldown=300
    ),
    AlertRule(
        name='low_success_rate',
        metric='success_rate',
        condition=lambda x: x < 0.90,  # 成功率 < 90%
        level=AlertLevel.ERROR,
        message='系统成功率低于 90%',
        cooldown=300
    ),
    AlertRule(
        name='high_concurrent_tasks',
        metric='active_tasks',
        condition=lambda x: x > 100,  # 活跃任务 > 100
        level=AlertLevel.WARNING,
        message='并发任务数超过 100',
        cooldown=300
    ),
    AlertRule(
        name='cache_hit_rate_low',
        metric='cache_hit_rate',
        condition=lambda x: x < 0.50,  # 缓存命中率 < 50%
        level=AlertLevel.INFO,
        message='缓存命中率低于 50%',
        cooldown=600
    ),
]


# 全局实例
_metrics_collector = MetricsCollector()
_alert_manager = AlertManager()

# 注册默认告警规则
for rule in DEFAULT_ALERT_RULES:
    _alert_manager.add_rule(rule)


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器"""
    return _metrics_collector


def get_alert_manager() -> AlertManager:
    """获取告警管理器"""
    return _alert_manager


# 便捷函数
def record_metric(name: str, value: Any, labels: Dict = None) -> None:
    """记录指标"""
    _metrics_collector.set(name, value, labels)


def increment_metric(name: str, value: int = 1, labels: Dict = None) -> None:
    """增加指标"""
    _metrics_collector.increment(name, value, labels)


def check_alerts() -> List[Alert]:
    """检查告警"""
    metrics = _metrics_collector.get_all()
    return _alert_manager.check_rules(metrics)


# 使用示例
"""
from wechat_backend.v2.services.monitoring import (
    record_metric,
    increment_metric,
    check_alerts,
    get_alert_manager
)

# 记录指标
record_metric('error_rate', 0.03)
record_metric('avg_latency', 5.5)
increment_metric('total_requests')

# 检查告警
alerts = check_alerts()

# 添加自定义告警回调
def send_notification(alert):
    # 发送通知逻辑
    pass

get_alert_manager().add_callback(send_notification)
"""
