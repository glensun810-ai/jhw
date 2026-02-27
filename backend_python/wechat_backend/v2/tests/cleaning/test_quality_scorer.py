"""
Unit Tests for Quality Scorer Step
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.steps.quality_scorer import QualityScorerStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class TestQualityScorerStep:
    """Test quality scorer step"""

    def test_calculate_length_score_ideal(self):
        """Test length score for ideal length"""
        step = QualityScorerStep()
        text = "x" * 500  # Ideal length
        
        score = step._calculate_length_score(text)
        assert 80 <= score <= 100  # Should be high

    def test_calculate_length_score_too_short(self):
        """Test length score for too short text"""
        step = QualityScorerStep()
        text = "Short"
        
        score = step._calculate_length_score(text)
        assert score < 50  # Should be low

    def test_calculate_length_score_too_long(self):
        """Test length score for too long text"""
        step = QualityScorerStep()
        text = "x" * 3000  # Much longer than max_acceptable
        
        score = step._calculate_length_score(text)
        assert score < 50  # Should be low

    def test_calculate_completeness_score_with_entities(self):
        """Test completeness score with entities"""
        step = QualityScorerStep()
        text = "Some text here"
        entity_result = {
            'entities': [
                {'entity_name': 'Brand', 'entity_type': 'brand'}
            ]
        }
        
        score = step._calculate_completeness_score(text, entity_result)
        assert score > 70  # Base score + entity bonus

    def test_calculate_completeness_score_no_entities(self):
        """Test completeness score without entities"""
        step = QualityScorerStep()
        text = "Some text here"
        entity_result = {'entities': []}
        
        score = step._calculate_completeness_score(text, entity_result)
        assert score >= 70  # At least base score

    def test_calculate_relevance_score_with_brand(self):
        """Test relevance score with brand mention"""
        step = QualityScorerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            raw_response={},
            response_content=""
        )
        text = "苹果公司发布新产品"
        
        score = step._calculate_relevance_score(text, context)
        assert score > 60  # Base + brand bonus

    def test_calculate_relevance_score_with_keywords(self):
        """Test relevance score with question keywords"""
        step = QualityScorerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="苹果手机怎么样",
            model="test",
            raw_response={},
            response_content=""
        )
        text = "苹果手机在市场上表现很好"
        
        score = step._calculate_relevance_score(text, context)
        assert score > 60  # Base + keyword bonus

    def test_extract_keywords(self):
        """Test keyword extraction"""
        step = QualityScorerStep()
        question = "苹果手机 performance 如何"
        
        keywords = step._extract_keywords(question)
        assert len(keywords) > 0
        assert '苹果' in keywords or '手机' in keywords

    def test_process_complete(self):
        """Test complete processing"""
        step = QualityScorerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="苹果手机怎么样",
            model="test",
            raw_response={},
            response_content="苹果手机在市场上表现非常好，用户评价很高"
        )
        
        # Add entity recognition results
        context.intermediate_data['entity_recognizer'] = {
            'entities': [
                {
                    'entity_name': '苹果',
                    'entity_type': 'brand',
                    'start_pos': 0,
                    'end_pos': 2,
                }
            ]
        }

        result = asyncio.run(step.process(context))
        quality_result = result.intermediate_data['quality_scorer']
        
        assert 'quality_score' in quality_result
        assert quality_result['quality_score']['overall'] > 0

    def test_process_empty_text(self):
        """Test processing empty text"""
        step = QualityScorerStep()
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

    def test_process_with_validation_issues(self):
        """Test processing with validation issues"""
        step = QualityScorerStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="Short"
        )
        
        # Add validation results with issues
        context.intermediate_data['validator'] = {
            'issues': ['min_length: Text too short'],
            'is_valid': False
        }

        result = asyncio.run(step.process(context))
        quality_result = result.intermediate_data['quality_scorer']
        
        # Issues should be carried over
        assert len(quality_result['quality_score']['issues']) > 0
