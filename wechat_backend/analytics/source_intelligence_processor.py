import re
import spacy
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
    信源情报解析引擎 (v2.1 - Robust)
    """
    def __init__(self):
        self.weight_library = SourceWeightLibrary()
        self.nlp = None
        try:
            self.nlp = spacy.load("zh_core_web_sm")
            api_logger.info("spaCy model 'zh_core_web_sm' loaded successfully.")
        except OSError:
            api_logger.warning("spaCy Chinese model 'zh_core_web_sm' not found. NER features will be disabled.")
            api_logger.warning("Please run: python -m spacy download zh_core_web_sm")

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

        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["ORG", "WORK_OF_ART"]:
                    if not any(ent.text in s['name'] for s in sources):
                        sources.append({'name': ent.text, 'url': None, 'type': 'ner'})
        
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
        if not self.nlp:
            return 0.5 

        doc = self.nlp(text)
        target_sentence = None
        for sent in doc.sents:
            if source_name.lower() in sent.text.lower():
                target_sentence = sent.text
                break
        
        if target_sentence:
            s = SnowNLP(target_sentence)
            return (s.sentiments - 0.5) * 2
        
        return 0.0

    def process(self, brand_name: str, ai_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理多平台AI文本数据流，生成信源情报图JSON
        """
        # 守护条款：如果NLP模型未加载，则优雅降级
        if not self.nlp:
            api_logger.warning("Skipping SourceIntelligenceProcessor due to missing spaCy model.")
            return {'nodes': [{'id': brand_name, 'name': brand_name, 'level': 0, 'symbolSize': 60, 'category': 'brand'}], 'links': []}

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
                if source['url']:
                    all_sources[source_name]['urls'].append(source['url'])

        nodes = [{'id': brand_name, 'name': brand_name, 'level': 0, 'symbolSize': 60, 'category': 'brand'}]
        links = []

        for source_name, data in all_sources.items():
            avg_weight = sum(data['weights']) / len(data['weights'])
            avg_sentiment = sum(data['sentiments']) / len(data['sentiments'])
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
