"""
RankAnalyzer单元测试
验证物理排位解析引擎的各项功能
"""
import unittest
from wechat_backend.analytics.rank_analyzer import RankAnalyzer


class TestRankAnalyzer(unittest.TestCase):
    """测试RankAnalyzer类的功能"""
    
    def setUp(self):
        """测试前准备"""
        self.analyzer = RankAnalyzer()
    
    def test_extract_ranking_list_basic(self):
        """测试基本排名提取功能"""
        ai_response = "德施曼的智能锁很好，小米也不错，凯迪仕也有一定市场。"
        brand_list = ["德施曼", "小米", "凯迪仕"]
        
        ranking_list = self.analyzer._extract_ranking_list(ai_response, brand_list)
        
        # 验证排名顺序
        self.assertEqual(ranking_list[0], "德施曼")
        self.assertEqual(ranking_list[1], "小米")
        self.assertEqual(ranking_list[2], "凯迪仕")
    
    def test_extract_ranking_list_with_overlap_names(self):
        """测试品牌名称重叠的情况"""
        ai_response = "小米手机很好，小米汽车也不错，小明品牌也有提及。"
        brand_list = ["小米", "小明"]
        
        ranking_list = self.analyzer._extract_ranking_list(ai_response, brand_list)
        
        # 小米应该在前面，因为先出现
        self.assertEqual(ranking_list[0], "小米")
        self.assertEqual(ranking_list[1], "小明")
    
    def test_extract_ranking_list_partial_match_avoidance(self):
        """测试避免部分匹配"""
        ai_response = "小明科技的产品很不错，明明是个好孩子。"
        brand_list = ["小明", "明明"]
        
        ranking_list = self.analyzer._extract_ranking_list(ai_response, brand_list)
        
        # 应该区分"小明"和"明明"，而不是将"小明"误认为是"明明"的一部分
        self.assertIn("小明", ranking_list)
        self.assertIn("明明", ranking_list)
    
    def test_brand_details_calculation(self):
        """测试品牌详情计算"""
        ai_response = "德施曼的智能锁很好，功能强大。小米性价比高。凯迪仕也不错。"
        brand_list = ["德施曼", "小米", "凯迪仕"]
        
        brand_details = self.analyzer._extract_brand_details(ai_response, brand_list)
        
        # 验证每个品牌都有详情
        self.assertIn("德施曼", brand_details)
        self.assertIn("小米", brand_details)
        self.assertIn("凯迪仕", brand_details)
        
        # 验证排名
        self.assertEqual(brand_details["德施曼"]["rank"], 1)
        self.assertGreaterEqual(brand_details["德施曼"]["word_count"], 0)
        self.assertGreaterEqual(brand_details["德施曼"]["sov_share"], 0)
        
    def test_word_count_calculation(self):
        """测试字数统计"""
        ai_response = "德施曼的智能锁很好，功能强大。小米性价比高。"
        word_count = self.analyzer._calculate_brand_word_count(ai_response, "德施曼")
        
        # 德施曼出现的位置及其周围句子的长度
        self.assertGreaterEqual(word_count, len("德施曼的智能锁很好，功能强大。"))
    
    def test_unlisted_competitors_detection(self):
        """测试未列出竞争对手的检测"""
        ai_response = "德施曼和小米都不错，但鹿客的用户体验更好，TCL也很有竞争力。"
        brand_list = ["德施曼", "小米"]
        
        unlisted = self.analyzer._identify_unlisted_competitors(ai_response, brand_list)
        
        # 验证检测到未列出的品牌
        self.assertIn("鹿客", unlisted)
        self.assertIn("TCL", unlisted)
    
    def test_analyze_method_full_workflow(self):
        """测试analyze方法的完整工作流程"""
        ai_response = "在智能锁领域，德施曼的技术领先，小米性价比突出，凯迪仕也有一定份额。鹿客用户体验更好。"
        brand_list = ["德施曼", "小米", "凯迪仕"]
        
        result = self.analyzer.analyze(ai_response, brand_list)
        
        # 验证返回结构符合exposure_analysis格式
        self.assertIn("ranking_list", result)
        self.assertIn("brand_details", result)
        self.assertIn("unlisted_competitors", result)
        
        # 验证排名列表
        self.assertEqual(result["ranking_list"][0], "德施曼")
        self.assertEqual(result["ranking_list"][1], "小米")
        self.assertEqual(result["ranking_list"][2], "凯迪仕")
        
        # 验证品牌详情
        self.assertIn("德施曼", result["brand_details"])
        self.assertIn("小米", result["brand_details"])
        self.assertIn("凯迪仕", result["brand_details"])
        
        # 验证未列出的竞争对手
        self.assertIn("鹿客", result["unlisted_competitors"])
    
    def test_empty_response_handling(self):
        """测试空响应的处理"""
        ai_response = ""
        brand_list = ["德施曼", "小米"]
        
        result = self.analyzer.analyze(ai_response, brand_list)
        
        # 验证即使在空响应情况下也能返回正确的结构
        self.assertEqual(result["ranking_list"], [])
        self.assertEqual(len(result["brand_details"]), 2)  # 两个品牌都应该有记录
        self.assertEqual(result["unlisted_competitors"], [])
    
    def test_no_monitored_brand_mentioned(self):
        """测试没有监控品牌被提及的情况"""
        ai_response = "这是一个关于其他产品的讨论。"
        brand_list = ["德施曼", "小米"]
        
        result = self.analyzer.analyze(ai_response, brand_list)
        
        # 验证排名列表为空
        self.assertEqual(result["ranking_list"], [])
        # 但品牌详情仍然存在，只是rank为-1
        for brand in brand_list:
            self.assertIn(brand, result["brand_details"])
            self.assertEqual(result["brand_details"][brand]["rank"], -1)
    
    def test_special_characters_and_boundaries(self):
        """测试特殊字符和边界情况"""
        ai_response = '用户说："德施曼不错"，但也提到了(小米)。'
        brand_list = ["德施曼", "小米"]
        
        result = self.analyzer.analyze(ai_response, brand_list)
        
        # 验证在引号、括号等特殊字符中也能正确识别品牌
        self.assertIn("德施曼", result["ranking_list"])
        self.assertIn("小米", result["ranking_list"])
    
    def test_case_insensitive_matching(self):
        """测试大小写不敏感匹配"""
        ai_response = "Apple手机很好，APPLE商店服务也不错。"
        brand_list = ["Apple"]
        
        result = self.analyzer.analyze(ai_response, brand_list)
        
        # 验证大小写不敏感的匹配
        self.assertIn("Apple", result["ranking_list"])
        self.assertGreater(result["brand_details"]["Apple"]["word_count"], 0)


if __name__ == '__main__':
    unittest.main()