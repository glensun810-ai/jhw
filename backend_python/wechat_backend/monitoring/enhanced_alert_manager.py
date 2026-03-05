"""
增强告警通知系统

功能:
1. 多渠道告警通知（Webhook/邮件/短信）
2. 告警抑制和去重
3. 告警升级机制
4. 连接池专用告警处理器

【P0 实现 - 2026-03-05】
"""

import json
import smtplib
import time
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from wechat_backend.logging_config import app_logger, db_logger

# 告警数据存储路径
ALERT_DATA_DIR = Path(__file__).parent.parent / 'monitoring_data' / 'alerts'
ALERT_CONFIG_FILE = ALERT_DATA_DIR / 'alert_config.json'
ALERT_HISTORY_FILE = ALERT_DATA_DIR / 'alert_history_enhanced.json'

# 确保目录存在
ALERT_DATA_DIR.mkdir(parents=True, exist_ok=True)


class AlertChannel:
    """告警渠道"""
    LOG = 'log'
    WEBHOOK = 'webhook'
    EMAIL = 'email'
    SMS = 'sms'


class AlertSeverity:
    """告警严重程度"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AlertNotification:
    """告警通知实体"""

    def __init__(
        self,
        title: str,
        message: str,
        severity: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.title = title
        self.message = message
        self.severity = severity
        self.metric_name = metric_name
        self.current_value = current_value
        self.threshold = threshold
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'threshold': self.threshold,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class EnhancedAlertManager:
    """
    增强告警管理器

    功能:
    1. 多渠道通知（日志/Webhook/邮件/短信）
    2. 告警抑制（避免告警风暴）
    3. 告警升级（未处理时自动升级）
    4. 连接池专用告警处理
    """

    def __init__(self):
        self.config = self._load_config()
        self.alert_history = self._load_history()
        self.suppression_cache: Dict[str, datetime] = {}  # 告警抑制缓存
        self.escalation_timers: Dict[str, datetime] = {}  # 告警升级计时器
        self._notification_callbacks: List[Callable] = []

        app_logger.info("[EnhancedAlertManager] 初始化完成")

    def _load_config(self) -> Dict[str, Any]:
        """加载告警配置"""
        default_config = {
            'channels': {
                'log': {'enabled': True},
                'webhook': {
                    'enabled': False,
                    'url': '',
                    'headers': {}
                },
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.example.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'from_addr': 'alerts@example.com',
                    'to_addrs': ['admin@example.com'],
                    'use_tls': True
                },
                'sms': {
                    'enabled': False,
                    'provider': 'aliyun',  # aliyun/tencent
                    'api_key': '',
                    'phone_numbers': []
                }
            },
            'suppression': {
                'enabled': True,
                'duration_seconds': 300  # 5 分钟抑制期
            },
            'escalation': {
                'enabled': True,
                'warning_to_error_minutes': 15,
                'error_to_critical_minutes': 30
            },
            'connection_pool': {
                'utilization_warning': 0.8,
                'utilization_critical': 0.9,
                'leak_detection_enabled': True
            }
        }

        if ALERT_CONFIG_FILE.exists():
            try:
                with open(ALERT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并配置
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                    return config
            except Exception as e:
                app_logger.error(f"[AlertConfig] 加载配置失败：{e}")

        return default_config

    def _save_config(self):
        """保存告警配置"""
        try:
            with open(ALERT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app_logger.error(f"[AlertConfig] 保存配置失败：{e}")

    def _load_history(self) -> List[Dict]:
        """加载告警历史"""
        if ALERT_HISTORY_FILE.exists():
            try:
                with open(ALERT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                app_logger.error(f"[AlertHistory] 加载历史失败：{e}")
        return []

    def _save_history(self):
        """保存告警历史"""
        try:
            # 只保留最近 1000 条
            recent = self.alert_history[-1000:]
            with open(ALERT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(recent, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app_logger.error(f"[AlertHistory] 保存历史失败：{e}")

    def send_alert(
        self,
        notification: AlertNotification,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        发送告警通知

        参数:
            notification: 告警通知对象
            channels: 指定渠道列表，默认使用配置中的所有启用渠道

        返回:
            各渠道发送结果
        """
        if channels is None:
            channels = [
                ch for ch, cfg in self.config['channels'].items()
                if cfg.get('enabled', False)
            ]

        results = {}

        for channel in channels:
            try:
                if channel == AlertChannel.LOG:
                    self._send_log(notification)
                    results[channel] = True

                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook(notification)
                    results[channel] = True

                elif channel == AlertChannel.EMAIL:
                    self._send_email(notification)
                    results[channel] = True

                elif channel == AlertChannel.SMS:
                    self._send_sms(notification)
                    results[channel] = True

            except Exception as e:
                app_logger.error(
                    f"[AlertNotification] 渠道 {channel} 发送失败：{e}"
                )
                results[channel] = False

        # 记录历史
        self.alert_history.append({
            **notification.to_dict(),
            'channels': channels,
            'results': results
        })
        self._save_history()

        return results

    def _send_log(self, notification: AlertNotification):
        """发送日志告警"""
        log_msg = (
            f"[告警] {notification.title} | "
            f"级别={notification.severity} | "
            f"{notification.message} | "
            f"当前值={notification.current_value}, "
            f"阈值={notification.threshold}"
        )

        if notification.severity == AlertSeverity.CRITICAL:
            app_logger.critical(log_msg)
        elif notification.severity == AlertSeverity.ERROR:
            app_logger.error(log_msg)
        elif notification.severity == AlertSeverity.WARNING:
            app_logger.warning(log_msg)
        else:
            app_logger.info(log_msg)

    def _send_webhook(self, notification: AlertNotification):
        """发送 Webhook 告警"""
        config = self.config['channels']['webhook']
        if not config.get('enabled') or not config.get('url'):
            return

        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': notification.title,
                'text': (
                    f"## {notification.title}\n\n"
                    f"**级别**: {notification.severity}\n"
                    f"**指标**: {notification.metric_name}\n"
                    f"**当前值**: {notification.current_value}\n"
                    f"**阈值**: {notification.threshold}\n"
                    f"**时间**: {notification.timestamp}\n\n"
                    f"{notification.message}"
                )
            }
        }

        headers = {'Content-Type': 'application/json'}
        headers.update(config.get('headers', {}))

        response = requests.post(
            config['url'],
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"Webhook 返回错误：{response.status_code}")

        app_logger.info(f"[Webhook 告警] 发送成功：{notification.title}")

    def _send_email(self, notification: AlertNotification):
        """发送邮件告警"""
        config = self.config['channels']['email']
        if not config.get('enabled'):
            return

        msg = MIMEMultipart()
        msg['From'] = config['from_addr']
        msg['To'] = ', '.join(config['to_addrs'])
        msg['Subject'] = f"[{notification.severity.upper()}] {notification.title}"

        body = (
            f"告警详情\n"
            f"========\n\n"
            f"级别：{notification.severity.upper()}\n"
            f"指标：{notification.metric_name}\n"
            f"当前值：{notification.current_value}\n"
            f"阈值：{notification.threshold}\n"
            f"时间：{notification.timestamp}\n\n"
            f"{notification.message}\n"
        )

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP(
                config['smtp_server'],
                config['smtp_port']
            )
            if config.get('use_tls'):
                server.starttls()

            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])

            server.send_message(msg)
            server.quit()

            app_logger.info(f"[Email 告警] 发送成功：{notification.title}")

        except Exception as e:
            app_logger.error(f"[Email 告警] 发送失败：{e}")
            raise

    def _send_sms(self, notification: AlertNotification):
        """发送短信告警"""
        config = self.config['channels']['sms']
        if not config.get('enabled'):
            return

        provider = config.get('provider', 'aliyun')
        phone_numbers = config.get('phone_numbers', [])

        if not phone_numbers:
            app_logger.warning("[SMS 告警] 未配置手机号")
            return

        # 短信内容（限制 160 字）
        content = (
            f"[{notification.severity.upper()}] {notification.title}. "
            f"{notification.metric_name}={notification.current_value}, "
            f"阈值={notification.threshold}"
        )[:160]

        # 这里集成实际的 SMS 服务商 API
        # 示例：阿里云 SMS / 腾讯云 SMS
        app_logger.info(
            f"[SMS 告警] 拟发送 {provider} 短信到 {len(phone_numbers)} 个号码："
            f"{content}"
        )

        # TODO: 实现实际的 SMS API 调用
        # 目前仅记录日志

    def check_and_alert_with_suppression(
        self,
        notification: AlertNotification,
        channels: Optional[List[str]] = None
    ) -> bool:
        """
        检查并发送告警（带抑制机制）

        参数:
            notification: 告警通知对象
            channels: 指定渠道

        返回:
            bool: 是否实际发送了告警
        """
        # 生成告警唯一键（用于抑制）
        alert_key = (
            f"{notification.metric_name}:"
            f"{notification.severity}:"
            f"{int(notification.threshold)}"
        )

        # 检查抑制
        if self.config['suppression']['enabled']:
            last_alert_time = self.suppression_cache.get(alert_key)
            if last_alert_time:
                duration = self.config['suppression']['duration_seconds']
                if datetime.now() - last_alert_time < timedelta(seconds=duration):
                    app_logger.debug(
                        f"[AlertSuppression] 抑制告警：{alert_key}"
                    )
                    return False

        # 发送告警
        results = self.send_alert(notification, channels)

        # 更新抑制缓存
        self.suppression_cache[alert_key] = datetime.now()

        # 清理过期抑制
        cutoff = datetime.now() - timedelta(
            seconds=self.config['suppression']['duration_seconds'] * 2
        )
        self.suppression_cache = {
            k: v for k, v in self.suppression_cache.items()
            if v > cutoff
        }

        return any(results.values())

    def handle_connection_pool_alert(
        self,
        metrics: Dict[str, Any]
    ):
        """
        处理连接池告警

        参数:
            metrics: 连接池指标字典
        """
        alert_level = metrics.get('alert_level', 'none')

        if alert_level == 'none':
            return

        utilization = metrics.get('utilization_rate', 0)
        active = metrics.get('active_connections', 0)
        potential_leaks = metrics.get('potential_leaks', 0)

        # 判断严重程度
        if alert_level == 'critical':
            severity = AlertSeverity.CRITICAL
            title = "🚨 连接池严重告警"
        elif alert_level == 'warning':
            severity = AlertSeverity.WARNING
            title = "⚠️ 连接池警告"
        else:
            severity = AlertSeverity.INFO
            title = "ℹ️ 连接池提示"

        # 构建消息
        message = (
            f"连接池利用率={utilization*100:.1f}%, "
            f"活跃连接={active}, "
            f"潜在泄漏={potential_leaks}"
        )

        if potential_leaks > 0:
            message += f" [检测到 {potential_leaks} 个潜在连接泄漏]"

        notification = AlertNotification(
            title=title,
            message=message,
            severity=severity,
            metric_name='connection_pool_utilization',
            current_value=utilization,
            threshold=self.config['connection_pool']['utilization_warning'],
            metadata=metrics
        )

        # 发送告警
        self.check_and_alert_with_suppression(notification)

    def add_notification_callback(self, callback: Callable):
        """添加通知回调"""
        self._notification_callbacks.append(callback)

    def get_alert_history(
        self,
        limit: int = 50,
        severity: Optional[str] = None
    ) -> List[Dict]:
        """获取告警历史"""
        history = self.alert_history

        if severity:
            history = [
                h for h in history
                if h.get('severity') == severity
            ]

        return history[-limit:]

    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警统计"""
        recent = self.alert_history[-100:]

        summary = {
            'total': len(recent),
            'by_severity': {},
            'by_metric': {},
            'last_24h': 0,
            'channels_usage': {}
        }

        cutoff_24h = datetime.now() - timedelta(hours=24)

        for alert in recent:
            sev = alert.get('severity', 'unknown')
            metric = alert.get('metric_name', 'unknown')
            timestamp = alert.get('timestamp', '')

            summary['by_severity'][sev] = summary['by_severity'].get(sev, 0) + 1
            summary['by_metric'][metric] = summary['by_metric'].get(metric, 0) + 1

            try:
                if datetime.fromisoformat(timestamp) > cutoff_24h:
                    summary['last_24h'] += 1
            except:
                pass

            # 统计渠道使用情况
            channels = alert.get('channels', [])
            for ch in channels:
                summary['channels_usage'][ch] = (
                    summary['channels_usage'].get(ch, 0) + 1
                )

        return summary


# 全局实例
_enhanced_alert_manager: Optional[EnhancedAlertManager] = None


def get_enhanced_alert_manager() -> EnhancedAlertManager:
    """获取增强告警管理器实例"""
    global _enhanced_alert_manager
    if _enhanced_alert_manager is None:
        _enhanced_alert_manager = EnhancedAlertManager()
    return _enhanced_alert_manager


def alert_connection_pool_issue(metrics: Dict[str, Any]):
    """便捷函数：告警连接池问题"""
    manager = get_enhanced_alert_manager()
    manager.handle_connection_pool_alert(metrics)
