"""
CompetitiveAnalyzer单元测试
验证语义差异分析引擎的各项功能
"""
import unittest
from wechat_backend.analytics.competitive_analyzer import CompetitiveAnalyzer


class TestCompetitiveAnalyzer(unittest.TestCase):
    """测试CompetitiveAnalyzer类的功能"""
    
    def setUp(self):
        """测试前准备"""
        self.analyzer = CompetitiveAnalyzer()
    
    def test_keyword_extraction_basic(self):
        """测试基本关键词提取功能"""
        text = "德施曼的智能锁技术先进，小米的性价比突出。"
        brand_name = "德施曼"
        
        keywords = self.analyzer._extract_keywords(text, brand_name)
        
        # 验证提取到的关键词中不包含品牌名
        self.assertNotIn("德施曼", keywords)
        
        # 验证提取到一些有意义的关键词
        self.assertGreaterEqual(len([k for k in keywords if len(k) >= 2]), 2)
    
    def test_keyword_extraction_with_overlap_names(self):
        """测试品牌名重叠情况下的关键词提取"""
        text = "小明明的智能锁不错，小明的性价比更高。"
        brand_name = "小明"
        
        keywords = self.analyzer._extract_keywords(text, brand_name)
        
        # 验证正确区分"小明"和"小明明"
        # "小明"不应该被提取，因为它是"小明明"的一部分
        # 但"小明明"应该被提取
        self.assertIn("小明明", keywords)
    
    def test_common_keywords_identification(self):
        """测试共同关键词识别"""
        my_text = "德施曼的智能锁技术先进，安全性高。"
        competitor_text = "小米的智能锁安全性高，性价比突出。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "小米")
        
        # 验证共同关键词
        self.assertIn("安全性", result['common_keywords'])
    
    def test_unique_keywords_identification(self):
        """测试独有关键词识别"""
        my_text = "德施曼的智能锁技术先进，工艺精湛。"
        competitor_text = "小米的智能锁性价比高，生态丰富。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "小米")
        
        # 验证我方独有关键词
        self.assertIn("技术", result['my_brand_unique_keywords'])
        self.assertIn("工艺", result['my_brand_unique_keywords'])
        
        # 验证竞品独有关键词
        self.assertIn("性价比", result['competitor_unique_keywords'])
        self.assertIn("生态", result['competitor_unique_keywords'])
    
    def test_differentiation_summary_generation(self):
        """测试差异总结生成"""
        my_text = "德施曼的智能锁技术领先，指纹识别准确。"
        competitor_text = "小米的智能锁性价比高，接入米家生态方便。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "小米")
        
        # 验证生成了差异总结
        self.assertIsNotNone(result['differentiation_gap'])
        self.assertIsInstance(result['differentiation_gap'], str)
        self.assertGreaterEqual(len(result['differentiation_gap']), 10)
    
    def test_empty_text_handling(self):
        """测试空文本处理"""
        result = self.analyzer.analyze("", "", "德施曼", "小米")
        
        # 验证即使在空文本情况下也能返回正确的结构
        self.assertIn('common_keywords', result)
        self.assertIn('my_brand_unique_keywords', result)
        self.assertIn('competitor_unique_keywords', result)
        self.assertIn('differentiation_gap', result)
        
        self.assertEqual(result['common_keywords'], [])
        self.assertEqual(result['my_brand_unique_keywords'], [])
        self.assertEqual(result['competitor_unique_keywords'], [])
    
    def test_no_shared_keywords(self):
        """测试没有共享关键词的情况"""
        my_text = "德施曼技术先进工艺精湛。"
        competitor_text = "小米价格便宜生态丰富。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "小米")
        
        # 验证没有共同关键词
        self.assertEqual(result['common_keywords'], [])
        
        # 验证各自有独有关键词
        self.assertGreaterEqual(len(result['my_brand_unique_keywords']), 1)
        self.assertGreaterEqual(len(result['competitor_unique_keywords']), 1)
    
    def test_full_analysis_workflow(self):
        """测试完整分析工作流程"""
        my_text = "德施曼的智能锁在技术方面表现突出，指纹识别算法先进，安全性能优异。"
        competitor_text = "小米的智能锁性价比高，接入米家生态系统，用户体验友好。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "小米")
        
        # 验证返回结构完整
        self.assertIn('common_keywords', result)
        self.assertIn('my_brand_unique_keywords', result)
        self.assertIn('competitor_unique_keywords', result)
        self.assertIn('differentiation_gap', result)
        
        # 验证各部分都有内容
        self.assertIsInstance(result['common_keywords'], list)
        self.assertIsInstance(result['my_brand_unique_keywords'], list)
        self.assertIsInstance(result['competitor_unique_keywords'], list)
        self.assertIsInstance(result['differentiation_gap'], str)
        
        print(f"共同关键词: {result['common_keywords']}")
        print(f"我方独有关键词: {result['my_brand_unique_keywords']}")
        print(f"竞品独有关键词: {result['competitor_unique_keywords']}")
        print(f"差异总结: {result['differentiation_gap']}")
    
    def test_special_characters_handling(self):
        """测试特殊字符处理"""
        my_text = '用户说："德施曼不错"，但也提到了(小米)。'
        competitor_text = "小米的性价比高，德施曼技术先进。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "小米")
        
        # 验证在包含引号、括号等特殊字符的情况下仍能正确分析
        self.assertIn('common_keywords', result)
        self.assertIn('differentiation_gap', result)
    
    def test_case_insensitive_brand_matching(self):
        """测试品牌名大小写不敏感匹配"""
        my_text = "德施曼的智能锁很好，技术和品质都很棒。"
        competitor_text = "MI的智能锁性价比高，技术和设计都很棒。"
        
        result = self.analyzer.analyze(my_text, competitor_text, "德施曼", "MI")
        
        # 验证即使大小写不同也能正确处理
        self.assertIn('common_keywords', result)
        self.assertIn('differentiation_gap', result)


if __name__ == '__main__':
    unittest.main()