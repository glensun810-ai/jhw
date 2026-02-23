"""
BaseAIProvider - AI平台提供者的抽象基类
定义标准化接口，包括发送请求、提取引用和转换为标准格式的方法
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import re
from urllib.parse import urlparse


class BaseAIProvider(ABC):
    """
    AI平台提供者的抽象基类
    定义标准化接口，包括发送请求、提取引用和转换为标准格式的方法
    """
    
    def __init__(self, api_key: str, model_name: str = None):
        """
        初始化AI提供者
        
        Args:
            api_key: API密钥
            model_name: 模型名称
        """
        self.api_key = api_key
        self.model_name = model_name
    
    @abstractmethod
    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """
        发送问题到AI平台
        
        Args:
            prompt: 问题提示词
            
        Returns:
            AI平台的原始响应
        """
        pass
    
    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        从原生响应中提取引用链接
        
        Args:
            raw_response: AI平台的原生响应
            
        Returns:
            List[Dict[str, str]]: 包含引用信息的字典列表
        """
        citations = []
        
        # 提取响应中的URL链接
        response_text = self._get_response_text(raw_response)
        
        # 提取URL链接
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
        
        # 提取Markdown格式的链接
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
        
        # 去重
        seen_urls = set()
        unique_citations = []
        for citation in citations:
            if citation['url'] not in seen_urls:
                seen_urls.add(citation['url'])
                unique_citations.append(citation)
        
        return unique_citations
    
    def _get_response_text(self, raw_response: Dict[str, Any]) -> str:
        """
        从原始响应中提取文本内容
        
        Args:
            raw_response: 原始响应字典
            
        Returns:
            str: 提取的文本内容
        """
        text_parts = []
        
        # 尝试从不同可能的字段中提取内容
        if 'choices' in raw_response:
            for choice in raw_response['choices']:
                if 'message' in choice and 'content' in choice['message']:
                    text_parts.append(choice['message']['content'])
                elif 'text' in choice:
                    text_parts.append(choice['text'])
        elif 'content' in raw_response:
            text_parts.append(raw_response['content'])
        elif 'result' in raw_response:
            text_parts.append(str(raw_response['result']))
        
        return ' '.join(text_parts)
    
    def to_standard_format(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        将结果转化为契约中的exposure_analysis草稿
        
        Args:
            raw_response: AI平台的原生响应
            
        Returns:
            Dict[str, Any]: 标准化的exposure_analysis格式
        """
        # 初始化exposure_analysis结构
        exposure_analysis = {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }
        
        # 提取响应文本
        response_text = self._get_response_text(raw_response)
        
        if not response_text:
            return exposure_analysis
        
        # 提取品牌提及信息（简化实现，实际应用中可能需要更复杂的NLP处理）
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
            '腾讯', '阿里', '百度', '字节跳动', '美团', '滴滴', '京东', '拼多多'
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