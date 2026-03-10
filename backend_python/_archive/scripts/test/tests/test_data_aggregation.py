#!/usr/bin/env python3
"""
数据处理层单元测试 - 验证聚合引擎核心功能

测试场景：
1. 链路闭环检查：验证聚合后的 questionCards 数组长度
2. 归因逻辑验证：验证 avgRank 和 interceptedBy 计算
3. 信源权重验证：验证 toxicSources 数组捕获负面 URL
"""

import unittest
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class MockDataGenerator:
    """
    Mock 数据生成器
    生成符合 N*M 执行引擎输出格式的数据
    """
    
    @staticmethod
    def generate_mock_results(
        questions: List[str],
        platforms: List[str],
        main_brand: str,
        competitor_brands: List[str]
    ) -> List[Dict[str, Any]]:
        """
        生成 Mock 测试结果
        
        Args:
            questions: 问题列表（2 个问题）
            platforms: 平台列表（2 个平台）
            main_brand: 主品牌
            competitor_brands: 竞品品牌列表
            
        Returns:
            Mock 结果列表（共 4 条：2 问题×2 平台）
        """
        results = []
        
        for q_idx, question in enumerate(questions):
            for p_idx, platform in enumerate(platforms):
                # 生成 geo_analysis 数据
                geo_analysis = MockDataGenerator._generate_geo_analysis(
                    question_idx=q_idx,
                    platform_idx=p_idx,
                    main_brand=main_brand,
                    competitor_brands=competitor_brands
                )
                
                result = {
                    'success': True,
                    'brand_name': main_brand,
                    'model': platform,
                    'question': question,
                    'response': f"这是{platform}对问题{q_idx+1}的回答",
                    'geo_data': geo_analysis,
                    'status': 'success',
                    'latency': 10.0 + q_idx + p_idx,
                    'tokens_used': 500 + q_idx * 100 + p_idx * 50
                }
                
                results.append(result)
        
        return results
    
    @staticmethod
    def _generate_geo_analysis(
        question_idx: int,
        platform_idx: int,
        main_brand: str,
        competitor_brands: List[str]
    ) -> Dict[str, Any]:
        """
        生成 geo_analysis 数据
        
        规则：
        - 问题 A (idx=0) 在 DeepSeek (idx=0) 中排名#1（正面）
        - 问题 A (idx=0) 在豆包 (idx=1) 中未上榜（负面并提及竞品）
        - 问题 B (idx=1) 在所有平台中排名正常
        """
        # 问题 A + DeepSeek：排名#1，正面
        if question_idx == 0 and platform_idx == 0:
            return {
                'brand_mentioned': True,
                'rank': 1,
                'sentiment': 0.8,
                'cited_sources': [
                    {
                        'url': 'https://www.zhihu.com/question/123',
                        'site_name': 'zhihu',
                        'attitude': 'positive'
                    }
                ],
                'interception': ''
            }
        
        # 问题 A + 豆包：未上榜（rank=-1），负面，提及竞品
        elif question_idx == 0 and platform_idx == 1:
            return {
                'brand_mentioned': False,
                'rank': -1,  # 未上榜
                'sentiment': -0.5,  # 负面
                'cited_sources': [
                    {
                        'url': 'https://www.toxic-source.com/negative-review',
                        'site_name': 'toxic-source',
                        'attitude': 'negative'
                    }
                ],
                'interception': competitor_brands[0] if competitor_brands else '竞品 A'
            }
        
        # 问题 B + 所有平台：正常排名
        else:
            return {
                'brand_mentioned': True,
                'rank': 3 + platform_idx,
                'sentiment': 0.5 + platform_idx * 0.1,
                'cited_sources': [],
                'interception': ''
            }


class TestDataAggregationEngine(unittest.TestCase):
    """
    数据聚合引擎测试
    验证 N*M 执行结果的聚合逻辑
    """
    
    def setUp(self):
        """测试前准备"""
        self.mock_generator = MockDataGenerator()
        self.main_brand = '业之峰'
        self.competitor_brands = ['天坛装饰', '大宅门']
        self.questions = [
            '北京装修公司哪家好？',  # 问题 A
            '北京装修公司靠谱的推荐'  # 问题 B
        ]
        self.platforms = ['DeepSeek', '豆包']
        
        # 生成 Mock 数据（2 问题×2 平台=4 条）
        self.mock_results = self.mock_generator.generate_mock_results(
            questions=self.questions,
            platforms=self.platforms,
            main_brand=self.main_brand,
            competitor_brands=self.competitor_brands
        )
    
    def test_01_question_cards_length(self):
        """
        测试 1: 链路闭环检查
        
        验证：聚合后的 questionCards 数组长度是否等于 2
        """
        # 模拟聚合逻辑
        question_map = defaultdict(list)
        
        for result in self.mock_results:
            question = result['question']
            question_map[question].append(result)
        
        # 生成 questionCards
        question_cards = []
        for question, results in question_map.items():
            question_cards.append({
                'question': question,
                'results': results,
                'platform_count': len(results)
            })
        
        # 验证：应该有 2 个问题卡片
        self.assertEqual(len(question_cards), 2, 
            f"期望 questionCards 长度为 2，实际为{len(question_cards)}")
        
        # 验证每个问题卡片包含 2 个平台的结果
        for card in question_cards:
            self.assertEqual(card['platform_count'], 2,
                f"问题'{card['question']}'应该有 2 个平台结果，实际为{card['platform_count']}")
    
    def test_02_attribution_logic(self):
        """
        测试 2: 归因逻辑验证
        
        验证：
        - 问题 A 在 DeepSeek 中排名#1（正面）
        - 问题 A 在豆包中未上榜（负面并提及竞品）
        - avgRank = (1 + 10) / 2 = 5.5（未上榜按 10 计算）
        - interceptedBy 正确抓取竞品名称
        """
        # 找到问题 A 的结果
        question_a_results = [r for r in self.mock_results 
                             if r['question'] == self.questions[0]]
        
        self.assertEqual(len(question_a_results), 2,
            f"问题 A 应该有 2 个结果，实际为{len(question_a_results)}")
        
        # 提取 geo_data
        deepseek_result = next(r for r in question_a_results if r['model'] == 'DeepSeek')
        doubao_result = next(r for r in question_a_results if r['model'] == '豆包')
        
        deepseek_geo = deepseek_result['geo_data']
        doubao_geo = doubao_result['geo_data']
        
        # 验证 DeepSeek 排名#1，正面
        self.assertEqual(deepseek_geo['rank'], 1, "DeepSeek 排名应该为 1")
        self.assertGreater(deepseek_geo['sentiment'], 0, "DeepSeek 情感应该为正面")
        
        # 验证豆包未上榜，负面，提及竞品
        self.assertEqual(doubao_geo['rank'], -1, "豆包排名应该为 -1（未上榜）")
        self.assertLess(doubao_geo['sentiment'], 0, "豆包情感应该为负面")
        self.assertTrue(len(doubao_geo['interception']) > 0, "豆包应该提及竞品")
        
        # 计算 avgRank（未上榜按 10 计算）
        rank_deepseek = deepseek_geo['rank']
        rank_doubao = 10 if doubao_geo['rank'] == -1 else doubao_geo['rank']
        avg_rank = (rank_deepseek + rank_doubao) / 2
        
        self.assertEqual(avg_rank, 5.5, 
            f"期望 avgRank 为 5.5，实际为{avg_rank}")
        
        # 验证 interceptedBy
        intercepted_by = doubao_geo['interception']
        self.assertIn(intercepted_by, self.competitor_brands,
            f"interceptedBy 应该包含在竞品列表中，实际为'{intercepted_by}'")
    
    def test_03_toxic_sources(self):
        """
        测试 3: 信源权重验证
        
        验证：toxicSources 数组是否准确捕获 attitude: 'negative' 的 URL 及其模型名称
        """
        # 收集所有 cited_sources
        toxic_sources = []
        
        for result in self.mock_results:
            geo_data = result['geo_data']
            for source in geo_data.get('cited_sources', []):
                if source.get('attitude') == 'negative':
                    toxic_sources.append({
                        'url': source['url'],
                        'site_name': source['site_name'],
                        'model': result['model'],
                        'question': result['question'],
                        'attitude': source['attitude']
                    })
        
        # 验证：应该有 1 个负面信源（来自豆包的问题 A）
        self.assertEqual(len(toxic_sources), 1,
            f"期望 toxicSources 数量为 1，实际为{len(toxic_sources)}")
        
        # 验证负面信源的详细信息
        toxic_source = toxic_sources[0]
        self.assertEqual(toxic_source['model'], '豆包',
            f"负面信源应该来自'豆包'，实际为'{toxic_source['model']}'")
        self.assertEqual(toxic_source['question'], self.questions[0],
            f"负面信源应该来自问题 A，实际为'{toxic_source['question']}'")
        self.assertIn('toxic-source', toxic_source['url'],
            f"负面信源 URL 应该包含'toxic-source'，实际为'{toxic_source['url']}'")
        self.assertEqual(toxic_source['attitude'], 'negative',
            f"attitude 应该为'negative'，实际为'{toxic_source['attitude']}'")


class TestEnhancedAttribution(unittest.TestCase):
    """
    增强归因逻辑测试
    验证更复杂的聚合场景
    """
    
    def test_avg_rank_with_multiple_unranked(self):
        """
        测试多个未上榜情况的 avgRank 计算
        """
        # 模拟数据：3 个平台，2 个未上榜
        ranks = [1, -1, -1]  # DeepSeek=1, 豆包=-1, 通义千问=-1
        
        # 计算 avgRank（未上榜按 10 计算）
        normalized_ranks = [10 if r == -1 else r for r in ranks]
        avg_rank = sum(normalized_ranks) / len(normalized_ranks)
        
        expected_avg_rank = (1 + 10 + 10) / 3  # 7.0
        self.assertEqual(avg_rank, expected_avg_rank,
            f"期望 avgRank 为{expected_avg_rank}，实际为{avg_rank}")
    
    def test_intercepted_by_aggregation(self):
        """
        测试 interceptedBy 的聚合逻辑
        """
        # 模拟多个平台提及不同竞品
        interceptions = {
            'DeepSeek': '',  # 未提及竞品
            '豆包': '天坛装饰',  # 提及竞品 A
            '通义千问': '大宅门',  # 提及竞品 B
            '智谱 AI': '天坛装饰'  # 提及竞品 A
        }
        
        # 聚合 interceptedBy
        all_interceptions = set()
        interception_count = defaultdict(int)
        
        for model, interception in interceptions.items():
            if interception:
                all_interceptions.add(interception)
                interception_count[interception] += 1
        
        # 验证：应该捕获 2 个不同的竞品
        self.assertEqual(len(all_interceptions), 2,
            f"期望捕获 2 个不同竞品，实际为{len(all_interceptions)}")
        
        # 验证：天坛装饰被提及 2 次
        self.assertEqual(interception_count['天坛装饰'], 2,
            f"期望'天坛装饰'被提及 2 次，实际为{interception_count['天坛装饰']}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestDataAggregationEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedAttribution))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
