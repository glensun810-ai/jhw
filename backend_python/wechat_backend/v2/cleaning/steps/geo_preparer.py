"""
GEO Data Preparation Step

Prepares基础 data for subsequent GEO (Generative Engine Optimization) analysis.
"""

import re
from typing import Dict, Any, List
from collections import Counter

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.models.cleaned_data import GeoPreparedData


class GeoPreparerStep(CleaningStep):
    """
    GEO data preparation step

    Prepares基础 data for subsequent GEO analysis,
    including text feature extraction, brand position recording, etc.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('geo_preparer', config)

        # Default configuration
        self.config.setdefault('detect_language', True)
        self.config.setdefault('extract_urls', True)
        self.config.setdefault('extract_numbers', True)
        self.config.setdefault('split_sentences', True)
        self.config.setdefault('max_sentences', 100)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Execute GEO data preparation"""

        # 1. Get text and entity information
        text = context.response_content
        if not text:
            context.add_warning("Empty text for GEO preparation")
            return context

        # 2. Get brand positions from entity recognition step
        entity_result = context.intermediate_data.get('entity_recognizer', {})
        entities = entity_result.get('entities', [])

        # 3. Extract text features
        geo_data = GeoPreparedData(
            text_length=len(text),
            sentence_count=self._count_sentences(text) if self.config['split_sentences'] else 1,
            has_brand_mention=False,
            brand_positions=[],
            competitor_mentions={},
            language=self._detect_language(text) if self.config['detect_language'] else 'zh',
            contains_numbers=self._contains_numbers(text) if self.config['extract_numbers'] else False,
            contains_urls=self._contains_urls(text) if self.config['extract_urls'] else False,
        )

        # 4. Record brand positions
        for entity in entities:
            if entity['entity_type'] == 'brand':
                geo_data.has_brand_mention = True
                geo_data.brand_positions.append(entity['start_pos'])
            elif entity['entity_type'] == 'competitor':
                comp_name = entity['entity_name']
                geo_data.competitor_mentions[comp_name] = \
                    geo_data.competitor_mentions.get(comp_name, 0) + 1

        # 5. Save results
        result = {
            'geo_data': {
                'text_length': geo_data.text_length,
                'sentence_count': geo_data.sentence_count,
                'has_brand_mention': geo_data.has_brand_mention,
                'brand_positions': geo_data.brand_positions,
                'competitor_mentions': geo_data.competitor_mentions,
                'language': geo_data.language,
                'contains_numbers': geo_data.contains_numbers,
                'contains_urls': geo_data.contains_urls,
            }
        }

        self.save_step_result(context, result)

        return context

    def _count_sentences(self, text: str) -> int:
        """Count sentence count"""
        # Simple split by period, exclamation, question mark
        sentences = re.split(r'[.!?.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > self.config['max_sentences']:
            return self.config['max_sentences']

        return len(sentences)

    def _detect_language(self, text: str) -> str:
        """Detect language (simplified version)"""
        # Check if contains Chinese characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        # Check if mainly English letters
        elif re.match(r'^[a-zA-Z\s,.!?]+$', text[:100]):
            return 'en'
        else:
            return 'unknown'

    def _contains_numbers(self, text: str) -> bool:
        """Whether contains numbers"""
        return bool(re.search(r'\d+', text))

    def _contains_urls(self, text: str) -> bool:
        """Whether contains URL"""
        url_pattern = r'https?://[^\s]+|www\.[^\s]+'
        return bool(re.search(url_pattern, text))

    def should_skip(self, context: PipelineContext) -> bool:
        """Skip if no text"""
        return not context.response_content
