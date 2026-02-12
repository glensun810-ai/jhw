"""
测试现有功能是否受到影响
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_views_import():
    """测试views模块能否正常导入"""
    print("=== 测试views模块导入 ===")
    try:
        from wechat_backend import views
        print("✓ views模块导入成功")
        return True
    except Exception as e:
        print(f"✗ views模块导入失败: {e}")
        return False


def test_app_import():
    """测试app模块能否正常导入"""
    print("=== 测试app模块导入 ===")
    try:
        from wechat_backend import app
        print("✓ app模块导入成功")
        return True
    except Exception as e:
        print(f"✗ app模块导入失败: {e}")
        return False


def test_basic_scoring_still_works():
    """测试基础评分功能是否仍然正常工作"""
    print("=== 测试基础评分功能 ===")
    try:
        from ai_judge_module import JudgeResult, ConfidenceLevel
        from scoring_engine import ScoringEngine
        
        # 创建示例评判结果
        sample_results = [
            JudgeResult(
                accuracy_score=85,
                completeness_score=78,
                sentiment_score=82,
                purity_score=75,
                consistency_score=80,
                judgement="回答较为准确完整",
                confidence_level=ConfidenceLevel.HIGH
            )
        ]
        
        # 使用基础评分引擎
        engine = ScoringEngine()
        result = engine.calculate(sample_results)
        
        print(f"✓ 基础评分功能正常，GEO分数: {result.geo_score}")
        return True
    except Exception as e:
        print(f"✗ 基础评分功能异常: {e}")
        return False


def test_enhanced_scoring_available():
    """测试增强评分功能是否可用"""
    print("=== 测试增强评分功能可用性 ===")
    try:
        from enhanced_scoring_engine import EnhancedScoringEngine, calculate_enhanced_scores
        from ai_judge_module import JudgeResult, ConfidenceLevel
        
        # 创建示例评判结果
        sample_results = [
            JudgeResult(
                accuracy_score=85,
                completeness_score=78,
                sentiment_score=82,
                purity_score=75,
                consistency_score=80,
                judgement="回答较为准确完整",
                confidence_level=ConfidenceLevel.HIGH
            )
        ]
        
        # 使用增强评分引擎
        result = calculate_enhanced_scores(sample_results)
        
        print(f"✓ 增强评分功能可用，GEO分数: {result.geo_score}")
        print(f"  认知置信度: {result.cognitive_confidence:.2f}")
        print(f"  建议数量: {len(result.recommendations)}")
        return True
    except Exception as e:
        print(f"✗ 增强评分功能异常: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试现有功能是否受影响...\n")
    
    results = []
    
    # 测试模块导入
    results.append(test_views_import())
    results.append(test_app_import())
    
    # 测试功能
    results.append(test_basic_scoring_still_works())
    results.append(test_enhanced_scoring_available())
    
    print(f"\n=== 测试总结 ===")
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✅ 所有测试通过！现有功能未受影响，新功能已成功集成。")
        return True
    else:
        print("❌ 存在测试失败，请检查问题。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)