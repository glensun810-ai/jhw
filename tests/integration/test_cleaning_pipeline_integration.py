"""
Integration Tests for Cleaning Pipeline
"""

import pytest
import asyncio
import os
from wechat_backend.v2.cleaning.pipeline import create_default_pipeline
from wechat_backend.v2.adapters.models import AIResponse


class TestCleaningPipelineIntegration:
    """Cleaning pipeline integration tests"""

    @pytest.mark.asyncio
    async def test_pipeline_with_html_content(self):
        """Test pipeline with HTML content"""
        pipeline = create_default_pipeline(competitors=['三星', '华为'])
        
        response = AIResponse(
            content="<p><strong>苹果公司</strong>发布新款产品，在市场上与&lt;三星&gt;和華為競爭。</p>",
            model="test",
            latency_ms=100
        )
        
        result = await pipeline.execute(
            execution_id="integration_test_1",
            report_id=1,
            brand="苹果",
            question="苹果手机市场表现如何？",
            model="test",
            response=response
        )
        
        # Verify cleaning results
        assert result.cleaned_text
        assert len(result.cleaned_text) > 0
        assert "<" not in result.cleaned_text  # HTML removed
        assert result.geo_data
        assert result.quality
        assert result.quality.overall_score >= 0

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_response(self):
        """Test pipeline with empty response"""
        pipeline = create_default_pipeline()
        
        response = AIResponse(
            content="",
            model="test",
            latency_ms=100
        )
        
        result = await pipeline.execute(
            execution_id="integration_test_2",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            response=response
        )
        
        # Should handle gracefully with warnings
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_very_long_text(self):
        """Test pipeline with very long text"""
        pipeline = create_default_pipeline()
        
        # Create very long content
        long_content = "<p>" + "苹果公司" * 1000 + "</p>"
        
        response = AIResponse(
            content=long_content,
            model="test",
            latency_ms=100
        )
        
        result = await pipeline.execute(
            execution_id="integration_test_3",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            response=response
        )
        
        # Should be truncated
        assert len(result.cleaned_text) <= 10000

    @pytest.mark.asyncio
    async def test_pipeline_entity_recognition(self):
        """Test entity recognition in pipeline"""
        pipeline = create_default_pipeline(competitors=['三星', '华为', '小米'])
        
        content = "苹果公司在手机市场与三星、华为和小米竞争激烈。苹果的产品质量很好。"
        
        response = AIResponse(
            content=content,
            model="test",
            latency_ms=100
        )
        
        result = await pipeline.execute(
            execution_id="integration_test_4",
            report_id=1,
            brand="苹果",
            question="手机市场竞争情况",
            model="test",
            response=response
        )
        
        # Verify entity recognition
        assert len(result.entities) > 0
        brand_mentions = [e for e in result.entities if e.entity_type == 'brand']
        competitor_mentions = [e for e in result.entities if e.entity_type == 'competitor']
        
        assert len(brand_mentions) >= 1
        assert len(competitor_mentions) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_geo_data_preparation(self):
        """Test GEO data preparation"""
        pipeline = create_default_pipeline()
        
        content = "苹果公司发布新产品。这款产品在市场上表现很好！了解更多请访问 https://apple.com"
        
        response = AIResponse(
            content=content,
            model="test",
            latency_ms=100
        )
        
        result = await pipeline.execute(
            execution_id="integration_test_5",
            report_id=1,
            brand="苹果",
            question="苹果新产品",
            model="test",
            response=response
        )
        
        # Verify GEO data
        assert result.geo_data
        assert result.geo_data.text_length > 0
        assert result.geo_data.sentence_count >= 2
        assert result.geo_data.has_brand_mention
        assert result.geo_data.contains_urls
        assert result.geo_data.contains_numbers

    @pytest.mark.asyncio
    async def test_pipeline_quality_scoring(self):
        """Test quality scoring"""
        pipeline = create_default_pipeline()
        
        # Good quality content
        good_content = "苹果公司在智能手机市场占据重要地位。其 iPhone 系列产品以高质量和创新设计闻名。消费者对苹果产品的评价普遍较高。"
        
        response = AIResponse(
            content=good_content,
            model="test",
            latency_ms=100
        )
        
        result = await pipeline.execute(
            execution_id="integration_test_6",
            report_id=1,
            brand="苹果",
            question="苹果手机市场地位",
            model="test",
            response=response
        )
        
        # Verify quality score
        assert result.quality
        assert result.quality.overall_score > 50  # Should be decent score
        
        # Short content should have lower score
        short_response = AIResponse(
            content="好",
            model="test",
            latency_ms=100
        )
        
        short_result = await pipeline.execute(
            execution_id="integration_test_7",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            response=short_response
        )
        
        assert short_result.quality.overall_score < result.quality.overall_score

    @pytest.mark.asyncio
    async def test_pipeline_batch_execution(self):
        """Test batch execution"""
        pipeline = create_default_pipeline()
        
        items = [
            {
                'execution_id': f'batch_{i}',
                'report_id': 1,
                'brand': '苹果',
                'question': 'test',
                'model': 'test',
                'response': AIResponse(
                    content=f"苹果公司内容{i}",
                    model="test",
                    latency_ms=100
                )
            }
            for i in range(3)
        ]
        
        results = await pipeline.execute_batch(items)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result.cleaned_text, str)

    @pytest.mark.skipif(not os.getenv('DEEPSEEK_API_KEY'), reason="DEEPSEEK_API_KEY not set")
    @pytest.mark.asyncio
    async def test_pipeline_with_real_adapter(self):
        """Test pipeline with real adapter (requires API key)"""
        from wechat_backend.v2.adapters.base import get_adapter
        
        # 1. Get adapter
        adapter = get_adapter('deepseek')
        
        # 2. Send request
        from wechat_backend.v2.adapters.models import AIRequest
        request = AIRequest(prompt="介绍一下苹果公司", model="deepseek-chat")
        response = await adapter.send(request)
        
        # 3. Clean data
        pipeline = create_default_pipeline()
        cleaned = await pipeline.execute(
            execution_id="integration_test_real",
            report_id=1,
            brand="苹果",
            question="介绍一下苹果公司",
            model="deepseek",
            response=response
        )
        
        # 4. Verify results
        assert cleaned.cleaned_text
        assert len(cleaned.cleaned_text) > 0
        assert cleaned.geo_data
        assert cleaned.quality
        assert cleaned.quality.overall_score > 0
