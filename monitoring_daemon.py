#!/usr/bin/env python3
"""
诊断系统持续监控脚本
P2-020: 持续监控诊断成功率和完成率指标

功能：
1. 定期检查关键指标
2. 超过阈值时触发告警
3. 生成监控报告
4. 支持后台运行

使用方法：
    # 前台运行
    python monitoring_daemon.py

    # 后台运行（Linux/Mac）
    nohup python monitoring_daemon.py > logs/monitoring.log 2>&1 &

    # 作为 systemd 服务运行
    sudo systemctl start diagnosis-monitoring
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

from wechat_backend.logging_config import api_logger, setup_logging
from wechat_backend.alert_system import (
    get_alert_system,
    AlertSeverity,
    send_dingtalk_alert,
    send_email_alert
)

# ==================== 监控配置 ====================

# 后端 API 地址
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5001')

# 检查间隔（秒）
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))  # 默认 5 分钟

# 告警阈值
THRESHOLDS = {
    'success_rate_min': float(os.getenv('SUCCESS_RATE_MIN', '95.0')),  # 最低成功率
    'completion_rate_min': float(os.getenv('COMPLETION_RATE_MIN', '90.0')),  # 最低完成率
    'quota_exhausted_max': float(os.getenv('QUOTA_EXHAUSTED_MAX', '20.0')),  # 最高配额用尽率
    'avg_duration_max': float(os.getenv('AVG_DURATION_MAX', '120.0')),  # 最大平均耗时（秒）
    'error_rate_max': float(os.getenv('ERROR_RATE_MAX', '10.0')),  # 最高错误率
}

# 告警冷却时间（秒）- 避免重复告警
ALERT_COOLDOWN = int(os.getenv('ALERT_COOLDOWN', '1800'))  # 默认 30 分钟

# 告警状态文件
ALERT_STATE_FILE = os.getenv('ALERT_STATE_FILE', '/tmp/diagnosis_monitor_state.json')


class MonitorState:
    """监控状态管理"""

    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """加载状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            api_logger.error(f"加载监控状态失败：{e}")
        return {'last_alerts': {}}

    def save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            api_logger.error(f"保存监控状态失败：{e}")

    def can_alert(self, alert_key: str) -> bool:
        """检查是否可以发送告警（冷却检查）"""
        last_alert_time = self.state['last_alerts'].get(alert_key, 0)
        now = time.time()
        return (now - last_alert_time) > ALERT_COOLDOWN

    def record_alert(self, alert_key: str):
        """记录告警时间"""
        self.state['last_alerts'][alert_key] = time.time()
        self.save_state()


class DiagnosisMonitor:
    """诊断监控器"""

    def __init__(self):
        self.state = MonitorState(ALERT_STATE_FILE)
        self.running = True

    def get_dashboard(self, period: str = 'today') -> Optional[Dict]:
        """获取监控大盘数据"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/monitoring/dashboard",
                params={'period': period},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result.get('data') if result.get('success') else None
        except Exception as e:
            api_logger.error(f"获取监控大盘失败：{e}")
            return None

    def check_metrics(self, data: Dict) -> list:
        """检查指标是否超过阈值"""
        alerts = []

        # 检查成功率
        if data['success_rate'] < THRESHOLDS['success_rate_min']:
            alerts.append({
                'key': 'success_rate',
                'name': '诊断成功率过低',
                'value': data['success_rate'],
                'threshold': THRESHOLDS['success_rate_min'],
                'severity': AlertSeverity.HIGH
            })

        # 检查完成率
        if data['completion']['avg_completion_rate'] < THRESHOLDS['completion_rate_min']:
            alerts.append({
                'key': 'completion_rate',
                'name': '平均完成率过低',
                'value': data['completion']['avg_completion_rate'],
                'threshold': THRESHOLDS['completion_rate_min'],
                'severity': AlertSeverity.MEDIUM
            })

        # 检查配额用尽率
        if data['quota']['quota_exhausted_rate'] > THRESHOLDS['quota_exhausted_max']:
            alerts.append({
                'key': 'quota_exhausted',
                'name': '配额用尽率过高',
                'value': data['quota']['quota_exhausted_rate'],
                'threshold': THRESHOLDS['quota_exhausted_max'],
                'severity': AlertSeverity.MEDIUM
            })

        # 检查平均耗时
        if data['performance']['avg_duration_seconds'] > THRESHOLDS['avg_duration_max']:
            alerts.append({
                'key': 'avg_duration',
                'name': '平均耗时过长',
                'value': data['performance']['avg_duration_seconds'],
                'threshold': THRESHOLDS['avg_duration_max'],
                'severity': AlertSeverity.MEDIUM
            })

        # 检查错误率
        error_rate = (data['errors']['total_errors'] / max(data['total_diagnosis'], 1)) * 100
        if error_rate > THRESHOLDS['error_rate_max']:
            alerts.append({
                'key': 'error_rate',
                'name': '错误率过高',
                'value': round(error_rate, 2),
                'threshold': THRESHOLDS['error_rate_max'],
                'severity': AlertSeverity.HIGH
            })

        return alerts

    def send_alert(self, alert: Dict, data: Dict):
        """发送告警"""
        alert_key = f"{alert['key']}_{datetime.now().strftime('%Y-%m-%d')}"

        # 检查冷却
        if not self.state.can_alert(alert_key):
            api_logger.info(f"告警冷却中，跳过：{alert['name']}")
            return

        # 构建告警内容
        content = f"""
## 🚨 诊断系统告警

**告警名称**: {alert['name']}
**严重程度**: {alert['severity'].value.upper()}
**当前值**: {alert['value']}
**阈值**: {alert['threshold']}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 详细指标
- 诊断总数：{data['total_diagnosis']}
- 成功数：{data['successful_diagnosis']}
- 失败数：{data['failed_diagnosis']}
- 成功率：{data['success_rate']}%
- 平均完成率：{data['completion']['avg_completion_rate']}%
- 配额用尽数：{data['quota']['quota_exhausted_count']}
- 平均耗时：{data['performance']['avg_duration_seconds']}s

### 建议操作
1. 查看监控大盘：{API_BASE_URL}/admin/monitoring
2. 检查日志：tail -f logs/app.log
3. 查看错误详情：{API_BASE_URL}/api/monitoring/recent?limit=20
"""

        # 发送钉钉告警
        send_dingtalk_alert(
            title=f"诊断系统告警 - {alert['name']}",
            content=content.strip(),
            severity=alert['severity']
        )

        # 严重告警发送邮件
        if alert['severity'] in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            send_email_alert(
                subject=f"诊断系统告警 - {alert['name']}",
                body=content.strip(),
                severity=alert['severity']
            )

        # 记录告警
        self.state.record_alert(alert_key)
        api_logger.warning(f"告警已发送：{alert['name']} (值：{alert['value']}, 阈值：{alert['threshold']})")

    def generate_report(self, data: Dict) -> str:
        """生成监控报告"""
        report = f"""
# 诊断系统监控报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 核心指标

| 指标 | 当前值 | 状态 |
|------|--------|------|
| 诊断总数 | {data['total_diagnosis']} | - |
| 成功率 | {data['success_rate']}% | {'✅' if data['success_rate'] >= THRESHOLDS['success_rate_min'] else '⚠️'} |
| 平均完成率 | {data['completion']['avg_completion_rate']}% | {'✅' if data['completion']['avg_completion_rate'] >= THRESHOLDS['completion_rate_min'] else '⚠️'} |
| 完全完成率 | {data['completion']['full_completion_rate']}% | - |
| 平均耗时 | {data['performance']['avg_duration_seconds']}s | {'✅' if data['performance']['avg_duration_seconds'] <= THRESHOLDS['avg_duration_max'] else '⚠️'} |
| P95 耗时 | {data['performance']['p95_duration_seconds']}s | - |
| 配额用尽率 | {data['quota']['quota_exhausted_rate']}% | {'✅' if data['quota']['quota_exhausted_rate'] <= THRESHOLDS['quota_exhausted_max'] else '⚠️'} |
| 错误总数 | {data['errors']['total_errors']} | - |

## 错误类型分布

"""
        for error_type, count in data['errors']['error_distribution'].items():
            report += f"- {error_type}: {count}\n"

        report += f"\n## 配额用尽模型\n\n"
        if data['quota']['exhausted_models']:
            for model in data['quota']['exhausted_models']:
                report += f"- {model}\n"
        else:
            report += "无\n"

        return report

    def run_check(self):
        """执行一次检查"""
        api_logger.info("开始执行监控检查...")

        # 获取监控数据
        data = self.get_dashboard('today')
        if not data:
            api_logger.error("无法获取监控数据，跳过本次检查")
            return

        # 检查指标
        alerts = self.check_metrics(data)

        if alerts:
            api_logger.warning(f"发现 {len(alerts)} 个告警")
            for alert in alerts:
                self.send_alert(alert, data)
        else:
            api_logger.info("所有指标正常")

        # 生成日报（每天第一次检查时）
        now = datetime.now()
        if now.hour < 1 and now.minute < 10:  # 凌晨 0:00-0:10 之间
            self.send_daily_report(data)

    def send_daily_report(self, data: Dict):
        """发送日报"""
        alert_key = f"daily_report_{datetime.now().strftime('%Y-%m-%d')}"

        if not self.state.can_alert(alert_key):
            return

        report = self.generate_report(data)

        # 发送钉钉日报
        send_dingtalk_alert(
            title="📊 诊断系统日报",
            content=report,
            severity=AlertSeverity.LOW
        )

        self.state.record_alert(alert_key)
        api_logger.info("日报已发送")

    def run(self):
        """运行监控"""
        api_logger.info(f"监控服务启动，检查间隔：{CHECK_INTERVAL}秒")
        api_logger.info(f"告警阈值配置：{THRESHOLDS}")

        try:
            while self.running:
                self.run_check()
                time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            api_logger.info("监控服务停止")
            self.running = False
        except Exception as e:
            api_logger.error(f"监控服务异常：{e}")
            raise


def main():
    """主函数"""
    # 设置日志
    setup_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file='logs/monitoring.log',
        max_bytes=10485760,
        backup_count=3
    )

    # 创建并运行监控器
    monitor = DiagnosisMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
