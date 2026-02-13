"""
BaseAIProvider 抽象类 - AI平台提供者的基类
定义标准化接口用于不同AI平台的适配
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import re
from urllib.parse import urlparse
from .base_adapter import AIResponse


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
    def ask_question(self, prompt: str) -> AIResponse:
        """
        发送问题到AI平台
        
        Args:
            prompt: 问题提示词
            
        Returns:
            AIResponse: AI平台的响应
        """
        pass
    
    def extract_citations(self, response: str) -> List[Dict[str, str]]:
        """
        从原生响应中提取引用链接
        
        Args:
            response: AI平台的原始响应文本
            
        Returns:
            List[Dict[str, str]]: 包含引用信息的字典列表
        """
        citations = []
        
        # 提取URL链接
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response)
        
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
        markdown_links = re.findall(markdown_pattern, response)
        
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
        
        # 提取引用标记（如 [1], [2] 等）
        citation_pattern = r'\[(\d+)\]'
        citation_numbers = re.findall(citation_pattern, response)
        
        for num in citation_numbers:
            # 在响应中查找引用标记前后的上下文
            pattern = rf'\[{num}\][\s\S]*?((?:https?://[^\s<>"{{}}|\\\\^`\\[\\]]+)|[^.\n]*?\.?)'
            matches = re.findall(pattern, response)
            for match in matches:
                if match.startswith('http'):
                    try:
                        parsed = urlparse(match)
                        domain = parsed.netloc
                        citations.append({
                            'url': match,
                            'domain': domain,
                            'title': f'Citation [{num}]',
                            'type': 'citation_reference'
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
    
    def to_standard_format(self, response: AIResponse, brand_name: str = None) -> Dict[str, Any]:
        """
        将结果转化为契约中的exposure_analysis草稿
        
        Args:
            response: AIResponse对象
            brand_name: 品牌名称（可选）
            
        Returns:
            Dict[str, Any]: 标准化的exposure_analysis格式
        """
        # 初始化exposure_analysis结构
        exposure_analysis = {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }
        
        if not response.success or not response.content:
            return exposure_analysis
        
        content = response.content
        
        # 提取品牌提及和排名信息
        brand_mentions = self._extract_brand_mentions(content, brand_name)
        
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
    
    def _extract_brand_mentions(self, content: str, main_brand: str = None) -> Dict[str, Any]:
        """
        从内容中提取品牌提及信息
        
        Args:
            content: AI响应内容
            main_brand: 主要品牌名称
            
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
        
        # 如果提供了主要品牌，添加到品牌列表中
        if main_brand and main_brand not in known_brands:
            known_brands.insert(0, main_brand)
        
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
                # 简化的感情分數（实际实现中需要情感分析）
                sentiment_scores[brand] = 50.0 + (count * 2)  # 埪设提及次数越多感情越好
        
        # 识别未在已知品牌列表中的品牌提及
        all_mentions = set()
        for brand in known_brands:
            all_mentions.update(re.findall(re.escape(brand), content))
        
        # 提取可能的竞争品牌（未在已知列表中的品牌提及）
        # 這里簡化處理，實際應用中需要更複雜的實體識別
        unlisted_competitors = []
        
        return {
            'mentioned_brands': mentioned_brands,
            'word_counts': word_counts,
            'sov_shares': sov_shares,
            'sentiment_scores': sentiment_scores,
            'unlisted_competitors': unlisted_competitors
        }