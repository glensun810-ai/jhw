"""
Cleaning Pipeline Main Orchestrator

Responsible for orchestrating and executing multiple cleaning steps.
"""

import asyncio
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.models.cleaned_data import CleanedData, EntityMention, GeoPreparedData, QualityScore
from wechat_backend.v2.cleaning.errors import PipelineConfigurationError, StepExecutionError
from wechat_backend.v2.adapters.models import AIResponse

logger = logging.getLogger(__name__)


class CleaningPipeline:
    """
    Cleaning pipeline main class

    Responsible for orchestrating and executing multiple cleaning steps,
    converting raw AI responses into structured data.
    Supports:
    1. Dynamic step configuration and orchestration
    2. Parallel/serial execution control
    3. Error handling and recovery
    4. Monitoring and logging
    """

    def __init__(self, name: str = "default", config: Optional[Dict[str, Any]] = None):
        """
        Initialize cleaning pipeline

        Args:
            name: Pipeline name
            config: Pipeline-level configuration
        """
        self.name = name
        self.config = config or {}
        self.steps: List[CleaningStep] = []

        # Default configuration
        self.config.setdefault('stop_on_error', True)      # Stop on error
        self.config.setdefault('continue_on_warning', True) # Continue on warning
        self.config.setdefault('parallel_steps', False)    # Whether to execute steps in parallel
        self.config.setdefault('timeout', 30)              # Total timeout in seconds

    def add_step(self, step: CleaningStep) -> 'CleaningPipeline':
        """Add cleaning step"""
        self.steps.append(step)
        return self

    def add_steps(self, steps: List[CleaningStep]) -> 'CleaningPipeline':
        """Batch add cleaning steps"""
        self.steps.extend(steps)
        return self

    def insert_step(self, index: int, step: CleaningStep) -> 'CleaningPipeline':
        """Insert step at specified position"""
        self.steps.insert(index, step)
        return self

    def remove_step(self, step_name: str) -> bool:
        """Remove step by name"""
        for i, step in enumerate(self.steps):
            if step.name == step_name:
                del self.steps[i]
                return True
        return False

    async def execute(
        self,
        execution_id: str,
        report_id: int,
        brand: str,
        question: str,
        model: str,
        response: AIResponse,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> CleanedData:
        """
        Execute cleaning pipeline

        Args:
            execution_id: Execution ID
            report_id: Report ID
            brand: Brand name
            question: Question
            model: AI model
            response: Standardized AI response
            additional_context: Additional context information

        Returns:
            Cleaned data

        Raises:
            PipelineConfigurationError: Pipeline configuration error
            StepExecutionError: Step execution failure
        """

        if not self.steps:
            raise PipelineConfigurationError(
                "No steps configured in pipeline",
                execution_id=execution_id
            )

        # 1. Create context
        context = PipelineContext(
            execution_id=execution_id,
            report_id=report_id,
            brand=brand,
            question=question,
            model=model,
            raw_response=response.raw_response or {},
            response_content=response.content,
            config=self.config,
        )

        # Add additional context
        if additional_context:
            context.intermediate_data.update(additional_context)

        # 2. Record start
        start_time = time.time()
        logger.info(
            "cleaning_pipeline_started",
            extra={
                'pipeline': self.name,
                'execution_id': execution_id,
                'step_count': len(self.steps),
            }
        )

        # 3. Execute steps serially
        try:
            for step in self.steps:
                # Check if should skip
                if step.should_skip(context):
                    logger.info(
                        "step_skipped",
                        extra={'step': step.name, 'execution_id': execution_id}
                    )
                    continue

                # Validate input
                if not step.validate_input(context):
                    context.add_warning(f"Step {step.name} input validation failed")
                    if self.config['stop_on_error']:
                        break
                    continue

                # Execute step
                step_start = time.time()
                try:
                    context = await step.process(context)
                    step_duration = (time.time() - step_start) * 1000

                    logger.info(
                        "step_completed",
                        extra={
                            'step': step.name,
                            'execution_id': execution_id,
                            'duration_ms': step_duration,
                        }
                    )

                except Exception as e:
                    step_duration = (time.time() - step_start) * 1000
                    logger.error(
                        "step_failed",
                        extra={
                            'step': step.name,
                            'execution_id': execution_id,
                            'duration_ms': step_duration,
                            'error': str(e),
                        }
                    )

                    context.add_error(f"Step {step.name} failed: {str(e)}")

                    if self.config['stop_on_error']:
                        raise StepExecutionError(
                            f"Step {step.name} failed: {str(e)}",
                            execution_id=execution_id,
                            step=step.name
                        ) from e

                    # Continue to next step
                    continue

            # 4. Build cleaned data
            cleaned_data = self._build_cleaned_data(context)

            # 5. Record completion
            total_duration = (time.time() - start_time) * 1000
            logger.info(
                "cleaning_pipeline_completed",
                extra={
                    'pipeline': self.name,
                    'execution_id': execution_id,
                    'duration_ms': total_duration,
                    'steps_completed': len(context.steps_completed),
                    'error_count': len(context.errors),
                    'warning_count': len(context.warnings),
                }
            )

            return cleaned_data

        except Exception as e:
            logger.error(
                "cleaning_pipeline_failed",
                extra={
                    'pipeline': self.name,
                    'execution_id': execution_id,
                    'error': str(e),
                }
            )
            raise

    async def execute_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[CleanedData]:
        """
        Batch execute cleaning

        Args:
            items: Each element contains execution_id, report_id, brand, question, model, response

        Returns:
            List of cleaned data
        """
        tasks = []
        for item in items:
            task = self.execute(
                execution_id=item['execution_id'],
                report_id=item['report_id'],
                brand=item['brand'],
                question=item['question'],
                model=item['model'],
                response=item['response']
            )
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)

    def _build_cleaned_data(self, context: PipelineContext) -> CleanedData:
        """Build cleaned data from context"""

        # Get results from each step
        text_result = context.intermediate_data.get('text_extractor', {})
        entity_result = context.intermediate_data.get('entity_recognizer', {})
        geo_result = context.intermediate_data.get('geo_preparer', {})
        quality_result = context.intermediate_data.get('quality_scorer', {})

        # Build entity list
        entities = []
        for e in entity_result.get('entities', []):
            entities.append(EntityMention(
                entity_name=e['entity_name'],
                entity_type=e['entity_type'],
                start_pos=e['start_pos'],
                end_pos=e['end_pos'],
                confidence=e.get('confidence', 1.0),
                context=e.get('context')
            ))

        # Build GEO data
        geo_data_dict = geo_result.get('geo_data', {})
        geo_data = GeoPreparedData(
            text_length=geo_data_dict.get('text_length', 0),
            sentence_count=geo_data_dict.get('sentence_count', 1),
            has_brand_mention=geo_data_dict.get('has_brand_mention', False),
            brand_positions=geo_data_dict.get('brand_positions', []),
            competitor_mentions=geo_data_dict.get('competitor_mentions', {}),
            language=geo_data_dict.get('language', 'zh'),
            contains_numbers=geo_data_dict.get('contains_numbers', False),
            contains_urls=geo_data_dict.get('contains_urls', False),
        )

        # Build quality score
        quality_dict = quality_result.get('quality_score', {})
        quality = QualityScore(
            overall_score=quality_dict.get('overall', 0),
            length_score=quality_dict.get('length', 0),
            completeness_score=quality_dict.get('completeness', 0),
            relevance_score=quality_dict.get('relevance', 0),
            issues=quality_dict.get('issues', []),
            warnings=quality_dict.get('warnings', []),
        )

        # Get original text from text extractor result
        original_text = text_result.get('extracted_text', context.response_content)

        # Build final data
        return CleanedData(
            execution_id=context.execution_id,
            report_id=context.report_id,
            brand=context.brand,
            question=context.question,
            model=context.model,
            cleaned_text=context.response_content,
            original_text=original_text,
            entities=entities,
            geo_data=geo_data,
            quality=quality,
            cleaning_version='1.0',
            steps_applied=context.steps_completed,
            warnings=context.warnings,
            errors=context.errors,
        )

    def get_step_names(self) -> List[str]:
        """Get all step names"""
        return [step.name for step in self.steps]

    def get_step_by_name(self, name: str) -> Optional[CleaningStep]:
        """Get step by name"""
        for step in self.steps:
            if step.name == name:
                return step
        return None


# Predefined common pipelines
def create_default_pipeline(competitors: List[str] = None) -> CleaningPipeline:
    """Create default cleaning pipeline"""
    from wechat_backend.v2.cleaning.steps.text_extractor import TextExtractorStep
    from wechat_backend.v2.cleaning.steps.entity_recognizer import EntityRecognizerStep
    from wechat_backend.v2.cleaning.steps.deduplicator import DeduplicatorStep
    from wechat_backend.v2.cleaning.steps.validator import ValidatorStep
    from wechat_backend.v2.cleaning.steps.geo_preparer import GeoPreparerStep
    from wechat_backend.v2.cleaning.steps.quality_scorer import QualityScorerStep

    pipeline = CleaningPipeline("default")
    
    # Configure entity recognizer with competitors
    entity_config = {}
    if competitors:
        entity_config['competitors'] = competitors
    
    pipeline.add_steps([
        TextExtractorStep(),
        ValidatorStep(),
        EntityRecognizerStep(config=entity_config),
        DeduplicatorStep(),
        GeoPreparerStep(),
        QualityScorerStep(),
    ])

    return pipeline


def create_minimal_pipeline() -> CleaningPipeline:
    """Create minimal cleaning pipeline (only essential cleaning)"""
    from wechat_backend.v2.cleaning.steps.text_extractor import TextExtractorStep
    from wechat_backend.v2.cleaning.steps.validator import ValidatorStep

    pipeline = CleaningPipeline("minimal")
    pipeline.add_steps([
        TextExtractorStep(),
        ValidatorStep(),
    ])

    return pipeline
