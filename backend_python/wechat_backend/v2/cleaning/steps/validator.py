"""
Validation Step

Validates cleaned data format and quality requirements.
"""

import re
from typing import Dict, Any, List, Tuple

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.errors import ValidationError


class ValidatorStep(CleaningStep):
    """
    Validation step

    Validates cleaned data format and quality requirements.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('validator', config)

        # Default validation rules
        self.config.setdefault('rules', [
            'min_length',
            'max_length',
            'no_empty',
            'valid_encoding',
            'no_invalid_chars'
        ])

        self.config.setdefault('min_length', 10)
        self.config.setdefault('max_length', 10000)
        self.config.setdefault('invalid_chars', ['\x00', '\x01', '\x02'])  # Control characters

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Execute validation"""

        # 1. Get text
        text = context.response_content
        if not text:
            context.add_warning("Empty text for validation")
            return context

        # 2. Execute validation rules
        validation_results = {}
        issues = []

        for rule in self.config['rules']:
            rule_method = getattr(self, f'_validate_{rule}', None)
            if rule_method:
                is_valid, message = rule_method(text, context)
                validation_results[rule] = {
                    'passed': is_valid,
                    'message': message
                }
                if not is_valid:
                    issues.append(f"{rule}: {message}")

        # 3. Save results
        result = {
            'validation_results': validation_results,
            'is_valid': len(issues) == 0,
            'issues': issues,
            'issue_count': len(issues),
        }

        self.save_step_result(context, result)

        # 4. Add issues to context warnings
        for issue in issues:
            context.add_warning(f"Validation issue: {issue}")

        return context

    def _validate_min_length(self, text: str, context: PipelineContext) -> Tuple[bool, str]:
        """Validate minimum length"""
        min_len = self.config['min_length']
        if len(text) < min_len:
            return False, f"Text too short: {len(text)} < {min_len}"
        return True, "OK"

    def _validate_max_length(self, text: str, context: PipelineContext) -> Tuple[bool, str]:
        """Validate maximum length"""
        max_len = self.config['max_length']
        if len(text) > max_len:
            return False, f"Text too long: {len(text)} > {max_len}"
        return True, "OK"

    def _validate_no_empty(self, text: str, context: PipelineContext) -> Tuple[bool, str]:
        """Validate non-empty"""
        if not text or not text.strip():
            return False, "Text is empty after stripping"
        return True, "OK"

    def _validate_valid_encoding(self, text: str, context: PipelineContext) -> Tuple[bool, str]:
        """Validate encoding is valid"""
        try:
            # Try encode then decode, check if consistent
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            if decoded != text:
                return False, "Encoding mismatch"
            return True, "OK"
        except UnicodeError as e:
            return False, f"Invalid encoding: {str(e)}"

    def _validate_no_invalid_chars(self, text: str, context: PipelineContext) -> Tuple[bool, str]:
        """Validate no invalid characters"""
        invalid_chars = self.config['invalid_chars']
        found = []

        for char in invalid_chars:
            if char in text:
                found.append(repr(char))

        if found:
            return False, f"Found invalid characters: {', '.join(found)}"
        return True, "OK"

    def should_skip(self, context: PipelineContext) -> bool:
        """Skip if text is empty"""
        return not context.response_content
