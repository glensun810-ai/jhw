import re
from urllib.parse import urlparse
from collections import defaultdict
from typing import List, Dict, Any
from snownlp import SnowNLP
from ..logging_config import api_logger

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
        all_sources = defaultdict(lambda: {'count': 0, 'weights': [], 'sentiments': [], 'source_type': 'unknown', 'urls': []})

        for resp in ai_responses:
            if not resp.get('success'):
                continue

            text = resp.get('response', '')

            found_sources = self.extract_sources(text, resp)

            for source in found_sources:
                source_name = source['name']
                all_sources[source_name]['count'] += 1
                all_sources[source_name]['weights'].append(self.match_source_weight(source_name))
                all_sources[source_name]['sentiments'].append(self.analyze_sentiment_from_context(text, source_name))
                if source.get('url'):
                    all_sources[source_name]['urls'].append(source['url'])

        nodes = [{'id': brand_name, 'name': brand_name, 'level': 0, 'symbolSize': 60, 'category': 'brand'}]
        links = []

        for source_name, data in all_sources.items():
            avg_weight = sum(data['weights']) / len(data['weights']) if data['weights'] else 0.3
            avg_sentiment = sum(data['sentiments']) / len(data['sentiments']) if data['sentiments'] else 0.0
            mention_frequency = data['count']

            level = 1 if avg_weight > 0.7 else 2
            symbol_size = 30 + avg_weight * 30

            nodes.append({
                'id': source_name,
                'name': source_name,
                'level': level,
                'symbolSize': symbol_size,
                'category': 'source',
                'value': avg_weight,
                'urls': list(set(data['urls']))
            })

            line_weight = avg_weight * (1 + (mention_frequency - 1) * 0.5)

            links.append({
                'source': brand_name,
                'target': source_name,
                'contribution_score': line_weight,
                'sentiment_bias': avg_sentiment
            })

        return {'nodes': nodes, 'links': links}

async def process_brand_source_intelligence(brand_name: str, ai_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    异步处理信源情报的辅助函数
    """
    processor = SourceIntelligenceProcessor()
    # 由于process方法目前是同步的，我们直接调用它
    # 如果process方法未来变成异步的，这里需要await
    return processor.process(brand_name, ai_responses)
