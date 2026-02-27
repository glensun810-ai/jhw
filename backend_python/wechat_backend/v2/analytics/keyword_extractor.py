"""
关键词提取器

功能：
- 从 AI 回答中提取高频关键词
- 生成关键词云数据
- 按品牌分组提取关键词
- 关键词情感关联分析

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict, Counter
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import AnalyticsDataError


class KeywordExtractor:
    """
    关键词提取器

    从 AI 回答中提取和分析关键词
    """

    # 中文停用词（部分）
    CHINESE_STOPWORDS = {
        '的', '了', '和', '是', '在', '就', '都', '而', '及', '与', '着',
        '就', '这', '那', '你', '我', '他', '她', '它', '们', '这个', '那个',
        '一个', '一些', '什么', '怎么', '如何', '为什么', '是否', '可以',
        '应该', '必须', '需要', '能够', '可能', '也许', '大概', '几乎',
        '非常', '特别', '十分', '很', '太', '最', '更', '越', '越来',
        '因为', '所以', '但是', '然而', '不过', '尽管', '即使', '如果',
        '假如', '要是', '只要', '只有', '除非', '否则', '而且', '并且',
        '或者', '及其', '以及', '还有', '此外', '另外', '同时', '同样',
        '比如', '例如', '像', '如', '至于', '关于', '对于', '对', '向',
        '往', '朝', '到', '从', '自', '由', '于', '在', '当', '让', '叫',
        '被', '给', '把', '将', '同', '跟', '和', '与', '及', '或', '等',
        '等等', '一个', '一些', '所有', '每个', '各', '每', '某', '本',
        '该', '此', '此', '这', '那', '这些', '那些', '这样', '那样',
        '怎么', '怎样', '如何', '什么', '谁', '哪', '哪里', '哪儿',
        '时候', '时间', '地方', '地方', '方面', '问题', '情况', '进行',
        '开始', '继续', '结束', '完成', '已经', '曾经', '正在', '将要',
        '马上', '立刻', '顿时', '终于', '渐渐', '逐渐', '慢慢', '快快',
    }

    # 品牌相关关键词模式
    BRAND_KEYWORD_PATTERNS = [
        r'品牌', r'牌子', r'商标', r'知名度', r'美誉度',
        r'质量', '品质', r'产品', r'服务', r'体验',
        r'价格', r'价值', r'性价比', r'高端', r'低端',
        r'推荐', r'购买', r'选择', r'偏好', r'首选',
        r'领先', r'一流', r'知名', r'著名', r'优秀',
        r'创新', r'科技', r'设计', r'时尚', r'潮流',
        r'专业', r'可靠', r'信任', r'口碑', r'影响',
    ]

    def __init__(self, min_word_length: int = 2, max_keywords: int = 50):
        """
        初始化关键词提取器

        参数:
            min_word_length: 最小词长
            max_keywords: 最大关键词数量
        """
        self.min_word_length = min_word_length
        self.max_keywords = max_keywords
        self.logger = api_logger
    
    def _validate_results(self, results: Any, method_name: str) -> None:
        """
        验证输入参数
        
        参数:
            results: 诊断结果列表
            method_name: 调用方法名（用于错误信息）
            
        raises:
            AnalyticsDataError: 参数验证失败
        """
        if not isinstance(results, list):
            raise AnalyticsDataError(
                f"{method_name}: results 必须是列表类型",
                field='results',
                value=type(results).__name__,
                expected_type='list'
            )
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                raise AnalyticsDataError(
                    f"{method_name}: results[{i}] 必须是字典类型",
                    field=f'results[{i}]',
                    value=type(result).__name__,
                    expected_type='dict'
                )
    
    def extract(
        self,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        从诊断结果中提取关键词

        参数:
            results: 诊断结果列表
            top_n: 返回前 N 个关键词（默认全部）

        返回:
            关键词列表，每个包含 word, count, sentiment

        示例:
            >>> extractor = KeywordExtractor()
            >>> results = [
            ...     {'geo_data': {'response_text': 'Nike 是一个优秀的品牌，质量很好'}},
            ...     {'geo_data': {'response_text': 'Adidas 设计时尚，深受年轻人喜爱'}},
            ... ]
            >>> extractor.extract(results)
            [
                {'word': '品牌', 'count': 1, 'sentiment': 'positive'},
                {'word': '质量', 'count': 1, 'sentiment': 'positive'},
                {'word': '设计', 'count': 1, 'sentiment': 'positive'},
                ...
            ]

        raises:
            AnalyticsDataError: 输入参数验证失败
        """
        # 【P1-002 修复】添加输入参数验证
        self._validate_results(results, 'extract')

        if not results:
            return []

        # 【P2-001 修复】拆分长函数：收集文本
        all_texts = self._collect_texts(results)
        if not all_texts:
            return []

        # 【P2-001 修复】拆分长函数：分析词汇
        word_counts, word_sentiments = self._analyze_words(all_texts)

        # 【P2-001 修复】拆分长函数：构建关键词列表
        keywords = self._build_keywords(word_counts, word_sentiments, top_n)

        # 【P3-002 修复】结构化日志
        self.logger.info("keywords_extracted", extra={
            'event': 'keywords_extracted',
            'keyword_count': len(keywords),
            'top_n': top_n or self.max_keywords,
        })
        return keywords

    def _collect_texts(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        从诊断结果中收集所有文本

        参数:
            results: 诊断结果列表

        返回:
            文本列表
        """
        texts = []
        for result in results:
            response_text = self._extract_response_text(result)
            if response_text:
                texts.append(response_text)
        return texts

    def _analyze_words(
        self,
        texts: List[str]
    ) -> Tuple[Counter, Dict[str, List[float]]]:
        """
        分词并统计词频和情感

        参数:
            texts: 文本列表

        返回:
            word_counts: 词频统计
            word_sentiments: 词汇情感列表
        """
        word_counts = Counter()
        word_sentiments = defaultdict(list)

        for text in texts:
            words = self._tokenize(text)
            sentiment = self._get_text_sentiment(text)

            for word in words:
                word_counts[word] += 1
                word_sentiments[word].append(sentiment)

        return word_counts, word_sentiments

    def _build_keywords(
        self,
        word_counts: Counter,
        word_sentiments: Dict[str, List[float]],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        构建关键词列表

        参数:
            word_counts: 词频统计
            word_sentiments: 词汇情感列表
            top_n: 返回前 N 个关键词

        返回:
            关键词列表
        """
        keywords = []
        max_count = top_n or self.max_keywords

        for word, count in word_counts.most_common(max_count):
            sentiments = word_sentiments[word]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            keywords.append({
                'word': word,
                'count': count,
                'sentiment': round(avg_sentiment, 3),
                'sentiment_label': self._sentiment_to_label(avg_sentiment)
            })

        return keywords
    
    def extract_by_brand(
        self,
        results: List[Dict[str, Any]],
        brand_name: str,
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        提取特定品牌的关键词
        
        参数:
            results: 诊断结果列表
            brand_name: 品牌名称
            top_n: 返回前 N 个关键词
            
        返回:
            品牌关键词列表
        """
        brand_results = [r for r in results if r.get('brand') == brand_name]
        return self.extract(brand_results, top_n)
    
    def generate_word_cloud_data(
        self,
        results: List[Dict[str, Any]],
        top_n: int = 100
    ) -> List[Dict[str, Any]]:
        """
        生成词云数据
        
        参数:
            results: 诊断结果列表
            top_n: 返回前 N 个关键词
            
        返回:
            词云数据，包含 word, size, color
        """
        keywords = self.extract(results, top_n)
        
        if not keywords:
            return []
        
        # 计算最大最小值用于归一化
        max_count = max(kw['count'] for kw in keywords) if keywords else 1
        min_count = min(kw['count'] for kw in keywords) if keywords else 1
        
        word_cloud_data = []
        for kw in keywords:
            # 归一化大小（12-48 像素）
            size_range = 36
            if max_count == min_count:
                normalized = 0.5
            else:
                normalized = (kw['count'] - min_count) / (max_count - min_count)
            size = int(12 + normalized * size_range)
            
            # 根据情感设置颜色
            color = self._sentiment_to_color(kw['sentiment'])
            
            word_cloud_data.append({
                'word': kw['word'],
                'size': size,
                'color': color,
                'count': kw['count'],
                'sentiment': kw['sentiment']
            })
        
        return word_cloud_data
    
    def extract_keywords_with_context(
        self,
        results: List[Dict[str, Any]],
        keyword: str
    ) -> List[Dict[str, Any]]:
        """
        提取包含特定关键词的上下文
        
        参数:
            results: 诊断结果列表
            keyword: 目标关键词
            
        返回:
            包含关键词的上下文片段
        """
        contexts = []
        
        for result in results:
            response_text = self._extract_response_text(result)
            if not response_text or keyword not in response_text:
                continue
            
            # 提取包含关键词的句子
            sentences = self._split_sentences(response_text)
            for sentence in sentences:
                if keyword in sentence:
                    contexts.append({
                        'text': sentence.strip(),
                        'brand': result.get('brand', 'unknown'),
                        'model': result.get('model', 'unknown'),
                        'sentiment': result.get('geo_data', {}).get('sentiment', 0.0)
                    })
        
        return contexts
    
    def get_brand_keyword_comparison(
        self,
        results: List[Dict[str, Any]],
        brands: List[str]
    ) -> Dict[str, Any]:
        """
        比较多个品牌的关键词
        
        参数:
            results: 诊断结果列表
            brands: 品牌列表
            
        返回:
            品牌关键词对比数据
        """
        comparison = {}
        
        for brand in brands:
            keywords = self.extract_by_brand(results, brand, top_n=20)
            comparison[brand] = {
                'keywords': keywords,
                'top_keywords': [kw['word'] for kw in keywords[:5]],
                'total_unique_keywords': len(keywords)
            }
        
        # 找出共同关键词
        all_brand_keywords = [set(kw['word'] for kw in comparison[brand]['keywords']) 
                             for brand in brands]
        if all_brand_keywords:
            common_keywords = set.intersection(*all_brand_keywords)
            comparison['common_keywords'] = list(common_keywords)
        
        return comparison
    
    def _extract_response_text(self, result: Dict[str, Any]) -> str:
        """从结果中提取响应文本"""
        # 尝试从多个位置获取文本
        geo_data = result.get('geo_data', {})
        
        # 优先使用 response_text
        if 'response_text' in geo_data:
            return geo_data['response_text']
        
        # 尝试从 content 获取
        if 'content' in geo_data:
            return geo_data['content']
        
        # 尝试从原始响应获取
        response = result.get('response', {})
        if isinstance(response, dict):
            return response.get('content', '') or response.get('text', '')
        
        return ''
    
    def _tokenize(self, text: str) -> List[str]:
        """
        中文分词（简化版）
        
        使用基于字符的分词方法，实际生产环境应使用 jieba 等专业分词库
        """
        # 提取中文词汇（2-4 字词）
        pattern = r'[\u4e00-\u9fa5]{' + str(self.min_word_length) + r',4}'
        words = re.findall(pattern, text)
        
        # 提取英文词汇
        en_pattern = r'\b[a-zA-Z]{' + str(self.min_word_length) + r',}\b'
        en_words = re.findall(en_pattern, text)
        
        all_words = words + en_words
        
        # 过滤停用词
        filtered_words = [
            word for word in all_words
            if word.lower() not in self.CHINESE_STOPWORDS
        ]
        
        return filtered_words
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 中文句子分割
        sentences = re.split(r'[。！？.!?]', text)
        return [s for s in sentences if s.strip()]
    
    def _get_text_sentiment(self, text: str) -> float:
        """
        简单的情感分析（基于关键词）
        
        实际生产环境应使用专业的情感分析模型
        """
        positive_words = {'优秀', '好', '棒', '出色', '领先', '一流', '推荐', '首选', '信任', '可靠'}
        negative_words = {'差', '不好', '糟糕', '落后', '避免', '失望', '问题', '缺陷', '不足'}
        
        words = self._tokenize(text)
        
        positive_count = sum(1 for w in words if w in positive_words)
        negative_count = sum(1 for w in words if w in negative_words)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        # 计算情感得分（-1 到 1）
        score = (positive_count - negative_count) / total
        return score
    
    def _sentiment_to_label(self, sentiment: float) -> str:
        """将情感得分转换为标签"""
        if sentiment > 0.3:
            return 'positive'
        elif sentiment < -0.3:
            return 'negative'
        else:
            return 'neutral'
    
    def _sentiment_to_color(self, sentiment: float) -> str:
        """将情感得分转换为颜色"""
        if sentiment > 0.3:
            return '#28a745'  # 绿色（正面）
        elif sentiment < -0.3:
            return '#dc3545'  # 红色（负面）
        else:
            return '#6c757d'  # 灰色（中性）
