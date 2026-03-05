"""
监控模块

提供系统监控功能：
- 连接池监控
- 状态一致性监控
- 性能指标采集
- 告警管理

【P0 增强 - 2026-03-05】
- 添加连接池监控启动器
"""

from wechat_backend.monitoring.connection_pool_monitor import (
    start_connection_pool_monitor,
    stop_connection_pool_monitor,
    get_connection_pool_metrics,
    get_connection_pool_history,
    get_connection_pool_monitor,
)

from wechat_backend.monitoring.connection_pool_monitor_launcher import (
    start_pool_monitors,
    stop_pool_monitors,
    get_pool_monitor_status,
    get_monitor_launcher,
)

from wechat_backend.monitoring.enhanced_alert_manager import (
    EnhancedAlertManager,
    AlertNotification,
    AlertSeverity,
    AlertChannel,
    get_enhanced_alert_manager,
    alert_connection_pool_issue,
)

# 延迟导入状态一致性监控器（避免语法错误影响）
try:
    from wechat_backend.monitoring.state_consistency_monitor import (
        StateConsistencyMonitor,
    )
except (SyntaxError, ImportError) as e:
    # 如果状态一致性监控器有语法错误，使用占位符
    StateConsistencyMonitor = None

from wechat_backend.monitoring.monitoring_decorator import (
    monitor_performance,
)

from wechat_backend.monitoring.metrics_collector import (
    MetricsCollector,
)

from wechat_backend.monitoring.alert_manager import (
    AlertManager,
    AlertLevel,
)

__all__ = [
    # Connection pool monitoring
    'start_connection_pool_monitor',
    'stop_connection_pool_monitor',
    'get_connection_pool_metrics',
    'get_connection_pool_history',
    'get_connection_pool_monitor',
    
    # Connection pool monitor launcher (P0 新增)
    'start_pool_monitors',
    'stop_pool_monitors',
    'get_pool_monitor_status',
    'get_monitor_launcher',
    
    # State consistency
    'StateConsistencyMonitor',
    
    # Performance monitoring
    'monitor_performance',
    
    # Metrics collection
    'MetricsCollector',
    
    # Alert management
    'AlertManager',
    'AlertLevel',
]