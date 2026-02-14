from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time


@dataclass
class AIResponse:
    """
    统一的AI响应数据结构

    Attributes:
        platform: AI平台名称 (如 'openai', 'anthropic', 'google')
        model: 使用的模型名称 (如 'gpt-4', 'claude-2', 'gemini-pro')
        content: AI返回的内容
        usage: 使用统计信息 (如 token 使用量)
        latency: 请求延迟时间 (秒)
        success: 请求是否成功
        error_message: 错误信息 (如果请求失败)
        mode: 调用模式 (如 'chat', 'reasoner')
    """
    platform: str
    model: str
    content: str
    usage: Dict[str, Any]
    latency: float
    success: bool
    error_message: Optional[str] = None
    mode: Optional[str] = None  # 新增 mode 字段，用于标识调用模式


class AIClient(ABC):
    """
    多AI平台系统的统一客户端抽象基类

    该基类定义了所有AI客户端必须实现的接口，确保不同AI平台的客户端具有统一的调用方式。
    """

    @abstractmethod
    def send_prompt(self, prompt: str) -> AIResponse:
        """
        发送提示到AI平台并获取响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含AI响应的统一数据结构
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        检查AI客户端的健康状态

        Returns:
            bool: 客户端是否健康可用
        """
        pass