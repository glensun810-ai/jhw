"""
Unit Tests for Validator Step
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.steps.validator import ValidatorStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class TestValidatorStep:
    """Test validator step"""

    def test_validate_min_length_pass(self):
        """Test minimum length validation - pass"""
        step = ValidatorStep()
        text = "This is a valid text"
        
        is_valid, message = step._validate_min_length(text, None)
        assert is_valid
        assert message == "OK"

    def test_validate_min_length_fail(self):
        """Test minimum length validation - fail"""
        step = ValidatorStep(config={'min_length': 100})
        text = "Short"
        
        is_valid, message = step._validate_min_length(text, None)
        assert not is_valid
        assert "too short" in message.lower()

    def test_validate_max_length_pass(self):
        """Test maximum length validation - pass"""
        step = ValidatorStep()
        text = "Short text"
        
        is_valid, message = step._validate_max_length(text, None)
        assert is_valid
        assert message == "OK"

    def test_validate_max_length_fail(self):
        """Test maximum length validation - fail"""
        step = ValidatorStep(config={'max_length': 10})
        text = "This is a very long text"
        
        is_valid, message = step._validate_max_length(text, None)
        assert not is_valid
        assert "too long" in message.lower()

    def test_validate_no_empty_pass(self):
        """Test non-empty validation - pass"""
        step = ValidatorStep()
        text = "Not empty"
        
        is_valid, message = step._validate_no_empty(text, None)
        assert is_valid

    def test_validate_no_empty_fail(self):
        """Test non-empty validation - fail"""
        step = ValidatorStep()
        text = "   "
        
        is_valid, message = step._validate_no_empty(text, None)
        assert not is_valid

    def test_validate_valid_encoding(self):
        """Test valid encoding validation"""
        step = ValidatorStep()
        text = "Valid UTF-8 text 中文"
        
        is_valid, message = step._validate_valid_encoding(text, None)
        assert is_valid

    def test_validate_no_invalid_chars_pass(self):
        """Test no invalid chars validation - pass"""
        step = ValidatorStep()
        text = "Clean text"
        
        is_valid, message = step._validate_no_invalid_chars(text, None)
        assert is_valid

    def test_validate_no_invalid_chars_fail(self):
        """Test no invalid chars validation - fail"""
        step = ValidatorStep()
        text = "Text with null\x00"
        
        is_valid, message = step._validate_no_invalid_chars(text, None)
        assert not is_valid
        assert "invalid characters" in message.lower()

    def test_process_all_rules(self):
        """Test processing all validation rules"""
        step = ValidatorStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="Valid text content"
        )

        result = asyncio.run(step.process(context))
        validation_result = result.intermediate_data['validator']
        
        assert 'validation_results' in validation_result
        assert 'is_valid' in validation_result

    def test_process_with_issues(self):
        """Test processing with validation issues"""
        step = ValidatorStep(config={'min_length': 100})
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content="Short"
        )

        result = asyncio.run(step.process(context))
        validation_result = result.intermediate_data['validator']
        
        assert not validation_result['is_valid']
        assert len(validation_result['issues']) > 0

    def test_should_skip_empty_text(self):
        """Test should_skip with empty text"""
        step = ValidatorStep()
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
