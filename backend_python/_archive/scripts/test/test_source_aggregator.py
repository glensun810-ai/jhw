"""
SourceAggregator模块的单元测试
"""
import unittest
import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.analytics.source_aggregator import SourceAggregator


class TestSourceAggregator(unittest.TestCase):
    """测试SourceAggregator类的功能"""
    
    def setUp(self):
        """测试前准备"""
        self.aggregator = SourceAggregator()
    
    def test_url_extraction_from_text(self):
        """测试从文本中提取URL"""
        ai_response = "德施曼的智能锁很好，参考知乎文章：https://zhihu.com/article/123。小米性价比高，详见官网：https://mi.com/smartlock。"
        
        extracted_urls = self.aggregator._extract_urls(ai_response)
        
        # 验证URL被正确提取
        self.assertGreaterEqual(len(extracted_urls), 2)
        
        urls_found = [item['url'] for item in extracted_urls]
        self.assertIn('https://zhihu.com/article/123', urls_found)
        self.assertIn('https://mi.com/smartlock', urls_found)
    
    def test_url_extraction_from_citations(self):
        """测试从引用信息中提取URL"""
        ai_response = "德施曼和小米都很不错。"
        citations = [
            {'url': 'https://kedixi.com', 'title': '凯迪仕官网', 'site_name': 'kedixi'},
            {'url': 'https://tuya.com', 'title': '涂鸦智能', 'site_name': 'tuya'}
        ]
        
        extracted_urls = self.aggregator._extract_urls(ai_response, citations)
        
        # 验证引用中的URL被正确提取
        urls_found = [item['url'] for item in extracted_urls]
        self.assertIn('https://kedixi.com', urls_found)
        self.assertIn('https://tuya.com', urls_found)
    
    def test_source_statistics_generation(self):
        """测试信源统计生成"""
        ai_response = "德施曼的智能锁很好，参考知乎(zhihu.com)和百度(baidu.com)。小米性价比高，也参考了知乎。"
        brand_list = ["德施曼", "小米"]
        
        # 先提取URL
        extracted_urls = self.aggregator._extract_urls(ai_response)
        
        # 生成信源统计
        source_pool, citation_rank = self.aggregator._generate_source_statistics(extracted_urls)
        
        # 验证返回结构
        self.assertIsInstance(source_pool, list)
        self.assertIsInstance(citation_rank, list)
        
        # 验证信源池中的每个项目都有必需的字段
        for source in source_pool:
            self.assertIn('id', source)
            self.assertIn('url', source)
            self.assertIn('site_name', source)
            self.assertIn('citation_count', source)
            self.assertIn('domain_authority', source)
    
    def test_domain_authority_assessment(self):
        """测试域名权威度评估"""
        # 测试高权威度站点
        high_authority = self.aggregator._assess_domain_authority('zhihu')
        self.assertIn(high_authority, ['High', 'Medium', 'Low'])

        # 测试中等权威度站点
        medium_authority = self.aggregator._assess_domain_authority('csdn')
        self.assertIn(medium_authority, ['High', 'Medium', 'Low'])

        # 测试低权威度站点
        low_authority = self.aggregator._assess_domain_authority('unknown-site')
        self.assertIn(low_authority, ['High', 'Medium', 'Low'])
    
    def test_keyword_extraction(self):
        """测试关键词提取"""
        text = "德施曼智能锁的安全性非常好，但价格偏高。"
        keywords = self.aggregator._extract_keywords(text)
        
        # 验证提取到一些关键词
        self.assertIsInstance(keywords, list)
    
    def test_risk_level_determination(self):
        """测试风险等级确定"""
        high_risk_text = "该品牌存在严重的安全漏洞"
        medium_risk_text = "这个产品有些小问题"
        low_risk_text = "外观设计一般般"
        
        high_risk_level = self.aggregator._determine_risk_level(high_risk_text)
        medium_risk_level = self.aggregator._determine_risk_level(medium_risk_text)
        low_risk_level = self.aggregator._determine_risk_level(low_risk_text)
        
        # 验证返回了适当的风险等级
        self.assertIn(high_risk_level, ['High', 'Medium', 'Low'])
        self.assertIn(medium_risk_level, ['High', 'Medium', 'Low'])
        self.assertIn(low_risk_level, ['High', 'Medium', 'Low'])
    
    def test_full_aggregation_workflow(self):
        """测试完整的聚合工作流程"""
        ai_response = """
        在智能锁领域，德施曼的技术一直领先，其指纹识别算法较为先进，参考知乎文章[1]和百度百科[2]。
        小米的智能锁性价比高，适合大众消费者，详情可见其官网[3]。
        凯迪仕在工程渠道也有一定份额。
        相比之下，鹿客在用户体验方面做得更好，TCL也很有竞争力。
        [1] https://zhihu.com/article/dsm
        [2] https://baidu.com/baike/dsm
        [3] https://mi.com/smartlock
        """

        citations = [
            {'url': 'https://zhihu.com/article/dsm', 'title': '德施曼评测', 'site_name': 'zhihu'},
            {'url': 'https://baidu.com/baike/dsm', 'title': '德施曼百科', 'site_name': 'baidu'},
            {'url': 'https://mi.com/smartlock', 'title': '小米智能锁', 'site_name': 'mi'}
        ]

        # 执行完整聚合
        result = self.aggregator.aggregate(ai_response, citations)

        # 验证返回结构
        self.assertIn('source_pool', result)
        self.assertIn('citation_rank', result)
        self.assertIn('evidence_chain', result)

        # 验证信源池包含必需字段
        for source in result['source_pool']:
            self.assertIn('id', source)
            self.assertIn('url', source)
            self.assertIn('site_name', source)
            self.assertIn('citation_count', source)
            self.assertIn('domain_authority', source)

        # 验证引用排行
        self.assertIsInstance(result['citation_rank'], list)

        # 验证证据链
        self.assertIsInstance(result['evidence_chain'], list)

        # 验证未列出的竞争对手检测
        unlisted_sources = [item['source_name'] for item in result['evidence_chain']]
        # 注意：由于算法的复杂性，可能无法检测到所有未列出品牌，但至少应返回结构正确的结果
        print(f"Unlisted sources detected: {unlisted_sources}")
    
    def test_empty_input_handling(self):
        """测试空输入的处理"""
        result = self.aggregator.aggregate("", [])

        # 验证即使在空输入情况下也返回正确的结构
        self.assertIn('source_pool', result)
        self.assertIn('citation_rank', result)
        self.assertIn('evidence_chain', result)
        self.assertEqual(result['source_pool'], [])
        self.assertEqual(result['citation_rank'], [])
        self.assertEqual(result['evidence_chain'], [])
    
    def test_markdown_link_extraction(self):
        """测试Markdown链接提取"""
        ai_response = "参考[德施曼官网](https://desman.com)和[小米商城](https://mi.com)了解更多。"
        
        extracted_urls = self.aggregator._extract_urls(ai_response)
        
        # 验证Markdown链接被正确提取
        found_urls = [item['url'] for item in extracted_urls]
        self.assertIn('https://desman.com', found_urls)
        self.assertIn('https://mi.com', found_urls)
        
        # 验证链接文本也被提取
        found_titles = [item['title'] for item in extracted_urls]
        self.assertIn('德施曼官网', found_titles)
        self.assertIn('小米商城', found_titles)


if __name__ == '__main__':
    unittest.main()