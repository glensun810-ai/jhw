"""
Unit Tests for Entity Recognizer Step
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.steps.entity_recognizer import EntityRecognizerStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class TestEntityRecognizerStep:
    """Test entity recognizer step"""

    def test_find_entity(self):
        """Test finding entity"""
        step = EntityRecognizerStep()
        text = "苹果公司发布新款 iPhone，苹果的股价上涨"

        mentions = step._find_entity(text, "苹果", "brand")
        assert len(mentions) == 2
        assert mentions[0].entity_name == "苹果"
        assert mentions[0].start_pos == 0

    def test_find_entity_not_found(self):
        """Test finding entity that doesn't exist"""
        step = EntityRecognizerStep()
        text = "微软发布新款软件"

        mentions = step._find_entity(text, "苹果", "brand")
        assert len(mentions) == 0

    def test_find_entity_short_name(self):
        """Test finding entity with short name"""
        step = EntityRecognizerStep()
        text = "苹果公司发布产品"

        mentions = step._find_entity(text, "A", "brand")
        assert len(mentions) == 0  # Names shorter than 2 chars are ignored

    def test_deduplicate_entities(self):
        """Test entity deduplication"""
        step = EntityRecognizerStep()
        
        from wechat_backend.v2.cleaning.models.cleaned_data import EntityMention
        
        entities = [
            EntityMention("苹果", "brand", 0, 2, 1.0),
            EntityMention("苹果", "brand", 0, 2, 1.0),  # Duplicate
            EntityMention("苹果", "brand", 10, 12, 1.0),
        ]

        unique = step._deduplicate_entities(entities)
        assert len(unique) == 2

    def test_process_with_entities(self):
        """Test processing with entities"""
        step = EntityRecognizerStep(config={'competitors': ['三星', '华为']})

        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            raw_response={},
            response_content="苹果和三星在手机市场竞争，华为也有不错的表现"
        )

        result = asyncio.run(step.process(context))
        step_result = result.intermediate_data['entity_recognizer']
        assert step_result['total_entities'] >= 3
        assert step_result['brand_mentions'] >= 1
        assert step_result['competitor_mentions'] >= 2

    def test_process_empty_text(self):
        """Test processing empty text"""
        step = EntityRecognizerStep()
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
        assert 'entity_recognizer' in result.intermediate_data

    def test_should_skip_no_competitors(self):
        """Test should_skip with no competitors"""
        step = EntityRecognizerStep(config={'competitors': []})
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="",  # No brand either
            question="test",
            model="test",
            raw_response={},
            response_content="test"
        )

        assert step.should_skip(context)
