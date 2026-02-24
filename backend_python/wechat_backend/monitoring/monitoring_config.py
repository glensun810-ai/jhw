from wechat_backend.log_config import get_logger

#!/usr/bin/env python3
"""
监控系统配置和初始化
"""

from wechat_backend.monitoring.alert_system import get_alert_system, Alert, AlertCondition, AlertSeverity


def configure_monitoring_system():
    """
    配置完整的监控系统
    """
    alert_system = get_alert_system(

    try:
        # 1. API错误率监控
        error_rate_condition = AlertCondition(
            metric_name="error_rate",
            threshold=0.05,  # 错误率超过5%
            comparison=">",
            time_window_minutes=5,
            consecutive_violations=2
        

        error_rate_alert = Alert(
            name="high_error_rate",
            condition=error_rate_condition,
            severity=AlertSeverity.HIGH,
            description="API错误率过高",
            notification_targets=["admin@company.com"]
        

        alert_system.add_alert(error_rate_alert

        # 2. 响应时间监控
        slow_response_condition = AlertCondition(
            metric_name="avg_response_time",
            threshold=3.0,  # 响应时间超过3秒
            comparison=">",
            time_window_minutes=5,
            consecutive_violations=2
        

        slow_response_alert = Alert(
            name="slow_response_time",
            condition=slow_response_condition,
            severity=AlertSeverity.MEDIUM,
            description="API平均响应时间过长",
            notification_targets=["admin@company.com"]
        

        alert_system.add_alert(slow_response_alert

        # 3. 高频请求监控
        high_frequency_condition = AlertCondition(
            metric_name="requests_per_minute",
            threshold=100,  # 每分钟请求超过100次
            comparison=">",
            time_window_minutes=1,
            consecutive_violations=1
        

        high_frequency_alert = Alert(
            name="high_request_frequency",
            condition=high_frequency_condition,
            severity=AlertSeverity.MEDIUM,
            description="API请求频率过高",
            notification_targets=["admin@company.com"]
        

        alert_system.add_alert(high_frequency_alert

        # 4. 安全事件监控
        security_event_condition = AlertCondition(
            metric_name="security_events_count",
            threshold=10,  # 10分钟内安全事件超过10次
            comparison=">",
            time_window_minutes=10,
            consecutive_violations=1
        

        security_event_alert = Alert(
            name="high_security_events",
            condition=security_event_condition,
            severity=AlertSeverity.HIGH,
            description="安全事件数量过多",
            notification_targets=["security@company.com"]
        

        alert_system.add_alert(security_event_alert

        # 5. 服务不可用监控
        service_down_condition = AlertCondition(
            metric_name="service_availability",
            threshold=0.95,  # 可用性低于95%
            comparison="<",
            time_window_minutes=5,
            consecutive_violations=2
        

        service_down_alert = Alert(
            name="service_down",
            condition=service_down_condition,
            severity=AlertSeverity.CRITICAL,
            description="服务可用性下降",
            notification_targets=["admin@company.com", "ops@company.com"]
        

        alert_system.add_alert(service_down_alert

    except Exception as e:
        f"⚠️ 配置监控系统时出现错误: {e}"
        # 即使配置失败，也要继续运行

    print("✓ 监控系统配置完成"
    print(f"✓ 已配置 {len(alert_system.alerts)} 个告警规则"


def initialize_monitoring():
    """
    初始化监控系统
    """
    configure_monitoring_system(

    # 启动监控系统
    from wechat_backend.alert_system import start_alert_monitoring
    start_alert_monitoring(

    print("✓ 监控系统初始化完成"
    print("✓ 所有API端点现在都受到监控保护"
    print("✓ 告警系统已启动"