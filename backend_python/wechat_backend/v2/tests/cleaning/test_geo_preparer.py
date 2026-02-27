"""
Unit Tests for GEO Preparer Step
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.steps.geo_preparer import GeoPreparerStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class TestGeoPreparerStep:
    """Test GEO preparer step"""

    def test_count_sentences(self):
        """Test sentence counting"""
        step = GeoPreparerStep()
        text = "这是第一句。这是第二句！这是第三句？"
        
        count = step._count_sentences(text)
        assert count == 3

    def test_count_sentences_english(self):
        """Test English sentence counting"""
        step = GeoPreparerStep()
        text = "First sentence. Second sentence! Third sentence?"
        
        count = step._count_sentences(text)
        assert count == 3

    def test_count_sentences_max_limit(self):
        """Test sentence count max limit"""
        step = GeoPreparerStep(config={'max_sentences': 5})
        text = "A. B. C. D. E. F. G."
        
        count = step._count_sentences(text)
        assert count == 5  # Limited to max

    def test_detect_language_chinese(self):
        """Test Chinese language detection"""
        step = GeoPreparerStep()
        text = "这是中文文本"
        
        language = step._detect_language(text)
        assert language == 'zh'

    def test_detect_language_english(self):
        """Test English language detection"""
        step = GeoPreparerStep()
        text = "This is English text with common punctuation."
        
        language = step._detect_language(text)
        assert language == 'en'

    def test_contains_numbers_true(self):
        """Test contains numbers - true"""
        step = GeoPreparerStep()
        text = "There are 123 items"
        
        assert step._contains_numbers(text)

    def test_contains_numbers_false(self):
        """Test contains numbers - false"""
        step = GeoPreparerStep()
        text = "No numbers here"
        
        assert not step._contains_numbers(text)

    def test_contains_urls_true(self):
        """Test contains URL - true"""
        step = GeoPreparerStep()
        text = "Visit https://example.com for more info"
        
        assert step._contains_urls(text)

    def test_contains_urls_false(self):
        """Test contains URL - false"""
        step = GeoPreparerStep()
        text = "No URLs in this text"
        
        assert not step._contains_urls(text)

    def test_process_with_entities(self):
        """Test processing with entity information"""
        step = GeoPreparerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            raw_response={},
            response_content="苹果公司发布新产品，在市场上表现出色"
        )
        
        # Add entity recognition results
        context.intermediate_data['entity_recognizer'] = {
            'entities': [
                {
                    'entity_name': '苹果',
                    'entity_type': 'brand',
                    'start_pos': 0,
                    'end_pos': 2,
                    'confidence': 1.0,
                    'context': '苹果公司发布新产品'
                }
            ]
        }

        result = asyncio.run(step.process(context))
        geo_result = result.intermediate_data['geo_preparer']
        
        assert geo_result['geo_data']['has_brand_mention']
        assert geo_result['geo_data']['text_length'] > 0

    def test_process_empty_text(self):
        """Test processing empty text"""
        step = GeoPreparerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content=""
        )

        result = asyncio.run(step.process(context))
        assert len(result.warnings) > 0

    def test_should_skip_empty_text(self):
        """Test should_skip with empty text"""
        step = GeoPreparerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content=""
        )

        assert step.should_skip(context)
