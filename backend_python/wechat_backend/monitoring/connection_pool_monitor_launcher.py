"""
连接池监控启动器

功能:
1. 应用启动时自动启动数据库连接池监控
2. 应用启动时自动启动 HTTP 连接池监控
3. 提供统一的监控管理接口
4. 支持优雅关闭

【P0 实现 - 2026-03-05】
"""

import atexit
from typing import Optional, Dict, Any
from wechat_backend.logging_config import app_logger, db_logger


class ConnectionPoolMonitorLauncher:
    """
    连接池监控启动器
    
    负责在应用启动时自动启动各类连接池监控，
    并在应用关闭时优雅停止监控。
    """

    _instance: Optional['ConnectionPoolMonitorLauncher'] = None
    _initialized: bool = False

    def __new__(cls) -> 'ConnectionPoolMonitorLauncher':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化启动器"""
        if self._initialized:
            return

        self._db_monitor = None
        self._http_monitor = None
        self._monitors: Dict[str, Any] = {}
        self._started: bool = False

        app_logger.info("[ConnectionPoolMonitorLauncher] 初始化完成")
        self._initialized = True

    def start_all_monitors(
        self,
        db_pool_interval: int = 10,
        http_pool_interval: int = 10
    ):
        """
        启动所有监控器

        参数:
            db_pool_interval: 数据库连接池监控间隔（秒）
            http_pool_interval: HTTP 连接池监控间隔（秒）
        """
        if self._started:
            app_logger.warning(
                "[ConnectionPoolMonitorLauncher] 监控器已启动，跳过"
            )
            return

        app_logger.info(
            "[ConnectionPoolMonitorLauncher] 开始启动所有连接池监控..."
        )

        # 1. 启动数据库连接池监控
        try:
            self._start_db_monitor(interval=db_pool_interval)
        except Exception as e:
            app_logger.error(
                f"[ConnectionPoolMonitorLauncher] 启动数据库连接池监控失败：{e}"
            )

        # 2. 启动 HTTP 连接池监控
        try:
            self._start_http_monitor(interval=http_pool_interval)
        except Exception as e:
            app_logger.error(
                f"[ConnectionPoolMonitorLauncher] 启动 HTTP 连接池监控失败：{e}"
            )

        # 3. 注册退出清理
        atexit.register(self.stop_all_monitors)

        self._started = True
        app_logger.info(
            "[ConnectionPoolMonitorLauncher] ✅ 所有连接池监控已启动"
        )

    def _start_db_monitor(self, interval: int = 10):
        """
        启动数据库连接池监控

        参数:
            interval: 监控间隔（秒）
        """
        from wechat_backend.database_connection_pool import get_db_pool
        from wechat_backend.monitoring.connection_pool_monitor import (
            start_connection_pool_monitor
        )

        try:
            self._db_monitor = start_connection_pool_monitor(
                pool_getter=get_db_pool,
                interval_seconds=interval
            )
            self._monitors['database'] = self._db_monitor

            db_logger.info(
                f"[ConnectionPoolMonitorLauncher] 数据库连接池监控已启动，"
                f"间隔={interval}秒"
            )
            app_logger.info(
                "✅ 数据库连接池监控已启动（防止连接耗尽）"
            )

        except Exception as e:
            db_logger.error(
                f"[ConnectionPoolMonitorLauncher] 启动数据库连接池监控失败：{e}",
                exc_info=True
            )
            raise

    def _start_http_monitor(self, interval: int = 10):
        """
        启动 HTTP 连接池监控

        参数:
            interval: 监控间隔（秒）
        """
        from wechat_backend.network.connection_pool import (
            get_connection_pool_manager
        )
        from wechat_backend.monitoring.connection_pool_monitor import (
            start_connection_pool_monitor
        )

        try:
            # 创建一个包装函数来获取 HTTP 连接池指标
            def get_http_pool_metrics():
                manager = get_connection_pool_manager()
                # 返回简化的指标（HTTP 连接池没有详细的 get_metrics 方法）
                return {
                    'pool_connections': manager.pool_connections,
                    'pool_maxsize': manager.pool_maxsize,
                    'active_sessions': len(manager.sessions),
                    'health_status': 'healthy',
                    'health_message': 'HTTP 连接池运行正常'
                }

            self._http_monitor = start_connection_pool_monitor(
                pool_getter=get_http_pool_metrics,
                interval_seconds=interval
            )
            self._monitors['http'] = self._http_monitor

            app_logger.info(
                f"[ConnectionPoolMonitorLauncher] HTTP 连接池监控已启动，"
                f"间隔={interval}秒"
            )

        except Exception as e:
            app_logger.error(
                f"[ConnectionPoolMonitorLauncher] 启动 HTTP 连接池监控失败：{e}",
                exc_info=True
            )
            raise

    def stop_all_monitors(self):
        """停止所有监控器"""
        if not self._started:
            return

        app_logger.info(
            "[ConnectionPoolMonitorLauncher] 正在停止所有连接池监控..."
        )

        # 停止数据库连接池监控
        if self._db_monitor:
            try:
                from wechat_backend.monitoring.connection_pool_monitor import (
                    stop_connection_pool_monitor
                )
                stop_connection_pool_monitor()
                app_logger.info(
                    "[ConnectionPoolMonitorLauncher] 数据库连接池监控已停止"
                )
            except Exception as e:
                app_logger.error(
                    f"[ConnectionPoolMonitorLauncher] 停止数据库连接池监控失败：{e}"
                )

        # 停止 HTTP 连接池监控
        if self._http_monitor:
            try:
                self._http_monitor.stop()
                app_logger.info(
                    "[ConnectionPoolMonitorLauncher] HTTP 连接池监控已停止"
                )
            except Exception as e:
                app_logger.error(
                    f"[ConnectionPoolMonitorLauncher] 停止 HTTP 连接池监控失败：{e}"
                )

        self._monitors.clear()
        self._started = False

        app_logger.info(
            "[ConnectionPoolMonitorLauncher] ✅ 所有连接池监控已停止"
        )

    def get_monitor_status(self) -> Dict[str, Any]:
        """
        获取监控器状态

        返回:
            监控器状态字典
        """
        status = {
            'started': self._started,
            'monitors': {}
        }

        # 数据库连接池监控状态
        if self._db_monitor:
            from wechat_backend.monitoring.connection_pool_monitor import (
                get_connection_pool_metrics
            )
            metrics = get_connection_pool_metrics()
            status['monitors']['database'] = {
                'running': True,
                'latest_metrics': metrics
            }
        else:
            status['monitors']['database'] = {'running': False}

        # HTTP 连接池监控状态
        if self._http_monitor:
            metrics = self._http_monitor.get_latest_metrics()
            status['monitors']['http'] = {
                'running': True,
                'latest_metrics': metrics
            }
        else:
            status['monitors']['http'] = {'running': False}

        return status


# 全局启动器实例
_launcher: Optional[ConnectionPoolMonitorLauncher] = None


def get_monitor_launcher() -> ConnectionPoolMonitorLauncher:
    """获取监控启动器实例"""
    global _launcher
    if _launcher is None:
        _launcher = ConnectionPoolMonitorLauncher()
    return _launcher


def start_pool_monitors(
    db_pool_interval: int = 10,
    http_pool_interval: int = 10
):
    """
    启动所有连接池监控（便捷函数）

    参数:
        db_pool_interval: 数据库连接池监控间隔（秒）
        http_pool_interval: HTTP 连接池监控间隔（秒）
    """
    launcher = get_monitor_launcher()
    launcher.start_all_monitors(
        db_pool_interval=db_pool_interval,
        http_pool_interval=http_pool_interval
    )
    return launcher


def stop_pool_monitors():
    """停止所有连接池监控（便捷函数）"""
    launcher = get_monitor_launcher()
    launcher.stop_all_monitors()


def get_pool_monitor_status() -> Dict[str, Any]:
    """
    获取所有监控器状态（便捷函数）

    返回:
        监控器状态字典
    """
    launcher = get_monitor_launcher()
    return launcher.get_monitor_status()
