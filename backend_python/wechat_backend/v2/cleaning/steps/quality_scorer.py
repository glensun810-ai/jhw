"""
Quality Scoring Step

Scores cleaned data based on multiple dimensions.
"""

from typing import Dict, Any, List
import re

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.models.cleaned_data import QualityScore


class QualityScorerStep(CleaningStep):
    """
    Quality scoring step

    Scores cleaned data based on multiple dimensions:
    1. Length score - whether text length is appropriate
    2. Completeness score - whether contains necessary information
    3. Relevance score - whether related to question (simplified)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('quality_scorer', config)

        # Scoring weights configuration
        self.config.setdefault('weights', {
            'length': 0.3,
            'completeness': 0.4,
            'relevance': 0.3,
        })

        self.config.setdefault('ideal_length', 500)  # Ideal length
        self.config.setdefault('min_acceptable_length', 50)
        self.config.setdefault('max_acceptable_length', 2000)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Execute quality scoring"""

        # 1. Get text
        text = context.response_content
        if not text:
            context.add_warning("Empty text for quality scoring")
            return context

        # 2. Get other step results
        entity_result = context.intermediate_data.get('entity_recognizer', {})
        validation_result = context.intermediate_data.get('validator', {})

        # 3. Calculate dimension scores
        length_score = self._calculate_length_score(text)
        completeness_score = self._calculate_completeness_score(text, entity_result)
        relevance_score = self._calculate_relevance_score(text, context)

        # 4. Overall score
        weights = self.config['weights']
        overall_score = (
            length_score * weights['length'] +
            completeness_score * weights['completeness'] +
            relevance_score * weights['relevance']
        )

        # 5. Collect issues and warnings
        issues = []
        warnings = []

        if length_score < 30:
            issues.append("Text too short")
        elif length_score > 95:
            warnings.append("Text may be too long")

        if completeness_score < 50:
            issues.append("Low completeness")

        if relevance_score < 30:
            issues.append("Low relevance to question")

        # 6. Get existing issues from validation step
        if validation_result:
            validation_issues = validation_result.get('issues', [])
            issues.extend(validation_issues)

        # 7. Create score object
        quality = QualityScore(
            overall_score=round(overall_score, 2),
            length_score=round(length_score, 2),
            completeness_score=round(completeness_score, 2),
            relevance_score=round(relevance_score, 2),
            issues=issues[:5],  # Only keep first 5 issues
            warnings=warnings[:3],
        )

        # 8. Save results
        result = {
            'quality_score': {
                'overall': quality.overall_score,
                'length': quality.length_score,
                'completeness': quality.completeness_score,
                'relevance': quality.relevance_score,
                'issues': quality.issues,
                'warnings': quality.warnings,
            }
        }

        self.save_step_result(context, result)

        # 9. Add warnings to context if any
        for warning in warnings:
            context.add_warning(f"Quality warning: {warning}")

        return context

    def _calculate_length_score(self, text: str) -> float:
        """Calculate length score"""
        length = len(text)
        ideal = self.config['ideal_length']
        min_accept = self.config['min_acceptable_length']
        max_accept = self.config['max_acceptable_length']

        if length < min_accept:
            # Too short: linear decrease
            return max(0, (length / min_accept) * 50)
        elif length > max_accept:
            # Too long: linear decrease
            excess = (length - max_accept) / max_accept
            return max(0, 100 - excess * 50)
        else:
            # Within ideal range: Gaussian distribution
            if length <= ideal:
                return 50 + 50 * (length - min_accept) / (ideal - min_accept)
            else:
                return 100 - 50 * (length - ideal) / (max_accept - ideal)

    def _calculate_completeness_score(self, text: str, entity_result: Dict) -> float:
        """Calculate completeness score"""
        score = 70  # Base score

        # Check if has entities
        entities = entity_result.get('entities', [])
        if entities:
            score += 15

        # Check text length
        if len(text) > 100:
            score += 15

        # Limit range
        return min(100, max(0, score))

    def _calculate_relevance_score(self, text: str, context: PipelineContext) -> float:
        """Calculate relevance score (simplified)"""
        score = 60  # Base score

        # Check if contains brand name
        if context.brand in text:
            score += 20

        # Check if contains keywords from question
        question_keywords = self._extract_keywords(context.question)
        for keyword in question_keywords:
            if keyword in text:
                score += 5

        return min(100, max(0, score))

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from question (simplified)"""
        # Simple tokenization (by spaces and common delimiters)
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', text)
        # Filter too short words
        return [w for w in words if len(w) > 1][:5]
