"""
DeepSeekProvider - DeepSeek平台提供者
继承自BaseAIProvider，实现DeepSeek平台的特定逻辑
"""
import time
import requests
import json
from typing import Dict, Any, List
from urllib.parse import urlparse
import re
from .base_provider import BaseAIProvider
from ..logging_config import api_logger
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error


class DeepSeekProvider(BaseAIProvider):
    """
    DeepSeek AI 平台提供者，实现BaseAIProvider接口
    专门针对 DeepSeek R1 的推理能力优化，捕获思考过程（reasoning content）
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.deepseek.com/v1",
        enable_reasoning_extraction: bool = True  # 启用推理链提取
    ):
        """
        初始化 DeepSeek 提供者

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-chat"
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示深度推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_reasoning_extraction: 是否启用推理链提取
        """
        super().__init__(api_key, model_name)
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_reasoning_extraction = enable_reasoning_extraction  # 存储推理提取开关

        # 初始化统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="deepseek",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )

        api_logger.info(f"DeepSeekProvider initialized for model: {model_name} with reasoning extraction enabled: {enable_reasoning_extraction}")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """
        向 DeepSeek 发送问题并返回原生响应，包含推理链信息
        使用环境变量中的 DEEPSEEK_API_KEY，符合 OpenAI 协议格式

        Args:
            prompt: 用户输入的提示文本

        Returns:
            Dict: 包含 DeepSeek 原生响应和推理链信息的字典
        """
        start_time = time.time()

        try:
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 根据模式构建不同的请求体，符合 OpenAI 协议格式
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 深度推理模式 (reasoner): 适用于需要深度分析和推理的问题
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

            # 如果启用推理链提取，可能需要特殊参数（根据 DeepSeek V3/R1 API 文档）
            if self.enable_reasoning_extraction:
                # 根据 DeepSeek API 文档，可能需要添加推理相关参数
                # 注意：实际参数需要根据 DeepSeek V3/R1 API 文档进行调整
                pass  # DeepSeek V3 可能不需要特殊参数，或使用其他参数名

            # 使用统一请求封装器发送请求到 DeepSeek API
            # DeepSeek 兼容 OpenAI 格式，使用标准的 /chat/completions 端点
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30  # 设置请求超时时间为30秒
            )

            # 计算请求延迟
            latency = time.time() - start_time

            if response.status_code != 200:
                error_message = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                api_logger.error(error_message)
                return {
                    'error': error_message,
                    'status_code': response.status_code,
                    'success': False,
                    'latency': latency
                }

            # 解析响应数据
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

                # 尝试提取推理链内容（如果 DeepSeek R1 支持）
                if self.enable_reasoning_extraction:
                    # 根据 DeepSeek R1 API 规范提取推理内容
                    # 可能的字段包括 reasoning, thoughts, thinking_process 等
                    reasoning_content = self._extract_reasoning_content(choice, response_data)

            usage = response_data.get("usage", {})

            # 返回成功的响应，包含推理链信息
            return {
                'content': content,
                'model': response_data.get("model", self.model_name),
                'platform': 'deepseek',
                'tokens_used': usage.get("total_tokens", 0),
                'latency': latency,
                'raw_response': response_data,
                'reasoning_content': reasoning_content,  # 推理链内容
                'has_reasoning': bool(reasoning_content),  # 是否包含推理内容
                'success': True
            }

        except requests.exceptions.Timeout:
            # 处理请求超时异常
            latency = time.time() - start_time
            error_msg = "请求超时"
            api_logger.error(error_msg)
            return {
                'error': error_msg,
                'success': False,
                'latency': latency
            }

        except requests.exceptions.RequestException as e:
            # 处理其他请求相关异常
            latency = time.time() - start_time
            error_msg = f"请求异常: {str(e)}"
            api_logger.error(error_msg)
            return {
                'error': error_msg,
                'success': False,
                'latency': latency
            }

        except ValueError as e:
            # 处理 API Key 验证等值错误
            latency = time.time() - start_time
            api_logger.error(f"Value error: {str(e)}")
            return {
                'error': str(e),
                'success': False,
                'latency': latency
            }

        except Exception as e:
            # 处理其他未预期的异常
            latency = time.time() - start_time
            error_msg = f"未知错误: {str(e)}"
            api_logger.error(error_msg)
            return {
                'error': error_msg,
                'success': False,
                'latency': latency
            }

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
            r"(?s)让我逐步分析[:：]?\s*(.*?)(?:\n\s*\n|所以|Therefore|Thus|$)",
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

    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        从 DeepSeek 原生响应中提取引用链接
        专门针对 DeepSeek 返回的引用格式进行正则解析

        Args:
            raw_response: DeepSeek 平台的原生响应

        Returns:
            List[Dict[str, str]]: 包含引用信息的字典列表
        """
        citations = []

        # 提取响应中的文本内容
        response_text = self._get_response_text(raw_response)

        # DeepSeek 特定的引用格式解析
        # 1. 标准 URL 格式
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response_text)

        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append({
                    'url': url,
                    'domain': domain,
                    'title': f'Link to {domain}',
                    'type': 'external_link'
                })
            except Exception:
                # 如果URL解析失败，跳过该URL
                continue

        # 2. Markdown 格式链接 [text](url)
        markdown_pattern = r'\[([^\]]+)\]\((https?://[^\s\)]+)\)'
        markdown_links = re.findall(markdown_pattern, response_text)

        for title, url in markdown_links:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append({
                    'url': url,
                    'domain': domain,
                    'title': title,
                    'type': 'markdown_link'
                })
            except Exception:
                continue

        # 3. DeepSeek 特有的引用格式（如 [1]、[2] 等数字引用）
        # 这些可能在响应中以 [1]: https://example.com 格式出现
        numbered_ref_pattern = r'\[(\d+)\]:\s*(https?://[^\s]+)'
        numbered_refs = re.findall(numbered_ref_pattern, response_text)

        for ref_num, url in numbered_refs:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append({
                    'url': url,
                    'domain': domain,
                    'title': f'Reference [{ref_num}]',
                    'type': 'numbered_reference'
                })
            except Exception:
                continue

        # 4. DeepSeek 可能使用的其他特定格式
        # 如 "参考来源: https://example.com" 或 "资料来源：[链接](https://example.com)"
        source_pattern = r'(?:参考来源|资料来源|信息来源)[:：]\s*(https?://[^\s<>"{}|\\^`\[\]]+)'
        source_urls = re.findall(source_pattern, response_text)

        for url in source_urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append({
                    'url': url,
                    'domain': domain,
                    'title': f'Source from {domain}',
                    'type': 'source_reference'
                })
            except Exception:
                continue

        # 去重处理
        seen_urls = set()
        unique_citations = []
        for citation in citations:
            if citation['url'] not in seen_urls:
                seen_urls.add(citation['url'])
                unique_citations.append(citation)

        return unique_citations

    def to_standard_format(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 DeepSeek 结果转化为契约中的 exposure_analysis 草稿
        确保输出数据结构（排名、篇幅、信源）完全符合契约定义

        Args:
            raw_response: DeepSeek 平台的原生响应

        Returns:
            Dict[str, Any]: 标准化的 exposure_analysis 格式
        """
        # 初始化 exposure_analysis 结构
        exposure_analysis = {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }

        # 提取响应文本
        response_text = self._get_response_text(raw_response)

        if not response_text:
            return exposure_analysis

        # 提取品牌提及信息
        brand_mentions = self._extract_brand_mentions(response_text)

        # 构建排名列表
        exposure_analysis['ranking_list'] = brand_mentions['mentioned_brands']

        # 构建品牌详情
        for brand in brand_mentions['mentioned_brands']:
            exposure_analysis['brand_details'][brand] = {
                'rank': brand_mentions['mentioned_brands'].index(brand) + 1,
                'word_count': brand_mentions['word_counts'].get(brand, 0),
                'sov_share': brand_mentions['sov_shares'].get(brand, 0.0),
                'sentiment_score': brand_mentions['sentiment_scores'].get(brand, 50.0)
            }

        # 提取未列出的竞争品牌
        exposure_analysis['unlisted_competitors'] = brand_mentions['unlisted_competitors']

        return exposure_analysis

    def _extract_brand_mentions(self, content: str) -> Dict[str, Any]:
        """
        从内容中提取品牌提及信息

        Args:
            content: AI响应内容

        Returns:
            Dict: 包含品牌提及信息的字典
        """
        # 简化的品牌提取逻辑 - 在实际实现中可能需要更复杂的NLP处理
        import re

        # 假设我们有一些常见的竞争品牌名称
        known_brands = [
            '小米', '华为', '苹果', '三星', 'OPPO', 'VIVO', '荣耀', '一加',
            '魅族', '努比亚', '锤子', '联想', '中兴', '酷派', '金立', '乐视',
            '腾讯', '阿里', '百度', '字节跳动', '美团', '滴滴', '京东', '拼多多',
            '德施曼', '凯迪仕', '云米', '鹿客', 'TCL', '长虹', '海信', '创维'
        ]

        mentioned_brands = []
        word_counts = {}
        sov_shares = {}
        sentiment_scores = {}

        # 统计每个品牌的提及次数
        for brand in known_brands:
            count = len(re.findall(re.escape(brand), content))
            if count > 0 and brand not in mentioned_brands:
                mentioned_brands.append(brand)
                word_counts[brand] = count
                # 简化的SOV计算（实际实现中需要更复杂的逻辑）
                sov_shares[brand] = count / max(1, len(mentioned_brands))
                # 简化的感情分数（实际实现中需要情感分析）
                sentiment_scores[brand] = 50.0 + (count * 2)  # 假设提及次数越多感情越好

        # 识别可能的竞争品牌（未在已知列表中的品牌提及）
        # 这里简化处理，实际应用中需要更复杂的实体识别
        unlisted_competitors = []

        return {
            'mentioned_brands': mentioned_brands,
            'word_counts': word_counts,
            'sov_shares': sov_shares,
            'sentiment_scores': sentiment_scores,
            'unlisted_competitors': unlisted_competitors
        }

    def health_check(self) -> bool:
        """
        检查 DeepSeek 提供者的健康状态
        通过发送一个简单的测试请求来验证连接

        Returns:
            bool: 提供者是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.ask_question("你好，请回复'正常'。")
            return test_response.get('success', False)
        except Exception:
            return False