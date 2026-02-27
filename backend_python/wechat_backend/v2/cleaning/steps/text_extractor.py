"""
Text Extraction Step

Extracts plain text from raw AI responses.
"""

import re
from typing import Dict, Any
import html

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.errors import TextExtractionError


class TextExtractorStep(CleaningStep):
    """
    Text extraction step

    Extracts pure text from raw responses, handling:
    1. HTML tags
    2. Escape characters
    3. Extra whitespace and newlines
    4. Special characters
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('text_extractor', config)

        # Default configuration
        self.config.setdefault('strip_html', True)
        self.config.setdefault('unescape_html', True)
        self.config.setdefault('normalize_whitespace', True)
        self.config.setdefault('max_length', 10000)  # Maximum text length
        self.config.setdefault('min_length', 10)     # Minimum effective text length

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Execute text extraction"""

        try:
            # 1. Get raw text (from context.response_content)
            raw_text = context.response_content

            if not raw_text:
                context.add_warning("Empty response content")
                context.intermediate_data[self.name] = {
                    'extracted_text': '',
                    'original_length': 0,
                    'cleaned_length': 0
                }
                return context

            original_length = len(raw_text)

            # 2. Apply cleaning rules
            cleaned_text = raw_text

            if self.config['strip_html']:
                cleaned_text = self._strip_html(cleaned_text)

            if self.config['unescape_html']:
                cleaned_text = self._unescape_html(cleaned_text)

            if self.config['normalize_whitespace']:
                cleaned_text = self._normalize_whitespace(cleaned_text)

            # 3. Length limit
            if len(cleaned_text) > self.config['max_length']:
                cleaned_text = cleaned_text[:self.config['max_length']]
                context.add_warning(f"Text truncated from {original_length} to {self.config['max_length']}")

            # 4. Check minimum length
            if len(cleaned_text) < self.config['min_length']:
                context.add_warning(f"Cleaned text too short: {len(cleaned_text)} chars")

            # 5. Save results
            result = {
                'extracted_text': cleaned_text,
                'original_length': original_length,
                'cleaned_length': len(cleaned_text),
                'truncated': len(cleaned_text) > self.config['max_length'],
            }

            self.save_step_result(context, result)

            # Also update context.response_content with cleaned text
            # So subsequent steps can use the cleaned text
            context.response_content = cleaned_text

            return context

        except Exception as e:
            context.add_error(f"Text extraction failed: {str(e)}")
            raise TextExtractionError(
                f"Failed to extract text: {str(e)}",
                execution_id=context.execution_id,
                step=self.name
            )

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags"""
        # Simple HTML tag removal
        text = re.sub(r'<[^>]+>', ' ', text)
        return text

    def _unescape_html(self, text: str) -> str:
        """Unescape HTML entities"""
        return html.unescape(text)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace"""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    def validate_input(self, context: PipelineContext) -> bool:
        """Validate input"""
        if not context.response_content:
            context.add_warning("No response content to extract")
            return False
        return True
