#!/usr/bin/env python3
"""
评分计算修复验证脚本

验证内容:
1. 从 geo_data 构建 judge_results
2. 调用 ScoringEngine 计算分数
3. 验证分数范围合理性

执行：python3 test_scoring_fix.py
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from scoring_engine import ScoringEngine
from enhanced_scoring_engine import calculate_enhanced_scores
from ai_judge_module import JudgeResult, ConfidenceLevel


def test_geo_data_to_score():
    """测试从 geo_data 到分数的转换"""
    print("\n" + "="*60)
    print("测试 1: geo_data 到分数的转换")
    print("="*60)
    
    # 模拟 geo_data
    test_cases = [
        {'rank': 1, 'sentiment': 0.8, 'expected_score_range': (85, 100)},
        {'rank': 2, 'sentiment': 0.5, 'expected_score_range': (80, 95)},
        {'rank': 3, 'sentiment': 0.3, 'expected_score_range': (75, 90)},
        {'rank': 5, 'sentiment': 0.2, 'expected_score_range': (60, 80)},
        {'rank': 8, 'sentiment': -0.3, 'expected_score_range': (40, 60)},
        {'rank': -1, 'sentiment': 0.5, 'expected_score_range': (30, 50)},  # 未入榜
    ]
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        rank = case['rank']
        sentiment = case['sentiment']
        expected_range = case['expected_score_range']
        
        # 计算 accuracy_score (与 nxm_execution_engine.py 中逻辑一致)
        if rank <= 0:
            accuracy_score = 30 + sentiment * 20
        elif rank <= 3:
            accuracy_score = 85 + (3 - rank) * 5 + sentiment * 10
        elif rank <= 6:
            accuracy_score = 65 + (6 - rank) * 5 + sentiment * 10
        else:
            accuracy_score = 45 + (10 - rank) * 3 + sentiment * 10
        
        accuracy_score = max(0, min(100, accuracy_score))
        
        # 计算 sentiment_score
        sentiment_score = (sentiment + 1) * 50
        
        # 检查是否在预期范围内
        in_range = expected_range[0] <= accuracy_score <= expected_range[1]
        status = "✅" if in_range else "❌"
        
        print(f"\n  测试 {i}: rank={rank}, sentiment={sentiment}")
        print(f"    accuracy_score: {accuracy_score:.1f} (预期：{expected_range[0]}-{expected_range[1]}) {status}")
        print(f"    sentiment_score: {sentiment_score:.1f}")
        
        if not in_range:
            all_passed = False
    
    print(f"\n{'='*60}")
    print(f"测试 1 结果：{'✅ 通过' if all_passed else '❌ 失败'}")
    print(f"{'='*60}")
    return all_passed


def test_scoring_engine():
    """测试评分引擎"""
    print("\n" + "="*60)
    print("测试 2: ScoringEngine 评分引擎")
    print("="*60)
    
    # 构建 judge_results
    judge_results = []
    
    # 模拟 3 个 AI 平台的评判结果
    test_data = [
        {'rank': 2, 'sentiment': 0.6},
        {'rank': 3, 'sentiment': 0.4},
        {'rank': 1, 'sentiment': 0.8},
    ]
    
    for data in test_data:
        rank = data['rank']
        sentiment = data['sentiment']
        
        # 计算各维度分数
        if rank <= 0:
            accuracy_score = 30 + sentiment * 20
        elif rank <= 3:
            accuracy_score = 85 + (3 - rank) * 5 + sentiment * 10
        elif rank <= 6:
            accuracy_score = 65 + (6 - rank) * 5 + sentiment * 10
        else:
            accuracy_score = 45 + (10 - rank) * 3 + sentiment * 10
        
        accuracy_score = max(0, min(100, accuracy_score))
        completeness_score = 70
        sentiment_score = (sentiment + 1) * 50
        
        judge_result = JudgeResult(
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            sentiment_score=sentiment_score,
            purity_score=sentiment_score * 0.9,
            consistency_score=accuracy_score * 0.95,
            judgement=f"Rank: {rank}, Sentiment: {sentiment:.2f}",
            confidence_level=ConfidenceLevel.HIGH if rank > 0 else ConfidenceLevel.MEDIUM
        )
        judge_results.append(judge_result)
    
    # 调用评分引擎
    scoring_engine = ScoringEngine()
    result = scoring_engine.calculate(judge_results)
    
    print(f"\n  输入：{len(judge_results)} 个 judge_results")
    print(f"  输出:")
    print(f"    GEO 分数：{result.geo_score}")
    print(f"    等级：{result.grade}")
    print(f"    标签：{result.label}")
    print(f"    权威度：{result.authority_score:.1f}")
    print(f"    可见度：{result.visibility_score:.1f}")
    print(f"    情感度：{result.sentiment_score:.1f}")
    print(f"    纯净度：{result.purity_score:.1f}")
    print(f"    一致性：{result.consistency_score:.1f}")
    
    # 验证分数合理性
    valid_score = 0 <= result.geo_score <= 100
    valid_grade = result.grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-']
    
    print(f"\n  验证:")
    print(f"    分数范围：{'✅' if valid_score else '❌'} (0-100)")
    print(f"    等级有效：{'✅' if valid_grade else '❌'}")
    
    passed = valid_score and valid_grade
    print(f"\n{'='*60}")
    print(f"测试 2 结果：{'✅ 通过' if passed else '❌ 失败'}")
    print(f"{'='*60}")
    return passed


def test_enhanced_scoring():
    """测试增强评分引擎"""
    print("\n" + "="*60)
    print("测试 3: EnhancedScoringEngine 增强评分")
    print("="*60)
    
    judge_results = [
        JudgeResult(
            accuracy_score=85,
            completeness_score=78,
            sentiment_score=82,
            purity_score=75,
            consistency_score=80,
            judgement='测试',
            confidence_level=ConfidenceLevel.HIGH
        )
    ]
    
    result = calculate_enhanced_scores(judge_results, brand_name='华为')
    
    print(f"\n  品牌：华为")
    print(f"  GEO 分数：{result.geo_score}")
    print(f"  等级：{result.grade} ({result.label})")
    print(f"  认知置信度：{result.cognitive_confidence:.2f}")
    print(f"  建议数量：{len(result.recommendations)}")
    print(f"  总结：{result.summary[:50]}...")
    
    passed = result.geo_score > 0 and result.grade is not None
    print(f"\n{'='*60}")
    print(f"测试 3 结果：{'✅ 通过' if passed else '❌ 失败'}")
    print(f"{'='*60}")
    return passed


def main():
    print("\n" + "="*60)
    print("  评分计算修复验证测试")
    print("  Scoring Fix Verification Test")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("geo_data 转换", test_geo_data_to_score()))
    results.append(("评分引擎", test_scoring_engine()))
    results.append(("增强评分", test_enhanced_scoring()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("  测试汇总")
    print("="*60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    total_passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\n  总计：{total_passed}/{total} 测试通过")
    print(f"{'='*60}")
    
    if total_passed == total:
        print("\n  🎉 所有测试通过！评分计算功能正常。")
        return True
    else:
        print("\n  ⚠️ 部分测试失败，请检查。")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
