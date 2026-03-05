"""
报告聚合器单元测试

测试覆盖：
1. 报告聚合主流程
2. 品牌分数计算
3. SOV 计算
4. 风险评分计算
5. 品牌健康度计算
6. 洞察文本生成
7. 首次提及率计算
8. 拦截风险计算

@author: 系统架构组
@date: 2026-03-04
"""

import pytest
from datetime import datetime
from wechat_backend.services.report_aggregator import (
    ReportAggregator,
    get_report_aggregator,
    aggregate_report
)


class TestReportAggregatorInit:
    """测试报告聚合器初始化"""
    
    def test_init(self):
        """测试初始化"""
        aggregator = ReportAggregator()
        assert aggregator is not None
        assert isinstance(aggregator.GRADE_MAPPING, dict)
        assert isinstance(aggregator.SCORE_SUMMARY, dict)
    
    def test_get_report_aggregator_singleton(self):
        """测试单例模式"""
        aggregator1 = get_report_aggregator()
        aggregator2 = get_report_aggregator()
        assert aggregator1 is aggregator2
    
    def test_aggregate_report_function(self):
        """测试便捷函数"""
        raw_results = [
            {'brand': 'BrandA', 'question': 'Q1', 'model': 'Model1', 'score': 80}
        ]
        report = aggregate_report(raw_results, 'BrandA', ['BrandB'])
        
        assert report is not None
        assert report['brandName'] == 'BrandA'
        assert 'brandScores' in report
        assert 'timestamp' in report


class TestAggregateReport:
    """测试报告聚合主流程"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    @pytest.fixture
    def sample_results(self):
        return [
            {
                'brand': 'BrandA',
                'question': '什么是最好的手机品牌？',
                'model': 'Qwen',
                'score': 85,
                'sentiment': 'positive',
                'response': {'content': 'BrandA 是很好的品牌'},
                'geo_data': {'brand_mentioned': True}
            },
            {
                'brand': 'BrandA',
                'question': '推荐一款笔记本电脑',
                'model': 'Qwen',
                'score': 75,
                'sentiment': 'neutral',
                'response': {'content': 'BrandA 的笔记本不错'},
                'geo_data': {'brand_mentioned': True}
            },
            {
                'brand': 'BrandB',
                'question': '什么是最好的手机品牌？',
                'model': 'Qwen',
                'score': 70,
                'sentiment': 'positive',
                'response': {'content': 'BrandB 也不错'},
                'geo_data': {'brand_mentioned': True}
            }
        ]
    
    def test_aggregate_basic(self, aggregator, sample_results):
        """测试基本聚合功能"""
        report = aggregator.aggregate(
            raw_results=sample_results,
            brand_name='BrandA',
            competitors=['BrandB']
        )
        
        assert report is not None
        assert report['brandName'] == 'BrandA'
        assert report['competitors'] == ['BrandB']
        assert 'brandScores' in report
        assert 'sov' in report
        assert 'risk' in report
        assert 'health' in report
        assert 'insights' in report
        assert 'overallScore' in report
    
    def test_aggregate_with_additional_data(self, aggregator, sample_results):
        """测试带额外数据的聚合"""
        additional_data = {
            'semantic_drift_data': {'drift_score': 0.1},
            'recommendation_data': {'recommendations': ['建议 1']},
            'negative_sources': [{'source': 'PlatformA'}],
            'competitive_analysis': {'analysis': '分析结果'}
        }
        
        report = aggregator.aggregate(
            raw_results=sample_results,
            brand_name='BrandA',
            competitors=['BrandB'],
            additional_data=additional_data
        )
        
        assert report['semanticDriftData'] == {'drift_score': 0.1}
        assert report['recommendationData'] == {'recommendations': ['建议 1']}
        assert report['negativeSources'] == [{'source': 'PlatformA'}]
        assert report['competitiveAnalysis'] == {'analysis': '分析结果'}
    
    def test_aggregate_empty_results(self, aggregator):
        """测试空结果聚合"""
        report = aggregator.aggregate(
            raw_results=[],
            brand_name='BrandA',
            competitors=['BrandB']
        )
        
        assert report is not None
        assert report['brandName'] == 'BrandA'
        assert report['overallScore'] == 50  # 默认分数
        assert report['brandScores']['BrandA']['overallScore'] == 50
    
    def test_aggregate_timestamp(self, aggregator, sample_results):
        """测试时间戳"""
        report = aggregator.aggregate(
            raw_results=sample_results,
            brand_name='BrandA',
            competitors=['BrandB']
        )
        
        assert 'timestamp' in report
        # 验证是 ISO 格式
        datetime.fromisoformat(report['timestamp'])


class TestCalculateBrandScores:
    """测试品牌分数计算"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_calculate_brand_scores_basic(self, aggregator):
        """测试基本品牌分数计算"""
        results = [
            {'brand': 'BrandA', 'score': 80},
            {'brand': 'BrandA', 'score': 90},
            {'brand': 'BrandB', 'score': 70}
        ]
        
        scores = aggregator._calculate_brand_scores(
            results, 'BrandA', ['BrandB']
        )
        
        assert 'BrandA' in scores
        assert 'BrandB' in scores
        assert scores['BrandA']['overallScore'] == 85  # (80+90)/2
        assert scores['BrandB']['overallScore'] == 70
    
    def test_calculate_brand_scores_empty(self, aggregator):
        """测试空结果"""
        scores = aggregator._calculate_brand_scores(
            [], 'BrandA', ['BrandB']
        )
        
        assert scores['BrandA']['overallScore'] == 50
        assert scores['BrandA']['overallGrade'] == 'C'
        assert scores['BrandB']['overallScore'] == 50
    
    def test_calculate_brand_scores_grade(self, aggregator):
        """测试等级计算"""
        results = [{'brand': 'BrandA', 'score': 95}]
        scores = aggregator._calculate_brand_scores(
            results, 'BrandA', []
        )
        assert scores['BrandA']['overallGrade'] == 'A+'
        
        results = [{'brand': 'BrandA', 'score': 85}]
        scores = aggregator._calculate_brand_scores(
            results, 'BrandA', []
        )
        assert scores['BrandA']['overallGrade'] == 'A'
        
        results = [{'brand': 'BrandA', 'score': 75}]
        scores = aggregator._calculate_brand_scores(
            results, 'BrandA', []
        )
        assert scores['BrandA']['overallGrade'] == 'B'
        
        results = [{'brand': 'BrandA', 'score': 65}]
        scores = aggregator._calculate_brand_scores(
            results, 'BrandA', []
        )
        assert scores['BrandA']['overallGrade'] == 'C'
        
        results = [{'brand': 'BrandA', 'score': 50}]
        scores = aggregator._calculate_brand_scores(
            results, 'BrandA', []
        )
        assert scores['BrandA']['overallGrade'] == 'D'


class TestCalculateSOV:
    """测试 SOV 计算"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_calculate_sov_basic(self, aggregator):
        """测试基本 SOV 计算"""
        results = [
            {'brand': 'BrandA'},
            {'brand': 'BrandA'},
            {'brand': 'BrandA'},
            {'brand': 'BrandB'},
            {'brand': 'BrandB'}
        ]
        
        sov = aggregator._calculate_sov(results, 'BrandA', ['BrandB'])
        
        assert sov['brandMentions'] == 3
        assert sov['competitorMentions'] == 2
        assert sov['totalMentions'] == 5
        assert sov['brandSOV'] == 60  # 3/5 * 100
        assert sov['competitorSOV'] == 40  # 2/5 * 100
    
    def test_calculate_sov_empty(self, aggregator):
        """测试空结果"""
        sov = aggregator._calculate_sov([], 'BrandA', ['BrandB'])
        
        assert sov['brandMentions'] == 0
        assert sov['competitorMentions'] == 0
        assert sov['totalMentions'] == 0
        assert sov['brandSOV'] == 0
        assert sov['competitorSOV'] == 0


class TestCalculateRisk:
    """测试风险评分计算"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_calculate_risk_basic(self, aggregator):
        """测试基本风险计算"""
        results = [
            {'brand': 'BrandA', 'sentiment': 'positive'},
            {'brand': 'BrandA', 'sentiment': 'positive'},
            {'brand': 'BrandA', 'sentiment': 'negative'},
        ]
        
        risk = aggregator._calculate_risk(results, 'BrandA')
        
        assert risk['positiveInterceptions'] == 2
        assert risk['negativeInterceptions'] == 1
        assert risk['totalMentions'] == 3
        assert risk['riskScore'] == 33  # 1/3 * 100 ≈ 33
        assert risk['riskLevel'] == 'medium'
    
    def test_calculate_risk_high(self, aggregator):
        """测试高风险"""
        results = [
            {'brand': 'BrandA', 'sentiment': 'negative'},
            {'brand': 'BrandA', 'sentiment': 'negative'},
            {'brand': 'BrandA', 'sentiment': 'positive'},
        ]
        
        risk = aggregator._calculate_risk(results, 'BrandA')
        
        assert risk['riskScore'] == 67  # 2/3 * 100 ≈ 67
        assert risk['riskLevel'] == 'high'
    
    def test_calculate_risk_empty(self, aggregator):
        """测试空结果"""
        risk = aggregator._calculate_risk([], 'BrandA')
        
        assert risk['riskScore'] == 50
        assert risk['riskLevel'] == 'medium'
        assert risk['totalMentions'] == 0


class TestCalculateBrandHealth:
    """测试品牌健康度计算"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_calculate_brand_health_basic(self, aggregator):
        """测试基本健康度计算"""
        brand_score = {
            'overallAuthority': 80,
            'overallVisibility': 70,
            'overallPurity': 90,
            'overallConsistency': 60
        }
        
        health = aggregator._calculate_brand_health(brand_score)
        
        assert health['score'] == 75  # (80+70+90+60)/4
        assert health['level'] == 'good'
        assert health['authority'] == 80
        assert health['visibility'] == 70
        assert health['purity'] == 90
        assert health['consistency'] == 60
    
    def test_calculate_brand_health_excellent(self, aggregator):
        """测试优秀健康度"""
        brand_score = {
            'overallAuthority': 90,
            'overallVisibility': 85,
            'overallPurity': 95,
            'overallConsistency': 80
        }
        
        health = aggregator._calculate_brand_health(brand_score)
        
        assert health['score'] == 88
        assert health['level'] == 'excellent'
    
    def test_calculate_brand_health_empty(self, aggregator):
        """测试空分数"""
        health = aggregator._calculate_brand_health({})
        
        assert health['score'] == 50
        assert health['level'] == 'medium'


class TestGenerateInsights:
    """测试洞察文本生成"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_generate_insights_high_score(self, aggregator):
        """测试高分数洞察"""
        brand_score = {'overallScore': 85}
        
        insights = aggregator._generate_insights(brand_score, 'BrandA')
        
        assert '表现卓越' in insights['summary']
        assert len(insights['strengths']) > 0
        assert len(insights['weaknesses']) > 0
        assert len(insights['opportunities']) > 0
        assert len(insights['threats']) > 0
    
    def test_generate_insights_low_score(self, aggregator):
        """测试低分数洞察"""
        brand_score = {'overallScore': 40}
        
        insights = aggregator._generate_insights(brand_score, 'BrandA')
        
        # 40 分对应"表现一般，需要加强"
        assert '需要加强' in insights['summary'] or '需要改进' in insights['summary']
    
    def test_generate_insights_empty(self, aggregator):
        """测试空分数"""
        insights = aggregator._generate_insights({}, 'BrandA')
        
        assert '暂无' in insights['summary']


class TestCalculateFirstMentionByPlatform:
    """测试首次提及率计算"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_calculate_first_mention_basic(self, aggregator):
        """测试基本首次提及率计算"""
        results = [
            {'model': 'Qwen', 'geo_data': {'brand_mentioned': True}},
            {'model': 'Qwen', 'geo_data': {'brand_mentioned': True}},
            {'model': 'Qwen', 'geo_data': {'brand_mentioned': False}},
            {'model': 'Doubao', 'geo_data': {'brand_mentioned': True}},
        ]
        
        first_mention = aggregator._calculate_first_mention_by_platform(results)
        
        qwen_data = next(f for f in first_mention if f['platform'] == 'Qwen')
        doubao_data = next(f for f in first_mention if f['platform'] == 'Doubao')
        
        assert qwen_data['total'] == 3
        assert qwen_data['firstMention'] == 2
        assert qwen_data['rate'] == 67  # 2/3 * 100 ≈ 67
        
        assert doubao_data['total'] == 1
        assert doubao_data['firstMention'] == 1
        assert doubao_data['rate'] == 100


class TestCalculateInterceptionRisks:
    """测试拦截风险计算"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_calculate_interception_risks_basic(self, aggregator):
        """测试基本拦截风险计算"""
        results = [
            {'geo_data': {'interception': 'BrandB'}},
            {'geo_data': {'interception': 'BrandB'}},
            {'geo_data': {'interception': 'BrandC'}},
            {'geo_data': {'interception': ''}},
        ]
        
        risks = aggregator._calculate_interception_risks(results, 'BrandA')
        
        assert len(risks) > 0
        brand_b_risk = next((r for r in risks if r['competitor'] == 'BrandB'), None)
        assert brand_b_risk is not None
        assert brand_b_risk['count'] == 2
    
    def test_calculate_interception_risks_empty(self, aggregator):
        """测试空拦截"""
        results = [
            {'geo_data': {'interception': ''}},
            {'geo_data': {}},
        ]
        
        risks = aggregator._calculate_interception_risks(results, 'BrandA')
        
        assert len(risks) == 0


class TestSanitizeResults:
    """测试数据清洗"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_sanitize_results_basic(self, aggregator):
        """测试基本数据清洗"""
        results = [
            {
                'brand': 'BrandA',
                'question': 'Q1',
                'model': 'Qwen',
                'score': 85,
                'sentiment': 'positive'
            }
        ]
        
        sanitized = aggregator._sanitize_results(results)
        
        assert len(sanitized) == 1
        assert sanitized[0]['brand'] == 'BrandA'
        assert sanitized[0]['score'] == 85
        assert 'response' in sanitized[0]
        assert 'geo_data' in sanitized[0]
    
    def test_sanitize_results_invalid_score(self, aggregator):
        """测试无效分数处理"""
        results = [
            {'brand': 'BrandA', 'score': 150},  # 超出范围
            {'brand': 'BrandB', 'score': -10},  # 负数
            {'brand': 'BrandC', 'score': 'invalid'},  # 无效类型
        ]
        
        sanitized = aggregator._sanitize_results(results)
        
        assert sanitized[0]['score'] == 100  # 限制到最大值
        assert sanitized[1]['score'] == 0  # 限制到最小值
        assert sanitized[2]['score'] == 50  # 默认值
    
    def test_sanitize_results_empty(self, aggregator):
        """测试空结果"""
        sanitized = aggregator._sanitize_results([])
        assert len(sanitized) == 0


class TestFillMissingData:
    """测试缺失数据填充"""
    
    @pytest.fixture
    def aggregator(self):
        return ReportAggregator()
    
    def test_fill_missing_data_basic(self, aggregator):
        """测试基本数据填充"""
        results = [
            {'brand': '', 'question': '', 'score': 80}
        ]
        
        filled = aggregator._fill_missing_data(results, 'BrandA')
        
        assert filled[0]['brand'] == 'BrandA'
        assert filled[0]['question'] == '通用诊断问题'


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
