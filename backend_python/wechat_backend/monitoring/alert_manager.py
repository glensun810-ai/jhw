#!/usr/bin/env python3
"""
P2-6 修复：监控告警模块

功能：
1. 关键指标监控
2. 自动告警通知
3. 告警历史记录
4. 告警级别管理

使用示例:
    from wechat_backend.monitoring.alert_manager import AlertManager
    
    alert_manager = AlertManager()
    
    # 检查并触发告警
    alert_manager.check_and_alert(
        metric_name='error_rate',
        value=0.15,
        threshold=0.1,
        alert_level='WARNING'
    )
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from wechat_backend.logging_config import api_logger

# 告警数据存储路径
ALERT_DATA_DIR = Path(__file__).parent.parent / 'monitoring_data' / 'alerts'
ALERT_HISTORY_FILE = ALERT_DATA_DIR / 'alert_history.json'

# 确保目录存在
ALERT_DATA_DIR.mkdir(parents=True, exist_ok=True)


class AlertLevel:
    """告警级别"""
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_history = self._load_alert_history()
        self.alert_thresholds = self._load_thresholds()
    
    def _load_alert_history(self) -> List[Dict]:
        """加载告警历史"""
        if ALERT_HISTORY_FILE.exists():
            try:
                with open(ALERT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                api_logger.error(f"[Alert] Error loading alert history: {e}", exc_info=True)
                return []
        return []
    
    def _save_alert_history(self):
        """保存告警历史"""
        try:
            # 只保留最近 1000 条
            recent_alerts = self.alert_history[-1000:]
            with open(ALERT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(recent_alerts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            api_logger.error(f'[Alert] 保存告警历史失败：{e}')
    
    def _load_thresholds(self) -> Dict:
        """加载告警阈值配置"""
        return {
            'error_rate': {'warning': 0.05, 'error': 0.1, 'critical': 0.2},
            'response_time': {'warning': 500, 'error': 1000, 'critical': 2000},  # ms
            'ai_failure_rate': {'warning': 0.1, 'error': 0.2, 'critical': 0.3},
            'auth_failure_rate': {'warning': 0.05, 'error': 0.1, 'critical': 0.2},
            'database_error_rate': {'warning': 0.01, 'error': 0.05, 'critical': 0.1},
        }
    
    def check_and_alert(
        self,
        metric_name: str,
        value: float,
        threshold: Optional[float] = None,
        alert_level: str = AlertLevel.WARNING,
        message: Optional[str] = None
    ) -> bool:
        """
        检查指标并触发告警
        
        Args:
            metric_name: 指标名称
            value: 当前值
            threshold: 阈值（可选，使用配置中的值）
            alert_level: 告警级别
            message: 自定义消息
        
        Returns:
            bool: 是否触发了告警
        """
        # 如果未提供阈值，使用配置中的值
        if threshold is None:
            if metric_name in self.alert_thresholds:
                threshold = self.alert_thresholds[metric_name].get(alert_level.lower())
        
        if threshold is None:
            return False
        
        # 检查是否超过阈值
        if value <= threshold:
            return False
        
        # 触发告警
        alert = {
            'timestamp': datetime.now().isoformat(),
            'metric_name': metric_name,
            'value': value,
            'threshold': threshold,
            'level': alert_level,
            'message': message or f'{metric_name} 超过阈值：{value} > {threshold}'
        }
        
        # 添加到历史记录
        self.alert_history.append(alert)
        self._save_alert_history()
        
        # 记录日志
        log_message = f"[Alert] {alert_level}: {alert['message']}"
        if alert_level == AlertLevel.CRITICAL:
            api_logger.critical(log_message)
        elif alert_level == AlertLevel.ERROR:
            api_logger.error(log_message)
        elif alert_level == AlertLevel.WARNING:
            api_logger.warning(log_message)
        else:
            api_logger.info(log_message)
        
        return True
    
    def check_error_rate(self, error_count: int, total_count: int):
        """检查错误率"""
        if total_count == 0:
            return
        
        error_rate = error_count / total_count
        
        self.check_and_alert(
            metric_name='error_rate',
            value=error_rate,
            alert_level=AlertLevel.WARNING,
            message=f'错误率过高：{error_rate:.2%} ({error_count}/{total_count})'
        )
    
    def check_response_time(self, response_time_ms: float):
        """检查响应时间"""
        self.check_and_alert(
            metric_name='response_time',
            value=response_time_ms,
            alert_level=AlertLevel.WARNING,
            message=f'响应时间过长：{response_time_ms:.0f}ms'
        )
    
    def check_ai_failure_rate(self, failure_count: int, total_count: int):
        """检查 AI 调用失败率"""
        if total_count == 0:
            return
        
        failure_rate = failure_count / total_count
        
        self.check_and_alert(
            metric_name='ai_failure_rate',
            value=failure_rate,
            alert_level=AlertLevel.WARNING,
            message=f'AI 调用失败率过高：{failure_rate:.2%} ({failure_count}/{total_count})'
        )
    
    def check_auth_failure_rate(self, failure_count: int, total_count: int):
        """检查认证失败率"""
        if total_count == 0:
            return
        
        failure_rate = failure_count / total_count
        
        self.check_and_alert(
            metric_name='auth_failure_rate',
            value=failure_rate,
            alert_level=AlertLevel.WARNING,
            message=f'认证失败率过高：{failure_rate:.2%} ({failure_count}/{total_count})'
        )
    
    def get_recent_alerts(self, limit: int = 10, level: Optional[str] = None) -> List[Dict]:
        """获取最近的告警"""
        alerts = self.alert_history
        
        if level:
            alerts = [a for a in alerts if a.get('level') == level]
        
        return alerts[-limit:]
    
    def get_alert_summary(self) -> Dict:
        """获取告警统计"""
        recent_alerts = self.alert_history[-100:]
        
        summary = {
            'total': len(recent_alerts),
            'by_level': {},
            'by_metric': {},
            'last_alert': None
        }
        
        for alert in recent_alerts:
            level = alert.get('level', 'UNKNOWN')
            metric = alert.get('metric_name', 'UNKNOWN')
            
            summary['by_level'][level] = summary['by_level'].get(level, 0) + 1
            summary['by_metric'][metric] = summary['by_metric'].get(metric, 0) + 1
        
        if recent_alerts:
            summary['last_alert'] = recent_alerts[-1]
        
        return summary
    
    def clear_old_alerts(self, days: int = 7):
        """清理旧告警"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        self.alert_history = [
            a for a in self.alert_history
            if datetime.fromisoformat(a['timestamp']).timestamp() > cutoff
        ]
        
        self._save_alert_history()
        api_logger.info(f'[Alert] 已清理 {days} 天前的告警')


# 全局告警管理器实例
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# 装饰器：自动监控函数执行时间
def monitor_execution(metric_name: str):
    """
    监控函数执行时间的装饰器
    
    Usage:
        @monitor_execution('api_response_time')
        def my_api_function():
            pass
    """
    from functools import wraps
    import time
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                alert_manager = get_alert_manager()
                alert_manager.check_response_time(elapsed_ms)
        
        return wrapper
    
    return decorator


if __name__ == '__main__':
    # 测试告警功能
    print("="*60)
    print("P2-6: 监控告警模块测试")
    print("="*60)
    print()
    
    alert_manager = get_alert_manager()
    
    # 测试错误率告警
    print("📊 测试错误率告警...")
    alert_manager.check_error_rate(15, 100)  # 15% 错误率
    
    # 测试响应时间告警
    print("⏱️  测试响应时间告警...")
    alert_manager.check_response_time(1500)  # 1500ms
    
    # 测试 AI 失败率告警
    print("🤖 测试 AI 失败率告警...")
    alert_manager.check_ai_failure_rate(25, 100)  # 25% 失败率
    
    # 获取告警统计
    print("\n📈 告警统计:")
    summary = alert_manager.get_alert_summary()
    print(f"  总告警数：{summary['total']}")
    print(f"  按级别：{summary['by_level']}")
    print(f"  按指标：{summary['by_metric']}")
    
    print("\n✅ 测试完成")
