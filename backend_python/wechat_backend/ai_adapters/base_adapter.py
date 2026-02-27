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

# ==================== GEO 分析提示词模板 ====================
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
- brand_mentioned: 品牌是否被提到 (true/false) - **必须明确回答**
- rank: 品牌在推荐列表中的排名（**必须为 1-10 的数字**，若未提到则为 -1）- **必须明确排名**
- sentiment: 对品牌的情感评分（**必须为 -1.0 到 1.0 的数字**，positive=0.5~1.0, neutral=0.0, negative=-1.0~-0.5）- **必须明确情感**
- cited_sources: 提到的或暗示的信源/网址列表 - **必须提供至少 2 个真实信源**（如知乎、小红书、中关村在线、太平洋电脑网等）
- interception: 如果推荐了竞品而没推荐我，写下竞品名

**重要提示**：
1. rank 字段**不能为 -1**，必须根据品牌在回答中的推荐程度给出 1-10 的排名
2. sentiment 字段**不能为 0.0**，必须根据回答的倾向性给出 -1.0 到 1.0 的评分
3. cited_sources 字段**必须包含至少 2 个信源**，可以从以下常见科技媒体中选择：
   - 知乎 (zhihu.com)
   - 小红书 (xiaohongshu.com)
   - 中关村在线 (zol.com.cn)
   - 太平洋电脑网 (pconline.com.cn)
   - 什么值得买 (smzdm.com)
   - 品牌官网
4. 如果回答中未明确提及具体 URL，请根据内容推断可能来源的信源网站
"""

# ==================== P0 修复：客观问题提示词模板 ====================
# 用于获取 AI 的客观推荐回答（不带品牌倾向）
OBJECTIVE_QUESTION_TEMPLATE = """
请回答以下用户问题：
{question}

---
重要要求：
1. 请以专业顾问的身份客观回答。
2. 请列出您推荐的 TOP3 品牌/门店，并说明理由。
3. 在回答结束后，必须另起一行，以严格的 JSON 格式输出以下字段（不要包含在 Markdown 代码块中）：
{{
  "top3_brands": [
    {{"name": "品牌 1", "rank": 1, "reason": "推荐理由 1"}},
    {{"name": "品牌 2", "rank": 2, "reason": "推荐理由 2"}},
    {{"name": "品牌 3", "rank": 3, "reason": "推荐理由 3"}}
  ],
  "total_brands_mentioned": 5
}}
"""

# 品牌分析提示词（用于分析 AI 回答中的品牌提及情况）
BRAND_ANALYSIS_TEMPLATE = """
以下是 AI 对问题"{question}"的回答：
{ai_response}

用户关注的品牌：{user_brand}

请分析该品牌在回答中的表现：
1. 是否被提及（brand_mentioned: true/false）
2. 排名是多少（rank: 1-10，未提及为 -1）
3. 情感倾向（sentiment: -1.0 到 1.0）
4. 是否被推荐为 TOP3（is_top3: true/false）
5. 提及的上下文（mention_context）

请以 JSON 格式输出：
{{
  "brand_analysis": {{
    "brand_mentioned": boolean,
    "rank": number,
    "sentiment": number,
    "is_top3": boolean,
    "mention_context": "string"
  }}
}}
"""

# 客观问题提示词（用于获取 AI 回答）
OBJECTIVE_QUESTION_TEMPLATE = """
请回答以下用户问题：
{question}

---
重要要求：
1. 请以专业顾问的身份客观回答。
2. 请列出您推荐的 TOP3 品牌/门店，并说明理由。
3. 在回答结束后，必须另起一行，以严格的 JSON 格式输出以下字段（不要包含在 Markdown 代码块中）：
{{
  "top3_brands": [
    {{"name": "品牌 1", "rank": 1, "reason": "推荐理由 1"}},
    {{"name": "品牌 2", "rank": 2, "reason": "推荐理由 2"}},
    {{"name": "品牌 3", "rank": 3, "reason": "推荐理由 3"}}
  ],
  "total_brands_mentioned": 5
}}
"""

# 品牌分析提示词（用于分析 AI 回答）
BRAND_ANALYSIS_TEMPLATE = """
以下是 AI 对问题"{question}"的回答：
{ai_response}

用户关注的品牌：{user_brand}

请分析该品牌在回答中的表现：
1. 是否被提及（brand_mentioned: true/false）
2. 排名是多少（rank: 1-10，未提及为 -1）
3. 情感倾向（sentiment: -1.0 到 1.0）
4. 是否被推荐为 TOP3（is_top3: true/false）

请以 JSON 格式输出：
{{
  "brand_analysis": {{
    "brand_mentioned": boolean,
    "rank": number,
    "sentiment": number,
    "is_top3": boolean,
    "mention_context": "提及的上下文"
  }}
}}
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


class PlatformRegion(Enum):
    """AI 平台区域分类"""
    DOMESTIC = "domestic"  # 国内平台
    OVERSEAS = "overseas"  # 海外平台


# AI 平台区域分类映射
PLATFORM_REGION_MAP = {
    # 国内平台
    "deepseek": PlatformRegion.DOMESTIC,
    "deepseekr1": PlatformRegion.DOMESTIC,
    "qwen": PlatformRegion.DOMESTIC,
    "wenxin": PlatformRegion.DOMESTIC,
    "doubao": PlatformRegion.DOMESTIC,
    "kimi": PlatformRegion.DOMESTIC,
    "yuanbao": PlatformRegion.DOMESTIC,
    "spark": PlatformRegion.DOMESTIC,
    "zhipu": PlatformRegion.DOMESTIC,
    # 海外平台
    "chatgpt": PlatformRegion.OVERSEAS,
    "claude": PlatformRegion.OVERSEAS,
    "gemini": PlatformRegion.OVERSEAS,
    "openai": PlatformRegion.OVERSEAS,
    "anthropic": PlatformRegion.OVERSEAS,
    "google": PlatformRegion.OVERSEAS,
}


def get_platform_region(platform_name: str) -> Optional[PlatformRegion]:
    """
    获取 AI 平台所属区域
    
    Args:
        platform_name: 平台名称
        
    Returns:
        PlatformRegion: 平台区域，未知平台返回 None
    """
    return PLATFORM_REGION_MAP.get(platform_name.lower())


def validate_model_region_consistency(selected_models: List[str]) -> tuple[bool, Optional[str]]:
    """
    验证所选模型是否来自同一区域（国内或海外）
    
    Args:
        selected_models: 所选模型名称列表
        
    Returns:
        (is_valid, error_message): 验证结果和错误信息
    """
    if not selected_models:
        return True, None
    
    regions_found = {}
    
    for model_name in selected_models:
        region = get_platform_region(model_name)
        if region is None:
            # 未知区域的平台，跳过检查（兼容性考虑）
            continue
        
        region_key = region.value
        if region_key not in regions_found:
            regions_found[region_key] = []
        regions_found[region_key].append(model_name)
    
    # 检查是否同时存在国内和海外平台
    if PlatformRegion.DOMESTIC.value in regions_found and PlatformRegion.OVERSEAS.value in regions_found:
        domestic_models = regions_found[PlatformRegion.DOMESTIC.value]
        overseas_models = regions_found[PlatformRegion.OVERSEAS.value]
        
        error_msg = (
            f"不能同时选择国内和海外 AI 平台。"
            f"国内平台：{', '.join(domestic_models)}；"
            f"海外平台：{', '.join(overseas_models)}。"
            f"由于网络连接问题，请只选择国内平台或只选择海外平台。"
        )
        return False, error_msg
    
    return True, None


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
