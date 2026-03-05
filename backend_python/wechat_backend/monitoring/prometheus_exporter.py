"""
Prometheus 指标导出器

功能:
1. 导出连接池指标到 Prometheus
2. 支持自定义指标前缀
3. 自动注册和采集指标
4. 提供 /metrics 端点

【P2 实现 - 2026-03-05】
"""

import time
from typing import Optional, Dict, Any
from wechat_backend.logging_config import app_logger

# 尝试导入 prometheus_client
try:
    from prometheus_client import (
        Gauge, Counter, Histogram, Info, CollectorRegistry,
        generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    app_logger.warning("[Prometheus] prometheus_client 未安装，指标导出功能将不可用")
    app_logger.warning("[Prometheus] 安装方式：pip install prometheus-client")


class PrometheusMetricsExporter:
    """
    Prometheus 指标导出器

    导出以下指标:
    - database_pool_active_connections: 活跃连接数
    - database_pool_available_connections: 可用连接数
    - database_pool_max_connections: 最大连接数
    - database_pool_utilization_rate: 利用率
    - database_pool_timeout_total: 超时总数
    - database_pool_potential_leaks: 潜在泄漏数
    - database_pool_health_status: 健康状态 (gauge)
    - pool_monitor_scrapes_total: 采集次数
    - pool_monitor_scrape_duration_seconds: 采集耗时
    """

    def __init__(self, prefix: str = 'pool'):
        """
        初始化导出器

        参数:
            prefix: 指标前缀，默认 'pool'
        """
        if not PROMETHEUS_AVAILABLE:
            app_logger.warning("[Prometheus] 无法初始化导出器，prometheus_client 不可用")
            self._enabled = False
            return

        self._enabled = True
        self.prefix = prefix
        self._registry = CollectorRegistry()
        self._last_scrape_time = 0
        self._scrape_count = 0

        # 定义指标
        self._define_metrics()

        app_logger.info(f"[Prometheus] 指标导出器已初始化，前缀={prefix}")

    def _define_metrics(self):
        """定义 Prometheus 指标"""
        prefix = self.prefix

        # 数据库连接池指标
        self.db_active = Gauge(
            f'{prefix}_database_pool_active_connections',
            'Number of active database connections',
            registry=self._registry
        )

        self.db_available = Gauge(
            f'{prefix}_database_pool_available_connections',
            'Number of available database connections',
            registry=self._registry
        )

        self.db_max = Gauge(
            f'{prefix}_database_pool_max_connections',
            'Maximum number of database connections',
            registry=self._registry
        )

        self.db_utilization = Gauge(
            f'{prefix}_database_pool_utilization_rate',
            'Database connection pool utilization rate (0-1)',
            registry=self._registry
        )

        self.db_timeout = Counter(
            f'{prefix}_database_pool_timeout_total',
            'Total number of database connection timeouts',
            registry=self._registry
        )

        self.db_leaks = Gauge(
            f'{prefix}_database_pool_potential_leaks',
            'Number of potential database connection leaks',
            registry=self._registry
        )

        self.db_health = Gauge(
            f'{prefix}_database_pool_health_status',
            'Database pool health status (0=unhealthy, 1=healthy)',
            registry=self._registry
        )

        # HTTP 连接池指标
        self.http_active = Gauge(
            f'{prefix}_http_pool_active_sessions',
            'Number of active HTTP sessions',
            registry=self._registry
        )

        self.http_max = Gauge(
            f'{prefix}_http_pool_max_size',
            'Maximum size of HTTP connection pool',
            registry=self._registry
        )

        # 监控器指标
        self.scrape_count = Counter(
            f'{prefix}_monitor_scrapes_total',
            'Total number of metric scrapes',
            registry=self._registry
        )

        self.scrape_duration = Histogram(
            f'{prefix}_monitor_scrape_duration_seconds',
            'Time spent scraping metrics',
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
            registry=self._registry
        )

        # 告警指标
        self.alert_total = Counter(
            f'{prefix}_alerts_total',
            'Total number of alerts',
            ['severity'],  # severity label: info/warning/error/critical
            registry=self._registry
        )

        self.alert_active = Gauge(
            f'{prefix}_alerts_active',
            'Number of active alerts',
            ['severity'],
            registry=self._registry
        )

        # 系统信息
        self.info = Info(
            f'{prefix}_info',
            'Connection pool monitoring system information',
            registry=self._registry
        )
        self.info.info({
            'version': '1.0.0',
            'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')
        })

    def update_metrics(self, pool_metrics: Dict[str, Any], alert_summary: Optional[Dict] = None):
        """
        更新 Prometheus 指标

        参数:
            pool_metrics: 连接池指标字典
            alert_summary: 告警统计字典（可选）
        """
        if not self._enabled:
            return

        start_time = time.time()

        try:
            # 更新数据库连接池指标
            db_metrics = pool_metrics.get('database', {})
            if db_metrics:
                self.db_active.set(db_metrics.get('active_connections', 0))
                self.db_available.set(db_metrics.get('available_connections', 0))
                self.db_max.set(db_metrics.get('max_connections', 0))
                self.db_utilization.set(db_metrics.get('utilization_rate', 0))
                self.db_leaks.set(db_metrics.get('potential_leaks', 0))

                # 健康状态转换
                health_status = db_metrics.get('health_status', 'healthy')
                health_map = {'healthy': 1.0, 'caution': 0.5, 'warning': 0.3, 'critical': 0.0}
                self.db_health.set(health_map.get(health_status, 0))

                # 超时计数（只增不减）
                timeout_count = db_metrics.get('timeout_count', 0)
                # 注意：Counter 只能递增，需要跟踪上次值
                # 这里简化处理，假设超时计数只增不减
                self.db_timeout._value._value = timeout_count

            # 更新 HTTP 连接池指标
            http_metrics = pool_metrics.get('http', {})
            if http_metrics:
                self.http_active.set(http_metrics.get('active_sessions', 0))
                self.http_max.set(http_metrics.get('pool_maxsize', 0))

            # 更新告警指标
            if alert_summary:
                by_severity = alert_summary.get('by_severity', {})
                for severity, count in by_severity.items():
                    self.alert_total.labels(severity=severity).inc(count)
                    self.alert_active.labels(severity=severity).set(count)

            # 更新采集统计
            self._scrape_count += 1
            self.scrape_count.inc()

            duration = time.time() - start_time
            self.scrape_duration.observe(duration)

            self._last_scrape_time = time.time()

        except Exception as e:
            app_logger.error(f"[Prometheus] 更新指标失败：{e}")

    def get_metrics(self) -> bytes:
        """
        获取 Prometheus 格式指标

        返回:
            Prometheus 格式的指标数据（字节）
        """
        if not self._enabled:
            return b"# Prometheus metrics not available\n"

        try:
            return generate_latest(self._registry)
        except Exception as e:
            app_logger.error(f"[Prometheus] 生成指标失败：{e}")
            return b"# Error generating metrics\n"

    def get_content_type(self) -> str:
        """获取内容类型"""
        return CONTENT_TYPE_LATEST

    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled


# 全局导出器实例
_exporter: Optional[PrometheusMetricsExporter] = None


def get_prometheus_exporter() -> Optional[PrometheusMetricsExporter]:
    """获取 Prometheus 导出器实例"""
    global _exporter
    if _exporter is None:
        _exporter = PrometheusMetricsExporter(prefix='pool')
    return _exporter


def update_prometheus_metrics(pool_metrics: Dict[str, Any], alert_summary: Optional[Dict] = None):
    """便捷函数：更新 Prometheus 指标"""
    exporter = get_prometheus_exporter()
    if exporter:
        exporter.update_metrics(pool_metrics, alert_summary)


def generate_prometheus_metrics() -> bytes:
    """便捷函数：生成 Prometheus 指标数据"""
    exporter = get_prometheus_exporter()
    if exporter:
        return exporter.get_metrics()
    return b"# Prometheus metrics not available\n"
