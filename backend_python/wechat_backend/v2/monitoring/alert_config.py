#!/usr/bin/env python3
"""
Step 2.1: v2 灰度监控告警配置

监控指标与告警规则:
| 指标 | 阈值 | 告警级别 |
|------|------|---------|
| v2 错误率 | > 5% | P1 |
| v2 超时率 | > 2% | P1 |
| 死信队列增长 | > 10/小时 | P2 |
| 平均响应时间 | > 30s | P2 |

使用方法:
    from wechat_backend.v2.monitoring.alert_config import ALERT_RULES, check_v2_metrics
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class AlertSeverity(Enum):
    """告警级别"""
    P0 = 'P0'  # 严重 - 系统不可用
    P1 = 'P1'  # 高 - 核心功能受损
    P2 = 'P2'  # 中 - 部分功能异常
    P3 = 'P3'  # 低 - 轻微问题


@dataclass
class AlertRule:
    """告警规则定义"""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # '>', '<', '>=', '<=', '=='
    window: str  # 时间窗口，如 '5m', '1h'
    severity: AlertSeverity
    description: str
    enabled: bool = True
    consecutive_violations: int = 1  # 连续违规次数触发告警
    notification_targets: List[str] = field(default_factory=list)


# ==================== v2 告警规则配置 ====================

ALERT_RULES: Dict[str, AlertRule] = {
    # P1 告警 - v2 错误率
    'v2_error_rate': AlertRule(
        name='v2_error_rate',
        metric_name='v2.error_rate',
        threshold=0.05,  # 5%
        comparison='>',
        window='5m',
        severity=AlertSeverity.P1,
        description='v2 版本错误率超过 5%',
        notification_targets=['admin@company.com', 'oncall@company.com'],
    ),

    # P1 告警 - v2 超时率
    'v2_timeout_rate': AlertRule(
        name='v2_timeout_rate',
        metric_name='v2.timeout_rate',
        threshold=0.02,  # 2%
        comparison='>',
        window='5m',
        severity=AlertSeverity.P1,
        description='v2 版本超时率超过 2%',
        notification_targets=['admin@company.com', 'oncall@company.com'],
    ),

    # P2 告警 - 死信队列增长
    'v2_dead_letter_growth': AlertRule(
        name='v2_dead_letter_growth',
        metric_name='v2.dead_letter_growth_per_hour',
        threshold=10,  # 10 条/小时
        comparison='>',
        window='1h',
        severity=AlertSeverity.P2,
        description='v2 死信队列每小时增长超过 10 条',
        notification_targets=['dev-team@company.com'],
    ),

    # P2 告警 - 平均响应时间
    'v2_avg_response_time': AlertRule(
        name='v2_avg_response_time',
        metric_name='v2.avg_response_time_seconds',
        threshold=30,  # 30 秒
        comparison='>',
        window='5m',
        severity=AlertSeverity.P2,
        description='v2 版本平均响应时间超过 30 秒',
        notification_targets=['dev-team@company.com'],
    ),

    # P3 告警 - v2 请求量下降（用于检测流量异常）
    'v2_request_volume_drop': AlertRule(
        name='v2_request_volume_drop',
        metric_name='v2.request_volume_drop_rate',
        threshold=0.3,  # 30%
        comparison='>',
        window='10m',
        severity=AlertSeverity.P3,
        description='v2 版本请求量下降超过 30%',
        notification_targets=['dev-team@company.com'],
    ),

    # P1 告警 - v2 AI 调用失败率
    'v2_ai_failure_rate': AlertRule(
        name='v2_ai_failure_rate',
        metric_name='v2.ai_failure_rate',
        threshold=0.1,  # 10%
        comparison='>',
        window='5m',
        severity=AlertSeverity.P1,
        description='v2 版本 AI 调用失败率超过 10%',
        notification_targets=['admin@company.com', 'oncall@company.com'],
    ),

    # P2 告警 - v2 数据库错误率
    'v2_database_error_rate': AlertRule(
        name='v2_database_error_rate',
        metric_name='v2.database_error_rate',
        threshold=0.01,  # 1%
        comparison='>',
        window='5m',
        severity=AlertSeverity.P2,
        description='v2 版本数据库错误率超过 1%',
        notification_targets=['dev-team@company.com'],
    ),

    # P1 告警 - v2 认证失败率
    'v2_auth_failure_rate': AlertRule(
        name='v2_auth_failure_rate',
        metric_name='v2.auth_failure_rate',
        threshold=0.05,  # 5%
        comparison='>',
        window='5m',
        severity=AlertSeverity.P1,
        description='v2 版本认证失败率超过 5%',
        notification_targets=['admin@company.com', 'security@company.com'],
    ),
}


# ==================== 监控指标数据模型 ====================

@dataclass
class MetricDataPoint:
    """监控指标数据点"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertEvent:
    """告警事件"""
    alert_time: datetime
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    message: str
    acknowledged: bool = False
    acknowledged_by: str = ''
    acknowledged_at: datetime = None
    resolved: bool = False
    resolved_at: datetime = None


# ==================== 告警历史存储 ====================

ALERT_DATA_DIR = Path(__file__).parent.parent.parent / 'monitoring_data' / 'v2_alerts'
ALERT_HISTORY_FILE = ALERT_DATA_DIR / 'alert_history.json'
METRICS_FILE = ALERT_DATA_DIR / 'metrics.json'

ALERT_DATA_DIR.mkdir(parents=True, exist_ok=True)


class V2AlertManager:
    """v2 告警管理器"""

    def __init__(self):
        self.alert_history: List[AlertEvent] = self._load_alert_history()
        self.metrics: List[MetricDataPoint] = self._load_metrics()
        self.active_alerts: Dict[str, AlertEvent] = {}

    def _load_alert_history(self) -> List[AlertEvent]:
        """加载告警历史"""
        if ALERT_HISTORY_FILE.exists():
            try:
                with open(ALERT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [
                        AlertEvent(
                            alert_time=datetime.fromisoformat(item['alert_time']),
                            rule_name=item['rule_name'],
                            metric_name=item['metric_name'],
                            current_value=item['current_value'],
                            threshold=item['threshold'],
                            severity=AlertSeverity(item['severity']),
                            message=item['message'],
                            acknowledged=item.get('acknowledged', False),
                            acknowledged_by=item.get('acknowledged_by', ''),
                            acknowledged_at=datetime.fromisoformat(item['acknowledged_at']) if item.get('acknowledged_at') else None,
                            resolved=item.get('resolved', False),
                            resolved_at=datetime.fromisoformat(item['resolved_at']) if item.get('resolved_at') else None,
                        )
                        for item in data[-1000:]  # 只保留最近 1000 条
                    ]
            except Exception as e:
                print(f"加载告警历史失败：{e}")
        return []

    def _save_alert_history(self):
        """保存告警历史"""
        try:
            data = []
            for alert in self.alert_history[-1000:]:
                item = {
                    'alert_time': alert.alert_time.isoformat(),
                    'rule_name': alert.rule_name,
                    'metric_name': alert.metric_name,
                    'current_value': alert.current_value,
                    'threshold': alert.threshold,
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'acknowledged': alert.acknowledged,
                    'acknowledged_by': alert.acknowledged_by,
                    'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                }
                data.append(item)

            with open(ALERT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存告警历史失败：{e}")

    def _load_metrics(self) -> List[MetricDataPoint]:
        """加载监控指标"""
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [
                        MetricDataPoint(
                            timestamp=datetime.fromisoformat(item['timestamp']),
                            metric_name=item['metric_name'],
                            value=item['value'],
                            tags=item.get('tags', {}),
                        )
                        for item in data[-10000:]  # 只保留最近 10000 条
                    ]
            except Exception as e:
                print(f"加载监控指标失败：{e}")
        return []

    def _save_metrics(self):
        """保存监控指标"""
        try:
            data = []
            for metric in self.metrics[-10000:]:
                item = {
                    'timestamp': metric.timestamp.isoformat(),
                    'metric_name': metric.metric_name,
                    'value': metric.value,
                    'tags': metric.tags,
                }
                data.append(item)

            with open(METRICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存监控指标失败：{e}")

    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """
        记录监控指标

        Args:
            metric_name: 指标名称
            value: 指标值
            tags: 标签字典
        """
        now = datetime.now()
        self.metrics.append(MetricDataPoint(
            timestamp=now,
            metric_name=metric_name,
            value=value,
            tags=tags or {},
        ))

        # 定期保存
        if len(self.metrics) % 100 == 0:
            self._save_metrics()

        # 检查是否触发告警
        self._check_alerts(metric_name, value, now)

    def _check_alerts(self, metric_name: str, value: float, timestamp: datetime):
        """检查是否触发告警"""
        for rule_name, rule in ALERT_RULES.items():
            if not rule.enabled:
                continue

            if rule.metric_name != metric_name:
                continue

            # 检查是否超过阈值
            violated = False
            if rule.comparison == '>' and value > rule.threshold:
                violated = True
            elif rule.comparison == '>=' and value >= rule.threshold:
                violated = True
            elif rule.comparison == '<' and value < rule.threshold:
                violated = True
            elif rule.comparison == '<=' and value <= rule.threshold:
                violated = True
            elif rule.comparison == '==' and value == rule.threshold:
                violated = True

            if violated:
                # 检查连续违规次数
                recent_violations = self._count_recent_violations(rule_name, rule.window)
                if recent_violations >= rule.consecutive_violations:
                    # 触发告警
                    self._trigger_alert(rule, value, timestamp)

    def _count_recent_violations(self, rule_name: str, window: str) -> int:
        """计算最近时间窗口内的违规次数"""
        window_seconds = self._parse_window(window)
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        count = 0
        for alert in reversed(self.alert_history):
            if alert.alert_time < cutoff:
                break
            if alert.rule_name == rule_name:
                count += 1

        return count

    def _parse_window(self, window: str) -> int:
        """解析时间窗口字符串为秒数"""
        if window.endswith('s'):
            return int(window[:-1])
        elif window.endswith('m'):
            return int(window[:-1]) * 60
        elif window.endswith('h'):
            return int(window[:-1]) * 3600
        elif window.endswith('d'):
            return int(window[:-1]) * 86400
        else:
            return int(window)

    def _trigger_alert(self, rule: AlertRule, value: float, timestamp: datetime):
        """触发告警"""
        # 检查是否已有活跃告警
        if rule.name in self.active_alerts:
            return

        alert = AlertEvent(
            alert_time=timestamp,
            rule_name=rule.name,
            metric_name=rule.metric_name,
            current_value=value,
            threshold=rule.threshold,
            severity=rule.severity,
            message=f"{rule.description} (当前值：{value}, 阈值：{rule.threshold})",
        )

        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)
        self._save_alert_history()

        # 发送通知
        self._send_notification(alert, rule)

        print(f"🚨 [ALERT] {rule.severity.value}: {alert.message}")

    def _send_notification(self, alert: AlertEvent, rule: AlertRule):
        """发送告警通知"""
        # TODO: 实现邮件、短信、钉钉等通知
        # 这里仅打印日志
        notification_msg = (
            f"[{alert.severity.value}] {alert.rule_name}\n"
            f"时间：{alert.alert_time.isoformat()}\n"
            f"指标：{alert.metric_name}\n"
            f"当前值：{alert.current_value}\n"
            f"阈值：{alert.threshold}\n"
            f"描述：{alert.message}\n"
            f"通知目标：{rule.notification_targets}"
        )
        print(notification_msg)

    def acknowledge_alert(self, alert_name: str, acknowledged_by: str):
        """确认告警"""
        if alert_name in self.active_alerts:
            alert = self.active_alerts[alert_name]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now()
            self._save_alert_history()
            del self.active_alerts[alert_name]
            print(f"✅ 告警 {alert_name} 已确认 (确认人：{acknowledged_by})")

    def resolve_alert(self, alert_name: str):
        """解决告警"""
        for alert in self.alert_history:
            if alert.rule_name == alert_name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                self._save_alert_history()
                print(f"✅ 告警 {alert_name} 已解决")
                break

    def get_active_alerts(self) -> List[AlertEvent]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取告警统计"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alert_history if a.alert_time > cutoff]

        summary = {
            'total': len(recent_alerts),
            'by_severity': {},
            'by_rule': {},
            'acknowledged': sum(1 for a in recent_alerts if a.acknowledged),
            'resolved': sum(1 for a in recent_alerts if a.resolved),
        }

        for alert in recent_alerts:
            severity = alert.severity.value
            rule = alert.rule_name

            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            summary['by_rule'][rule] = summary['by_rule'].get(rule, 0) + 1

        return summary

    def get_metric_stats(self, metric_name: str, window: str = '1h') -> Dict[str, float]:
        """获取指标统计"""
        window_seconds = self._parse_window(window)
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        recent_values = [
            m.value for m in self.metrics
            if m.metric_name == metric_name and m.timestamp > cutoff
        ]

        if not recent_values:
            return {'count': 0, 'avg': 0, 'min': 0, 'max': 0, 'latest': 0}

        return {
            'count': len(recent_values),
            'avg': sum(recent_values) / len(recent_values),
            'min': min(recent_values),
            'max': max(recent_values),
            'latest': recent_values[-1],
        }


# ==================== 全局实例 ====================

_v2_alert_manager: V2AlertManager = None


def get_v2_alert_manager() -> V2AlertManager:
    """获取 v2 告警管理器实例"""
    global _v2_alert_manager
    if _v2_alert_manager is None:
        _v2_alert_manager = V2AlertManager()
    return _v2_alert_manager


# ==================== 便捷函数 ====================

def check_v2_metrics(
    error_rate: float = None,
    timeout_rate: float = None,
    dead_letter_count: int = None,
    avg_response_time: float = None,
):
    """
    检查 v2 核心指标并记录

    Args:
        error_rate: 错误率
        timeout_rate: 超时率
        dead_letter_count: 死信队列数量
        avg_response_time: 平均响应时间 (秒)
    """
    manager = get_v2_alert_manager()

    if error_rate is not None:
        manager.record_metric('v2.error_rate', error_rate)

    if timeout_rate is not None:
        manager.record_metric('v2.timeout_rate', timeout_rate)

    if dead_letter_count is not None:
        manager.record_metric('v2.dead_letter_growth_per_hour', dead_letter_count)

    if avg_response_time is not None:
        manager.record_metric('v2.avg_response_time_seconds', avg_response_time)


def get_v2_health_status() -> Dict[str, Any]:
    """
    获取 v2 健康状态

    Returns:
        Dict: 健康状态信息
    """
    manager = get_v2_alert_manager()

    active_alerts = manager.get_active_alerts()
    summary = manager.get_alert_summary(hours=1)

    # 计算健康分数
    health_score = 100
    for alert in active_alerts:
        if alert.severity == AlertSeverity.P0:
            health_score -= 50
        elif alert.severity == AlertSeverity.P1:
            health_score -= 25
        elif alert.severity == AlertSeverity.P2:
            health_score -= 10
        else:
            health_score -= 5

    health_score = max(0, health_score)

    return {
        'health_score': health_score,
        'active_alerts': len(active_alerts),
        'alerts_by_severity': summary['by_severity'],
        'is_healthy': health_score >= 80,
        'last_check': datetime.now().isoformat(),
    }


if __name__ == '__main__':
    # 测试告警功能
    print("=" * 60)
    print("Step 2.1: v2 灰度监控告警测试")
    print("=" * 60)
    print()

    manager = get_v2_alert_manager()

    # 测试错误率告警
    print("📊 测试 v2 错误率告警...")
    manager.record_metric('v2.error_rate', 0.06)  # 6% > 5%

    # 测试超时率告警
    print("⏱️  测试 v2 超时率告警...")
    manager.record_metric('v2.timeout_rate', 0.03)  # 3% > 2%

    # 测试死信队列增长
    print("📦 测试死信队列增长告警...")
    manager.record_metric('v2.dead_letter_growth_per_hour', 15)  # 15 > 10

    # 测试响应时间
    print("🐌 测试响应时间告警...")
    manager.record_metric('v2.avg_response_time_seconds', 35)  # 35s > 30s

    # 获取告警统计
    print("\n📈 告警统计:")
    summary = manager.get_alert_summary(hours=1)
    print(f"  总告警数：{summary['total']}")
    print(f"  按级别：{summary['by_severity']}")
    print(f"  已确认：{summary['acknowledged']}")
    print(f"  已解决：{summary['resolved']}")

    # 获取健康状态
    print("\n🏥 v2 健康状态:")
    health = get_v2_health_status()
    print(f"  健康分数：{health['health_score']}")
    print(f"  活跃告警：{health['active_alerts']}")
    print(f"  是否健康：{health['is_healthy']}")

    print("\n✅ 测试完成")
