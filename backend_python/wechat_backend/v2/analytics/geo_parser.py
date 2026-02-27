"""
GEO（生成式引擎优化）数据分析器

用于分析 AI 响应中的品牌露出、情感倾向、关键词等。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import Counter


@dataclass
class GEOData:
    """
    GEO 分析数据
    
    Attributes:
        exposure: 品牌是否露出
        sentiment: 情感倾向（positive/neutral/negative）
        keywords: 关键词列表
        confidence: 置信度（0-1）
        details: 详细分析数据
    """
    exposure: bool
    sentiment: str
    keywords: List[str]
    confidence: float = 1.0
    details: Optional[Dict[str, Any]] = None


class GEOAnalyzer:
    """
    GEO 数据分析器
    
    职责：
    1. 判断品牌在 AI 响应中是否露出
    2. 分析情感倾向（正面/中性/负面）
    3. 提取关键词
    4. 竞品分析
    
    使用示例:
        >>> analyzer = GEOAnalyzer()
        >>> result = analyzer.analyze("品牌 A 是一款非常优秀的产品", "品牌 A")
        >>> print(result.exposure)  # True
        >>> print(result.sentiment)  # 'positive'
    """
    
    def __init__(self):
        """初始化 GEO 分析器"""
        # 情感词典（可扩展）
        self.sentiment_dict: Dict[str, List[str]] = {
            'positive': [
                '好', '优秀', '出色', '领先', '创新', '推荐', '值得', '满意',
                '好评', '认可', '信赖', '首选', '知名', '强大', '可靠',
                '卓越', '一流', '顶级', '最佳', '完美', '精彩', '优质'
            ],
            'negative': [
                '差', '糟糕', '落后', '问题', '投诉', '不建议', '失望', '不满',
                '缺陷', '故障', '差评', '质疑', '争议', '风险', '谨慎',
                '避免', '小心', '注意', '缺点', '不足', '遗憾', '失望'
            ],
        }
        
        # 停用词表
        self.stopwords: set = {
            '的', '了', '和', '与', '或', '在', '是', '有', '这', '那',
            '一个', '一些', '这个', '那个', '什么', '怎么', '如何',
            '我们', '你们', '他们', '可以', '可能', '应该', '需要'
        }
        
        # 品牌词缓存
        self.brand_cache: Dict[str, List[str]] = {}
    
    def analyze(
        self,
        response_text: str,
        brand_name: str,
        competitor_brands: Optional[List[str]] = None,
    ) -> GEOData:
        """
        分析 AI 响应内容
        
        Args:
            response_text: AI 响应的文本内容
            brand_name: 主品牌名称
            competitor_brands: 竞品品牌列表（可选）
        
        Returns:
            GEOData: GEO 分析结果
        """
        if not response_text:
            return GEOData(
                exposure=False,
                sentiment='neutral',
                keywords=[],
                confidence=0.0,
            )
        
        # 1. 判断品牌露出
        exposure = self._check_exposure(response_text, brand_name)
        
        # 2. 情感分析
        sentiment = self._analyze_sentiment(response_text)
        
        # 3. 提取关键词
        keywords = self._extract_keywords(response_text)
        
        # 4. 竞品分析（如果有）
        competitor_analysis = None
        if competitor_brands:
            competitor_analysis = self._analyze_competitors(
                response_text,
                competitor_brands,
            )
        
        # 5. 计算置信度
        confidence = self._calculate_confidence(response_text)
        
        return GEOData(
            exposure=exposure,
            sentiment=sentiment,
            keywords=keywords,
            confidence=confidence,
            details={
                'competitor_analysis': competitor_analysis,
                'text_length': len(response_text),
            },
        )
    
    def _check_exposure(self, text: str, brand_name: str) -> bool:
        """
        检查品牌是否露出
        
        Args:
            text: 文本内容
            brand_name: 品牌名称
        
        Returns:
            bool: 是否露出
        """
        if not text or not brand_name:
            return False
        
        # 简单的字符串匹配（后续可升级为 NLP）
        return brand_name in text
    
    def _analyze_sentiment(self, text: str) -> str:
        """
        分析情感倾向
        
        Args:
            text: 文本内容
        
        Returns:
            str: 'positive', 'neutral', 或 'negative'
        """
        if not text:
            return 'neutral'
        
        text_lower = text.lower()
        
        # 统计正面/负面词出现次数
        positive_count = sum(
            1 for word in self.sentiment_dict['positive']
            if word in text_lower
        )
        negative_count = sum(
            1 for word in self.sentiment_dict['negative']
            if word in text_lower
        )
        
        # 判断情感倾向
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 文本内容
            top_n: 返回的关键词数量
        
        Returns:
            List[str]: 关键词列表
        """
        if not text:
            return []
        
        # 提取中文和英文单词
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', text)
        
        # 过滤停用词和单字符
        filtered_words = [
            w for w in words
            if w not in self.stopwords and len(w) > 1
        ]
        
        # 统计词频
        word_counts = Counter(filtered_words)
        
        # 返回 top_n 个关键词
        return [word for word, _ in word_counts.most_common(top_n)]
    
    def _analyze_competitors(
        self,
        text: str,
        competitors: List[str],
    ) -> Dict[str, bool]:
        """
        分析竞品露出情况
        
        Args:
            text: 文本内容
            competitors: 竞品品牌列表
        
        Returns:
            Dict[str, bool]: 竞品露出情况
        """
        return {
            comp: comp in text
            for comp in competitors
        }
    
    def _calculate_confidence(self, text: str) -> float:
        """
        计算分析置信度
        
        Args:
            text: 文本内容
        
        Returns:
            float: 置信度（0-1）
        """
        if not text:
            return 0.0
        
        # 基于文本长度计算置信度
        length = len(text)
        if length > 1000:
            return 1.0
        elif length > 500:
            return 0.8
        elif length > 100:
            return 0.5
        else:
            return 0.3
