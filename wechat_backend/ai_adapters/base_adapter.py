from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any

class AIPlatformType(Enum):
    """支持的AI平台枚举"""
    DEEPSEEK = "deepseek"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GEMINI = "gemini"
    QWEN = "qwen"
    WENXIN = "wenxin"
    DOUBAO = "doubao"
    KIMI = "kimi"
    YUANBAO = "yuanbao"
    SPARK = "spark"
    ZHIPU = "zhipu"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

class AIErrorType(Enum):
    """标准化的AI错误类型枚举"""
    INVALID_API_KEY = "无效的API Key"
    INSUFFICIENT_QUOTA = "配额不足"
    CONTENT_SAFETY = "内容安全审查不通过"
    RATE_LIMIT_EXCEEDED = "请求频率超限"
    SERVER_ERROR = "平台服务器错误"
    SERVICE_UNAVAILABLE = "服务不可用（熔断中）"
    UNKNOWN_ERROR = "未知错误"

@dataclass
class AIResponse:
    """标准化的AI响应数据结构"""
    success: bool
    content: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[AIErrorType] = None # 新增错误类型字段
    model: Optional[str] = None
    platform: Optional[str] = None
    tokens_used: int = 0
    latency: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """将响应对象转换为字典"""
        data = asdict(self)
        if self.error_type:
            data['error_type'] = self.error_type.value
        return data


class AIClient(ABC):
    """AI客户端接口"""
    def __init__(self, platform_type: AIPlatformType, model_name: str, api_key: str):
        self.platform_type = platform_type
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向AI平台发送prompt并获取响应
        """
        pass
