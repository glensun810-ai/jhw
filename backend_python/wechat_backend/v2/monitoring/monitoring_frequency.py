#!/usr/bin/env python3
"""
Step 2.2: v2 监控频率配置

支持根据灰度比例动态调整监控频率:
- 10% 灰度：5 分钟检查窗口
- 30% 灰度：1 分钟检查窗口
- 100% 灰度：1 分钟检查窗口 + 更严格的阈值

使用方法:
    from wechat_backend.v2.monitoring.monitoring_frequency import get_monitoring_config
    
    config = get_monitoring_config(gray_percentage=30)
    print(config['window_seconds'])  # 60
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class MonitoringMode(Enum):
    """监控模式"""
    STANDARD = 'standard'      # 标准监控（5 分钟）
    ENHANCED = 'enhanced'      # 增强监控（1 分钟）
    CRITICAL = 'critical'      # 关键监控（30 秒）


@dataclass
class MonitoringConfig:
    """监控配置"""
    mode: MonitoringMode
    window_seconds: int
    check_interval_seconds: int
    alert_cooldown_seconds: int
    metrics_retention_hours: int


# 预定义的监控配置
MONITORING_PRESETS: Dict[MonitoringMode, MonitoringConfig] = {
    MonitoringMode.STANDARD: MonitoringConfig(
        mode=MonitoringMode.STANDARD,
        window_seconds=300,  # 5 分钟
        check_interval_seconds=60,  # 1 分钟检查一次
        alert_cooldown_seconds=300,  # 告警冷却 5 分钟
        metrics_retention_hours=24,
    ),
    MonitoringMode.ENHANCED: MonitoringConfig(
        mode=MonitoringMode.ENHANCED,
        window_seconds=60,  # 1 分钟
        check_interval_seconds=30,  # 30 秒检查一次
        alert_cooldown_seconds=120,  # 告警冷却 2 分钟
        metrics_retention_hours=48,
    ),
    MonitoringMode.CRITICAL: MonitoringConfig(
        mode=MonitoringMode.CRITICAL,
        window_seconds=30,  # 30 秒
        check_interval_seconds=15,  # 15 秒检查一次
        alert_cooldown_seconds=60,  # 告警冷却 1 分钟
        metrics_retention_hours=168,  # 7 天
    ),
}


def get_monitoring_config(gray_percentage: int = 10) -> MonitoringConfig:
    """
    根据灰度比例获取监控配置

    Args:
        gray_percentage: 灰度比例 (0-100)

    Returns:
        MonitoringConfig: 监控配置
    """
    if gray_percentage >= 100:
        # 全量发布：关键监控
        return MONITORING_PRESETS[MonitoringMode.CRITICAL]
    elif gray_percentage >= 30:
        # 扩大灰度：增强监控
        return MONITORING_PRESETS[MonitoringMode.ENHANCED]
    else:
        # 内部测试：标准监控
        return MONITORING_PRESETS[MonitoringMode.STANDARD]


def get_alert_thresholds(gray_percentage: int = 10) -> Dict[str, float]:
    """
    根据灰度比例获取告警阈值

    灰度比例越高，阈值越严格

    Args:
        gray_percentage: 灰度比例 (0-100)

    Returns:
        Dict[str, float]: 告警阈值配置
    """
    if gray_percentage >= 100:
        # 全量发布：最严格阈值
        return {
            'error_rate': 0.03,        # 3%
            'timeout_rate': 0.01,      # 1%
            'dead_letter_growth': 5,   # 5/小时
            'avg_response_time': 20,   # 20 秒
            'ai_failure_rate': 0.05,   # 5%
        }
    elif gray_percentage >= 30:
        # 扩大灰度：中等阈值
        return {
            'error_rate': 0.04,        # 4%
            'timeout_rate': 0.015,     # 1.5%
            'dead_letter_growth': 8,   # 8/小时
            'avg_response_time': 25,   # 25 秒
            'ai_failure_rate': 0.08,   # 8%
        }
    else:
        # 内部测试：宽松阈值
        return {
            'error_rate': 0.05,        # 5%
            'timeout_rate': 0.02,      # 2%
            'dead_letter_growth': 10,  # 10/小时
            'avg_response_time': 30,   # 30 秒
            'ai_failure_rate': 0.10,   # 10%
        }


def update_monitoring_frequency(gray_percentage: int) -> Dict[str, Any]:
    """
    更新监控频率

    Args:
        gray_percentage: 灰度比例

    Returns:
        Dict[str, Any]: 更新后的配置
    """
    config = get_monitoring_config(gray_percentage)
    thresholds = get_alert_thresholds(gray_percentage)

    result = {
        'mode': config.mode.value,
        'window_seconds': config.window_seconds,
        'check_interval_seconds': config.check_interval_seconds,
        'alert_cooldown_seconds': config.alert_cooldown_seconds,
        'thresholds': thresholds,
    }

    # 记录配置变更
    print(f"📊 监控频率已更新:")
    print(f"   模式：{config.mode.value}")
    print(f"   时间窗口：{config.window_seconds}秒")
    print(f"   检查间隔：{config.check_interval_seconds}秒")
    print(f"   告警冷却：{config.alert_cooldown_seconds}秒")
    print(f"   错误率阈值：{thresholds['error_rate']:.2%}")

    return result


def get_monitoring_status() -> Dict[str, Any]:
    """
    获取当前监控状态

    Returns:
        Dict[str, Any]: 监控状态信息
    """
    # 这里可以从配置中心或数据库读取当前配置
    # 暂时返回默认配置
    config = MONITORING_PRESETS[MonitoringMode.STANDARD]

    return {
        'current_mode': config.mode.value,
        'window_seconds': config.window_seconds,
        'check_interval_seconds': config.check_interval_seconds,
        'is_active': True,
        'last_updated': None,
    }


if __name__ == '__main__':
    # 测试监控频率配置
    print("=" * 60)
    print("Step 2.2: v2 监控频率配置测试")
    print("=" * 60)
    print()

    # 测试不同灰度比例的配置
    test_percentages = [10, 30, 100]

    for percent in test_percentages:
        print(f"\n📊 灰度比例：{percent}%")
        print("-" * 40)

        config = get_monitoring_config(percent)
        thresholds = get_alert_thresholds(percent)

        print(f"  监控模式：{config.mode.value}")
        print(f"  时间窗口：{config.window_seconds}秒 ({config.window_seconds // 60}分钟)")
        print(f"  检查间隔：{config.check_interval_seconds}秒")
        print(f"  告警冷却：{config.alert_cooldown_seconds}秒")
        print()
        print(f"  告警阈值:")
        print(f"    - 错误率：{thresholds['error_rate']:.2%}")
        print(f"    - 超时率：{thresholds['timeout_rate']:.2%}")
        print(f"    - 死信队列：{thresholds['dead_letter_growth']}/小时")
        print(f"    - 响应时间：{thresholds['avg_response_time']}秒")
        print(f"    - AI 失败率：{thresholds['ai_failure_rate']:.2%}")

    print("\n✅ 测试完成")
