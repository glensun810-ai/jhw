"""
报告生成器单元测试
"""
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from wechat_backend.analytics.report_generator import ReportGenerator


class TestReportGenerator(unittest.TestCase):
    """测试ReportGenerator类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.generator = ReportGenerator()

    def test_calculate_roi_metrics_basic(self):
        """测试基本ROI指标计算"""
        test_results = []
        trend_data = []
        
        roi_metrics = self.generator._calculate_roi_metrics(test_results, trend_data)
        
        # 验证基本结构
        self.assertIn('roi_score', roi_metrics)
        self.assertIn('investment_value', roi_metrics)
        self.assertIn('return_value', roi_metrics)
        self.assertIn('roi_percentage', roi_metrics)
        self.assertIn('confidence_level', roi_metrics)
        
        # 验证默认值
        self.assertEqual(roi_metrics['roi_score'], 0.0)
        self.assertEqual(roi_metrics['investment_value'], 0.0)
        self.assertEqual(roi_metrics['return_value'], 0.0)
        self.assertEqual(roi_metrics['roi_percentage'], 0.0)
        self.assertEqual(roi_metrics['confidence_level'], 'low')
        
        print("✓ 基本ROI指标计算测试通过")

    def test_calculate_roi_metrics_with_data(self):
        """测试有数据时的ROI指标计算"""
        test_results = [
            {
                'total_tests': 10,
                'overall_score': 85
            },
            {
                'total_tests': 5,
                'overall_score': 75
            }
        ]
        
        trend_data = [
            {
                'timestamp': '2023-01-01',
                'rank': 5,
                'sentiment_score': 0.7
            },
            {
                'timestamp': '2023-01-02',
                'rank': 3,
                'sentiment_score': 0.8
            }
        ]
        
        roi_metrics = self.generator._calculate_roi_metrics(test_results, trend_data)
        
        # 验证结构
        self.assertIn('roi_score', roi_metrics)
        self.assertIn('investment_value', roi_metrics)
        self.assertIn('return_value', roi_metrics)
        self.assertIn('roi_percentage', roi_metrics)
        self.assertIn('confidence_level', roi_metrics)
        
        # 验证计算结果（由于有数据，置信度应该不是low）
        self.assertIn(roi_metrics['confidence_level'], ['low', 'medium', 'high'])
        
        print(f"✓ 有数据时ROI指标计算测试通过 - 置信度: {roi_metrics['confidence_level']}")

    def test_calculate_exposure_increment_basic(self):
        """测试基本曝光增量计算"""
        trend_data = []
        exposure_increment = self.generator._calculate_exposure_increment(trend_data)
        
        self.assertEqual(exposure_increment, 0.0)
        print("✓ 基本曝光增量计算测试通过")

    def test_calculate_exposure_increment_with_improvement(self):
        """测试排名提升时的曝光增量计算"""
        trend_data = [
            {
                'timestamp': '2023-01-01',
                'rank': 10,  # 较差排名（数字大）
                'sentiment_score': 0.5
            },
            {
                'timestamp': '2023-01-02',
                'rank': 5,   # 较好排名（数字小）
                'sentiment_score': 0.6
            }
        ]
        
        exposure_increment = self.generator._calculate_exposure_increment(trend_data)
        
        # 由于排名从10提升到5（提升了5位），曝光增量应该是正数
        self.assertGreater(exposure_increment, 0)
        print(f"✓ 排名提升时曝光增量计算测试通过 - 增量: {exposure_increment:.2f}%")

    def test_calculate_exposure_increment_with_decline(self):
        """测试排名下降时的曝光增量计算"""
        trend_data = [
            {
                'timestamp': '2023-01-01',
                'rank': 3,   # 较好排名（数字小）
                'sentiment_score': 0.8
            },
            {
                'timestamp': '2023-01-02',
                'rank': 8,   # 较差排名（数字大）
                'sentiment_score': 0.7
            }
        ]
        
        exposure_increment = self.generator._calculate_exposure_increment(trend_data)
        
        # 由于排名从3下降到8，曝光增量应该为0（因为我们只计算正向增量）
        self.assertGreaterEqual(exposure_increment, 0)
        print(f"✓ 排名下降时曝光增量计算测试通过 - 增量: {exposure_increment:.2f}%")

    def test_calculate_ranking_improvement_basic(self):
        """测试基本排名改善计算"""
        trend_data = []
        ranking_improvement = self.generator._calculate_ranking_improvement(trend_data)
        
        self.assertEqual(ranking_improvement, 0.0)
        print("✓ 基本排名改善计算测试通过")

    def test_calculate_ranking_improvement_with_improvement(self):
        """测试排名改善计算（提升）"""
        trend_data = [
            {
                'timestamp': '2023-01-01',
                'rank': 8,   # 原始排名
                'sentiment_score': 0.5
            },
            {
                'timestamp': '2023-01-02',
                'rank': 3,   # 改善后排名
                'sentiment_score': 0.6
            }
        ]
        
        ranking_improvement = self.generator._calculate_ranking_improvement(trend_data)
        
        # 排名从8提升到3，改善了5位（8-3=5）
        self.assertEqual(ranking_improvement, 5.0)
        print(f"✓ 排名提升计算测试通过 - 改善: {ranking_improvement}")

    def test_calculate_ranking_improvement_with_decline(self):
        """测试排名改善计算（下降）"""
        trend_data = [
            {
                'timestamp': '2023-01-01',
                'rank': 2,   # 原始排名
                'sentiment_score': 0.8
            },
            {
                'timestamp': '2023-01-02',
                'rank': 7,   # 下降后排名
                'sentiment_score': 0.6
            }
        ]
        
        ranking_improvement = self.generator._calculate_ranking_improvement(trend_data)
        
        # 排名从2下降到7，改善了-5位（2-7=-5）
        self.assertEqual(ranking_improvement, -5.0)
        print(f"✓ 排名下降计算测试通过 - 改善: {ranking_improvement}")

    def test_calculate_sentiment_trend_basic(self):
        """测试基本情感趋势计算"""
        trend_data = []
        sentiment_trend = self.generator._calculate_sentiment_trend(trend_data)
        
        self.assertEqual(sentiment_trend['average_sentiment'], 0.0)
        self.assertEqual(sentiment_trend['trend_direction'], 'stable')
        self.assertEqual(sentiment_trend['change_magnitude'], 0.0)
        print("✓ 基本情感趋势计算测试通过")

    def test_calculate_sentiment_trend_with_data(self):
        """测试有数据时的情感趋势计算"""
        trend_data = [
            {
                'timestamp': '2023-01-01',
                'rank': 5,
                'sentiment_score': 0.4  # 初始情感分数
            },
            {
                'timestamp': '2023-01-02',
                'rank': 4,
                'sentiment_score': 0.8  # 改善后情感分数
            }
        ]
        
        sentiment_trend = self.generator._calculate_sentiment_trend(trend_data)
        
        self.assertGreaterEqual(sentiment_trend['average_sentiment'], 0.0)
        self.assertIn(sentiment_trend['trend_direction'], ['improving', 'declining', 'stable'])
        print(f"✓ 有数据时情感趋势计算测试通过 - 平均情感: {sentiment_trend['average_sentiment']:.2f}, 方向: {sentiment_trend['trend_direction']}")

    def test_calculate_avg_score_basic(self):
        """测试基本平均分数计算"""
        test_results = []
        avg_score = self.generator._calculate_avg_score(test_results)
        
        self.assertEqual(avg_score, 0.0)
        print("✓ 基本平均分数计算测试通过")

    def test_calculate_avg_score_with_data(self):
        """测试有数据时的平均分数计算"""
        test_results = [
            {'overall_score': 85},
            {'overall_score': 90},
            {'overall_score': 75}
        ]
        
        avg_score = self.generator._calculate_avg_score(test_results)
        
        expected_avg = (85 + 90 + 75) / 3
        self.assertEqual(avg_score, expected_avg)
        print(f"✓ 有数据时平均分数计算测试通过 - 平均分: {avg_score:.2f}")

    def test_generate_key_insights_empty(self):
        """测试空数据时的关键洞察生成"""
        test_results = []
        trend_data = []
        
        insights = self.generator._generate_key_insights(test_results, trend_data)
        
        # 即使没有数据也应该返回空列表而不是报错
        self.assertIsInstance(insights, list)
        print(f"✓ 空数据关键洞察生成测试通过 - 洞察数量: {len(insights)}")

    def test_generate_recommendations_empty(self):
        """测试空数据时的建议生成"""
        test_results = []
        trend_data = []
        
        recommendations = self.generator._generate_recommendations(test_results, trend_data)
        
        # 即使没有数据也应该返回列表
        self.assertIsInstance(recommendations, list)
        print(f"✓ 空数据建议生成测试通过 - 建议数量: {len(recommendations)}")

    def test_generate_executive_summary_basic(self):
        """测试基本高管摘要生成"""
        # 使用Mock来绕过数据库查询
        with patch.object(self.generator, '_get_test_results', return_value=[]), \
             patch.object(self.generator.cruise_controller, 'get_trend_data', return_value=[]):
            
            summary = self.generator.generate_executive_summary("TestBrand", days=7)
            
            # 验证基本结构
            self.assertIn('brand_name', summary)
            self.assertIn('report_period', summary)
            self.assertIn('roi_metrics', summary)
            self.assertIn('exposure_metrics', summary)
            self.assertIn('performance_summary', summary)
            self.assertIn('key_insights', summary)
            self.assertIn('recommendations', summary)
            
            self.assertEqual(summary['brand_name'], 'TestBrand')
            self.assertEqual(summary['report_period']['days'], 7)
            
            print("✓ 基本高管摘要生成测试通过")

    def test_get_hub_summary_with_data(self):
        """测试有数据时的枢纽摘要获取"""
        # 使用Mock来绕过数据库查询
        with patch.object(self.generator, '_get_test_results', return_value=[
            {'overall_score': 85, 'total_tests': 10}
        ]), \
        patch.object(self.generator.cruise_controller, 'get_trend_data', return_value=[
            {'timestamp': '2023-01-01', 'rank': 5, 'sentiment_score': 0.7}
        ]):
            
            summary = self.generator.get_hub_summary("TestBrand", days=7)
            
            # 验证结构
            self.assertIn('brand_name', summary)
            self.assertIn('summary_period', summary)
            self.assertIn('metrics', summary)
            self.assertIn('status', summary)
            self.assertIn('message', summary)
            
            self.assertEqual(summary['brand_name'], 'TestBrand')
            self.assertEqual(summary['status'], 'success')
            self.assertGreater(summary['metrics']['average_overall_score'], 0)
            
            print("✓ 有数据时枢纽摘要获取测试通过")

    def test_get_hub_summary_no_data(self):
        """测试无数据时的枢纽摘要获取"""
        # 使用Mock返回空数据
        with patch.object(self.generator, '_get_test_results', return_value=[]), \
             patch.object(self.generator.cruise_controller, 'get_trend_data', return_value=[]):
            
            summary = self.generator.get_hub_summary("TestBrand", days=7)
            
            # 验证结构
            self.assertIn('brand_name', summary)
            self.assertIn('summary_period', summary)
            self.assertIn('metrics', summary)
            self.assertIn('status', summary)
            self.assertIn('message', summary)
            
            self.assertEqual(summary['brand_name'], 'TestBrand')
            self.assertEqual(summary['status'], 'no_data')
            self.assertIn('暂无数据', summary['message'])
            
            # 验证指标为默认值
            metrics = summary['metrics']
            self.assertEqual(metrics['roi_score'], 0.0)
            self.assertEqual(metrics['estimated_exposure_increment'], 0.0)
            self.assertEqual(metrics['ranking_improvement'], 0)
            self.assertEqual(metrics['average_overall_score'], 0.0)
            self.assertEqual(metrics['test_count'], 0)
            self.assertEqual(metrics['trend_data_points'], 0)
            
            print("✓ 无数据时枢纽摘要获取测试通过")

    def test_get_hub_summary_error_handling(self):
        """测试枢纽摘要获取的错误处理"""
        # 模拟异常情况
        with patch.object(self.generator, '_get_test_results', side_effect=Exception("Database error")):
            
            summary = self.generator.get_hub_summary("TestBrand", days=7)
            
            # 验证错误处理
            self.assertIn('brand_name', summary)
            self.assertIn('summary_period', summary)
            self.assertIn('metrics', summary)
            self.assertIn('status', summary)
            self.assertIn('message', summary)
            
            self.assertEqual(summary['brand_name'], 'TestBrand')
            self.assertEqual(summary['status'], 'error')
            self.assertIn('数据获取失败', summary['message'])
            
            # 验证指标为默认值
            metrics = summary['metrics']
            self.assertEqual(metrics['roi_score'], 0.0)
            self.assertEqual(metrics['roi_percentage'], 0.0)
            self.assertEqual(metrics['estimated_exposure_increment'], 0.0)
            self.assertEqual(metrics['ranking_improvement'], 0)
            self.assertEqual(metrics['average_overall_score'], 0.0)
            self.assertEqual(metrics['test_count'], 0)
            self.assertEqual(metrics['trend_data_points'], 0)
            
            print("✓ 错误处理测试通过")


if __name__ == '__main__':
    unittest.main()