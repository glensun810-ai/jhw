#!/usr/bin/env python3
"""
P2-2 修复：请求限流监控

功能：
1. 记录限流触发事件
2. 统计限流频率
3. 识别潜在的攻击行为
4. 发送告警通知
"""

import time
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from wechat_backend.logging_config import api_logger

# 监控数据保存路径
MONITORING_DATA_DIR = Path(__file__).parent.parent / 'monitoring_data'
RATE_LIMIT_STATS_FILE = MONITORING_DATA_DIR / 'rate_limit_stats.json'


class RateLimitMonitor:
    """
    限流监控器
    
    功能：
    1. 记录每次限流触发
    2. 统计限流频率
    3. 识别异常模式
    4. 生成监控报告
    """
    
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'total_limited': 0,
            'limited_by_endpoint': defaultdict(int),
            'limited_by_ip': defaultdict(int),
            'limited_by_user': defaultdict(int),
            'hourly_stats': defaultdict(lambda: {'requests': 0, 'limited': 0}),
            'recent_limits': []  # 最近 100 次限流记录
        }
        self._load_stats()
    
    def _load_stats(self):
        """加载统计数据"""
        try:
            if RATE_LIMIT_STATS_FILE.exists():
                with open(RATE_LIMIT_STATS_FILE, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    # 合并加载的统计数据
                    self.stats['total_requests'] = loaded_stats.get('total_requests', 0)
                    self.stats['total_limited'] = loaded_stats.get('total_limited', 0)
                    
                    # 合并字典
                    for key in ['limited_by_endpoint', 'limited_by_ip', 'limited_by_user']:
                        if key in loaded_stats:
                            self.stats[key].update(loaded_stats[key])
                    
                    # 合并小时统计（只保留最近 24 小时）
                    if 'hourly_stats' in loaded_stats:
                        now = datetime.now()
                        cutoff = now - timedelta(hours=24)
                        for hour_str, hour_data in loaded_stats['hourly_stats'].items():
                            try:
                                hour_dt = datetime.fromisoformat(hour_str)
                                if hour_dt >= cutoff:
                                    self.stats['hourly_stats'][hour_str] = hour_data
                            except Exception as e:
                                api_logger.error(f"[RateLimit] Error parsing hour string {hour_str}: {e}", exc_info=True)
                                # 小时时间戳解析失败，跳过该小时数据
        except Exception as e:
            api_logger.error(f"[RateLimit] 加载统计数据失败：{e}")
    
    def _save_stats(self):
        """保存统计数据"""
        try:
            MONITORING_DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            # 转换为可序列化的格式
            stats_to_save = {
                'total_requests': self.stats['total_requests'],
                'total_limited': self.stats['total_limited'],
                'limited_by_endpoint': dict(self.stats['limited_by_endpoint']),
                'limited_by_ip': dict(self.stats['limited_by_ip']),
                'limited_by_user': dict(self.stats['limited_by_user']),
                'hourly_stats': dict(self.stats['hourly_stats']),
                'recent_limits': self.stats['recent_limits'][-100:]  # 只保留最近 100 条
            }
            
            with open(RATE_LIMIT_STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            api_logger.error(f"[RateLimit] 保存统计数据失败：{e}")
    
    def record_request(self, endpoint: str = None, ip: str = None, user_id: str = None):
        """
        记录请求
        
        Args:
            endpoint: API 端点
            ip: IP 地址
            user_id: 用户 ID
        """
        self.stats['total_requests'] += 1
        
        # 小时统计
        hour_key = datetime.now().strftime('%Y-%m-%d-%H')
        self.stats['hourly_stats'][hour_key]['requests'] += 1
        
        # 每 1000 次请求保存一次
        if self.stats['total_requests'] % 1000 == 0:
            self._save_stats()
    
    def record_limit(self, endpoint: str = None, ip: str = None, user_id: str = None, 
                     limit_type: str = 'endpoint', limit_value: int = None):
        """
        记录限流事件
        
        Args:
            endpoint: API 端点
            ip: IP 地址
            user_id: 用户 ID
            limit_type: 限流类型 (endpoint, ip, user)
            limit_value: 限制值
        """
        self.stats['total_limited'] += 1
        
        # 按端点统计
        if endpoint:
            self.stats['limited_by_endpoint'][endpoint] += 1
        
        # 按 IP 统计
        if ip:
            self.stats['limited_by_ip'][ip] += 1
        
        # 按用户统计
        if user_id:
            self.stats['limited_by_user'][user_id] += 1
        
        # 小时统计
        hour_key = datetime.now().strftime('%Y-%m-%d-%H')
        self.stats['hourly_stats'][hour_key]['limited'] += 1
        
        # 记录最近限流事件
        limit_event = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'ip': ip,
            'user_id': user_id,
            'limit_type': limit_type,
            'limit_value': limit_value
        }
        self.stats['recent_limits'].append(limit_event)
        
        # 保持最近 100 条
        if len(self.stats['recent_limits']) > 100:
            self.stats['recent_limits'] = self.stats['recent_limits'][-100:]
        
        # 记录日志
        api_logger.warning(
            f"[RateLimit] 限流触发：endpoint={endpoint}, ip={ip}, user={user_id}, "
            f"type={limit_type}, limit={limit_value}"
        )
        
        # 检查是否需要告警
        self._check_alert_conditions(endpoint, ip, user_id)
        
        # 保存统计
        self._save_stats()
    
    def _check_alert_conditions(self, endpoint: str, ip: str, user_id: str):
        """
        检查告警条件
        
        Args:
            endpoint: API 端点
            ip: IP 地址
            user_id: 用户 ID
        """
        # 检查 IP 限流频率
        if ip and self.stats['limited_by_ip'][ip] > 100:
            api_logger.error(f"[RateLimit] ⚠️  告警：IP {ip} 触发限流超过 100 次，可能存在攻击行为")
        
        # 检查端点限流频率
        if endpoint and self.stats['limited_by_endpoint'][endpoint] > 1000:
            api_logger.error(f"[RateLimit] ⚠️  告警：端点 {endpoint} 触发限流超过 1000 次")
        
        # 检查小时限流率
        hour_key = datetime.now().strftime('%Y-%m-%d-%H')
        hour_data = self.stats['hourly_stats'].get(hour_key, {})
        requests = hour_data.get('requests', 1)
        limited = hour_data.get('limited', 0)
        
        if requests > 0:
            limit_rate = limited / requests
            if limit_rate > 0.1:  # 限流率超过 10%
                api_logger.warning(
                    f"[RateLimit] ⚠️  告警：当前小时限流率过高：{limit_rate:.2%} "
                    f"(requests={requests}, limited={limited})"
                )
    
    def get_stats(self) -> Dict:
        """
        获取统计数据
        
        Returns:
            统计数据字典
        """
        # 计算限流率
        total = self.stats['total_requests']
        limited = self.stats['total_limited']
        limit_rate = (limited / total * 100) if total > 0 else 0
        
        # 获取 Top 10 限流端点
        top_endpoints = sorted(
            self.stats['limited_by_endpoint'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # 获取 Top 10 限流 IP
        top_ips = sorted(
            self.stats['limited_by_ip'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_requests': total,
            'total_limited': limited,
            'limit_rate': f"{limit_rate:.2f}%",
            'top_limited_endpoints': top_endpoints,
            'top_limited_ips': top_ips,
            'recent_limits_count': len(self.stats['recent_limits']),
            'hourly_stats_count': len(self.stats['hourly_stats'])
        }
    
    def reset_stats(self):
        """重置统计数据"""
        self.stats = {
            'total_requests': 0,
            'total_limited': 0,
            'limited_by_endpoint': defaultdict(int),
            'limited_by_ip': defaultdict(int),
            'limited_by_user': defaultdict(int),
            'hourly_stats': defaultdict(lambda: {'requests': 0, 'limited': 0}),
            'recent_limits': []
        }
        self._save_stats()
        api_logger.info("[RateLimit] 统计数据已重置")


# 全局监控器实例
_rate_limit_monitor = None


def get_rate_limit_monitor() -> RateLimitMonitor:
    """
    获取限流监控器实例
    
    Returns:
        限流监控器实例
    """
    global _rate_limit_monitor
    if _rate_limit_monitor is None:
        _rate_limit_monitor = RateLimitMonitor()
    return _rate_limit_monitor


# 装饰器：自动记录限流
def monitored_rate_limit(func):
    """
    限流监控装饰器
    
    用法:
        @monitored_rate_limit
        def check_rate_limit(...):
            ...
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 调用原函数
        result = func(*args, **kwargs)
        
        # 如果返回 False，表示触发限流
        if result is False:
            monitor = get_rate_limit_monitor()
            monitor.record_limit(
                endpoint=kwargs.get('endpoint'),
                ip=kwargs.get('ip'),
                user_id=kwargs.get('user_id'),
                limit_type=kwargs.get('limit_type', 'unknown')
            )
        
        return result
    
    return wrapper


if __name__ == '__main__':
    print("="*60)
    print("P2-2: 请求限流监控")
    print("="*60)
    print()
    
    # 测试监控器
    monitor = get_rate_limit_monitor()
    
    # 模拟请求
    for i in range(10):
        monitor.record_request(endpoint='/api/test', ip='192.168.1.1')
    
    # 模拟限流
    for i in range(5):
        monitor.record_limit(
            endpoint='/api/test',
            ip='192.168.1.1',
            limit_type='endpoint',
            limit_value=100
        )
    
    # 获取统计
    stats = monitor.get_stats()
    print("统计数据:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
