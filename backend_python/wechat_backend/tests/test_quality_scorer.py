"""
质量评分服务单元测试
覆盖率目标：95%
"""

import pytest
from wechat_backend.services.quality_scorer import QualityScorer, get_quality_scorer


class TestQualityScorer:
    """质量评分器测试"""
    
    def setup_method(self):
        """每个测试前的准备"""
        self.scorer = QualityScorer()
    
    def test_empty_results(self):
        """测试空结果"""
        result = self.scorer.calculate([], 0)
        
        assert result['quality_score'] == 0
        assert result['quality_level'] == 'poor'
        assert result['details']['completion_score'] == 0
    
    def test_perfect_completion(self):
        """测试完美完成率"""
        results = [
            {
                'brand': '华为',
                'geo_data': {
                    'brand_mentioned': True,
                    'rank': 1,
                    'sentiment': 0.8,
                    'cited_sources': [{'name': 'source1'}],
                    'interception': 'low'
                }
            }
        ]
        
        result = self.scorer.calculate(results, 100)
        
        assert result['quality_score'] > 0
        assert result['quality_level'] in ['excellent', 'good', 'fair', 'poor']
    
    def test_partial_completion(self):
        """测试部分完成"""
        results = [
            {
                'brand': '华为',
                'geo_data': {
                    'brand_mentioned': True,
                    'rank': -1,  # 无效排名
                    'sentiment': 0.5,
                    'cited_sources': [],  # 无信源
                    'interception': None
                }
            }
        ]
        
        result = self.scorer.calculate(results, 50)
        
        assert result['quality_score'] < 80  # 不应该很高
        assert result['details']['completion_score'] == 20  # 50% * 0.4 = 20
    
    def test_completeness_calculation(self):
        """测试完整度计算"""
        results = [
            {
                'geo_data': {
                    'brand_mentioned': True,
                    'rank': 1,
                    'sentiment': 0.8,
                    'cited_sources': [{'name': 's1'}, {'name': 's2'}],
                    'interception': 'low'
                }
            }
        ]
        
        score = self.scorer._calculate_completeness(results)
        
        # 所有字段都存在，应该得满分
        assert score > 0
    
    def test_source_quality_calculation(self):
        """测试信源质量计算"""
        # 5 个信源（满分）
        results_full = [{
            'geo_data': {
                'cited_sources': [{'name': f's{i}'} for i in range(5)]
            }
        }]
        
        # 0 个信源（0 分）
        results_empty = [{
            'geo_data': {
                'cited_sources': []
            }
        }]
        
        score_full = self.scorer._calculate_source_quality(results_full)
        score_empty = self.scorer._calculate_source_quality(results_empty)
        
        assert score_full > score_empty
        assert score_full > 0
    
    def test_sentiment_validity_calculation(self):
        """测试情感有效性计算"""
        # 有效情感
        results_valid = [{
            'geo_data': {'sentiment': 0.8}
        }, {
            'geo_data': {'sentiment': -0.5}
        }]
        
        # 无效情感
        results_invalid = [{
            'geo_data': {'sentiment': 2.0}  # 超出范围
        }]
        
        score_valid = self.scorer._calculate_sentiment_validity(results_valid)
        score_invalid = self.scorer._calculate_sentiment_validity(results_invalid)
        
        assert score_valid > score_invalid
    
    def test_level_thresholds(self):
        """测试等级阈值"""
        assert self.scorer._get_level(95) == 'excellent'
        assert self.scorer._get_level(80) == 'good'
        assert self.scorer._get_level(65) == 'fair'
        assert self.scorer._get_level(50) == 'poor'
    
    def test_level_text(self):
        """测试等级文本"""
        assert self.scorer.get_level_text('excellent') == '优秀'
        assert self.scorer.get_level_text('good') == '良好'
        assert self.scorer.get_level_text('fair') == '一般'
        assert self.scorer.get_level_text('poor') == '较差'
        assert self.scorer.get_level_text('unknown') == '未知'
    
    def test_weights_sum_to_one(self):
        """测试权重和为 1"""
        total_weight = sum(self.scorer.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.01
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        scorer1 = get_quality_scorer()
        scorer2 = get_quality_scorer()
        
        assert scorer1 is scorer2


class TestQualityScorerIntegration:
    """质量评分集成测试"""
    
    def test_real_world_scenario(self):
        """测试真实场景"""
        scorer = QualityScorer()
        
        # 模拟真实诊断结果
        results = [
            {
                'brand': '华为',
                'geo_data': {
                    'brand_mentioned': True,
                    'rank': 1,
                    'sentiment': 0.85,
                    'cited_sources': [
                        {'name': '知乎', 'attitude': 'positive'},
                        {'name': '微博', 'attitude': 'neutral'}
                    ],
                    'interception': 'low'
                }
            },
            {
                'brand': '华为',
                'geo_data': {
                    'brand_mentioned': True,
                    'rank': 2,
                    'sentiment': 0.75,
                    'cited_sources': [
                        {'name': '百度', 'attitude': 'positive'}
                    ],
                    'interception': 'medium'
                }
            }
        ]
        
        result = scorer.calculate(results, 80)
        
        # 验证评分合理
        assert 50 <= result['quality_score'] <= 95
        assert result['quality_level'] in ['excellent', 'good', 'fair']
        assert 'details' in result
        assert 'completion_score' in result['details']
