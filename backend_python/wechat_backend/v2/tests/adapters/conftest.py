"""
Test Fixtures for Adapter Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from wechat_backend.v2.adapters.models import AIRequest, AIResponse


@pytest.fixture
def sample_ai_request():
    """Create a sample AI request for testing"""
    return AIRequest(
        prompt="请分析品牌特斯拉在市场上的表现",
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=2000,
        timeout=60,
        request_id="test-request-123"
    )


@pytest.fixture
def sample_ai_response():
    """Create a sample AI response for testing"""
    return AIResponse(
        content='''```json
{
    "brand": "特斯拉",
    "sentiment": "positive",
    "confidence": 0.85,
    "keywords": ["电动车", "创新", "自动驾驶"],
    "regions": ["中国", "美国", "欧洲"]
}
```''',
        model="deepseek-chat",
        latency_ms=1500,
        prompt_tokens=50,
        completion_tokens=200,
        total_tokens=250,
        finish_reason="stop",
        provider="deepseek",
        request_id="test-request-123"
    )


@pytest.fixture
def sample_geo_json_response():
    """Sample JSON response for GEO data parsing"""
    return {
        "brand": "特斯拉",
        "sentiment": "positive",
        "confidence": 0.85,
        "keywords": ["电动车", "创新", "自动驾驶"],
        "regions": ["中国", "美国", "欧洲"],
        "market_share": 0.15,
        "competitors": ["比亚迪", "蔚来", "小鹏"]
    }


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for HTTP request testing"""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.post = MagicMock(return_value=mock_response)
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        yield mock_session


@pytest.fixture
def deepseek_adapter():
    """Create a DeepSeek adapter instance"""
    from wechat_backend.v2.adapters.deepseek_adapter import DeepSeekAdapter
    
    with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
        adapter = DeepSeekAdapter()
        yield adapter


@pytest.fixture
def doubao_adapter():
    """Create a Doubao adapter instance"""
    from wechat_backend.v2.adapters.doubao_adapter import DoubaoAdapter
    
    with patch.dict('os.environ', {'DOUBAO_API_KEY': 'test-key'}):
        adapter = DoubaoAdapter()
        yield adapter


@pytest.fixture
def qwen_adapter():
    """Create a Qwen adapter instance"""
    from wechat_backend.v2.adapters.qwen_adapter import QwenAdapter
    
    with patch.dict('os.environ', {'QWEN_API_KEY': 'test-key'}):
        adapter = QwenAdapter()
        yield adapter
