"""
AI 超时监控模块

功能：
1. 统计各 AI 平台的超时率
2. 超时告警（超过阈值时触发）
3. 超时趋势分析
4. 为模型切换提供决策依据

作者：系统架构组
日期：2026-03-04
版本：v1.0
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger


@dataclass
class TimeoutRecord:
    """超时记录"""
    platform: str
    model: str
    timestamp: float
    duration: float  # 实际耗时（秒）
    timeout_threshold: float  # 超时阈值（秒）
    success: bool  # 最终是否成功（重试后）


@dataclass
class PlatformStats:
    """平台统计数据"""
    total_requests: int = 0
    timeout_count: int = 0
    total_duration: float = 0.0
    last_timeout_time: float = 0.0
    consecutive_timeouts: int = 0
    max_consecutive_timeouts: int = 0


class AITimeoutMonitor:
    """
    AI 超时监控器

    使用示例:
        from wechat_backend.ai_adapters.timeout_monitor import get_timeout_monitor

        monitor = get_timeout_monitor()

        # 记录请求开始
        start_time = time.time()

        try:
            # 执行 AI 调用
            result = await ai_client.send_prompt(...)

            # 记录成功
            monitor.record_request(
                platform='qwen',
                model='qwen-max',
                duration=time.time() - start_time,
                timeout_threshold=30.0,
                success=True
            )
        except TimeoutError:
            # 记录超时
            monitor.record_request(
                platform='qwen',
                model='qwen-max',
                duration=time.time() - start_time,
                timeout_threshold=30.0,
                success=False
            )

            # 检查是否需要告警
            if monitor.should_alert('qwen'):
                api_logger.warning("⚠️ Qwen 平台超时率过高，建议切换模型")
    """

    def __init__(
        self,
        alert_threshold: float = 0.05,  # 超时率告警阈值（5%）
        window_seconds: int = 300,  # 统计时间窗口（5 分钟）
        min_requests_for_alert: int = 10  # 触发告警的最小请求数
    ):
        """
        初始化超时监控器

        参数:
            alert_threshold: 超时率告警阈值（默认 5%）
            window_seconds: 统计时间窗口（秒）
            min_requests_for_alert: 触发告警所需的最小请求数
        """
        self.alert_threshold = alert_threshold
        self.window_seconds = window_seconds
        self.min_requests_for_alert = min_requests_for_alert

        # 超时记录列表
        self._records: List[TimeoutRecord] = []
        self._lock = threading.Lock()

        # 平台统计（实时）
        self._platform_stats: Dict[str, PlatformStats] = defaultdict(PlatformStats)

        # 告警状态（防止重复告警）
        self._last_alert_time: Dict[str, float] = {}
        self._alert_cooldown = 60.0  # 告警冷却时间（秒）

        api_logger.info(
            f"[AITimeoutMonitor] 初始化完成：alert_threshold={alert_threshold:.1%}, "
            f"window={window_seconds}s"
        )

    def record_request(
        self,
        platform: str,
        model: str,
        duration: float,
        timeout_threshold: float,
        success: bool
    ):
        """
        记录一次 AI 请求

        参数:
            platform: AI 平台名称（qwen/doubao/deepseek 等）
            model: 模型名称
            duration: 实际耗时（秒）
            timeout_threshold: 超时阈值（秒）
            success: 是否成功（False 表示超时）
        """
        is_timeout = not success or duration > timeout_threshold

        with self._lock:
            # 记录详细数据
            record = TimeoutRecord(
                platform=platform,
                model=model,
                timestamp=time.time(),
                duration=duration,
                timeout_threshold=timeout_threshold,
                success=success
            )
            self._records.append(record)

            # 更新平台统计
            stats = self._platform_stats[platform]
            stats.total_requests += 1
            stats.total_duration += duration

            if is_timeout:
                stats.timeout_count += 1
                stats.last_timeout_time = time.time()
                stats.consecutive_timeouts += 1
                stats.max_consecutive_timeouts = max(
                    stats.max_consecutive_timeouts,
                    stats.consecutive_timeouts
                )
            else:
                stats.consecutive_timeouts = 0

            # 清理过期记录（超出时间窗口）
            self._cleanup_old_records()

        # 记录日志
        if is_timeout:
            api_logger.warning(
                f"[AI 超时] platform={platform}, model={model}, "
                f"duration={duration:.2f}s, threshold={timeout_threshold}s"
            )

    def _cleanup_old_records(self):
        """清理过期记录"""
        cutoff_time = time.time() - self.window_seconds
        self._records = [
            r for r in self._records if r.timestamp > cutoff_time
        ]

    def get_timeout_rate(self, platform: str) -> float:
        """
        获取平台超时率

        参数:
            platform: 平台名称

        返回:
            超时率（0.0-1.0）
        """
        with self._lock:
            stats = self._platform_stats.get(platform)
            if not stats or stats.total_requests == 0:
                return 0.0

            return stats.timeout_count / stats.total_requests

    def get_platform_stats(self, platform: str) -> Dict[str, Any]:
        """
        获取平台详细统计

        参数:
            platform: 平台名称

        返回:
            统计数据字典
        """
        with self._lock:
            stats = self._platform_stats.get(platform)
            if not stats:
                return {}

            timeout_rate = (
                stats.timeout_count / stats.total_requests
                if stats.total_requests > 0 else 0.0
            )

            avg_duration = (
                stats.total_duration / stats.total_requests
                if stats.total_requests > 0 else 0.0
            )

            return {
                'platform': platform,
                'total_requests': stats.total_requests,
                'timeout_count': stats.timeout_count,
                'timeout_rate': timeout_rate,
                'avg_duration': avg_duration,
                'consecutive_timeouts': stats.consecutive_timeouts,
                'max_consecutive_timeouts': stats.max_consecutive_timeouts,
                'last_timeout_time': datetime.fromtimestamp(
                    stats.last_timeout_time
                ).isoformat() if stats.last_timeout_time > 0 else None
            }

    def should_alert(self, platform: str) -> bool:
        """
        判断是否应该触发告警

        参数:
            platform: 平台名称

        返回:
            True 表示应该告警
        """
        with self._lock:
            stats = self._platform_stats.get(platform)
            if not stats:
                return False

            # 检查请求数是否达到阈值
            if stats.total_requests < self.min_requests_for_alert:
                return False

            # 计算超时率
            timeout_rate = stats.timeout_count / stats.total_requests

            # 检查是否超过阈值
            if timeout_rate < self.alert_threshold:
                return False

            # 检查冷却时间
            now = time.time()
            last_alert = self._last_alert_time.get(platform, 0)
            if now - last_alert < self._alert_cooldown:
                return False

            # 更新告警时间
            self._last_alert_time[platform] = now
            return True

    def get_all_platforms_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有平台的状态

        返回:
            所有平台的统计数据
        """
        with self._lock:
            result = {}
            for platform in self._platform_stats.keys():
                result[platform] = self.get_platform_stats(platform)
            return result

    def get_recommendation(self, platform: str) -> Optional[str]:
        """
        获取平台使用建议

        参数:
            platform: 当前平台名称

        返回:
            建议信息（如果有）
        """
        stats_data = self.get_platform_stats(platform)
        if not stats_data:
            return None

        timeout_rate = stats_data.get('timeout_rate', 0)
        consecutive = stats_data.get('consecutive_timeouts', 0)

        # 连续超时 3 次以上，建议立即切换
        if consecutive >= 3:
            return (
                f"⚠️ {platform} 连续超时{consecutive}次，"
                f"建议立即切换到备用模型"
            )

        # 超时率超过 10%，建议切换
        if timeout_rate > 0.10:
            return (
                f"⚠️ {platform} 超时率过高 ({timeout_rate:.1%})，"
                f"建议切换到备用模型"
            )

        # 超时率超过 5%，发出警告
        if timeout_rate > self.alert_threshold:
            return (
                f"⚠️ {platform} 超时率偏高 ({timeout_rate:.1%})，"
                f"请密切关注"
            )

        return None

    def reset_stats(self, platform: Optional[str] = None):
        """
        重置统计数据

        参数:
            platform: 平台名称（None 表示重置所有）
        """
        with self._lock:
            if platform:
                if platform in self._platform_stats:
                    self._platform_stats[platform] = PlatformStats()
            else:
                self._platform_stats.clear()
                self._records.clear()

    def export_metrics(self) -> Dict[str, Any]:
        """
        导出监控指标（用于 Prometheus 等监控系统）

        返回:
            指标字典
        """
        with self._lock:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'window_seconds': self.window_seconds,
                'alert_threshold': self.alert_threshold,
                'platforms': {}
            }

            for platform, stats in self._platform_stats.items():
                timeout_rate = (
                    stats.timeout_count / stats.total_requests
                    if stats.total_requests > 0 else 0.0
                )

                metrics['platforms'][platform] = {
                    'requests_total': stats.total_requests,
                    'timeouts_total': stats.timeout_count,
                    'timeout_rate': timeout_rate,
                    'avg_duration_seconds': (
                        stats.total_duration / stats.total_requests
                        if stats.total_requests > 0 else 0.0
                    ),
                    'consecutive_timeouts': stats.consecutive_timeouts
                }

            return metrics


# 全局监控器实例
_timeout_monitor: Optional[AITimeoutMonitor] = None


def get_timeout_monitor() -> AITimeoutMonitor:
    """获取全局超时监控器实例"""
    global _timeout_monitor
    if _timeout_monitor is None:
        _timeout_monitor = AITimeoutMonitor(
            alert_threshold=0.05,  # 5% 超时率告警
            window_seconds=300,    # 5 分钟统计窗口
            min_requests_for_alert=10  # 至少 10 次请求才告警
        )
    return _timeout_monitor


def reset_timeout_monitor():
    """重置全局监控器（用于测试）"""
    global _timeout_monitor
    _timeout_monitor = None


# ==================== 装饰器支持 ====================

def monitor_ai_timeout(timeout_threshold: float = 30.0):
    """
    AI 调用超时监控装饰器

    使用示例:
        @monitor_ai_timeout(timeout_threshold=30.0)
        async def send_prompt(self, prompt: str, **kwargs):
            # AI 调用逻辑
            ...

    参数:
        timeout_threshold: 超时阈值（秒）
    """
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 提取平台和模型信息
            self_obj = args[0] if args else None
            platform = getattr(self_obj, 'platform_type', None)
            if platform:
                platform = platform.value if hasattr(platform, 'value') else str(platform)
            else:
                platform = func.__module__.split('.')[-1]

            model = getattr(self_obj, 'model_name', 'unknown')

            # 记录开始时间
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                # 记录请求
                duration = time.time() - start_time
                monitor = get_timeout_monitor()
                monitor.record_request(
                    platform=platform,
                    model=model,
                    duration=duration,
                    timeout_threshold=timeout_threshold,
                    success=success
                )

                # 检查是否需要告警
                if monitor.should_alert(platform):
                    api_logger.warning(
                        f"⚠️ [AI 超时告警] {platform} 平台超时率过高，"
                        f"建议切换模型"
                    )

        return wrapper
    return decorator
