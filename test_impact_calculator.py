"""
测试ImpactCalculator的测试文件
"""
import unittest
import sys
import os

# 添加项目根目录到Python路径，以便导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from wechat_backend.analytics.impact_calculator import ImpactCalculator


class TestImpactCalculator(unittest.TestCase):
    """测试ImpactCalculator类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.calculator = ImpactCalculator()

    def test_calculate_impact_index_basic(self):
        """测试基本影响力指数计算"""
        # 测试高引用、高覆盖、正面情感的情况
        impact = self.calculator.calculate_impact_index(
            citation_count=10,
            model_coverage=5,
            sentiment_score=0.8,
            domain_authority='High'
        )
        
        # 验证返回的是合理的数值
        self.assertIsInstance(impact, float)
        self.assertGreaterEqual(impact, 0.0)
        self.assertLessEqual(impact, 100.0)
        print(f"高引用、高覆盖、正面情感、高权威度: {impact:.2f}")

    def test_calculate_impact_index_low_values(self):
        """测试低引用、低覆盖、负面情感的情况"""
        impact = self.calculator.calculate_impact_index(
            citation_count=1,
            model_coverage=1,
            sentiment_score=-0.5,
            domain_authority='Low'
        )
        
        # 验证返回的是合理的数值
        self.assertIsInstance(impact, float)
        self.assertGreaterEqual(impact, 0.0)
        self.assertLessEqual(impact, 100.0)
        print(f"低引用、低覆盖、负面情感、低权威度: {impact:.2f}")

    def test_calculate_impact_index_medium_values(self):
        """测试中等引用、中等覆盖、中性情感的情况"""
        impact = self.calculator.calculate_impact_index(
            citation_count=5,
            model_coverage=3,
            sentiment_score=0.0,
            domain_authority='Medium'
        )
        
        # 验证返回的是合理的数值
        self.assertIsInstance(impact, float)
        self.assertGreaterEqual(impact, 0.0)
        self.assertLessEqual(impact, 100.0)
        print(f"中等引用、中等覆盖、中性情感、中等权威度: {impact:.2f}")

    def test_calculate_impact_index_zero_values(self):
        """测试零引用、零覆盖的情况"""
        impact = self.calculator.calculate_impact_index(
            citation_count=0,
            model_coverage=0,
            sentiment_score=0.0,
            domain_authority='Medium'
        )
        
        # 零引用和零覆盖应该得到较低的影响力指数
        self.assertIsInstance(impact, float)
        self.assertGreaterEqual(impact, 0.0)
        self.assertLessEqual(impact, 100.0)
        print(f"零引用、零覆盖、中性情感、中等权威度: {impact:.2f}")

    def test_calculate_impact_index_max_values(self):
        """测试最大引用、最大覆盖的情况"""
        impact = self.calculator.calculate_impact_index(
            citation_count=100,  # 最大引用次数
            model_coverage=10,   # 最大覆盖模型数
            sentiment_score=1.0, # 最强正面情感
            domain_authority='High'
        )
        
        # 验证返回的是合理的数值
        self.assertIsInstance(impact, float)
        self.assertGreaterEqual(impact, 0.0)
        self.assertLessEqual(impact, 100.0)
        print(f"最大引用、最大覆盖、最强正面情感、高权威度: {impact:.2f}")

    def test_normalize_citation_score(self):
        """测试引用频次标准化"""
        score = self.calculator._normalize_citation_score(10)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        print(f"引用频次10的标准化得分: {score:.2f}")

        score = self.calculator._normalize_citation_score(0)
        self.assertEqual(score, 0.0)
        print(f"引用频次0的标准化得分: {score:.2f}")

        score = self.calculator._normalize_citation_score(1000)  # 超过最大值
        self.assertLessEqual(score, 100.0)
        print(f"引用频次1000的标准化得分: {score:.2f}")

    def test_normalize_coverage_score(self):
        """测试模型覆盖度标准化"""
        score = self.calculator._normalize_coverage_score(5)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        print(f"模型覆盖度5的标准化得分: {score:.2f}")

        score = self.calculator._normalize_coverage_score(0)
        self.assertEqual(score, 0.0)
        print(f"模型覆盖度0的标准化得分: {score:.2f}")

        score = self.calculator._normalize_coverage_score(15)  # 超过最大值
        self.assertLessEqual(score, 100.0)
        print(f"模型覆盖度15的标准化得分: {score:.2f}")

    def test_normalize_sentiment_score(self):
        """测试情感偏向标准化"""
        score = self.calculator._normalize_sentiment_score(0.8)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        print(f"情感偏向0.8的标准化得分: {score:.2f}")

        score = self.calculator._normalize_sentiment_score(-0.8)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        print(f"情感偏向-0.8的标准化得分: {score:.2f}")

        score = self.calculator._normalize_sentiment_score(0.0)
        self.assertEqual(score, 0.0)
        print(f"情感偏向0.0的标准化得分: {score:.2f}")

    def test_get_authority_multiplier(self):
        """测试权威度乘数"""
        multiplier = self.calculator._get_authority_multiplier('High')
        self.assertEqual(multiplier, 1.2)

        multiplier = self.calculator._get_authority_multiplier('Medium')
        self.assertEqual(multiplier, 1.0)

        multiplier = self.calculator._get_authority_multiplier('Low')
        self.assertEqual(multiplier, 0.8)

        multiplier = self.calculator._get_authority_multiplier('Unknown')
        self.assertEqual(multiplier, 1.0)

    def test_calculate_batch_impacts(self):
        """测试批量计算影响力指数"""
        source_data = [
            {
                'citation_count': 10,
                'model_coverage': 5,
                'sentiment_score': 0.8,
                'domain_authority': 'High'
            },
            {
                'citation_count': 1,
                'model_coverage': 1,
                'sentiment_score': -0.5,
                'domain_authority': 'Low'
            },
            {
                'citation_count': 5,
                'model_coverage': 3,
                'sentiment_score': 0.0,
                'domain_authority': 'Medium'
            }
        ]

        results = self.calculator.calculate_batch_impacts(source_data)

        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIn('impact_index', result)
            self.assertGreaterEqual(result['impact_index'], 0.0)
            self.assertLessEqual(result['impact_index'], 100.0)

        print("批量计算结果:")
        for i, result in enumerate(results):
            print(f"  数据项 {i+1}: 影响力指数 = {result['impact_index']:.2f}")


if __name__ == '__main__':
    unittest.main()