"""
告警服务 - P0 关键修复

核心功能：
1. 关键失败告警（钉钉/企业微信/邮件）
2. 告警级别分类
3. 告警频率限制（避免告警风暴）
4. 告警历史记录

作者：首席测试专家
日期：2026-02-27
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from wechat_backend.logging_config import api_logger, db_logger


# ==================== 告警级别枚举 ====================

class AlertLevel:
    """告警级别"""
    INFO = 'info'           # 信息
    WARNING = 'warning'     # 警告
    ERROR = 'error'         # 错误
    CRITICAL = 'critical'   # 严重


# ==================== 告警配置 ====================

class AlertConfig:
    """告警配置"""
    
    # 告警频率限制（秒）
    RATE_LIMITS = {
        AlertLevel.INFO: 60,        # 信息类：60 秒内不重复
        AlertLevel.WARNING: 120,    # 警告类：120 秒内不重复
        AlertLevel.ERROR: 300,      # 错误类：300 秒内不重复
        AlertLevel.CRITICAL: 60,    # 严重类：60 秒内不重复（需要立即响应）
    }
    
    # 钉钉 webhook 配置
    DINGTALK_WEBHOOK = ''  # 从环境变量读取
    
    # 企业微信 webhook 配置
    WECHAT_WORK_WEBHOOK = ''  # 从环境变量读取
    
    # 邮件告警配置
    EMAIL_RECIPIENTS = []  # 从环境变量读取
    
    # 是否启用告警（生产环境为 True）
    ENABLED = True


# ==================== 告警历史记录存储 ====================

_alert_history: Dict[str, float] = {}  # key: alert_hash, value: last_alert_time
_alert_count: Dict[str, int] = {}  # key: date_hour, value: count


def _get_alert_hash(alert_type: str, message: str) -> str:
    """生成告警唯一标识（用于频率限制）"""
    content = f"{alert_type}:{message}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _should_send_alert(alert_type: str, message: str, level: str) -> bool:
    """
    判断是否应该发送告警（频率限制）
    
    返回:
        bool: True=可以发送，False=应该跳过
    """
    global _alert_history
    
    alert_hash = _get_alert_hash(alert_type, message)
    now = time.time()
    
    # 获取该类型告警的频率限制
    rate_limit = AlertConfig.RATE_LIMITS.get(level, 300)
    
    # 检查是否超过频率限制
    if alert_hash in _alert_history:
        last_alert_time = _alert_history[alert_hash]
        if now - last_alert_time < rate_limit:
            api_logger.debug(
                f"[告警频率限制] 跳过告警：{alert_type}, "
                f"距离上次告警 {now - last_alert_time:.1f}s < {rate_limit}s"
            )
            return False
    
    # 更新告警时间
    _alert_history[alert_hash] = now
    
    # 清理过期的告警记录（超过 1 小时）
    expiry_time = now - 3600
    _alert_history = {
        k: v for k, v in _alert_history.items()
        if v > expiry_time
    }
    
    return True


def _record_alert_count(level: str):
    """记录告警次数（用于告警风暴检测）"""
    global _alert_count
    
    now = datetime.now()
    hour_key = now.strftime('%Y-%m-%d-%H')
    
    if hour_key not in _alert_count:
        _alert_count[hour_key] = 0
    
    _alert_count[hour_key] += 1
    
    # 清理过期的计数
    expiry_time = (now - timedelta(hours=2)).strftime('%Y-%m-%d-%H')
    _alert_count = {
        k: v for k, v in _alert_count.items()
        if k >= expiry_time
    }
    
    # 检测告警风暴
    if _alert_count[hour_key] > 100:
        api_logger.warning(
            f"[告警风暴检测] 当前小时已发送 {_alert_count[hour_key]} 条告警"
        )


def send_dingtalk_alert(title: str, content: str, level: str):
    """
    发送钉钉告警
    
    钉钉机器人文档：
    https://open.dingtalk.com/document/robots/custom-robot-access
    """
    if not AlertConfig.DINGTALK_WEBHOOK:
        api_logger.debug("[钉钉告警] Webhook 未配置，跳过发送")
        return
    
    try:
        import requests
        
        # 构建消息内容
        if level == AlertLevel.CRITICAL:
            color = 'red'
            emoji = '🚨'
        elif level == AlertLevel.ERROR:
            color = 'orange'
            emoji = '❌'
        elif level == AlertLevel.WARNING:
            color = 'yellow'
            emoji = '⚠️'
        else:
            color = 'blue'
            emoji = 'ℹ️'
        
        markdown_content = f"""
## {emoji} {title}

**告警级别**: {level.upper()}
**告警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**详情**:
{content}

---
*来自品牌诊断系统*
        """.strip()
        
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': markdown_content
            },
            'at': {
                'isAtAll': True  # @所有人
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(
            AlertConfig.DINGTALK_WEBHOOK,
            data=json.dumps(payload),
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                api_logger.info(f"[钉钉告警] ✅ 发送成功：{title}")
            else:
                api_logger.error(f"[钉钉告警] ❌ 发送失败：{result.get('errmsg')}")
        else:
            api_logger.error(f"[钉钉告警] ❌ HTTP 错误：{response.status_code}")
            
    except Exception as e:
        api_logger.error(f"[钉钉告警] ❌ 异常：{e}")


def send_wechat_work_alert(title: str, content: str, level: str):
    """
    发送企业微信告警
    
    企业微信机器人文档：
    https://work.weixin.qq.com/api/doc/90000/90136/91770
    """
    if not AlertConfig.WECHAT_WORK_WEBHOOK:
        api_logger.debug("[企业微信告警] Webhook 未配置，跳过发送")
        return
    
    try:
        import requests
        
        # 构建消息内容
        if level == AlertLevel.CRITICAL:
            color = 'warning'
        elif level == AlertLevel.ERROR:
            color = 'warning'
        elif level == AlertLevel.WARNING:
            color = 'warning'
        else:
            color = 'info'
        
        markdown_content = f"""
## {title}
> 告警级别：<font color="{color}">{level.upper()}</font>
> 告警时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 
> {content}
        """.strip()
        
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'content': markdown_content
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(
            AlertConfig.WECHAT_WORK_WEBHOOK,
            data=json.dumps(payload),
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                api_logger.info(f"[企业微信告警] ✅ 发送成功：{title}")
            else:
                api_logger.error(f"[企业微信告警] ❌ 发送失败：{result.get('errmsg')}")
        else:
            api_logger.error(f"[企业微信告警] ❌ HTTP 错误：{response.status_code}")
            
    except Exception as e:
        api_logger.error(f"[企业微信告警] ❌ 异常：{e}")


# ==================== 统一告警接口 ====================

def alert_critical_failure(
    component: str,
    error_message: str,
    execution_id: Optional[str] = None,
    attempts: int = 1
):
    """
    关键失败告警
    
    使用场景：
    - 数据库写入失败（重试后仍然失败）
    - AI 调用全部失败
    - 执行器崩溃
    - 状态同步失败
    
    参数:
        component: 组件名称（如：database, ai_executor, scheduler）
        error_message: 错误信息
        execution_id: 执行 ID（可选）
        attempts: 尝试次数
    """
    if not AlertConfig.ENABLED:
        api_logger.debug("[告警服务] 告警已禁用")
        return
    
    # 构建告警内容
    title = f"🚨 关键失败告警 - {component}"
    
    content_parts = [
        f"**组件**: {component}",
        f"**错误**: {error_message}",
    ]
    
    if execution_id:
        content_parts.append(f"**执行 ID**: `{execution_id}`")
    
    if attempts > 1:
        content_parts.append(f"**尝试次数**: {attempts}")
    
    content = '\n'.join(content_parts)
    
    # 记录告警次数
    _record_alert_count(AlertLevel.CRITICAL)
    
    # 发送告警（多渠道）
    send_dingtalk_alert(title, content, AlertLevel.CRITICAL)
    send_wechat_work_alert(title, content, AlertLevel.CRITICAL)
    
    # 记录日志
    db_logger.error(
        f"🚨 [关键失败告警] "
        f"组件：{component}, "
        f"执行 ID: {execution_id}, "
        f"尝试次数：{attempts}, "
        f"错误：{error_message}"
    )


def alert_warning(
    component: str,
    warning_message: str,
    context: Optional[Dict[str, Any]] = None
):
    """
    警告级别告警
    
    使用场景：
    - 数据库写入失败（首次失败，会重试）
    - AI 调用超时
    - 性能下降
    
    参数:
        component: 组件名称
        warning_message: 警告信息
        context: 上下文信息（可选）
    """
    if not AlertConfig.ENABLED:
        return
    
    # 检查频率限制
    if not _should_send_alert(component, warning_message, AlertLevel.WARNING):
        return
    
    title = f"⚠️ 警告 - {component}"
    
    content = f"**组件**: {component}\n\n**警告**: {warning_message}"
    
    if context:
        content += "\n\n**上下文**:\n"
        for key, value in context.items():
            content += f"- {key}: {value}\n"
    
    # 发送告警
    send_dingtalk_alert(title, content, AlertLevel.WARNING)
    
    # 记录日志
    api_logger.warning(f"[警告] {component}: {warning_message}")


def alert_error(
    component: str,
    error_message: str,
    execution_id: Optional[str] = None
):
    """
    错误级别告警
    
    使用场景：
    - 数据库写入最终失败（重试 3 次后）
    - 关键业务逻辑失败
    - 数据不一致
    
    参数:
        component: 组件名称
        error_message: 错误信息
        execution_id: 执行 ID（可选）
    """
    if not AlertConfig.ENABLED:
        return
    
    # 检查频率限制
    if not _should_send_alert(component, error_message, AlertLevel.ERROR):
        return
    
    title = f"❌ 错误 - {component}"
    
    content = f"**组件**: {component}\n\n**错误**: {error_message}"
    
    if execution_id:
        content += f"\n\n**执行 ID**: `{execution_id}`"
    
    # 发送告警
    send_dingtalk_alert(title, content, AlertLevel.ERROR)
    send_wechat_work_alert(title, content, AlertLevel.ERROR)
    
    # 记录日志
    api_logger.error(f"[错误] {component}: {error_message}")


def get_alert_status() -> Dict[str, Any]:
    """
    获取告警服务状态
    
    返回:
        dict: 告警服务状态信息
    """
    now = time.time()
    
    # 统计最近 1 小时的告警
    hour_ago = now - 3600
    recent_alerts = sum(
        1 for t in _alert_history.values()
        if t > hour_ago
    )
    
    return {
        'enabled': AlertConfig.ENABLED,
        'recent_alerts_1h': recent_alerts,
        'dingtalk_configured': bool(AlertConfig.DINGTALK_WEBHOOK),
        'wechat_work_configured': bool(AlertConfig.WECHAT_WORK_WEBHOOK),
        'rate_limits': AlertConfig.RATE_LIMITS,
    }


# ==================== 健康检查端点 ====================

def health_check() -> Dict[str, Any]:
    """
    告警服务健康检查
    
    返回:
        dict: 健康状态
    """
    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
    }
    
    # 检查告警配置
    if not AlertConfig.ENABLED:
        status['status'] = 'warning'
        status['warning'] = '告警服务已禁用'
    
    # 检查告警频率
    now = time.time()
    hour_ago = now - 3600
    recent_alerts = sum(
        1 for t in _alert_history.values()
        if t > hour_ago
    )
    
    if recent_alerts > 100:
        status['status'] = 'warning'
        status['warning'] = f'最近 1 小时告警过多：{recent_alerts}'
    
    # 检查告警渠道配置
    if not AlertConfig.DINGTALK_WEBHOOK and not AlertConfig.WECHAT_WORK_WEBHOOK:
        status['status'] = 'warning'
        status['warning'] = '未配置任何告警渠道'
    
    return status
