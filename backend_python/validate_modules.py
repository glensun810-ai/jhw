#!/usr/bin/env python3
"""
完整验证物理排位解析引擎和信源聚合器
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer
from wechat_backend.analytics.source_aggregator import SourceAggregator


def test_rank_analyzer():
    """测试排名分析器"""
    print("=== 测试排名分析器 ===")
    analyzer = RankAnalyzer()
    
    # 测试文本
    ai_response = "在智能锁领域，德施曼的技术一直领先，其指纹识别算法较为先进。小米的智能锁性价比高，适合大众消费者。凯迪仕也有一定市场份额。相比之下，鹿客在用户体验方面做得更好。TCL也很有竞争力。"
    brand_list = ["德施曼", "小米", "凯迪仕"]
    
    print(f"AI回复: {ai_response}")
    print(f"品牌列表: {brand_list}")
    
    # 执行分析
    result = analyzer.analyze(ai_response, brand_list)
    
    print("分析结果:")
    print(f"- 排名列表: {result['ranking_list']}")
    print(f"- 品牌详情: {result['brand_details']}")
    print(f"- 未列出的竞争对手: {result['unlisted_competitors']}")
    
    # 验证结果结构
    assert 'ranking_list' in result
    assert 'brand_details' in result
    assert 'unlisted_competitors' in result
    print("✓ 排名分析器测试通过\n")


def test_source_aggregator():
    """测试信源聚合器"""
    print("=== 测试信源聚合器 ===")
    aggregator = SourceAggregator()
    
    # 测试文本
    ai_response = """
    在智能锁领域，德施曼的技术一直领先，参考知乎文章[1]和百度百科[2]。
    小米的智能锁性价比高，详情见其官网[3]。
    凯迪仕也有一定市场份额。
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
    
    print(f"AI回复: {ai_response}")
    print(f"引用信息: {citations}")
    
    # 执行聚合
    result = aggregator.aggregate(ai_response, citations)
    
    print("聚合结果:")
    print(f"- 信源池: {result['source_pool']}")
    print(f"- 引用排行: {result['citation_rank']}")
    print(f"- 证据链: {result['evidence_chain']}")
    
    # 验证结果结构
    assert 'source_pool' in result
    assert 'citation_rank' in result
    assert 'evidence_chain' in result
    
    # 验证信源池中的每个项目都有必需字段
    for source in result['source_pool']:
        assert 'id' in source
        assert 'url' in source
        assert 'site_name' in source
        assert 'citation_count' in source
        assert 'domain_authority' in source
    
    print("✓ 信源聚合器测试通过\n")


def test_integration():
    """测试两个模块的集成"""
    print("=== 测试模块集成 ===")
    
    # 创建分析器和聚合器实例
    rank_analyzer = RankAnalyzer()
    source_aggregator = SourceAggregator()
    
    # 综合测试文本
    ai_response = """
    在智能锁市场，德施曼的技术实力较强，指纹识别算法先进，参考知乎[1]和百度百科[2]。
    小米的智能锁性价比突出，适合大众市场，详情见官网[3]。
    凯迪仕在工程渠道有一定份额。
    但鹿客在用户体验方面更胜一筹，TCL也很有竞争力。
    [1] https://zhihu.com/article/dsm-tech
    [2] https://baidu.com/baike/dsm-overview
    [3] https://mi.com/smart-lock-info
    """
    
    brand_list = ["德施曼", "小米", "凯迪仕"]
    citations = [
        {'url': 'https://zhihu.com/article/dsm-tech', 'title': '德施曼技术分析', 'site_name': 'zhihu'},
        {'url': 'https://baidu.com/baike/dsm-overview', 'title': '德施曼概述', 'site_name': 'baidu'},
        {'url': 'https://mi.com/smart-lock-info', 'title': '小米智能锁信息', 'site_name': 'mi'}
    ]
    
    print(f"综合测试 - AI回复: {ai_response}")
    print(f"品牌列表: {brand_list}")
    
    # 执行排名分析
    rank_result = rank_analyzer.analyze(ai_response, brand_list)
    print(f"排名分析结果: {rank_result}")
    
    # 执行信源聚合
    source_result = source_aggregator.aggregate(ai_response, citations)
    print(f"信源聚合结果: {source_result}")
    
    # 验证两个模块都能正常工作
    assert isinstance(rank_result, dict)
    assert isinstance(source_result, dict)
    
    print("✓ 模块集成测试通过\n")


if __name__ == "__main__":
    print("开始验证物理排位解析引擎和信源聚合器...\n")
    
    test_rank_analyzer()
    test_source_aggregator()
    test_integration()
    
    print("🎉 所有验证测试通过！")
    print("物理排位解析引擎和信源聚合器已成功实现并集成。")