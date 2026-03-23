"""
评分维度算法与问题诊断墙单元测试

测试模块：
1. DimensionScorer - 评分维度计算器
2. DiagnosticWallGenerator - 问题诊断墙生成器
3. MetricsCalculator - 核心指标计算器

@author: 系统架构组
@date: 2026-03-22
@version: 1.0
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# 添加后端路径
backend_root = Path(__file__).parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from wechat_backend.services.dimension_scorer import DimensionScorer
from wechat_backend.services.diagnostic_wall_generator import DiagnosticWallGenerator
from wechat_backend.services.metrics_calculator import (
    calculate_diagnosis_metrics,
    calculate_dimension_scores,
    generate_diagnostic_wall
)


class TestDimensionScorer(unittest.TestCase):
    """测试评分维度计算器"""
    
    def setUp(self):
        """测试前准备"""
        self.scorer = DimensionScorer()
        self.brand_name = "德施曼"
        self.sample_results = [
            {
                'model': 'deepseek',
                'question': '高端智能锁哪个品牌好？',
                'raw_response': '德施曼是高端智能锁的领先品牌，成立于 2007 年，总部位于浙江。德施曼专注于智能锁研发，产品质量优秀，深受用户信赖。相比之下，小米性价比更高，凯迪仕也是不错的选择。',
                'extracted_brand': '德施曼',
                'brand_word_count': 80,
            },
            {
                'model': 'doubao',
                'question': '高端智能锁哪个品牌好？',
                'raw_response': '在高端智能锁领域，德施曼排名第一，是最值得推荐的品牌。德施曼的安全性和可靠性都非常出色。小米和凯迪仕也是主流品牌。',
                'extracted_brand': '德施曼',
                'brand_word_count': 60,
            },
            {
                'model': 'qwen',
                'question': '高端智能锁哪个品牌好？',
                'raw_response': '智能锁品牌有很多，小米因为性价比高排在前面，德施曼、凯迪仕、鹿客也都是知名品牌。小米在智能家居生态方面有优势。',
                'extracted_brand': '小米',
                'brand_word_count': 40,
            },
        ]
        self.ranking_list = ["德施曼", "小米", "凯迪仕", "鹿客"]
    
    def test_score_visibility_brand_mentioned(self):
        """测试可见度得分 - 品牌被提及"""
        score = self.scorer.score_visibility(self.sample_results, self.brand_name)
        
        # 品牌在所有结果中都被提及，基础分 60
        # 位置加分和篇幅加分取决于具体位置
        self.assertGreater(score, 60)
        self.assertLessEqual(score, 100)
    
    def test_score_visibility_brand_not_mentioned(self):
        """测试可见度得分 - 品牌未被提及"""
        score = self.scorer.score_visibility(self.sample_results, "不存在的品牌")
        
        # 品牌未被提及，得分为 0
        self.assertEqual(score, 0)
    
    def test_score_rank_first_place(self):
        """测试排位得分 - 第 1 名"""
        score = self.scorer.score_rank(["德施曼", "小米", "凯迪仕"], "德施曼")
        self.assertEqual(score, 100)
    
    def test_score_rank_second_place(self):
        """测试排位得分 - 第 2 名"""
        score = self.scorer.score_rank(["小米", "德施曼", "凯迪仕"], "德施曼")
        self.assertEqual(score, 80)
    
    def test_score_rank_third_place(self):
        """测试排位得分 - 第 3 名"""
        score = self.scorer.score_rank(["小米", "凯迪仕", "德施曼"], "德施曼")
        self.assertEqual(score, 60)
    
    def test_score_rank_not_in_list(self):
        """测试排位得分 - 品牌不在列表中"""
        score = self.scorer.score_rank(["小米", "凯迪仕", "鹿客"], "德施曼")
        self.assertEqual(score, 0)
    
    def test_score_sov_high(self):
        """测试声量得分 - 高 SOV"""
        # 模拟高 SOV 场景
        results = [
            {
                'raw_response': '德施曼德施曼德施曼德施曼德施曼',
                'extracted_brand': '德施曼'
            }
        ]
        score = self.scorer.score_sov(results, "德施曼")
        self.assertGreaterEqual(score, 80)
    
    def test_score_sentiment_positive(self):
        """测试情感得分 - 正面情感"""
        results = [
            {
                'raw_response': '德施曼是领先品牌，产品质量优秀，深受用户信赖，值得推荐',
                'extracted_brand': '德施曼'
            }
        ]
        score = self.scorer.score_sentiment(results, "德施曼")
        self.assertGreater(score, 60)
    
    def test_score_sentiment_negative(self):
        """测试情感得分 - 负面情感"""
        results = [
            {
                'raw_response': '德施曼存在不足，有问题，需要谨慎，避免购买',
                'extracted_brand': '德施曼'
            }
        ]
        score = self.scorer.score_sentiment(results, "德施曼")
        self.assertLess(score, 60)
    
    def test_calculate_overall_score(self):
        """测试综合评分计算"""
        overall = self.scorer.calculate_overall_score(
            visibility_score=80,
            rank_score=100,
            sov_score=60,
            sentiment_score=80
        )
        
        # 权重：visibility 25%, rank 35%, sov 25%, sentiment 15%
        # 80*0.25 + 100*0.35 + 60*0.25 + 80*0.15 = 20 + 35 + 15 + 12 = 82
        self.assertEqual(overall, 82)
    
    def test_calculate_all_dimensions(self):
        """测试所有维度计算"""
        result = self.scorer.calculate_all_dimensions(
            results=self.sample_results,
            brand_name=self.brand_name,
            ranking_list=self.ranking_list
        )
        
        self.assertIn('visibility_score', result)
        self.assertIn('rank_score', result)
        self.assertIn('sov_score', result)
        self.assertIn('sentiment_score', result)
        self.assertIn('overall_score', result)
        self.assertIn('detailed_data', result)
        
        # 验证得分范围
        self.assertGreaterEqual(result['visibility_score'], 0)
        self.assertLessEqual(result['visibility_score'], 100)
        self.assertGreaterEqual(result['overall_score'], 0)
        self.assertLessEqual(result['overall_score'], 100)
    
    def test_cross_platform_consistency(self):
        """测试跨平台一致性计算"""
        # 完全一致
        consistency = self.scorer.calculate_cross_platform_consistency([80, 80, 80])
        self.assertEqual(consistency, 100)
        
        # 差异较大
        consistency = self.scorer.calculate_cross_platform_consistency([20, 80, 90])
        self.assertLess(consistency, 100)
        
        # 单平台
        consistency = self.scorer.calculate_cross_platform_consistency([80])
        self.assertEqual(consistency, 100)


class TestDiagnosticWallGenerator(unittest.TestCase):
    """测试问题诊断墙生成器"""
    
    def setUp(self):
        """测试前准备"""
        self.generator = DiagnosticWallGenerator()
    
    def test_generate_high_risk_low_rank(self):
        """测试高风险 - 排名落后"""
        result = self.generator.generate(
            visibility_score=50,
            rank_score=20,  # 第 4 名以后
            sov_score=50,
            sentiment_score=50,
            overall_score=50,
            detailed_data={
                'position': 5,
                'sov': 15,
                'word_count': 50
            }
        )
        
        self.assertIn('high_risks', result)
        self.assertIn('medium_risks', result)
        self.assertIn('recommendations', result)
        
        # 应该有高风险（排名严重落后）
        high_risk_types = [r['type'] for r in result['high_risks']]
        self.assertIn('RISK-001', high_risk_types)  # 排名严重落后
    
    def test_generate_high_risk_low_sov(self):
        """测试高风险 - 声量份额过低"""
        result = self.generator.generate(
            visibility_score=50,
            rank_score=50,
            sov_score=20,  # SOV 得分低
            sentiment_score=50,
            overall_score=50,
            detailed_data={
                'position': 2,
                'sov': 8,  # SOV 仅 8%
                'word_count': 30
            }
        )
        
        # 应该有高风险（声量份额过低）
        high_risk_types = [r['type'] for r in result['high_risks']]
        self.assertIn('RISK-002', high_risk_types)  # 声量份额过低
    
    def test_generate_high_risk_negative_sentiment(self):
        """测试高风险 - 负面评价"""
        result = self.generator.generate(
            visibility_score=50,
            rank_score=50,
            sov_score=50,
            sentiment_score=20,  # 情感得分低
            overall_score=50,
            detailed_data={
                'position': 2,
                'sov': 25,
                'sentiment': -0.5,
                'negative_keywords': ['不足', '问题', '谨慎']
            }
        )
        
        # 应该有高风险（负面评价风险）
        high_risk_types = [r['type'] for r in result['high_risks']]
        self.assertIn('RISK-004', high_risk_types)  # 负面评价风险
    
    def test_generate_medium_risk(self):
        """测试中风险"""
        result = self.generator.generate(
            visibility_score=70,  # 中等
            rank_score=50,  # 中等
            sov_score=50,  # 中等
            sentiment_score=50,  # 中等
            overall_score=65,
            detailed_data={
                'position': 2,
                'sov': 22
            }
        )
        
        # 应该有中风险
        self.assertGreater(len(result['medium_risks']), 0)
    
    def test_generate_good_performance(self):
        """测试表现良好场景"""
        result = self.generator.generate(
            visibility_score=90,
            rank_score=100,  # 第 1 名
            sov_score=90,
            sentiment_score=90,
            overall_score=95,
            detailed_data={
                'position': 1,
                'sov': 45
            }
        )
        
        # 不应该有高风险
        self.assertEqual(len(result['high_risks']), 0)
        
        # 应该有鼓励性建议
        self.assertGreater(len(result['recommendations']), 0)
    
    def test_recommendations_sorting(self):
        """测试建议排序"""
        result = self.generator.generate(
            visibility_score=30,  # 低
            rank_score=20,  # 低
            sov_score=30,  # 低
            sentiment_score=30,  # 低
            overall_score=30,
            detailed_data={
                'position': 5,
                'sov': 8
            }
        )
        
        # 建议应该按优先级排序
        recommendations = result['recommendations']
        if len(recommendations) > 1:
            priorities = [r.get('priority', 'low') for r in recommendations]
            # high 应该排在 medium 前面
            high_indices = [i for i, p in enumerate(priorities) if p == 'high']
            medium_indices = [i for i, p in enumerate(priorities) if p == 'medium']
            
            if high_indices and medium_indices:
                self.assertLess(max(high_indices), min(medium_indices))
    
    def test_generate_summary(self):
        """测试摘要生成"""
        result = self.generator.generate(
            visibility_score=90,
            rank_score=100,
            sov_score=90,
            sentiment_score=90,
            overall_score=92,
            detailed_data={}
        )
        
        self.assertIn('summary', result)
        summary = result['summary']
        
        self.assertEqual(summary['grade'], 'S')
        self.assertEqual(summary['grade_text'], '优秀')
    
    def test_generate_with_cross_platform_inconsistency(self):
        """测试跨平台不一致性检测"""
        result = self.generator.generate(
            visibility_score=50,
            rank_score=50,
            sov_score=50,
            sentiment_score=50,
            overall_score=50,
            cross_platform_consistency=40,  # 一致性低
            detailed_data={}
        )
        
        # 应该有中风险（评价不一致）
        medium_risk_types = [r['type'] for r in result['medium_risks']]
        self.assertIn('RISK-105', medium_risk_types)  # 评价不一致


class TestMetricsCalculator(unittest.TestCase):
    """测试核心指标计算器"""
    
    def test_calculate_diagnosis_metrics(self):
        """测试核心指标计算"""
        brand_name = "德施曼"
        sov_data = {'brandShare': {'德施曼': 35, '小米': 30, '凯迪仕': 20, '鹿客': 15}}
        results = [
            {'extracted_brand': '德施曼', 'sentiment': 'positive'},
            {'extracted_brand': '德施曼', 'sentiment': 'positive'},
            {'extracted_brand': '小米', 'sentiment': 'neutral'},
            {'extracted_brand': '凯迪仕', 'sentiment': 'neutral'},
        ]
        
        metrics = calculate_diagnosis_metrics(brand_name, sov_data, results)
        
        self.assertIn('sov', metrics)
        self.assertIn('sentiment', metrics)
        self.assertIn('rank', metrics)
        self.assertIn('influence', metrics)
        
        # SOV 应该是 35（从 sov_data）
        self.assertEqual(metrics['sov'], 35)
        
        # 排名应该是 1（德施曼提及最多）
        self.assertEqual(metrics['rank'], 1)
        
        # 情感应该是正面
        self.assertGreater(metrics['sentiment'], 50)
    
    def test_calculate_dimension_scores(self):
        """测试维度得分计算"""
        brand_name = "德施曼"
        results = [
            {
                'raw_response': '德施曼是领先品牌，产品质量优秀',
                'extracted_brand': '德施曼'
            }
        ]
        sov_data = {'brandShare': {'德施曼': 40}}
        
        scores = calculate_dimension_scores(brand_name, results, sov_data)
        
        self.assertIn('authority', scores)
        self.assertIn('visibility', scores)
        self.assertIn('purity', scores)
        self.assertIn('consistency', scores)
    
    def test_generate_diagnostic_wall(self):
        """测试诊断墙生成"""
        brand_name = "德施曼"
        metrics = {
            'sov': 35,
            'sentiment': 60,
            'rank': 2,
            'influence': 70
        }
        dimension_scores = {
            'authority': 70,
            'visibility': 70,
            'purity': 60,
            'consistency': 80
        }
        
        wall = generate_diagnostic_wall(brand_name, metrics, dimension_scores)
        
        self.assertIn('high_risks', wall)
        self.assertIn('medium_risks', wall)
        self.assertIn('recommendations', wall)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_pipeline(self):
        """测试完整流程：从原始数据到诊断墙"""
        # 1. 准备测试数据
        brand_name = "德施曼"
        results = [
            {
                'model': 'deepseek',
                'question': '高端智能锁哪个品牌好？',
                'raw_response': '德施曼是高端智能锁的领先品牌，成立于 2007 年，总部位于浙江。德施曼专注于智能锁研发，产品质量优秀，深受用户信赖。',
                'extracted_brand': '德施曼',
                'brand_word_count': 80,
            },
            {
                'model': 'doubao',
                'question': '高端智能锁哪个品牌好？',
                'raw_response': '在高端智能锁领域，德施曼排名第一，是最值得推荐的品牌。德施曼的安全性和可靠性都非常出色。',
                'extracted_brand': '德施曼',
                'brand_word_count': 60,
            },
        ]
        ranking_list = ["德施曼", "小米", "凯迪仕"]
        
        # 2. 计算维度得分
        scorer = DimensionScorer()
        dimension_data = scorer.calculate_all_dimensions(
            results=results,
            brand_name=brand_name,
            ranking_list=ranking_list
        )
        
        # 3. 生成诊断墙
        generator = DiagnosticWallGenerator()
        diagnostic_wall = generator.generate(
            visibility_score=dimension_data.get('visibility_score', 50),
            rank_score=dimension_data.get('rank_score', 0),
            sov_score=dimension_data.get('sov_score', 50),
            sentiment_score=dimension_data.get('sentiment_score', 50),
            overall_score=dimension_data.get('overall_score', 50),
            cross_platform_consistency=dimension_data.get('cross_platform_consistency', 100),
            detailed_data=dimension_data.get('detailed_data', {})
        )
        
        # 4. 验证结果
        self.assertIn('high_risks', diagnostic_wall)
        self.assertIn('medium_risks', diagnostic_wall)
        self.assertIn('recommendations', diagnostic_wall)
        self.assertIn('summary', diagnostic_wall)
        
        # 验证摘要
        summary = diagnostic_wall['summary']
        self.assertIn('grade', summary)
        self.assertIn('overall_score', summary)
        self.assertEqual(summary['overall_score'], dimension_data.get('overall_score', 50))


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestDimensionScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosticWallGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
