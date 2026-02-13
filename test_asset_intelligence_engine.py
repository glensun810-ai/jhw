"""
资产智能引擎单元测试
"""
import unittest
from wechat_backend.analytics.asset_intelligence_engine import AssetIntelligenceEngine


class TestAssetIntelligenceEngine(unittest.TestCase):
    """测试AssetIntelligenceEngine类的功能"""

    def setUp(self):
        """设置测试环境"""
        self.engine = AssetIntelligenceEngine()

    def test_calculate_content_hit_rate_basic(self):
        """测试基本内容命中率计算"""
        official_content = "我们是一家AI技术创新公司，提供高品质解决方案"
        ai_content = "这是一家AI技术公司，提供高质量的解决方案"
        
        hit_rate = self.engine.calculate_content_hit_rate(official_content, ai_content)
        
        self.assertIsInstance(hit_rate, float)
        self.assertGreaterEqual(hit_rate, 0.0)
        self.assertLessEqual(hit_rate, 100.0)
        print(f"基本内容命中率: {hit_rate:.2f}%")

    def test_calculate_content_hit_rate_different_content(self):
        """测试不同内容的命中率计算"""
        official_content = "我们专注于人工智能技术创新"
        ai_content = "这是一个完全不相关的主题"
        
        hit_rate = self.engine.calculate_content_hit_rate(official_content, ai_content)
        
        self.assertIsInstance(hit_rate, float)
        self.assertGreaterEqual(hit_rate, 0.0)
        self.assertLess(hit_rate, 50.0)  # 应该很低
        print(f"不同内容命中率: {hit_rate:.2f}%")

    def test_calculate_content_hit_rate_identical_content(self):
        """测试相同内容的命中率计算"""
        content = "我们是一家AI技术创新公司，提供高品质解决方案"
        
        hit_rate = self.engine.calculate_content_hit_rate(content, content)
        
        self.assertIsInstance(hit_rate, float)
        self.assertGreaterEqual(hit_rate, 80.0)  # 应该很高
        print(f"相同内容命中率: {hit_rate:.2f}%")

    def test_analyze_content_matching_basic(self):
        """测试基本内容匹配分析"""
        official_asset = "我们是一家专注于AI技术创新的公司，致力于提供高品质的解决方案"
        
        ai_preferences = {
            'doubao': [
                "这是一家AI技术公司，技术实力不错",
                "他们提供高质量的AI解决方案"
            ],
            'qwen': [
                "该公司在AI领域有技术创新",
                "提供高品质的技术服务"
            ]
        }
        
        result = self.engine.analyze_content_matching(official_asset, ai_preferences)
        
        # 验证结果结构
        self.assertIn('content_hit_rate', result)
        self.assertIn('platform_analyses', result)
        self.assertIn('overall_score', result)
        self.assertIn('optimization_suggestions', result)
        self.assertIn('semantic_gaps', result)
        
        # 验证数据类型
        self.assertIsInstance(result['content_hit_rate'], float)
        self.assertIsInstance(result['platform_analyses'], dict)
        self.assertIsInstance(result['overall_score'], float)
        self.assertIsInstance(result['optimization_suggestions'], list)
        self.assertIsInstance(result['semantic_gaps'], list)
        
        print(f"总体匹配得分: {result['overall_score']:.2f}")
        print(f"平台分析数量: {len(result['platform_analyses'])}")
        print(f"优化建议数量: {len(result['optimization_suggestions'])}")
        print(f"语义鸿沟数量: {len(result['semantic_gaps'])}")

    def test_get_optimization_recommendations(self):
        """测试优化建议获取"""
        official_asset = "我们是一家AI技术创新公司，提供高品质解决方案"
        
        ai_preferences = {
            'doubao': [
                "这家公司在AI领域技术实力不错，特别是在机器学习方面有深厚积累",
                "他们的AI解决方案在业界有一定知名度"
            ]
        }
        
        recommendations = self.engine.get_optimization_recommendations(official_asset, ai_preferences)
        
        self.assertIsInstance(recommendations, list)
        for rec in recommendations:
            self.assertIsInstance(rec, str)
        
        print(f"优化建议数量: {len(recommendations)}")
        for i, rec in enumerate(recommendations):
            print(f"  建议 {i+1}: {rec}")

    def test_analyze_single_platform(self):
        """测试单平台分析"""
        official_asset = "我们是一家AI技术创新公司"
        ai_contents = [
            "这是一家AI技术公司",
            "他们在AI领域有创新"
        ]
        
        result = self.engine._analyze_single_platform(official_asset, ai_contents, 'doubao')
        
        # 验证结果结构
        self.assertIn('hit_rate', result)
        self.assertIn('semantic_similarity', result)
        self.assertIn('keyword_overlap', result)
        self.assertIn('official_keywords', result)
        self.assertIn('ai_keywords', result)
        self.assertIn('missing_keywords', result)
        
        # 验证数据类型
        self.assertIsInstance(result['hit_rate'], float)
        self.assertIsInstance(result['semantic_similarity'], float)
        self.assertIsInstance(result['keyword_overlap'], float)
        self.assertIsInstance(result['official_keywords'], list)
        self.assertIsInstance(result['ai_keywords'], list)
        self.assertIsInstance(result['missing_keywords'], list)
        
        print(f"单平台命中率: {result['hit_rate']:.2f}%")
        print(f"语义相似度: {result['semantic_similarity']:.2f}")
        print(f"关键词重合度: {result['keyword_overlap']:.2f}")

    def test_generate_optimization_suggestions(self):
        """测试优化建议生成"""
        official_asset = "我们是一家AI技术创新公司"
        ai_preferences = {
            'doubao': [
                "这是一家AI技术公司，技术实力不错",
                "他们在AI领域有深厚积累"
            ]
        }
        platform_analyses = {
            'doubao': {
                'hit_rate': 40.0,  # 低于60%，应该生成建议
                'missing_keywords': ['技术实力', '深厚积累']
            }
        }
        
        suggestions = self.engine._generate_optimization_suggestions(
            official_asset, ai_preferences, platform_analyses
        )
        
        self.assertIsInstance(suggestions, list)
        for suggestion in suggestions:
            self.assertIsInstance(suggestion, dict)
            self.assertIn('platform', suggestion)
            self.assertIn('type', suggestion)
            self.assertIn('description', suggestion)
            self.assertIn('suggested_keywords', suggestion)
            self.assertIn('rationale', suggestion)
        
        print(f"生成的优化建议数量: {len(suggestions)}")
        for i, suggestion in enumerate(suggestions):
            print(f"  建议 {i+1}: {suggestion['description']}")

    def test_identify_semantic_gaps(self):
        """测试语义鸿沟识别"""
        official_asset = "我们是一家AI技术创新公司"
        ai_preferences = {
            'doubao': [
                "这是一家完全不同类型的公司",
                "与AI技术无关的业务"
            ]
        }
        
        gaps = self.engine._identify_semantic_gaps(official_asset, ai_preferences)
        
        self.assertIsInstance(gaps, list)
        for gap in gaps:
            self.assertIsInstance(gap, dict)
            self.assertIn('platform', gap)
            self.assertIn('drift_score', gap)
            self.assertIn('severity', gap)
            self.assertIn('missing_keywords', gap)
            self.assertIn('unexpected_keywords', gap)
            self.assertIn('description', gap)
        
        print(f"识别的语义鸿沟数量: {len(gaps)}")
        for i, gap in enumerate(gaps):
            print(f"  鸿沟 {i+1}: {gap['description']} (偏移得分: {gap['drift_score']})")

    def test_empty_inputs(self):
        """测试空输入"""
        # 测试空官方资产
        result = self.engine.analyze_content_matching("", {'doubao': ["some content"]})
        self.assertIsInstance(result, dict)
        
        # 测试空AI偏好
        result = self.engine.analyze_content_matching("some content", {})
        self.assertIsInstance(result, dict)
        
        print("空输入测试通过")

    def test_special_characters(self):
        """测试特殊字符处理"""
        official_asset = "我们是一家AI公司，提供高品质解决方案！@#$%^&*()"
        ai_contents = ["这是一家AI公司，提供高质量服务"]
        
        hit_rate = self.engine.calculate_content_hit_rate(official_asset, ai_contents[0])
        self.assertIsInstance(hit_rate, float)
        print(f"特殊字符内容命中率: {hit_rate:.2f}%")


if __name__ == '__main__':
    unittest.main()