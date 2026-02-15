"""
DeepSeek R1 适配器 - 支持推理链提取
实现 OpenAI 协议兼容，捕获 DeepSeek R1 的思考过程
"""
import time
import json
import requests
from typing import Dict, Any, Optional, List
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from ..config_manager import Config as PlatformConfigManager


class DeepSeekR1Adapter(AIClient):
    """
    DeepSeek R1 适配器 - 支持推理链提取
    专门针对 DeepSeek R1 的推理能力优化，捕获思考过程（reasoning content）
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-r1",  # 默认使用 R1 模型
        temperature: float = 0.1,  # R1 是推理模型，使用较低温度以获得更一致的推理
        max_tokens: int = 4096,
        base_url: str = "https://api.deepseek.com/v1",
        enable_reasoning_extraction: bool = True  # 启用推理链提取
    ):
        """
        初始化 DeepSeek R1 适配器

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-r1"
            temperature: 温度参数，推理模型使用较低温度以获得一致性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_reasoning_extraction: 是否启用推理链提取
        """
        super().__init__(AIPlatformType.DEEPSEEKR1, model_name, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_reasoning_extraction = enable_reasoning_extraction

        # 初始化统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="deepseek",
            base_url=base_url,
            api_key=api_key,
            timeout=60,  # R1 推理可能需要更长时间
            max_retries=3
        )

        api_logger.info(f"DeepSeekR1Adapter initialized for model: {model_name} with reasoning extraction enabled: {enable_reasoning_extraction}")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示到 DeepSeek R1 并返回标准化响应，包含推理链信息

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含 DeepSeek R1 响应和推理链信息的统一数据结构
        """
        start_time = time.time()

        try:
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 构建请求体，特别为 R1 推理模型优化
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False  # 暂时不使用流式输出，便于推理链提取
            }

            # 如果启用推理链提取，可能需要特殊参数（根据 DeepSeek R1 API 文档）
            if self.enable_reasoning_extraction:
                # 添加可能的推理相关参数（具体参数需根据实际 API 文档调整）
                payload["reasoning_enable"] = True  # 假设 R1 支持推理启用参数
                payload["reasoning_mode"] = "complex"  # 假设 R1 支持推理模式选择

            # 使用统一请求封装器发送请求到 DeepSeek R1 API
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=kwargs.get('timeout', 60)  # R1 推理需要更长时间
            )

            latency = time.time() - start_time

            if response.status_code != 200:
                error_message = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVER_ERROR,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

            response_data = response.json()

            # 提取响应内容
            content = ""
            reasoning_content = ""
            usage = {}
            choices = response_data.get("choices", [])

            if choices:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                
                # 尝试提取推理链内容（DeepSeek R1 特有字段）
                if self.enable_reasoning_extraction:
                    # 根据 DeepSeek R1 API 规范提取推理内容
                    # 可能的字段包括 reasoning, thoughts, thinking_process 等
                    reasoning_content = self._extract_reasoning_content(choice, response_data)

            usage = response_data.get("usage", {})

            # 创建响应对象，包含推理链信息
            ai_response = AIResponse(
                success=True,
                content=content,
                model=response_data.get("model", self.model_name),
                platform=self.platform_type.value,
                tokens_used=usage.get("total_tokens", 0),
                latency=latency,
                metadata={
                    **response_data,
                    "reasoning_content": reasoning_content,  # 推理链内容
                    "has_reasoning": bool(reasoning_content)  # 是否包含推理内容
                }
            )

            # 记录推理链提取信息
            if reasoning_content:
                api_logger.info(f"Extracted reasoning chain from DeepSeek R1 response, length: {len(reasoning_content)} chars")

            return ai_response

        except requests.exceptions.Timeout:
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message="请求超时",
                error_type=AIErrorType.SERVER_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except requests.exceptions.RequestException as e:
            latency = time.time() - start_time
            error_type = self._map_request_exception(e)
            return AIResponse(
                success=False,
                error_message=f"请求异常: {str(e)}",
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except ValueError as e:
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message=str(e),
                error_type=AIErrorType.INVALID_API_KEY,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except Exception as e:
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message=f"未知错误: {str(e)}",
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _extract_reasoning_content(self, choice_data: Dict[str, Any], full_response: Dict[str, Any]) -> str:
        """
        从 DeepSeek R1 响应中提取推理链内容

        Args:
            choice_data: 选择数据
            full_response: 完整响应数据

        Returns:
            str: 推理链内容
        """
        reasoning_content = ""

        # 尝试多种可能的推理内容字段
        # 根据 DeepSeek R1 API 规范，推理内容可能存在于以下字段中：
        
        # 1. 直接在 choice 中的 reasoning 字段
        if "reasoning" in choice_data:
            reasoning_content = choice_data["reasoning"]
        elif "reasoning" in choice_data.get("message", {}):
            reasoning_content = choice_data["message"]["reasoning"]
        
        # 2. 在 delta 中（如果是流式响应）
        elif "delta" in choice_data and "reasoning" in choice_data["delta"]:
            reasoning_content = choice_data["delta"]["reasoning"]
        
        # 3. 在响应的其他可能字段中
        elif "reasoning_content" in full_response:
            reasoning_content = full_response["reasoning_content"]
        elif "thinking_process" in full_response:
            reasoning_content = full_response["thinking_process"]
        elif "thoughts" in full_response:
            reasoning_content = full_response["thoughts"]
        
        # 4. 在 usage 或其他嵌套结构中
        elif "reasoning" in full_response.get("usage", {}):
            reasoning_content = full_response["usage"]["reasoning"]
        
        # 5. 尝试从 content 中分离推理和最终答案（如果推理和答案在同一字段中）
        message_content = choice_data.get("message", {}).get("content", "")
        if message_content and not reasoning_content:
            # 尝试使用模式匹配来分离推理过程和最终答案
            reasoning_content = self._extract_reasoning_from_content(message_content)

        return reasoning_content if reasoning_content else ""

    def _extract_reasoning_from_content(self, content: str) -> str:
        """
        从内容中提取推理过程（如果推理和答案混合在一起）

        Args:
            content: 完整响应内容

        Returns:
            str: 推理过程内容
        """
        # 尝试识别常见的推理标记
        import re
        
        # 模式1: 推理/思考过程标记
        reasoning_patterns = [
            r"(?s)(?:思考过程|推理过程|分析过程|Reasoning|Thinking|Analysis)[:：]?\s*(.*?)(?:\n\s*\n|最终答案|Final Answer|$)",
            r"(?s)\[reasoning\](.*?)\[\/reasoning\]",
            r"(?s)<reasoning>(.*?)<\/reasoning>",
            r"(?s)Let me think through this step by step[:：]?\s*(.*?)(?:\n\s*\n|So,|Therefore,|$)",
            r"(?s)分析[:：]?\s*(.*?)(?:\n\s*\n|结论|Conclusion|$)"
        ]
        
        for pattern in reasoning_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                reasoning_part = match.group(1).strip()
                # 如果推理部分占内容的一半以上，认为是有效的推理
                if len(reasoning_part) > len(content) * 0.3:  # 至少占30%
                    return reasoning_part
        
        # 如果没有找到明确的推理标记，返回空字符串
        return ""

    def analyze_reasoning_chain(self, reasoning_content: str, target_brand: str) -> Dict[str, Any]:
        """
        分析推理链，识别 AI 在得出结论前如何"联想"到竞品

        Args:
            reasoning_content: 推理链内容
            target_brand: 目标品牌名称

        Returns:
            Dict: 包含分析结果的字典
        """
        if not reasoning_content:
            return {
                "competitor_mentions_in_reasoning": [],
                "reasoning_steps": 0,
                "reasoning_depth": "shallow",
                "competitor_connection_strength": 0.0,
                "reasoning_quality_score": 0.0
            }

        import re
        
        # 分析推理步骤数量
        steps_count = len(re.findall(r'(?:step|步骤|第\d+步|分析\d+)', reasoning_content.lower())) or \
                     len(re.findall(r'(?:\d+\.\s|\d+\)\s)', reasoning_content)) or \
                     len(re.findall(r'(?:首先|其次|然后|最后|综上)', reasoning_content))
        
        # 查找竞品提及
        # 这里需要根据实际情况定义竞品列表
        common_competitors = [
            '小米', '华为', '苹果', '三星', 'OPPO', 'VIVO', '荣耀', '一加',
            '魅族', '努比亚', '锤子', '联想', '中兴', '酷派', '金立', '乐视',
            '腾讯', '阿里', '百度', '字节跳动', '美团', '滴滴', '京东', '拼多多'
        ]
        
        competitor_mentions = []
        for competitor in common_competitors:
            if competitor in reasoning_content and competitor != target_brand:
                # 找到竞品在推理中的上下文
                pattern = rf'.{{0,50}}{re.escape(competitor)}.{{0,50}}'
                contexts = re.findall(pattern, reasoning_content)
                competitor_mentions.append({
                    'competitor': competitor,
                    'mention_count': reasoning_content.count(competitor),
                    'contexts': contexts[:3]  # 只取前3个上下文
                })
        
        # 评估推理深度
        reasoning_depth = "shallow"
        if steps_count >= 5:
            reasoning_depth = "deep"
        elif steps_count >= 2:
            reasoning_depth = "moderate"
        
        # 评估竞品连接强度（基于提及频率和上下文相关性）
        connection_strength = min(len(competitor_mentions) * 0.3 + (steps_count * 0.1), 1.0)
        
        # 评估推理质量（基于步骤数、长度和结构化程度）
        quality_score = min((steps_count * 0.2) + (len(reasoning_content) / 1000 * 0.3), 1.0)
        
        return {
            "competitor_mentions_in_reasoning": competitor_mentions,
            "reasoning_steps": steps_count,
            "reasoning_depth": reasoning_depth,
            "competitor_connection_strength": connection_strength,
            "reasoning_quality_score": quality_score,
            "total_reasoning_length": len(reasoning_content)
        }

    def _map_request_exception(self, e: requests.RequestException) -> AIErrorType:
        """将请求异常映射到标准错误类型"""
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                return AIErrorType.INVALID_API_KEY
            elif status_code == 429:
                return AIErrorType.RATE_LIMIT_EXCEEDED
            elif status_code >= 500:
                return AIErrorType.SERVER_ERROR
            elif status_code == 403:
                return AIErrorType.INVALID_API_KEY
        return AIErrorType.UNKNOWN_ERROR

    def health_check(self) -> bool:
        """
        检查 DeepSeek R1 客户端的健康状态

        Returns:
            bool: 客户端是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.send_prompt("请简单介绍一下你自己。")
            return test_response.success
        except Exception:
            return False