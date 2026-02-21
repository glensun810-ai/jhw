import time
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any, List
from wechat_backend.logging_config import api_logger
from wechat_backend.optimization.request_frequency_optimizer import optimize_request_frequency, RequestPriority
from wechat_backend.ai_adapters.geo_parser import parse_geo_json_enhanced

# 保持向后兼容
parse_geo_json = parse_geo_json_enhanced

# GEO Analysis Prompt Template with self-audit instructions
GEO_PROMPT_TEMPLATE = """
用户品牌：{brand_name}
竞争对手：{competitors}

请回答以下用户问题：
{question}

---
重要要求：
1. 请以专业顾问的身份客观回答。
2. 在回答结束后，必须另起一行，以严格的 JSON 格式输出以下字段（不要包含在 Markdown 代码块中）：
{{
  "geo_analysis": {{
    "brand_mentioned": boolean,
    "rank": number,
    "sentiment": number,
    "cited_sources": [
      {{"url": "string", "site_name": "string", "attitude": "positive/negative/neutral"}}
    ],
    "interception": "string"
  }}
}}

字段说明：
- brand_mentioned: 品牌是否被提到 (true/false)
- rank: 品牌在推荐列表中的排名（1-10），若未提到或未排名则为 -1
- sentiment: 对品牌的情感评分（-1.0 到 1.0）
- cited_sources: 提到的或暗示的信源/网址列表
- interception: 如果推荐了竞品而没推荐我，写下竞品名
"""

class AIPlatformType(Enum):
    """支持的AI平台枚举"""
    DEEPSEEK = "deepseek"
    DEEPSEEKR1 = "deepseekr1"  # New DeepSeek R1 platform type
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
        # 应用请求频率优化装饰器
        self._apply_frequency_control()

    def _apply_frequency_control(self):
        """应用请求频率控制"""
        # 为send_prompt方法应用频率控制装饰器
        original_send_prompt = self.send_prompt
        decorated_send_prompt = optimize_request_frequency(
            self.platform_type.value, 
            RequestPriority.MEDIUM
        )(original_send_prompt)
        self.send_prompt = decorated_send_prompt

    @abstractmethod
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向AI平台发送prompt并获取响应
        """
        pass
