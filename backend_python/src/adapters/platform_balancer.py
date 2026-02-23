"""
AI Platform Load Balancer and Health Checker
Provides intelligent routing and health monitoring for AI platforms
"""
import time
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.logging_config import api_logger


class PlatformHealthStatus(Enum):
    """平台健康状态枚举"""
    HEALTHY = "healthy"      # 健康状态
    WARNING = "warning"      # 警告状态
    UNHEALTHY = "unhealthy"  # 不健康状态
    UNKNOWN = "unknown"      # 未知状态


class PlatformMetrics:
    """平台性能指标"""
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count: int = 0
        self.failure_count: int = 0
        self.last_access_time: Optional[float] = None
        self.health_status: PlatformHealthStatus = PlatformHealthStatus.UNKNOWN
    
    def add_response_time(self, response_time: float):
        """添加响应时间记录"""
        self.response_times.append(response_time)
        # 只保留最近100条记录
        if len(self.response_times) > 100:
            self.response_times.pop(0)
    
    def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total_requests = self.success_count + self.failure_count
        if total_requests == 0:
            return 1.0  # 默认成功率为100%
        return self.success_count / total_requests
    
    def update_health_status(self):
        """更新健康状态"""
        avg_response_time = self.get_avg_response_time()
        success_rate = self.get_success_rate()
        
        # 基于响应时间和成功率判断健康状态
        if success_rate < 0.7:  # 成功率低于70%
            self.health_status = PlatformHealthStatus.UNHEALTHY
        elif avg_response_time > 30.0 or success_rate < 0.9:  # 响应时间超过30秒或成功率低于90%
            self.health_status = PlatformHealthStatus.WARNING
        else:
            self.health_status = PlatformHealthStatus.HEALTHY


class PlatformBalancer:
    """AI平台负载均衡器"""
    
    def __init__(self):
        self.metrics: Dict[str, PlatformMetrics] = {}
        self.lock = threading.Lock()
        self.health_check_interval = 300  # 5分钟健康检查间隔
        self.start_health_monitoring()
    
    def get_or_create_metrics(self, platform_name: str) -> PlatformMetrics:
        """获取或创建平台指标对象"""
        with self.lock:
            if platform_name not in self.metrics:
                self.metrics[platform_name] = PlatformMetrics()
            return self.metrics[platform_name]
    
    def record_request_result(self, platform_name: str, response_time: float, success: bool):
        """记录请求结果"""
        metrics = self.get_or_create_metrics(platform_name)
        
        with self.lock:
            metrics.add_response_time(response_time)
            if success:
                metrics.success_count += 1
            else:
                metrics.failure_count += 1
            metrics.last_access_time = time.time()
            metrics.update_health_status()
    
    def get_platform_priority_list(self) -> List[Tuple[str, float]]:
        """获取平台优先级列表，基于健康状态和性能"""
        priorities = []
        
        with self.lock:
            for platform_name, metrics in self.metrics.items():
                # 检查平台是否在AIAdapterFactory中注册
                if not AIAdapterFactory.is_platform_available(platform_name):
                    continue
                
                # 计算优先级分数
                # 健康状态权重: 健康=1.0, 警告=0.7, 不健康=0.3, 未知=0.8
                health_weight = {
                    PlatformHealthStatus.HEALTHY: 1.0,
                    PlatformHealthStatus.WARNING: 0.7,
                    PlatformHealthStatus.UNHEALTHY: 0.3,
                    PlatformHealthStatus.UNKNOWN: 0.8
                }.get(metrics.health_status, 0.5)
                
                # 响应时间权重: 响应越快优先级越高
                avg_response_time = metrics.get_avg_response_time()
                if avg_response_time == 0:
                    response_weight = 1.0  # 如果没有记录，默认高优先级
                else:
                    # 响应时间权重，最大1.0（最快），最小0.1（最慢）
                    response_weight = max(0.1, min(1.0, 10.0 / (avg_response_time + 1)))
                
                # 成功率权重
                success_rate = metrics.get_success_rate()
                success_weight = success_rate
                
                # 综合得分
                score = health_weight * 0.5 + response_weight * 0.3 + success_weight * 0.2
                priorities.append((platform_name, score))
        
        # 按分数降序排列
        priorities.sort(key=lambda x: x[1], reverse=True)
        return priorities
    
    def select_best_platform(self, available_platforms: List[str]) -> Optional[str]:
        """从可用平台中选择最佳平台"""
        if not available_platforms:
            return None
        
        # 获取所有平台的优先级
        all_priorities = self.get_platform_priority_list()
        
        # 只考虑在available_platforms中的平台
        filtered_priorities = [(name, score) for name, score in all_priorities 
                              if name in available_platforms]
        
        if filtered_priorities:
            # 返回优先级最高的平台
            return filtered_priorities[0][0]
        else:
            # 如果没有可用平台的性能记录，随机选择一个
            return available_platforms[0] if available_platforms else None
    
    def get_healthy_platforms(self) -> List[str]:
        """获取健康状态的平台列表"""
        healthy_platforms = []
        
        with self.lock:
            for platform_name, metrics in self.metrics.items():
                if (metrics.health_status in [PlatformHealthStatus.HEALTHY, PlatformHealthStatus.UNKNOWN] 
                    and AIAdapterFactory.is_platform_available(platform_name)):
                    healthy_platforms.append(platform_name)
        
        return healthy_platforms
    
    def start_health_monitoring(self):
        """启动健康监控线程"""
        def health_check_worker():
            while True:
                try:
                    self.perform_health_check()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    api_logger.error(f"Error in health check worker: {e}")
        
        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()
        api_logger.info("Started platform health monitoring thread")
    
    def perform_health_check(self):
        """执行健康检查"""
        # 这里可以实现主动健康检查逻辑
        # 暂时只是更新健康状态
        with self.lock:
            for platform_name, metrics in self.metrics.items():
                metrics.update_health_status()
        
        api_logger.debug("Performed platform health check")


# 全局负载均衡器实例
balancer = PlatformBalancer()


def get_platform_balancer() -> PlatformBalancer:
    """获取全局负载均衡器实例"""
    return balancer