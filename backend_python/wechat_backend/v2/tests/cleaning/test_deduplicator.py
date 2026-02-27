"""
Unit Tests for Deduplicator Step
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.steps.deduplicator import DeduplicatorStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class TestDeduplicatorStep:
    """Test deduplicator step"""

    def test_compute_exact_hash(self):
        """Test exact hash computation"""
        step = DeduplicatorStep()
        text = "Hello world"
        hash1 = step._compute_exact_hash(text)
        hash2 = step._compute_exact_hash(text)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 char hex

    def test_compute_simhash(self):
        """Test simhash computation"""
        step = DeduplicatorStep()
        text = "Hello world"
        hash1 = step._compute_simhash(text)
        hash2 = step._compute_simhash(text)
        
        assert hash1 == hash2

    def test_normalize_text(self):
        """Test text normalization"""
        step = DeduplicatorStep()
        text = "Hello, World! 123"
        normalized = step._normalize_text(text)
        
        assert "hello" in normalized
        assert "world" in normalized
        assert "," not in normalized

    def test_split_into_chunks(self):
        """Test text chunking"""
        step = DeduplicatorStep()
        text = "one two three four five"
        chunks = step._split_into_chunks(text, 2)
        
        assert len(chunks) == 3  # [one two, three four, five]

    def test_process_duplicate_detection(self):
        """Test duplicate detection"""
        step = DeduplicatorStep()
        
        # First text
        context1 = PipelineContext(
            execution_id="test1",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="Hello world"
        )
        
        result1 = asyncio.run(step.process(context1))
        hash1 = result1.intermediate_data['deduplicator']['content_hash']
        
        # Second text (same content, should be detected as duplicate)
        context2 = PipelineContext(
            execution_id="test2",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="Hello world"
        )
        
        # Share intermediate_data to simulate batch processing
        context2.intermediate_data = context1.intermediate_data
        
        result2 = asyncio.run(step.process(context2))
        is_duplicate = result2.intermediate_data['deduplicator']['is_duplicate']
        
        assert is_duplicate

    def test_process_empty_text(self):
        """Test processing empty text"""
        step = DeduplicatorStep()
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
        step = DeduplicatorStep()
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
