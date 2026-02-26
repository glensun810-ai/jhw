"""
告警系统模块
P1 修复：恢复缺失的告警模块
P1-018 新增：数据库持久化告警机制
"""

from wechat_backend.logging_config import api_logger
from enum import Enum
from typing import List, Optional, Callable, Dict
from datetime import datetime, timedelta
import threading
import os

# P1-018 新增：持久化错误计数器（线程安全）
_persistence_error_lock = threading.Lock()
_persistence_error_counts: Dict[str, Dict] = {}  # execution_id -> {count, last_error, last_time}
PERSISTENCE_ERROR_THRESHOLD = 10  # 连续 10 次失败触发告警
PERSISTENCE_ERROR_WINDOW = 300  # 5 分钟窗口（秒）


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class AlertCondition:
    """告警条件"""
    
    def __init__(self, name: str, threshold: float, severity: AlertSeverity = AlertSeverity.MEDIUM):
        self.name = name
        self.threshold = threshold
        self.severity = severity
        self.callback: Optional[Callable] = None
    
    def check(self, value: float) -> bool:
        """检查是否触发告警"""
        return value >= self.threshold
    
    def trigger(self, value: float):
        """触发告警"""
        if self.callback:
            self.callback(self, value)
        api_logger.warning(f"Alert triggered: {self.name} (value: {value}, threshold: {self.threshold})")


class Alert:
    """告警"""
    
    def __init__(self, name: str, message: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
        self.name = name
        self.message = message
        self.severity = severity
        self.created_at = datetime.now()
        self.acknowledged = False
    
    def acknowledge(self):
        """确认告警"""
        self.acknowledged = True
        api_logger.info(f"Alert acknowledged: {self.name}")


class AlertSystem:
    """告警系统"""
    
    def __init__(self):
        self.conditions: List[AlertCondition] = []
        self.alerts: List[Alert] = []
        self.enabled = True
    
    def add_condition(self, condition: AlertCondition):
        """添加告警条件"""
        self.conditions.append(condition)
        api_logger.info(f"Alert condition added: {condition.name}")
    
    def check_conditions(self, metric_name: str, value: float):
        """检查所有条件"""
        if not self.enabled:
            return
        
        for condition in self.conditions:
            if condition.name == metric_name and condition.check(value):
                condition.trigger(value)
                self.create_alert(
                    name=condition.name,
                    message=f"{condition.name} exceeded threshold: {value} >= {condition.threshold}",
                    severity=condition.severity
                )
    
    def create_alert(self, name: str, message: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
        """创建告警"""
        alert = Alert(name, message, severity)
        self.alerts.append(alert)
        api_logger.warning(f"Alert created: {name} - {message}")
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃的告警"""
        return [a for a in self.alerts if not a.acknowledged]
    
    def enable(self):
        """启用告警系统"""
        self.enabled = True
        api_logger.info("Alert system enabled")
    
    def disable(self):
        """禁用告警系统"""
        self.enabled = False
        api_logger.info("Alert system disabled")


# 全局实例
_alert_system: Optional[AlertSystem] = None


def get_alert_system() -> AlertSystem:
    """获取告警系统实例"""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system


def init_default_alerts():
    """初始化默认告警"""
    alert_system = get_alert_system()
    
    # 添加默认告警条件
    alert_system.add_condition(AlertCondition(
        name='error_rate',
        threshold=0.1,
        severity=AlertSeverity.HIGH
    ))
    
    alert_system.add_condition(AlertCondition(
        name='response_time',
        threshold=5.0,
        severity=AlertSeverity.MEDIUM
    ))
    
    alert_system.add_condition(AlertCondition(
        name='cpu_usage',
        threshold=0.8,
        severity=AlertSeverity.HIGH
    ))
    
    api_logger.info('Default alerts initialized')


def start_alert_monitoring():
    """启动告警监控"""
    init_default_alerts()
    api_logger.info('Alert monitoring started')


# ==================== P1-018 新增：数据库持久化告警机制 ====================

def record_persistence_error(
    execution_id: str,
    error_type: str = 'unknown',
    error_message: str = ''
) -> bool:
    """
    记录数据库持久化错误
    
    功能：
    1. 统计每个 execution_id 的持久化错误次数
    2. 在时间窗口内累计错误
    3. 达到阈值时触发告警
    
    参数：
        execution_id: 执行 ID
        error_type: 错误类型（dimension_result, task_status 等）
        error_message: 错误信息
    
    返回：
        是否触发告警
    """
    global _persistence_error_counts
    
    now = datetime.now()
    alert_triggered = False
    
    with _persistence_error_lock:
        # 初始化或获取错误计数
        if execution_id not in _persistence_error_counts:
            _persistence_error_counts[execution_id] = {
                'count': 0,
                'first_error_time': now,
                'last_error_time': now,
                'last_error': '',
                'error_type': error_type
            }
        
        error_info = _persistence_error_counts[execution_id]
        
        # 检查是否超出时间窗口，超出则重置
        time_since_first = (now - error_info['first_error_time']).total_seconds()
        if time_since_first > PERSISTENCE_ERROR_WINDOW:
            api_logger.info(f"[P1-018] 重置错误计数：{execution_id} (超出 {PERSISTENCE_ERROR_WINDOW}s 窗口)")
            error_info['count'] = 0
            error_info['first_error_time'] = now
        
        # 累加错误计数
        error_info['count'] += 1
        error_info['last_error_time'] = now
        error_info['last_error'] = error_message
        error_info['error_type'] = error_type
        
        # 检查是否达到阈值
        if error_info['count'] >= PERSISTENCE_ERROR_THRESHOLD:
            alert_triggered = True
            api_logger.error(
                f"[P1-018 告警触发] execution_id={execution_id}, "
                f"错误次数={error_info['count']}, "
                f"错误类型={error_type}, "
                f"时间窗口={time_since_first:.1f}s"
            )
            
            # 创建告警
            try:
                alert_system = get_alert_system()
                alert_system.create_alert(
                    name='persistence_error',
                    message=f'数据库持久化连续失败 {error_info["count"]} 次 - execution_id: {execution_id}, 错误：{error_message}',
                    severity=AlertSeverity.HIGH
                )
            except Exception as e:
                api_logger.error(f"[P1-018] 创建告警失败：{e}")
            
            # 重置计数（避免重复告警）
            error_info['count'] = 0
    
    return alert_triggered


def check_persistence_alert(execution_id: str) -> Dict:
    """
    检查执行 ID 的持久化告警状态
    
    参数：
        execution_id: 执行 ID
    
    返回：
        告警状态字典 {is_alerting, count, last_error}
    """
    with _persistence_error_lock:
        if execution_id in _persistence_error_counts:
            error_info = _persistence_error_counts[execution_id]
            return {
                'is_alerting': error_info['count'] >= PERSISTENCE_ERROR_THRESHOLD,
                'count': error_info['count'],
                'last_error': error_info['last_error'],
                'error_type': error_info.get('error_type', 'unknown')
            }
        return {
            'is_alerting': False,
            'count': 0,
            'last_error': '',
            'error_type': 'unknown'
        }


def clear_persistence_errors(execution_id: str):
    """
    清除执行 ID 的持久化错误计数
    
    参数：
        execution_id: 执行 ID
    """
    with _persistence_error_lock:
        if execution_id in _persistence_error_counts:
            del _persistence_error_counts[execution_id]
            api_logger.info(f"[P1-018] 清除错误计数：{execution_id}")


# ==================== P2-021 新增：告警通知配置 ====================

# 告警通知配置（可从环境变量读取）
ALERT_DINGTALK_WEBHOOK = os.getenv('ALERT_DINGTALK_WEBHOOK', '')
ALERT_EMAIL_RECIPIENTS = os.getenv('ALERT_EMAIL_RECIPIENTS', '').split(',') if os.getenv('ALERT_EMAIL_RECIPIENTS') else []
ALERT_ENABLED = os.getenv('ALERT_ENABLED', 'true').lower() == 'true'


def send_dingtalk_alert(title: str, content: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
    """
    发送钉钉机器人告警
    
    参数：
        title: 告警标题
        content: 告警内容
        severity: 严重程度
    """
    if not ALERT_DINGTALK_WEBHOOK or not ALERT_ENABLED:
        api_logger.info(f"[P2-021 告警] 钉钉告警未配置或已禁用，跳过发送")
        return False
    
    try:
        import requests
        
        # 根据严重程度设置颜色
        color_map = {
            AlertSeverity.LOW: '#20C997',
            AlertSeverity.MEDIUM: '#FFC107',
            AlertSeverity.HIGH: '#FF6B6B',
            AlertSeverity.CRITICAL: '#DC3545'
        }
        
        # 钉钉 Markdown 消息格式
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{content}\n\n**严重程度**: {severity.value.upper()}\n\n**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        response = requests.post(
            ALERT_DINGTALK_WEBHOOK,
            json=message,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                api_logger.info(f"[P2-021 告警] 钉钉告警发送成功：{title}")
                return True
            else:
                api_logger.error(f"[P2-021 告警] 钉钉告警发送失败：{result}")
                return False
        else:
            api_logger.error(f"[P2-021 告警] 钉钉告警 HTTP 错误：{response.status_code}")
            return False
            
    except Exception as e:
        api_logger.error(f"[P2-021 告警] 发送钉钉告警异常：{e}")
        return False


def send_email_alert(subject: str, body: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
    """
    发送邮件告警

    参数：
        subject: 邮件主题
        body: 邮件正文
        severity: 严重程度
    
    P0-003 修复：添加完整的异常处理
    """
    if not ALERT_EMAIL_RECIPIENTS or not ALERT_ENABLED:
        api_logger.info(f"[P2-021 告警] 邮件告警未配置或已禁用，跳过发送")
        return False

    try:
        # P0-003 修复：在 try 块中导入，捕获导入失败
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
    except ImportError as e:
        api_logger.error(f"[P2-021 告警] 邮件模块导入失败：{e}")
        return False

    try:
        # 从环境变量读取 SMTP 配置
        smtp_server = os.getenv('SMTP_SERVER', '')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        sender_email = os.getenv('SENDER_EMAIL', '')

        if not all([smtp_server, smtp_user, smtp_password, sender_email]):
            api_logger.warning(f"[P2-021 告警] SMTP 配置不完整，跳过邮件发送")
            return False

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(ALERT_EMAIL_RECIPIENTS)
        msg['Subject'] = f"[诊断系统告警] {subject} ({severity.value.upper()})"

        # 邮件正文
        email_body = f"""
<html>
<body>
    <h2>诊断系统告警</h2>
    <p><strong>主题:</strong> {subject}</p>
    <p><strong>严重程度:</strong> {severity.value.upper()}</p>
    <p><strong>时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <hr/>
    <h3>告警详情:</h3>
    <pre>{body}</pre>
    <hr/>
    <p style="color: #888; font-size: 12px;">此邮件由诊断系统自动发送，请勿回复。</p>
</body>
</html>
        """

        msg.attach(MIMEText(email_body, 'html', 'utf-8'))

        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        api_logger.info(f"[P2-021 告警] 邮件告警发送成功：{subject}")
        return True

    except Exception as e:
        api_logger.error(f"[P2-021 告警] 发送邮件告警异常：{e}")
        return False


def send_alert_notification(alert: Alert):
    """
    发送告警通知（根据配置选择通知方式）
    
    参数：
        alert: 告警对象
    """
    title = f"{alert.name} - {alert.severity.value.upper()}"
    content = alert.message
    
    # 根据严重程度选择通知方式
    if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
        # 严重告警：同时发送钉钉和邮件
        send_dingtalk_alert(title, content, alert.severity)
        send_email_alert(title, content, alert.severity)
    elif alert.severity == AlertSeverity.MEDIUM:
        # 中等告警：只发送钉钉
        send_dingtalk_alert(title, content, alert.severity)
    else:
        # 低优先级告警：仅记录日志
        api_logger.info(f"[P2-021 告警] 低优先级告警，仅记录日志：{alert.name}")


# 修改 AlertSystem 的 create_alert 方法，集成通知功能
_original_create_alert = AlertSystem.create_alert

def _enhanced_create_alert(self, name: str, message: str, severity: AlertSeverity = AlertSeverity.MEDIUM):
    """增强的 create_alert 方法，集成告警通知"""
    # 创建告警
    alert = Alert(name, message, severity)
    self.alerts.append(alert)
    api_logger.warning(f"Alert created: {name} - {message}")
    
    # 发送通知
    try:
        send_alert_notification(alert)
    except Exception as e:
        api_logger.error(f"[P2-021 告警] 发送通知失败：{e}")


# 应用增强
AlertSystem.create_alert = _enhanced_create_alert


__all__ = [
    'AlertSeverity',
    'AlertCondition',
    'Alert',
    'AlertSystem',
    'get_alert_system',
    'init_default_alerts',
    'start_alert_monitoring',
    # P1-018 新增
    'record_persistence_error',
    'check_persistence_alert',
    'clear_persistence_errors'
]
