"""
Pytest Configuration for Cleaning Tests
"""

import pytest
import sys
import os

# Add backend_python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend_python'))


@pytest.fixture
def sample_context():
    """Create a sample pipeline context"""
    from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
    
    return PipelineContext(
        execution_id="test_exec",
        report_id=1,
        brand="测试品牌",
        question="测试问题",
        model="test-model",
        raw_response={},
        response_content="测试内容"
    )


@pytest.fixture
def sample_ai_response():
    """Create a sample AI response"""
    from wechat_backend.v2.adapters.models import AIResponse
    
    return AIResponse(
        content="<p>这是测试内容</p>",
        model="test-model",
        latency_ms=100
    )
