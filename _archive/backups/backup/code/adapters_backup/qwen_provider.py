"""
QwenProvider - 通义千问平台提供者
继承自BaseAIProvider，实现通义千问平台的特定逻辑，重点优化引源提取功能
"""
import time
import requests
import json
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from wechat_backend.ai_adapters.base_provider import BaseAIProvider
from wechat_backend.logging_config import api_logger
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.monitoring.metrics_collector import record_api_call, record_error
from wechat_backend.monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager


class QwenProvider(BaseAIProvider):
    """
    通义千问 AI 平台提供者，实现BaseAIProvider接口
    专门针对 Qwen 的引源格式优化，精准提取参考链接
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "qwen-max",  # 默认使用qwen-max以获得更好的引源支持
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    ):
        """
        初始化 通义千问 提供者

        Args:
            api_key: 通义千问 API 密钥
            model_name: 使用的模型名称，默认为 "qwen-max"
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
        """
        super().__init__(api_key, model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

        # 初始化统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="qwen",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )

        api_logger.info(f"QwenProvider initialized for model: {model_name} with citation extraction capabilities")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """
        向 通义千问 发送问题并返回原生响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            Dict: 包含 通义千问 原生响应的字典
        """
        start_time = time.time()

        try:
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("通义千问 API Key 未设置")

            # 构建请求体
            payload = {
                "model": self.model_name,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            }

            # 使用统一请求封装器发送请求到 通义千问 API
            response = self.request_wrapper.make_ai_request(
                endpoint="",  # Qwen API endpoint is specified in base_url
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
            tokens_used = 0
            usage = {}

            # 从响应中提取实际回答文本
            if response_data and response_data.get("output"):
                output = response_data["output"]
                content = output.get("text", "")
                
                # 提取使用情况信息
                if "usage" in response_data:
                    usage = response_data["usage"]
                    tokens_used = usage.get("total_tokens", 0)

            # 返回成功的响应
            return {
                'content': content,
                'model': response_data.get("model", self.model_name),
                'platform': 'qwen',
                'tokens_used': tokens_used,
                'latency': latency,
                'raw_response': response_data,
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

    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        从 通义千问 原生响应中精准提取引用链接
        专门针对 Qwen 返回的引源格式进行正则解析

        Args:
            raw_response: 通义千问 平台的原生响应

        Returns:
            List[Dict[str, str]]: 包含引用信息的字典列表
        """
        citations = []

        # 提取响应中的文本内容
        response_text = self._get_response_text(raw_response)

        # Qwen 特定的引源格式解析
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

        # 3. Qwen 特有的引源格式（如 [1]、[2] 等数字引用）
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

        # 4. Qwen 可能使用的其他特定格式
        # 如 "参考资料：" 或 "参考文献：" 后跟随的链接
        ref_pattern = r'(?:参考资料|参考文献|引用来源)[:：]\s*(https?://[^\s<>"{}|\\^`\[\]]+)'
        ref_urls = re.findall(ref_pattern, response_text)

        for url in ref_urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append({
                    'url': url,
                    'domain': domain,
                    'title': f'Reference from {domain}',
                    'type': 'reference_link'
                })
            except Exception:
                continue

        # 5. Qwen 特有的引源格式（如 "来源：[链接文本](URL)"）
        source_pattern = r'来源[:：]?\s*\[([^\]]+)\]\((https?://[^\s\)]+)\)'
        source_links = re.findall(source_pattern, response_text)

        for title, url in source_links:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append({
                    'url': url,
                    'domain': domain,
                    'title': title,
                    'type': 'source_link'
                })
            except Exception:
                continue

        # 6. Qwen 可能使用的另一种格式（如 "参考链接：[URL]"）
        link_pattern = r'参考链接[:：]?\s*\[([^\]]+)\]'
        link_matches = re.findall(link_pattern, response_text)
        # 这种格式可能需要进一步处理，因为方括号内的可能是URL或描述

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
        将 通义千问 结果转化为契约中的 source_intelligence 草稿
        映射到节点（Nodes）和链路（Links）结构

        Args:
            raw_response: 通义千问 平台的原生响应

        Returns:
            Dict[str, Any]: 标准化的 source_intelligence 格式
        """
        # 初始化 source_intelligence 结构
        source_intelligence = {
            'nodes': [],
            'links': [],
            'source_pool': [],
            'citation_rank': [],
            'evidence_chain': []
        }

        # 提取响应文本
        response_text = self._get_response_text(raw_response)

        if not response_text:
            return source_intelligence

        # 提取引源信息
        citations = self.extract_citations(raw_response)

        # 构建节点和链路结构
        nodes = []
        links = []

        # 添加品牌节点（假设品牌名为"MainBrand"，实际应用中应从上下文获取）
        brand_name = "MainBrand"  # 实际应用中应从上下文或参数获取
        nodes.append({
            'id': brand_name,
            'name': brand_name,
            'level': 0,  # 品牌层级
            'symbolSize': 60,
            'category': 'brand',
            'value': 100  # 品牌影响力值
        })

        # 为每个引源创建节点
        for i, citation in enumerate(citations):
            source_id = f"qwen_src_{i+1}"
            source_name = citation['domain']

            # 评估域名权威度
            authority = self._assess_domain_authority(citation['domain'])

            # 根据权威度设置节点大小
            size_map = {'High': 40, 'Medium': 30, 'Low': 20}
            symbol_size = size_map.get(authority, 25)

            nodes.append({
                'id': source_id,
                'name': source_name,
                'level': 1,  # 信源层级
                'symbolSize': symbol_size,
                'category': 'source',
                'value': authority,
                'url': citation['url'],
                'source_type': citation['type'],
                'authority_level': authority
            })

            # 创建从品牌到信源的链路
            links.append({
                'source': brand_name,
                'target': source_id,
                'value': 1,  # 引用关系强度
                'citation_url': citation['url'],
                'contribution_score': self._calculate_contribution_score(citation, response_text)
            })

        # 添加到 source_intelligence
        source_intelligence['nodes'] = nodes
        source_intelligence['links'] = links
        source_intelligence['citation_rank'] = [node['id'] for node in nodes if node['category'] == 'source']

        # 构建证据链（如果响应中包含负面内容）
        evidence_chain = self._extract_evidence_chain(response_text, citations)
        source_intelligence['evidence_chain'] = evidence_chain

        return source_intelligence

    def _calculate_contribution_score(self, citation: Dict[str, str], response_text: str) -> float:
        """
        计算引源对响应的贡献分数

        Args:
            citation: 引源信息
            response_text: 响应文本

        Returns:
            float: 贡献分数 (0.0-1.0)
        """
        # 简化的贡献分数计算逻辑
        # 在实际实现中可能需要更复杂的算法

        # 检查引源URL在响应中的提及次数
        url_mentions = response_text.lower().count(citation['url'].lower())

        # 检查域名在响应中的提及次数
        domain_mentions = response_text.lower().count(citation['domain'].lower())

        # 基础分数
        base_score = min(1.0, (url_mentions * 0.5 + domain_mentions * 0.3) / 10.0)

        # 权威度加分
        authority = self._assess_domain_authority(citation['domain'])
        authority_bonus = 0.2 if authority == 'High' else 0.1 if authority == 'Medium' else 0.0

        # 总分
        total_score = min(1.0, base_score + authority_bonus)

        return total_score

    def _assess_domain_authority(self, domain: str) -> str:
        """
        评估域名权威度

        Args:
            domain: 域名

        Returns:
            str: 权威度等级（High/Medium/Low）
        """
        # 定义高权威度域名
        high_authority_domains = [
            'zhihu.com', 'baidu.com', 'baidu.com.cn', 'weibo.com', 'toutiao.com', 
            'qq.com', '163.com', 'sohu.com', 'tmall.com', 'taobao.com', 
            'jd.com', 'pdd.com', 'vip.com', 'gome.com.cn', 'suning.com',
            'weixin.qq.com', 'douyin.com', 'kuaishou.com', 'xigua.com', 
            'bilibili.com', '360.cn', 'sogou.com', 'sm.cn', 'uc.cn',
            'gov.cn', 'edu.cn', 'org.cn', 'mil.cn', 'net.cn', 'com.cn',
            'bloomberg.com', 'reuters.com', 'wsj.com', 'nytimes.com', 
            'ft.com', 'scmp.com', 'wikipedia.org', 'wikimedia.org'
        ]

        # 根据域名评估权威度
        for high_auth_domain in high_authority_domains:
            if high_auth_domain in domain:
                return 'High'

        # 中等权威度域名
        medium_authority_domains = [
            'csdn.net', 'jianshu.com', 'segmentfault.com', 'zcool.com.cn', 
            'ui.cn', 'pmcaff.com', 'medium.com', 'dev.to', 'github.com', 
            'stackoverflow.com', 'reddit.com', 'quora.com'
        ]

        for med_auth_domain in medium_authority_domains:
            if med_auth_domain in domain:
                return 'Medium'

        # 其他域名视为低权威度
        return 'Low'

    def _extract_evidence_chain(self, response_text: str, citations: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        从响应文本中提取证据链

        Args:
            response_text: 响应文本
            citations: 引用列表

        Returns:
            List[Dict[str, str]]: 证据链列表
        """
        evidence_chain = []

        # 简化的证据提取逻辑 - 在实际实现中可能需要更复杂的NLP处理
        # 检查是否包含负面关键词
        negative_keywords = [
            '问题', '缺陷', '不足', '风险', '隐患', '差', '不好', '糟糕',
            '缺点', '劣势', '失败', '错误', '漏洞', '安全问题', '投诉'
        ]

        for keyword in negative_keywords:
            if keyword in response_text:
                # 找到相关的引用链接
                associated_citations = [c for c in citations if keyword in response_text.lower()]
                
                for citation in associated_citations:
                    evidence_chain.append({
                        'negative_fragment': f"提到{keyword}",
                        'associated_url': citation['url'],
                        'source_name': citation['domain'],
                        'risk_level': 'Medium' if keyword in ['问题', '不足', '风险'] else 'High'
                    })

        return evidence_chain

    def health_check(self) -> bool:
        """
        检查 通义千问 提供者的健康状态
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