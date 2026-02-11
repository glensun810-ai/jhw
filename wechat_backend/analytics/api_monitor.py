"""API状态监控服务"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import threading
from dataclasses import dataclass


class ApiStatus(Enum):
    """API状态枚举"""
    ACTIVE = "active"           # 活跃
    INACTIVE = "inactive"       # 未配置
    OVER_QUOTA = "over_quota"   # 流量超限
    INVALID = "invalid"         # 密钥无效


@dataclass
class QuotaInfo:
    """配额信息"""
    daily_limit: Optional[int] = None
    used_today: int = 0
    reset_time: Optional[str] = None
    
    @property
    def remaining(self) -> Optional[int]:
        if self.daily_limit is not None:
            return max(0, self.daily_limit - self.used_today)
        return None


class ApiMonitor:
    """API状态监控服务"""
    
    def __init__(self):
        self.platform_status = {}
        self.request_counts: Dict[str, List[float]] = {}  # 记录请求时间戳
        self.lock = threading.Lock()
    
    def update_platform_config(self, platform: str, config):
        """更新平台配置"""
        with self.lock:
            self.platform_status[platform] = config
    
    def check_api_availability(self, platform: str) -> bool:
        """检查API可用性"""
        if platform not in self.platform_status:
            return False
            
        config = self.platform_status[platform]
        # 检查是否有API密钥和配额
        has_api_key = hasattr(config, 'api_key') and bool(config.api_key)
        has_quota = (hasattr(config, 'quota_info') and config.quota_info and 
                    (config.quota_info.remaining is None or config.quota_info.remaining > 0))
        
        # 检查API状态
        api_status = getattr(config, 'api_status', ApiStatus.INACTIVE)
        
        return has_api_key and has_quota and api_status == ApiStatus.ACTIVE
    
    def record_request(self, platform: str):
        """记录请求"""
        with self.lock:
            if platform not in self.request_counts:
                self.request_counts[platform] = []
            self.request_counts[platform].append(time.time())
            
            # 清理超过1分钟的记录
            cutoff = time.time() - 60
            self.request_counts[platform] = [
                t for t in self.request_counts[platform] if t > cutoff
            ]
    
    def get_rate_limit_remaining(self, platform: str) -> int:
        """获取速率限制剩余"""
        if platform not in self.request_counts:
            config = self.platform_status.get(platform)
            if config and hasattr(config, 'rate_limit_per_minute'):
                return config.rate_limit_per_minute or 0
            return 0
            
        config = self.platform_status.get(platform)
        limit = getattr(config, 'rate_limit_per_minute', 0) if config else 0
        if not limit:
            return float('inf')  # 无限制
            
        return max(0, limit - len(self.request_counts[platform]))
    
    def is_rate_limited(self, platform: str) -> bool:
        """检查是否达到速率限制"""
        config = self.platform_status.get(platform)
        if not config or not getattr(config, 'rate_limit_per_minute', None):
            return False
        return len(self.request_counts.get(platform, [])) >= config.rate_limit_per_minute