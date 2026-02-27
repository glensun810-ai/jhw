"""
Unit Tests for Cleaning Pipeline
"""

import pytest
import asyncio
from wechat_backend.v2.cleaning.pipeline import CleaningPipeline, create_default_pipeline, create_minimal_pipeline
from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.errors import PipelineConfigurationError, StepExecutionError
from wechat_backend.v2.adapters.models import AIResponse


class TestCleaningPipeline:
    """Test cleaning pipeline"""

    def test_init_default(self):
        """Test default initialization"""
        pipeline = CleaningPipeline()
        
        assert pipeline.name == "default"
        assert len(pipeline.steps) == 0

    def test_add_step(self):
        """Test adding a step"""
        pipeline = CleaningPipeline()
        
        class DummyStep(CleaningStep):
            async def process(self, context):
                return context
        
        step = DummyStep("dummy")
        pipeline.add_step(step)
        
        assert len(pipeline.steps) == 1

    def test_add_steps(self):
        """Test adding multiple steps"""
        pipeline = CleaningPipeline()
        
        class DummyStep(CleaningStep):
            def __init__(self, name):
                super().__init__(name)
            async def process(self, context):
                return context
        
        steps = [DummyStep(f"step{i}") for i in range(3)]
        pipeline.add_steps(steps)
        
        assert len(pipeline.steps) == 3

    def test_remove_step(self):
        """Test removing a step"""
        pipeline = CleaningPipeline()
        
        class DummyStep(CleaningStep):
            def __init__(self, name):
                super().__init__(name)
            async def process(self, context):
                return context
        
        step = DummyStep("removable")
        pipeline.add_step(step)
        
        result = pipeline.remove_step("removable")
        assert result
        assert len(pipeline.steps) == 0

    def test_remove_nonexistent_step(self):
        """Test removing nonexistent step"""
        pipeline = CleaningPipeline()
        
        result = pipeline.remove_step("nonexistent")
        assert not result

    def test_get_step_names(self):
        """Test getting step names"""
        pipeline = CleaningPipeline()
        
        class DummyStep(CleaningStep):
            def __init__(self, name):
                super().__init__(name)
            async def process(self, context):
                return context
        
        pipeline.add_steps([DummyStep("step1"), DummyStep("step2")])
        
        names = pipeline.get_step_names()
        assert names == ["step1", "step2"]

    def test_execute_no_steps_error(self):
        """Test execute with no steps raises error"""
        pipeline = CleaningPipeline()
        
        response = AIResponse(
            content="test",
            model="test",
            latency_ms=100
        )
        
        with pytest.raises(PipelineConfigurationError):
            asyncio.run(pipeline.execute(
                execution_id="test",
                report_id=1,
                brand="test",
                question="test",
                model="test",
                response=response
            ))

    def test_execute_single_step(self):
        """Test executing single step"""
        pipeline = CleaningPipeline()
        
        class DummyStep(CleaningStep):
            async def process(self, context):
                context.response_content = "processed"
                return context
        
        pipeline.add_step(DummyStep("dummy"))
        
        response = AIResponse(
            content="original",
            model="test",
            latency_ms=100
        )
        
        result = asyncio.run(pipeline.execute(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            response=response
        ))
        
        assert result.cleaned_text == "processed"

    def test_execute_multiple_steps(self):
        """Test executing multiple steps"""
        pipeline = CleaningPipeline()
        
        class AppendStep(CleaningStep):
            def __init__(self, name, text):
                super().__init__(name)
                self.text = text
            async def process(self, context):
                context.response_content += self.text
                return context
        
        pipeline.add_steps([
            AppendStep("step1", "A"),
            AppendStep("step2", "B"),
            AppendStep("step3", "C"),
        ])
        
        response = AIResponse(
            content="",
            model="test",
            latency_ms=100
        )
        
        result = asyncio.run(pipeline.execute(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            response=response
        ))
        
        assert result.cleaned_text == "ABC"
        assert len(result.steps_applied) == 3

    def test_execute_with_step_error_stop(self):
        """Test step error with stop_on_error"""
        pipeline = CleaningPipeline(config={'stop_on_error': True})
        
        class FailingStep(CleaningStep):
            async def process(self, context):
                raise Exception("Test error")
        
        pipeline.add_step(FailingStep("failing"))
        
        response = AIResponse(
            content="test",
            model="test",
            latency_ms=100
        )
        
        with pytest.raises(StepExecutionError):
            asyncio.run(pipeline.execute(
                execution_id="test",
                report_id=1,
                brand="test",
                question="test",
                model="test",
                response=response
            ))

    def test_execute_with_step_error_continue(self):
        """Test step error with continue"""
        pipeline = CleaningPipeline(config={'stop_on_error': False})
        
        class FailingStep(CleaningStep):
            async def process(self, context):
                raise Exception("Test error")
        
        class SuccessStep(CleaningStep):
            async def process(self, context):
                context.response_content = "success"
                return context
        
        pipeline.add_steps([FailingStep("failing"), SuccessStep("success")])
        
        response = AIResponse(
            content="test",
            model="test",
            latency_ms=100
        )
        
        result = asyncio.run(pipeline.execute(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            response=response
        ))
        
        # Should continue to success step
        assert result.cleaned_text == "success"
        assert len(result.errors) > 0

    def test_create_default_pipeline(self):
        """Test creating default pipeline"""
        pipeline = create_default_pipeline()
        
        assert len(pipeline.steps) == 6
        assert 'text_extractor' in pipeline.get_step_names()
        assert 'validator' in pipeline.get_step_names()
        assert 'entity_recognizer' in pipeline.get_step_names()

    def test_create_minimal_pipeline(self):
        """Test creating minimal pipeline"""
        pipeline = create_minimal_pipeline()
        
        assert len(pipeline.steps) == 2
        assert 'text_extractor' in pipeline.get_step_names()
        assert 'validator' in pipeline.get_step_names()

    def test_execute_with_real_response(self):
        """Test execution with realistic response"""
        pipeline = create_default_pipeline(competitors=['三星', '华为'])
        
        response = AIResponse(
            content="<p>苹果公司发布新款 iPhone，在市场上与三星和华为竞争。</p>",
            model="test",
            latency_ms=100
        )
        
        result = asyncio.run(pipeline.execute(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="苹果手机市场表现如何？",
            model="test",
            response=response
        ))
        
        assert isinstance(result.cleaned_text, str)
        assert len(result.cleaned_text) > 0
        assert result.geo_data is not None
        assert result.quality is not None
