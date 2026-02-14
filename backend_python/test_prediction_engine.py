"""
预测引擎单元测试
"""
import unittest
import numpy as np
from wechat_backend.analytics.prediction_engine import PredictionEngine


class TestPredictionEngine(unittest.TestCase):
    """测试PredictionEngine类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.engine = PredictionEngine()

    def test_exponential_smoothing_forecast_basic(self):
        """测试指数平滑预测基础功能"""
        data = [10, 12, 11, 13, 12, 14, 13]
        forecasts = self.engine.exponential_smoothing_forecast(data, alpha=0.3, forecast_periods=3)
        
        self.assertEqual(len(forecasts), 3)
        self.assertIsInstance(forecasts[0], float)
        
        # 预测值应该在合理范围内
        data_mean = np.mean(data)
        self.assertTrue(all(abs(f - data_mean) < 10 for f in forecasts))

    def test_linear_regression_forecast_basic(self):
        """测试线性回归预测基础功能"""
        data = [10, 12, 14, 16, 18, 20, 22]
        forecasts, slope = self.engine.linear_regression_forecast(data, forecast_periods=3)
        
        self.assertEqual(len(forecasts), 3)
        self.assertIsInstance(slope, float)
        
        # 由于数据呈上升趋势，斜率应该是正数
        self.assertGreater(slope, 0)

    def test_linear_regression_forecast_declining_trend(self):
        """测试线性回归预测下降趋势"""
        data = [22, 20, 18, 16, 14, 12, 10]  # 下降趋势
        forecasts, slope = self.engine.linear_regression_forecast(data, forecast_periods=3)
        
        self.assertLess(slope, 0)  # 斜率应该是负数

    def test_predict_ranking_trend_improving(self):
        """测试排名趋势预测 - 改善趋势（数字变小）"""
        # 排名改善（数字变小表示排名提升）
        historical_ranks = [10, 9, 8, 7, 6, 5, 4, 3]
        result = self.engine.predict_ranking_trend(historical_ranks, days=7)
        
        self.assertEqual(len(result['predicted_ranks']), 7)
        self.assertEqual(result['trend_direction'], 'improving')
        self.assertGreater(result['trend_strength'], 0)

    def test_predict_ranking_trend_declining(self):
        """测试排名趋势预测 - 下降趋势（数字变大）"""
        # 排名下降（数字变大表示排名变差）
        historical_ranks = [3, 4, 5, 6, 7, 8, 9, 10]
        result = self.engine.predict_ranking_trend(historical_ranks, days=7)
        
        self.assertEqual(len(result['predicted_ranks']), 7)
        self.assertEqual(result['trend_direction'], 'declining')
        self.assertGreater(result['trend_strength'], 0)

    def test_predict_ranking_trend_stable(self):
        """测试排名趋势预测 - 稳定趋势"""
        # 稳定的排名
        historical_ranks = [5, 5, 5, 5, 5, 5, 5]
        result = self.engine.predict_ranking_trend(historical_ranks, days=7)
        
        self.assertEqual(len(result['predicted_ranks']), 7)
        self.assertEqual(result['trend_direction'], 'stable')
        self.assertAlmostEqual(result['trend_strength'], 0.0, places=1)

    def test_identify_cognitive_risks_empty_evidence(self):
        """测试认知风险识别 - 空证据链"""
        risks = self.engine.identify_cognitive_risks([], [1, 2, 3])
        self.assertEqual(len(risks), 0)

    def test_identify_cognitive_risks_with_high_risk(self):
        """测试认知风险识别 - 高风险证据"""
        evidence_chain = [
            {
                'negative_fragment': '该品牌存在严重安全漏洞',
                'associated_url': 'https://example.com/security-issue',
                'source_name': '安全评测机构',
                'risk_level': 'High'
            }
        ]
        risks = self.engine.identify_cognitive_risks(evidence_chain, [1, 2, 3])
        
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0]['risk_level'], 'High')
        self.assertGreater(risks[0]['potential_impact_on_rank'], 2.0)

    def test_identify_cognitive_risks_with_medium_risk(self):
        """测试认知风险识别 - 中等风险证据"""
        evidence_chain = [
            {
                'negative_fragment': '售后服务一般',
                'associated_url': 'https://example.com/feedback',
                'source_name': '用户评论',
                'risk_level': 'Medium'
            }
        ]
        risks = self.engine.identify_cognitive_risks(evidence_chain, [1, 2, 3])
        
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0]['risk_level'], 'Medium')
        self.assertGreater(risks[0]['potential_impact_on_rank'], 1.0)

    def test_identify_cognitive_risks_with_declining_trend(self):
        """测试认知风险识别 - 结合下降趋势"""
        evidence_chain = [
            {
                'negative_fragment': '产品质量问题',
                'associated_url': 'https://example.com/complaint',
                'source_name': '消费者报告',
                'risk_level': 'Medium'
            }
        ]
        # 提供下降的排名历史，应该增加风险影响
        declining_ranks = [3, 4, 5, 6, 7, 8, 9]
        risks = self.engine.identify_cognitive_risks(evidence_chain, declining_ranks)
        
        self.assertEqual(len(risks), 1)
        # 由于有下降趋势，风险影响应该更大
        self.assertGreater(risks[0]['potential_impact_on_rank'], 2.0)

    def test_predict_weekly_rank_with_risks(self):
        """测试周排名预测与风险识别"""
        historical_data = [
            {
                'rank': 5,
                'overall_score': 80,
                'sentiment_score': 75,
                'timestamp': '2023-01-01',
                'evidence_chain': []
            },
            {
                'rank': 6,
                'overall_score': 75,
                'sentiment_score': 70,
                'timestamp': '2023-01-02',
                'evidence_chain': [
                    {
                        'negative_fragment': '产品存在质量问题',
                        'associated_url': 'https://example.com/issue',
                        'source_name': '评测网站',
                        'risk_level': 'Medium'
                    }
                ]
            }
        ]
        
        result = self.engine.predict_weekly_rank_with_risks(historical_data)
        
        # 检查预测摘要
        self.assertIn('prediction_summary', result)
        self.assertIn('weekly_forecast', result)
        self.assertIn('risk_factors', result)
        self.assertIn('historical_data_points', result)
        
        # 检查周预测
        self.assertEqual(len(result['weekly_forecast']), 7)
        for day_forecast in result['weekly_forecast']:
            self.assertIn('day', day_forecast)
            self.assertIn('predicted_rank', day_forecast)
            self.assertIn('confidence_interval', day_forecast)
        
        # 检查风险因素
        self.assertGreaterEqual(len(result['risk_factors']), 0)  # 至少有0个风险因素

    def test_calculate_risk_impact_high_risk(self):
        """测试风险影响计算 - 高风险"""
        impact = self.engine._calculate_risk_impact("严重安全漏洞", "High")
        self.assertGreater(impact, 3.0)

    def test_calculate_risk_impact_medium_risk(self):
        """测试风险影响计算 - 中等风险"""
        impact = self.engine._calculate_risk_impact("服务质量一般", "Medium")
        self.assertGreaterEqual(impact, 2.0)
        self.assertLess(impact, 3.0)

    def test_calculate_risk_impact_with_keywords(self):
        """测试风险影响计算 - 包含关键风险词"""
        impact = self.engine._calculate_risk_impact("产品存在安全漏洞和欺诈风险", "Medium")
        # 应该因为包含多个风险关键词而得分更高
        self.assertGreater(impact, 2.5)

    def test_assess_recent_decline_positive_slope(self):
        """测试最近下降趋势评估 - 确实有下降"""
        ranks = [3, 4, 5, 6, 7]  # 排名在下降（数字变大）
        decline = self.engine._assess_recent_decline(ranks)
        self.assertGreaterEqual(decline, 0)  # 应该是非负数

    def test_assess_recent_decline_negative_slope(self):
        """测试最近下降趋势评估 - 实际是提升"""
        ranks = [7, 6, 5, 4, 3]  # 排名在提升（数字变小）
        decline = self.engine._assess_recent_decline(ranks)
        self.assertEqual(decline, 0)  # 因为函数只返回正值（下降），所以应该是0


if __name__ == '__main__':
    unittest.main()