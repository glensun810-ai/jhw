"""
连接池监控模块

功能:
1. 定期采集连接池指标
2. 发送告警（利用率>80% 警告，>90% 严重）
3. 记录监控历史

【P2 新增】2026-03-05
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from wechat_backend.logging_config import api_logger


class ConnectionPoolMonitor:
    """连接池监控器"""

    def __init__(self, pool_getter: Callable):
        """
        初始化监控器

        参数:
            pool_getter: 获取连接池实例的函数
        """
        self._pool_getter = pool_getter
        self._history = []
        self._max_history = 1000  # 最多保留 1000 条记录
        self._stop_event = threading.Event()
        self._thread = None
        self._alert_callbacks = []  # 告警回调列表

        api_logger.info("[ConnectionPoolMonitor] 初始化完成")

    def start(self, interval_seconds: int = 10):
        """
        启动监控

        参数:
            interval_seconds: 采集间隔
        """
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ConnectionPoolMonitor"
        )
        self._thread.start()
        api_logger.info(
            f"[ConnectionPoolMonitor] 监控已启动，间隔={interval_seconds}秒"
        )

    def stop(self):
        """停止监控"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        api_logger.info("[ConnectionPoolMonitor] 监控已停止")

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加告警回调

        参数:
            callback: 告警回调函数，接收 metrics 字典
        """
        self._alert_callbacks.append(callback)
        api_logger.debug("[ConnectionPoolMonitor] 添加告警回调")

    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                pool = self._pool_getter()
                if pool:
                    metrics = pool.get_metrics()
                    self._record_metric(metrics)
                    self._check_alerts(metrics)
            except Exception as e:
                api_logger.error(
                    f"[ConnectionPoolMonitor] 采集失败：{e}"
                )

            self._stop_event.wait(10.0)  # 每 10 秒采集一次

    def _record_metric(self, metrics: Dict[str, Any]):
        """记录指标"""
        metrics['timestamp'] = datetime.now().isoformat()
        self._history.append(metrics)

        # 限制历史记录大小
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def _check_alerts(self, metrics: Dict[str, Any]):
        """检查告警"""
        alert_level = metrics.get('alert_level', 'none')

        if alert_level == 'critical':
            api_logger.error(
                f"[连接池告警] 严重：{metrics['health_message']}, "
                f"利用率={metrics['utilization_rate']*100:.1f}%, "
                f"active={metrics['active_connections']}, "
                f"available={metrics['available_connections']}, "
                f"potential_leaks={metrics['potential_leaks']}"
            )
            self._notify_alerts(metrics)
            # 【P0 新增】使用增强告警管理器发送多渠道告警
            self._send_enhanced_alert(metrics)

        elif alert_level == 'warning':
            api_logger.warning(
                f"[连接池告警] 警告：{metrics['health_message']}, "
                f"利用率={metrics['utilization_rate']*100:.1f}%, "
                f"active={metrics['active_connections']}"
            )
            self._notify_alerts(metrics)
            # 【P0 新增】使用增强告警管理器发送多渠道告警
            self._send_enhanced_alert(metrics)

    def _send_enhanced_alert(self, metrics: Dict[str, Any]):
        """
        使用增强告警管理器发送多渠道告警

        参数:
            metrics: 连接池指标
        """
        try:
            from wechat_backend.monitoring.enhanced_alert_manager import (
                get_enhanced_alert_manager
            )
            alert_manager = get_enhanced_alert_manager()
            alert_manager.handle_connection_pool_alert(metrics)
        except Exception as e:
            api_logger.error(
                f"[ConnectionPoolMonitor] 发送增强告警失败：{e}"
            )

    def _notify_alerts(self, metrics: Dict[str, Any]):
        """通知告警回调"""
        for callback in self._alert_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                api_logger.error(
                    f"[ConnectionPoolMonitor] 告警回调失败：{e}"
                )

    def get_history(self, limit: int = 100) -> list:
        """
        获取历史记录

        参数:
            limit: 返回数量限制

        返回:
            历史记录列表
        """
        return self._history[-limit:]

    def get_latest_metrics(self) -> Optional[Dict[str, Any]]:
        """获取最新指标"""
        if self._history:
            return self._history[-1]
        return None


# 全局监控器实例
_monitor: Optional[ConnectionPoolMonitor] = None


def start_connection_pool_monitor(
    pool_getter: Callable,
    interval_seconds: int = 10
) -> ConnectionPoolMonitor:
    """
    启动连接池监控

    参数:
        pool_getter: 获取连接池实例的函数
        interval_seconds: 采集间隔

    返回:
        监控器实例
    """
    global _monitor
    if _monitor is None:
        _monitor = ConnectionPoolMonitor(pool_getter)
        _monitor.start(interval_seconds)
    return _monitor


def get_connection_pool_monitor() -> Optional[ConnectionPoolMonitor]:
    """获取监控器实例"""
    return _monitor


def get_connection_pool_metrics() -> Optional[Dict[str, Any]]:
    """获取最新指标"""
    global _monitor
    if _monitor:
        return _monitor.get_latest_metrics()
    return None


def get_connection_pool_history(limit: int = 100) -> list:
    """获取历史记录"""
    global _monitor
    if _monitor:
        return _monitor.get_history(limit)
    return []


def stop_connection_pool_monitor():
    """停止监控"""
    global _monitor
    if _monitor:
        _monitor.stop()
        _monitor = None
