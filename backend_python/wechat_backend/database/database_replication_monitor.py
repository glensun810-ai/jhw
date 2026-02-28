"""
数据库复制监控模块

功能：
- 复制延迟监控
- 从库健康监控
- 告警通知
- 监控指标 API

参考：P2-6: 数据库读写分离未实现
"""

import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from wechat_backend.logging_config import db_logger, api_logger
from config.config_database import db_router_config


class ReplicationMonitor:
    """
    数据库复制监控器
    
    功能：
    1. 复制延迟监控
    2. 从库健康检查
    3. 告警通知
    4. 监控指标收集
    """
    
    def __init__(self):
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._metrics: Dict[str, Any] = {
            'total_checks': 0,
            'healthy_slaves': 0,
            'unhealthy_slaves': 0,
            'avg_replication_lag_bytes': 0,
            'max_replication_lag_bytes': 0,
            'last_check_time': 0,
            'alerts_triggered': 0,
        }
        self._alert_cooldown: Dict[str, float] = {}
    
    def start(self, interval: int = None):
        """
        启动监控线程
        
        Args:
            interval: 监控间隔（秒）
        """
        if interval is None:
            interval = db_router_config.REPLICATION_LAG_CHECK_INTERVAL
        
        self._running = True
        
        def monitor_loop():
            db_logger.info("数据库复制监控线程已启动")
            while self._running:
                try:
                    self._check_replication_status()
                except Exception as e:
                    db_logger.error(f"复制监控失败：{e}")
                
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop(self):
        """停止监控线程"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            db_logger.info("数据库复制监控已停止")
    
    def _check_replication_status(self):
        """检查复制状态"""
        if not db_router_config.is_read_write_splitting_enabled():
            return
        
        from wechat_backend.database.database_replication import get_replication_manager
        
        manager = get_replication_manager()
        if not manager:
            return
        
        status = manager.get_status()
        slaves = status.get('slaves', [])
        
        healthy_count = 0
        unhealthy_count = 0
        total_lag = 0
        max_lag = 0
        
        for slave in slaves:
            path = slave.get('path', '')
            exists = slave.get('exists', False)
            lag_bytes = slave.get('replication_lag_bytes', 0)
            
            total_lag += lag_bytes
            max_lag = max(max_lag, lag_bytes)
            
            if exists:
                healthy_count += 1
            else:
                unhealthy_count += 1
                self._trigger_alert('slave_unhealthy', f'从库不可用：{path}')
            
            # 检查复制延迟
            if lag_bytes > db_router_config.MAX_REPLICATION_LAG:
                self._trigger_alert(
                    'high_replication_lag',
                    f'复制延迟过高：{path} ({lag_bytes} bytes)'
                )
        
        # 更新监控指标
        self._metrics.update({
            'total_checks': self._metrics['total_checks'] + 1,
            'healthy_slaves': healthy_count,
            'unhealthy_slaves': unhealthy_count,
            'avg_replication_lag_bytes': total_lag / len(slaves) if slaves else 0,
            'max_replication_lag_bytes': max_lag,
            'last_check_time': time.time(),
        })
        
        db_logger.debug(
            f"复制状态检查完成：健康={healthy_count}, "
            f"不健康={unhealthy_count}, 平均延迟={total_lag / len(slaves) if slaves else 0:.0f} bytes"
        )
    
    def _trigger_alert(self, alert_type: str, message: str):
        """
        触发告警（带冷却机制）
        
        Args:
            alert_type: 告警类型
            message: 告警消息
        """
        current_time = time.time()
        
        # 检查冷却时间
        if alert_type in self._alert_cooldown:
            if current_time - self._alert_cooldown[alert_type] < db_router_config.REPLICATION_LAG_ALERT_THRESHOLD:
                return
        
        # 触发告警
        self._alert_cooldown[alert_type] = current_time
        self._metrics['alerts_triggered'] += 1
        
        api_logger.warning(f"[数据库复制告警] {alert_type}: {message}")
        
        # 这里可以集成通知渠道（邮件、短信等）
        # self._send_notification(alert_type, message)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        return self._metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            'is_running': self._running,
            'metrics': self.get_metrics(),
            'config': db_router_config.get_config_summary(),
        }


# 全局监控器实例
_replication_monitor: Optional[ReplicationMonitor] = None


def get_replication_monitor() -> Optional[ReplicationMonitor]:
    """获取复制监控器实例"""
    global _replication_monitor
    
    if _replication_monitor is None:
        _replication_monitor = ReplicationMonitor()
    
    return _replication_monitor


def start_replication_monitoring(interval: int = None):
    """启动复制监控"""
    if not db_router_config.is_read_write_splitting_enabled():
        db_logger.info("读写分离未启用，跳过复制监控")
        return
    
    monitor = get_replication_monitor()
    monitor.start(interval)
    db_logger.info("数据库复制监控已启动")


def stop_replication_monitoring():
    """停止复制监控"""
    monitor = get_replication_monitor()
    monitor.stop()
    db_logger.info("数据库复制监控已停止")


def get_replication_metrics() -> Dict[str, Any]:
    """获取复制监控指标"""
    monitor = get_replication_monitor()
    
    if monitor:
        return monitor.get_metrics()
    
    return {
        'enabled': False,
        'message': '监控未启动'
    }


def get_replication_status() -> Dict[str, Any]:
    """获取复制状态"""
    from wechat_backend.database.database_replication import get_replication_status as get_repl_status
    
    status = get_repl_status()
    monitor = get_replication_monitor()
    
    if monitor:
        status['monitoring'] = monitor.get_status()
    
    return status
