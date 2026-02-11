"""增强版AI客户端基础类"""
from .base_adapter import AIClient, AIResponse, AIPlatformType
from ..analytics.api_monitor import ApiMonitor
import time
import requests
from typing import Optional


class EnhancedAIClient(AIClient):
    """增强版AI客户端"""
    
    def __init__(self, platform_type: AIPlatformType, model_name: str, api_key: str):
        super().__init__(platform_type, model_name, api_key)
        self.monitor = ApiMonitor()
        self.last_request_time = 0
        self.consecutive_failures = 0
        self.failure_threshold = 3  # 连续失败阈值
    
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """发送提示，包含智能错误处理"""
        platform_name = self.platform_type.value
        
        # 检查速率限制
        if self.monitor.is_rate_limited(platform_name):
            return self._create_rate_limit_response()
        
        # 检查API状态
        if not self._is_platform_available():
            return self._create_fallback_response(prompt, **kwargs)
        
        start_time = time.time()
        
        try:
            # 记录请求
            self.monitor.record_request(platform_name)
            self.last_request_time = start_time
            
            # 执行原始请求
            response = self._send_actual_request(prompt, **kwargs)
            
            if response.success:
                self.consecutive_failures = 0  # 重置失败计数
                return response
            else:
                self.consecutive_failures += 1
                return response
                
        except Exception as e:
            self.consecutive_failures += 1
            return AIResponse(
                success=False,
                error_message=f"Request failed: {str(e)}",
                model=self.model_name,
                platform=self.platform_type.value,
                latency=time.time() - start_time
            )
    
    def _is_platform_available(self) -> bool:
        """检查平台是否可用"""
        platform_name = self.platform_type.value
        return (self.monitor.check_api_availability(platform_name) and 
                self.consecutive_failures < self.failure_threshold)
    
    def _create_rate_limit_response(self) -> AIResponse:
        """创建速率限制响应"""
        return AIResponse(
            success=False,
            error_message="Rate limit exceeded",
            error_type=getattr(self, 'AIErrorType', None).__dict__.get('RATE_LIMIT_EXCEEDED') if hasattr(self, 'AIErrorType') else None,
            model=self.model_name,
            platform=self.platform_type.value,
            latency=0.0
        )
    
    def _create_fallback_response(self, prompt: str, **kwargs) -> AIResponse:
        """创建备用响应"""
        # 这里可以实现备用逻辑，比如返回模拟数据
        return AIResponse(
            success=False,
            error_message="Platform unavailable",
            error_type=getattr(self, 'AIErrorType', None).__dict__.get('SERVER_ERROR') if hasattr(self, 'AIErrorType') else None,
            model=self.model_name,
            platform=self.platform_type.value,
            latency=0.0
        )
    
    def _send_actual_request(self, prompt: str, **kwargs) -> AIResponse:
        """执行实际的API请求 - 子类需实现"""
        raise NotImplementedError("_send_actual_request method must be implemented by subclasses")