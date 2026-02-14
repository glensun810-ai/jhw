import re
from urllib.parse import urlparse
from collections import defaultdict
from typing import List, Dict, Any
from snownlp import SnowNLP
from ..logging_config import api_logger
from .source_aggregator import SourceAggregator
from .impact_calculator import ImpactCalculator

class SourceWeightLibrary:
    """
    信源权重库 (模拟实现)
    """
    def __init__(self):
        self.weights = {
            "wikipedia.org": 0.9,
            "zhihu.com": 0.7,
            "baidu.com": 0.8,
            "36kr.com": 0.75,
            "weibo.com": 0.6,
            "xiaohongshu.com": 0.6,
            "default": 0.3,
            "competitor": 0.1
        }
        self.name_weights = {
            "维基百科": 0.9,
            "知乎": 0.7,
            "百度百科": 0.8,
            "财新网": 0.8,
            "第一财经": 0.78,
        }

    def get_weight(self, source_name: str) -> float:
        if source_name in self.name_weights:
            return self.name_weights[source_name]
        for key, weight in self.weights.items():
            if key in source_name:
                return weight
        return self.weights["default"]

class SourceIntelligenceProcessor:
    """
    信源情报解析引擎 (v2.1 - Robust) - 移除了spacy依赖
    """
    def __init__(self):
        self.weight_library = SourceWeightLibrary()
        self.source_aggregator = SourceAggregator()
        self.impact_calculator = ImpactCalculator()
        # 移除spacy依赖，仅使用基础的文本处理功能

    def extract_sources(self, text: str, ai_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        sources = []
        url_pattern = r'\[[^\]]*\]\((https?:\/\/[^\s\)]+)\)|https?:\/\/[^\s<>"]+'
        found_urls = re.findall(url_pattern, text)

        for match in found_urls:
            url = match[0] if isinstance(match, tuple) and match[0] else match
            if url:
                cleaned_url = re.sub(r'[.,!?:;]$', '', url)
                domain = urlparse(cleaned_url).netloc.replace('www.', '')
                sources.append({'name': domain, 'url': cleaned_url, 'type': 'url'})

        citations = ai_response.get('metadata', {}).get('citations', [])
        for cit in citations:
            sources.append({'name': urlparse(cit).netloc.replace('www.', ''), 'url': cit, 'type': 'citation'})

        # 移除NER部分（不再使用spacy提取实体）
        # 现在只基于URL和引用进行信源提取

        unique_sources = []
        seen_names = set()
        for source in sources:
            if source['name'] not in seen_names:
                unique_sources.append(source)
                seen_names.add(source['name'])

        return unique_sources

    def match_source_weight(self, source_name: str) -> float:
        return self.weight_library.get_weight(source_name)

    def analyze_sentiment_from_context(self, text: str, source_name: str) -> float:
        # 使用简单的方法代替spacy的句子分割
        # 按句号、感叹号、问号分割文本
        sentences = re.split(r'[。！？.!?]', text)

        target_sentence = None
        for sentence in sentences:
            if source_name.lower() in sentence.lower():
                target_sentence = sentence.strip()
                break

        if target_sentence:
            s = SnowNLP(target_sentence)
            return (s.sentiments - 0.5) * 2

        return 0.0

    def process(self, brand_name: str, ai_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理多平台AI文本数据流，生成信源情报图JSON
        """
        # 准备模型响应数据用于聚合
        model_responses = []
        for resp in ai_responses:
            if not resp.get('success'):
                continue

            # 提取模型名称，如果不存在则使用默认值
            model_name = resp.get('aiModel', resp.get('model', 'default'))

            # 提取问题，如果存在的话
            question = resp.get('question', '')

            # 提取响应文本
            text = resp.get('response', '')

            # 提取引用信息，如果存在的话
            citations = resp.get('citations', [])

            model_responses.append({
                'model_name': model_name,
                'ai_response': text,
                'citations': citations,
                'question': question
            })

        # 使用增强的SourceAggregator聚合多模型数据
        aggregation_result = self.source_aggregator.aggregate_multiple_models(model_responses)

        # 提取聚合后的信源池
        source_pool = aggregation_result['source_pool']

        # 为每个信源计算影响力指数
        enhanced_source_pool = []
        for source in source_pool:
            # 估算情感偏向得分（这里使用简化的计算方式）
            # 实际应用中可能需要更复杂的情感分析
            sentiment_score = self._estimate_sentiment_for_source(source, ai_responses)

            # 计算影响力指数
            impact_index = self.impact_calculator.calculate_impact_index(
                citation_count=source['citation_count'],
                model_coverage=source['cross_model_coverage'],
                sentiment_score=sentiment_score,
                domain_authority=source['domain_authority']
            )

            # 添加影响力指数到信源数据
            enhanced_source = source.copy()
            enhanced_source['impact_index'] = impact_index
            enhanced_source_pool.append(enhanced_source)

        # 构建节点和链接数据
        nodes = [{'id': brand_name, 'name': brand_name, 'level': 0, 'symbolSize': 60, 'category': 'brand'}]
        links = []

        for source in enhanced_source_pool:
            # 使用影响力指数作为节点大小的基础
            symbol_size = 30 + (source['impact_index'] / 100.0) * 50  # 映射到30-80的范围

            nodes.append({
                'id': source['id'],
                'name': source['site_name'],
                'level': 1,  # 所有信源都在同一层级
                'symbolSize': symbol_size,
                'category': 'source',
                'value': source['impact_index'],  # 使用影响力指数作为值
                'urls': [source['url']],  # 简化处理，只包含主要URL
                'cross_model_coverage': source['cross_model_coverage'],
                'citation_count': source['citation_count'],
                'impact_index': source['impact_index']
            })

            # 创建从品牌到信源的链接
            links.append({
                'source': brand_name,
                'target': source['id'],
                'contribution_score': source['citation_count'] / max(len(ai_responses), 1),  # 标准化贡献度
                'sentiment_bias': self._estimate_sentiment_for_source(source, ai_responses)  # 估算情感偏向
            })

        return {'nodes': nodes, 'links': links}

    def _estimate_sentiment_for_source(self, source: Dict, ai_responses: List[Dict[str, Any]]) -> float:
        """
        估算特定信源的情感偏向得分

        Args:
            source: 信源信息
            ai_responses: AI响应列表

        Returns:
            情感偏向得分 (-1.0 到 1.0)
        """
        # 简化的实现：基于信源在AI响应中出现的上下文进行情感分析
        total_sentiment = 0.0
        sentiment_count = 0

        source_url = source['url']

        for resp in ai_responses:
            if not resp.get('success'):
                continue

            text = resp.get('response', '')

            # 检查响应中是否包含该信源的URL
            if source_url in text:
                # 使用SnowNLP进行简单的情感分析
                s = SnowNLP(text)
                # 将0-1的情感得分映射到-1到1的范围
                sentiment = (s.sentiments - 0.5) * 2
                total_sentiment += sentiment
                sentiment_count += 1

        # 返回平均情感得分，如果没有找到相关文本则返回中性值
        if sentiment_count > 0:
            return total_sentiment / sentiment_count
        else:
            return 0.0

async def process_brand_source_intelligence(brand_name: str, ai_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    异步处理信源情报的辅助函数
    """
    processor = SourceIntelligenceProcessor()
    # 由于process方法目前是同步的，我们直接调用它
    # 如果process方法未来变成异步的，这里需要await
    return processor.process(brand_name, ai_responses)
