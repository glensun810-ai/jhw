"""
GEO Data Parsing Tests

Tests for the parse_geo_data method in all adapters.
This is a critical feature for P2-T1 AI Platform Standardized Data Interface Layer.
"""

import pytest
from unittest.mock import patch
from wechat_backend.v2.adapters.models import AIResponse


class TestDeepSeekGeoParsing:
    """Test DeepSeek adapter GEO data parsing"""
    
    @pytest.fixture
    def adapter(self):
        from wechat_backend.v2.adapters.deepseek_adapter import DeepSeekAdapter
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
            return DeepSeekAdapter()
    
    def test_parse_geo_data_standard_json(self, adapter):
        """Test parsing standard JSON response"""
        response = AIResponse(
            content='''{
                "brand": "特斯拉",
                "sentiment": "positive",
                "confidence": 0.85,
                "keywords": ["电动车", "创新"],
                "regions": ["中国", "美国"]
            }''',
            model="deepseek-chat",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "特斯拉"
        assert result['sentiment'] == "positive"
        assert result['confidence'] == 0.85
        assert result['keywords'] == ["电动车", "创新"]
        assert result['regions'] == ["中国", "美国"]
        assert 'raw_data' in result
    
    def test_parse_geo_data_markdown_json(self, adapter):
        """Test parsing JSON wrapped in markdown code blocks"""
        response = AIResponse(
            content='''```json
{
    "brand": "比亚迪",
    "sentiment": "positive",
    "confidence": 0.9,
    "keywords": ["新能源", "电池技术"],
    "regions": ["中国", "欧洲"]
}
```''',
            model="deepseek-chat",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "比亚迪"
        assert result['sentiment'] == "positive"
        assert result['confidence'] == 0.9
    
    def test_parse_geo_data_empty_content(self, adapter):
        """Test parsing empty response"""
        response = AIResponse(
            content="",
            model="deepseek-chat",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == ""
        assert result['sentiment'] == "neutral"
        assert result['confidence'] == 0.0
        assert result['keywords'] == []
        assert result['regions'] == []
    
    def test_parse_geo_data_invalid_json(self, adapter):
        """Test parsing invalid JSON response"""
        response = AIResponse(
            content="This is not valid JSON at all!",
            model="deepseek-chat",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['sentiment'] == "neutral"
        assert result['confidence'] == 0.0
        assert result['raw_data'] == {'content': "This is not valid JSON at all!"}
    
    def test_parse_geo_data_alternative_fields(self, adapter):
        """Test parsing with alternative field names"""
        response = AIResponse(
            content='''{
                "brand_name": "蔚来",
                "score": 0.75,
                "tags": ["高端", "智能"],
                "geo_data": {
                    "regions": ["上海", "北京"]
                }
            }''',
            model="deepseek-chat",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "蔚来"
        assert result['confidence'] == 0.75
        assert result['keywords'] == ["高端", "智能"]
        assert result['regions'] == ["上海", "北京"]


class TestDoubaoGeoParsing:
    """Test Doubao adapter GEO data parsing"""
    
    @pytest.fixture
    def adapter(self):
        from wechat_backend.v2.adapters.doubao_adapter import DoubaoAdapter
        with patch.dict('os.environ', {'DOUBAO_API_KEY': 'test-key'}):
            return DoubaoAdapter()
    
    def test_parse_geo_data_standard_json(self, adapter):
        """Test parsing standard JSON response"""
        response = AIResponse(
            content='''{
                "brand": "小米",
                "sentiment": "neutral",
                "confidence": 0.7,
                "keywords": ["手机", "IoT"],
                "regions": ["中国", "印度"]
            }''',
            model="doubao-lite-32k",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "小米"
        assert result['sentiment'] == "neutral"
        assert result['confidence'] == 0.7
        assert result['keywords'] == ["手机", "IoT"]
    
    def test_parse_geo_data_markdown_blocks(self, adapter):
        """Test parsing JSON with markdown code blocks"""
        response = AIResponse(
            content='''```
{
    "brand": "华为",
    "sentiment": "positive",
    "confidence": 0.88,
    "keywords": ["5G", "芯片"],
    "regions": ["中国", "非洲"]
}
```''',
            model="doubao-lite-32k",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "华为"
        assert result['sentiment'] == "positive"
        assert result['confidence'] == 0.88


class TestQwenGeoParsing:
    """Test Qwen adapter GEO data parsing"""
    
    @pytest.fixture
    def adapter(self):
        from wechat_backend.v2.adapters.qwen_adapter import QwenAdapter
        with patch.dict('os.environ', {'QWEN_API_KEY': 'test-key'}):
            return QwenAdapter()
    
    def test_parse_geo_data_standard_json(self, adapter):
        """Test parsing standard JSON response"""
        response = AIResponse(
            content='''{
                "brand": "理想汽车",
                "sentiment": "positive",
                "confidence": 0.82,
                "keywords": ["增程式", "家庭用车"],
                "regions": ["中国", "中东"]
            }''',
            model="qwen-turbo",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "理想汽车"
        assert result['sentiment'] == "positive"
        assert result['confidence'] == 0.82
        assert result['keywords'] == ["增程式", "家庭用车"]
    
    def test_parse_geo_data_with_whitespace(self, adapter):
        """Test parsing JSON with extra whitespace"""
        response = AIResponse(
            content='''
            
            ```json
            {
                "brand": "小鹏汽车",
                "sentiment": "neutral",
                "confidence": 0.65,
                "keywords": ["自动驾驶", "智能化"],
                "regions": ["中国"]
            }
            ```
            
            ''',
            model="qwen-turbo",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "小鹏汽车"
        assert result['sentiment'] == "neutral"
        assert result['confidence'] == 0.65


class TestGeoParsingEdgeCases:
    """Test edge cases across all adapters"""
    
    @pytest.fixture(params=['deepseek', 'doubao', 'qwen'])
    def adapter(self, request):
        """Parametrized fixture for testing all adapters"""
        provider = request.param
        if provider == 'deepseek':
            from wechat_backend.v2.adapters.deepseek_adapter import DeepSeekAdapter
            with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
                return DeepSeekAdapter()
        elif provider == 'doubao':
            from wechat_backend.v2.adapters.doubao_adapter import DoubaoAdapter
            with patch.dict('os.environ', {'DOUBAO_API_KEY': 'test-key'}):
                return DoubaoAdapter()
        else:  # qwen
            from wechat_backend.v2.adapters.qwen_adapter import QwenAdapter
            with patch.dict('os.environ', {'QWEN_API_KEY': 'test-key'}):
                return QwenAdapter()
    
    def test_parse_geo_data_none_content(self, adapter):
        """Test parsing None content"""
        response = AIResponse(
            content=None,
            model="test-model",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == ""
        assert result['sentiment'] == "neutral"
        assert result['confidence'] == 0.0
    
    def test_parse_geo_data_minimal_json(self, adapter):
        """Test parsing minimal JSON with only required fields"""
        response = AIResponse(
            content='{"brand": "测试品牌"}',
            model="test-model",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        assert result['brand'] == "测试品牌"
        assert result['sentiment'] == "neutral"  # default
        assert result['confidence'] == 0.0  # default
    
    def test_parse_geo_data_malformed_markdown(self, adapter):
        """Test parsing with malformed markdown blocks"""
        response = AIResponse(
            content='```json{invalid markdown',
            model="test-model",
            latency_ms=100
        )
        
        result = adapter.parse_geo_data(response)
        
        # Should fall back to default with raw content
        assert result['sentiment'] == "neutral"
        assert 'content' in result['raw_data']
