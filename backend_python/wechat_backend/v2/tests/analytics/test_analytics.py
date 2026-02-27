"""
统计算法模块测试

测试范围：
- 品牌分布分析
- 情感分析
- 关键词提取
- 趋势对比分析

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0

注意：本测试文件使用通用测试品牌名，避免使用真实品牌
"""

import unittest
from wechat_backend.v2.analytics.brand_distribution_analyzer import BrandDistributionAnalyzer
from wechat_backend.v2.analytics.sentiment_analyzer import SentimentAnalyzer
from wechat_backend.v2.analytics.keyword_extractor import KeywordExtractor
from wechat_backend.v2.analytics.trend_analyzer import TrendAnalyzer


# ==================== 测试数据常量 ====================
# 【P3-001 修复】使用通用测试品牌名，避免使用真实品牌
TEST_BRAND_A = '测试品牌 A'
TEST_BRAND_B = '测试品牌 B'
TEST_BRAND_C = '测试品牌 C'


class TestBrandDistributionAnalyzer(unittest.TestCase):
    """品牌分布分析器测试"""

    def setUp(self):
        """测试准备"""
        self.analyzer = BrandDistributionAnalyzer()
        # 【P3-001 修复】使用通用测试品牌名
        self.sample_results = [
            {'brand': TEST_BRAND_A, 'model': 'qwen'},
            {'brand': TEST_BRAND_B, 'model': 'qwen'},
            {'brand': TEST_BRAND_A, 'model': 'deepseek'},
            {'brand': TEST_BRAND_C, 'model': 'qwen'},
            {'brand': TEST_BRAND_A, 'model': 'qwen'},
        ]
    
    def test_analyze(self):
        """测试品牌分布分析"""
        distribution = self.analyzer.analyze(self.sample_results)

        # 【P2-003 修复】新返回格式包含 data, total_count, warning
        self.assertIn('data', distribution)
        self.assertIn('total_count', distribution)
        self.assertIn('warning', distribution)
        
        data = distribution['data']
        # 【P3-001 修复】使用测试品牌常量
        self.assertIn(TEST_BRAND_A, data)
        self.assertIn(TEST_BRAND_B, data)
        self.assertIn(TEST_BRAND_C, data)

        # 测试品牌 A 占 60%
        self.assertAlmostEqual(data[TEST_BRAND_A], 60.0, places=2)
        
        # 验证总数
        self.assertEqual(distribution['total_count'], 5)

    def test_analyze_empty(self):
        """测试空结果"""
        distribution = self.analyzer.analyze([])
        
        # 【P2-003 修复】新返回格式
        self.assertEqual(distribution['data'], {})
        self.assertEqual(distribution['total_count'], 0)
        self.assertEqual(distribution['warning'], '分析结果为空')

    def test_analyze_by_model(self):
        """测试按模型分析"""
        distribution = self.analyzer.analyze_by_model(self.sample_results)

        self.assertIn('qwen', distribution)
        self.assertIn('deepseek', distribution)

    def test_analyze_competitors(self):
        """测试竞品分析"""
        result = self.analyzer.analyze_competitors(self.sample_results, TEST_BRAND_A)

        self.assertEqual(result['main_brand'], TEST_BRAND_A)
        # 【P2-003 修复】main_brand_share 现在在 data 中
        self.assertEqual(result['main_brand_share'], 60.0)
        self.assertEqual(result['rank'], 1)
    
    def test_get_brand_details(self):
        """测试品牌详情"""
        details = self.analyzer.get_brand_details(self.sample_results, TEST_BRAND_A)

        self.assertEqual(details['brand'], TEST_BRAND_A)
        self.assertEqual(details['total_mentions'], 3)


class TestSentimentAnalyzer(unittest.TestCase):
    """情感分析器测试"""
    
    def setUp(self):
        """测试准备"""
        self.analyzer = SentimentAnalyzer()
        self.sample_results = [
            {'geo_data': {'sentiment': 0.8}},  # 正面
            {'geo_data': {'sentiment': 0.0}},  # 中性
            {'geo_data': {'sentiment': -0.6}}, # 负面
            {'geo_data': {'sentiment': 0.5}},  # 正面
        ]
    
    def test_analyze(self):
        """测试情感分布"""
        distribution = self.analyzer.analyze(self.sample_results)

        # 【P2-003 修复】新返回格式包含 data, total_count, warning
        self.assertIn('data', distribution)
        self.assertIn('total_count', distribution)
        self.assertIn('warning', distribution)
        
        data = distribution['data']
        self.assertIn('positive', data)
        self.assertIn('neutral', data)
        self.assertIn('negative', data)

        # 正面占 50%
        self.assertAlmostEqual(data['positive'], 50.0, places=2)

    def test_analyze_empty(self):
        """测试空结果"""
        distribution = self.analyzer.analyze([])
        
        # 【P2-003 修复】新返回格式
        self.assertEqual(distribution['data']['positive'], 0.0)
        self.assertEqual(distribution['data']['neutral'], 0.0)
        self.assertEqual(distribution['data']['negative'], 0.0)
        self.assertEqual(distribution['total_count'], 0)
        self.assertEqual(distribution['warning'], '分析结果为空')
    
    def test_calculate_sentiment_score(self):
        """测试情感得分计算"""
        score = self.analyzer.calculate_sentiment_score(self.sample_results)
        
        self.assertIn('avg_score', score)
        self.assertIn('max_score', score)
        self.assertIn('min_score', score)
        
        # 平均分 = (0.8 + 0.0 - 0.6 + 0.5) / 4 = 0.175
        self.assertAlmostEqual(score['avg_score'], 0.175, places=3)
    
    def test_get_positive_rate(self):
        """测试正面率"""
        positive_rate = self.analyzer.get_positive_rate(self.sample_results)
        
        # sentiment > 0.3 才算正面：只有 0.8 符合，0.5 不符合（因为 0.5 不大于 0.5 阈值）
        # 1 个正面 / 4 个总数 = 25%
        self.assertAlmostEqual(positive_rate, 25.0, places=2)
    
    def test_get_negative_rate(self):
        """测试负面率"""
        negative_rate = self.analyzer.get_negative_rate(self.sample_results)
        
        # 1 个负面 / 4 个总数 = 25%
        self.assertAlmostEqual(negative_rate, 25.0, places=2)


class TestKeywordExtractor(unittest.TestCase):
    """关键词提取器测试"""
    
    def setUp(self):
        """测试准备"""
        self.extractor = KeywordExtractor()
        # 【P3-001 修复】使用通用测试品牌名
        self.sample_results = [
            {
                'brand': TEST_BRAND_A,
                'geo_data': {
                    'response_text': '测试品牌 A 是一个优秀的品牌，质量很好，设计时尚'
                }
            },
            {
                'brand': TEST_BRAND_B,
                'geo_data': {
                    'response_text': '测试品牌 B 设计精美，深受年轻人喜爱，性价比高'
                }
            },
        ]

    def test_extract(self):
        """测试关键词提取"""
        keywords = self.extractor.extract(self.sample_results)

        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)

        # 检查关键词格式
        for kw in keywords:
            self.assertIn('word', kw)
            self.assertIn('count', kw)
            self.assertIn('sentiment', kw)

    def test_extract_empty(self):
        """测试空结果"""
        keywords = self.extractor.extract([])
        self.assertEqual(keywords, [])

    def test_extract_by_brand(self):
        """测试按品牌提取"""
        keywords = self.extractor.extract_by_brand(self.sample_results, TEST_BRAND_A)

        self.assertIsInstance(keywords, list)
    
    def test_generate_word_cloud_data(self):
        """测试词云数据生成"""
        word_cloud = self.extractor.generate_word_cloud_data(self.sample_results)
        
        self.assertIsInstance(word_cloud, list)
        
        if word_cloud:
            item = word_cloud[0]
            self.assertIn('word', item)
            self.assertIn('size', item)
            self.assertIn('color', item)


class TestTrendAnalyzer(unittest.TestCase):
    """趋势分析器测试"""

    def setUp(self):
        """测试准备"""
        self.analyzer = TrendAnalyzer()
        # 【P3-001 修复】使用通用测试品牌名
        self.current_results = [
            {'brand': TEST_BRAND_A, 'geo_data': {'sentiment': 0.7}},
            {'brand': TEST_BRAND_B, 'geo_data': {'sentiment': 0.5}},
            {'brand': TEST_BRAND_A, 'geo_data': {'sentiment': 0.6}},
        ]
        self.historical_results = [
            {'brand': TEST_BRAND_A, 'geo_data': {'sentiment': 0.5}},
            {'brand': TEST_BRAND_B, 'geo_data': {'sentiment': 0.6}},
        ]

    def test_compare_with_history(self):
        """测试历史对比"""
        # 【P1-002 修复】历史数据应该是扁平列表，不是嵌套列表
        result = self.analyzer.compare_with_history(
            self.current_results,
            self.historical_results  # 直接传递列表，不是 [list]
        )

        self.assertIn('current', result)
        self.assertIn('historical', result)  # 更新为新的返回键名
        self.assertIn('trend', result)

    def test_compare_with_history_empty(self):
        """测试空历史数据"""
        result = self.analyzer.compare_with_history(self.current_results, [])

        self.assertIn('error', result)

    def test_analyze_competitors(self):
        """测试竞品分析"""
        result = self.analyzer.analyze_competitors(self.current_results, TEST_BRAND_A)

        self.assertIn('main_brand', result)
        self.assertIn('main_metrics', result)
        self.assertIn('competitors', result)
        self.assertIn('ranking', result)
    
    def test_analyze_time_series(self):
        """测试时间序列分析"""
        time_series = [
            {'date': '2026-01-01', 'value': 0.5},
            {'date': '2026-01-02', 'value': 0.6},
            {'date': '2026-01-03', 'value': 0.7},
        ]
        
        result = self.analyzer.analyze_time_series(time_series)
        
        self.assertIn('trend_direction', result)
        self.assertIn('growth_rate', result)
    
    def test_predict_trend(self):
        """测试趋势预测"""
        time_series = [
            {'date': '2026-01-01', 'value': 0.5},
            {'date': '2026-01-02', 'value': 0.6},
            {'date': '2026-01-03', 'value': 0.7},
        ]
        
        predictions = self.analyzer.predict_trend(time_series, periods=2)
        
        self.assertEqual(len(predictions), 2)
        self.assertIn('predicted_value', predictions[0])
        self.assertIn('confidence', predictions[0])


class TestIntegration(unittest.TestCase):
    """统计算法集成测试"""
    
    def setUp(self):
        """测试准备"""
        self.brand_analyzer = BrandDistributionAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.keyword_extractor = KeywordExtractor()
        self.trend_analyzer = TrendAnalyzer()
        
        # 【P3-001 修复】使用通用测试品牌名
        self.comprehensive_results = [
            {
                'brand': TEST_BRAND_A,
                'model': 'qwen',
                'geo_data': {
                    'sentiment': 0.7,
                    'response_text': '测试品牌 A 是领先品牌，质量优秀，设计时尚'
                }
            },
            {
                'brand': TEST_BRAND_B,
                'model': 'qwen',
                'geo_data': {
                    'sentiment': 0.5,
                    'response_text': '测试品牌 B 性价比不错，适合年轻人'
                }
            },
            {
                'brand': TEST_BRAND_A,
                'model': 'deepseek',
                'geo_data': {
                    'sentiment': 0.6,
                    'response_text': '测试品牌 A 价格偏高但品质可靠'
                }
            },
            {
                'brand': TEST_BRAND_C,
                'model': 'qwen',
                'geo_data': {
                    'sentiment': 0.3,
                    'response_text': '测试品牌 C 是中等品牌，表现一般'
                }
            },
        ]

    def test_full_analysis_pipeline(self):
        """测试完整分析流程"""
        # 1. 品牌分布分析
        brand_dist = self.brand_analyzer.analyze(self.comprehensive_results)
        # 【P2-003 修复】新返回格式
        self.assertIn('data', brand_dist)
        self.assertGreater(len(brand_dist['data']), 0)

        # 2. 情感分析
        sentiment_dist = self.sentiment_analyzer.analyze(self.comprehensive_results)
        # 【P2-003 修复】新返回格式
        self.assertIn('data', sentiment_dist)
        self.assertIn('positive', sentiment_dist['data'])

        # 3. 关键词提取
        keywords = self.keyword_extractor.extract(self.comprehensive_results)
        self.assertGreater(len(keywords), 0)

        # 4. 竞品分析
        competitor_analysis = self.brand_analyzer.analyze_competitors(
            self.comprehensive_results, TEST_BRAND_A
        )
        self.assertEqual(competitor_analysis['main_brand'], TEST_BRAND_A)
    
    def test_cross_brand_comparison(self):
        """测试跨品牌对比"""
        # 品牌分布
        brand_dist = self.brand_analyzer.analyze(self.comprehensive_results)
        
        # 情感得分
        sentiment_score = self.sentiment_analyzer.calculate_sentiment_score(
            self.comprehensive_results
        )
        
        # 验证数据一致性
        self.assertGreater(len(brand_dist), 0)
        self.assertIn('avg_score', sentiment_score)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestBrandDistributionAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestKeywordExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestTrendAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return {
        'total': result.testsRun,
        'passed': len(result.failures) + len(result.errors) == 0,
        'failures': len(result.failures),
        'errors': len(result.errors)
    }


if __name__ == '__main__':
    result = run_tests()
    print(f"\n测试结果：{result['passed']} - {result['total']} 测试通过")
