"""
Entity Recognition Step

Identifies brand and competitor mentions in text.
"""

import re
from typing import List, Dict, Any, Set
from collections import defaultdict

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.models.cleaned_data import EntityMention
from wechat_backend.v2.cleaning.errors import EntityRecognitionError


class EntityRecognizerStep(CleaningStep):
    """
    Entity recognition step

    Identifies brand and competitor names in text, recording positions.
    Uses simple string matching (can be upgraded to NLP later).
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('entity_recognizer', config)

        # Default configuration
        self.config.setdefault('case_sensitive', False)
        self.config.setdefault('min_confidence', 0.8)
        self.config.setdefault('enable_partial_match', False)
        self.config.setdefault('max_entities', 100)  # Maximum entities to recognize

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Execute entity recognition"""

        try:
            # 1. Get cleaned text
            text = context.response_content
            if not text:
                context.add_warning("Empty text for entity recognition")
                return context

            # 2. Get entities to recognize
            # Main brand
            main_brand = context.brand

            # Competitors (need to get from config or context)
            # Simplified here, actual implementation may query from report table
            competitors = self._get_competitors(context)

            # 3. Execute recognition
            entities = []

            # Recognize main brand
            brand_mentions = self._find_entity(text, main_brand, 'brand')
            entities.extend(brand_mentions)

            # Recognize competitors
            for competitor in competitors:
                competitor_mentions = self._find_entity(text, competitor, 'competitor')
                entities.extend(competitor_mentions)

            # 4. Deduplicate and sort
            entities = self._deduplicate_entities(entities)
            entities.sort(key=lambda e: e.start_pos)

            # 5. Limit count
            if len(entities) > self.config['max_entities']:
                entities = entities[:self.config['max_entities']]
                context.add_warning(f"Entity count truncated to {self.config['max_entities']}")

            # 6. Save results
            result = {
                'entities': [
                    {
                        'entity_name': e.entity_name,
                        'entity_type': e.entity_type,
                        'start_pos': e.start_pos,
                        'end_pos': e.end_pos,
                        'confidence': e.confidence,
                        'context': e.context
                    }
                    for e in entities
                ],
                'total_entities': len(entities),
                'brand_mentions': sum(1 for e in entities if e.entity_type == 'brand'),
                'competitor_mentions': sum(1 for e in entities if e.entity_type == 'competitor'),
            }

            self.save_step_result(context, result)

            return context

        except Exception as e:
            context.add_error(f"Entity recognition failed: {str(e)}")
            raise EntityRecognitionError(
                f"Failed to recognize entities: {str(e)}",
                execution_id=context.execution_id,
                step=self.name
            )

    def _find_entity(self, text: str, entity_name: str, entity_type: str) -> List[EntityMention]:
        """Find entity in text"""
        mentions = []

        if not entity_name or len(entity_name) < 2:
            return mentions

        search_name = entity_name.lower() if not self.config['case_sensitive'] else entity_name
        search_text = text.lower() if not self.config['case_sensitive'] else text

        # Simple string search
        start = 0
        while True:
            pos = search_text.find(search_name, start)
            if pos == -1:
                break

            # Calculate context (20 chars before and after)
            context_start = max(0, pos - 20)
            context_end = min(len(text), pos + len(entity_name) + 20)
            context_text = text[context_start:context_end]

            mention = EntityMention(
                entity_name=entity_name,
                entity_type=entity_type,
                start_pos=pos,
                end_pos=pos + len(entity_name),
                confidence=1.0,
                context=context_text
            )
            mentions.append(mention)

            start = pos + len(entity_name)

        return mentions

    def _get_competitors(self, context: PipelineContext) -> List[str]:
        """Get competitor list"""
        # Get from context config
        # Actual implementation may query from database
        # Here simplified to read from config
        return self.config.get('competitors', [])

    def _deduplicate_entities(self, entities: List[EntityMention]) -> List[EntityMention]:
        """Deduplicate (same position same entity only kept once)"""
        seen = set()
        unique = []

        for e in entities:
            key = (e.start_pos, e.end_pos, e.entity_name)
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return unique

    def should_skip(self, context: PipelineContext) -> bool:
        """Skip if no competitor configuration"""
        return len(self._get_competitors(context)) == 0 and not context.brand
