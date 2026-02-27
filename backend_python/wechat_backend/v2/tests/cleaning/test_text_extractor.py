"""
Unit Tests for Text Extractor Step
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.steps.text_extractor import TextExtractorStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class TestTextExtractorStep:
    """Test text extractor step"""

    def test_strip_html(self):
        """Test HTML tag removal"""
        step = TextExtractorStep()
        text = "<p>Hello <b>world</b></p>"
        result = step._strip_html(text)
        assert result == " Hello  world "

    def test_unescape_html(self):
        """Test HTML entity unescape"""
        step = TextExtractorStep()
        text = "Hello &amp; world"
        result = step._unescape_html(text)
        assert result == "Hello & world"

    def test_normalize_whitespace(self):
        """Test whitespace normalization"""
        step = TextExtractorStep()
        text = "Hello   world\n\t test"
        result = step._normalize_whitespace(text)
        assert result == "Hello world test"

    def test_process_empty_text(self):
        """Test empty text processing"""
        step = TextExtractorStep()
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
        assert "extracted_text" in result.intermediate_data[step.name]
        assert result.intermediate_data[step.name]['extracted_text'] == ""

    def test_process_with_html_content(self):
        """Test processing HTML content"""
        step = TextExtractorStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="<p>Hello <b>world</b></p>"
        )

        result = asyncio.run(step.process(context))
        assert result.response_content == " Hello world "

    def test_process_with_truncation(self):
        """Test text truncation"""
        step = TextExtractorStep(config={'max_length': 10})
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="This is a very long text that should be truncated"
        )

        result = asyncio.run(step.process(context))
        assert len(result.response_content) <= 10
        assert len(result.warnings) > 0

    def test_validate_input_empty(self):
        """Test input validation with empty content"""
        step = TextExtractorStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content=""
        )

        assert not step.validate_input(context)

    def test_validate_input_valid(self):
        """Test input validation with valid content"""
        step = TextExtractorStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="Valid content"
        )

        assert step.validate_input(context)
