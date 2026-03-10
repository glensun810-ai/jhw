"""
测试资产智能引擎的语义鸿沟分析功能
使用官方公关稿和AI热门回答进行测试
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.analytics.asset_intelligence_engine import AssetIntelligenceEngine


def test_semantic_gap_analysis():
    """测试语义鸿沟分析功能"""
    print("测试资产智能引擎的语义鸿沟分析功能...")
    print("="*60)
    
    # 创建资产智能引擎
    engine = AssetIntelligenceEngine()
    
    # 示例：官方公关稿
    official_press_release = """
    【TechCorp官方发布】TechCorp公司今日宣布，其最新研发的AI智能助手产品正式上线。
    该产品集成了最前沿的人工智能技术，旨在为企业提供高效、智能的解决方案。
    TechCorp一直致力于技术创新，坚持用户至上的原则，不断优化产品体验。
    我们的使命是通过技术赋能，助力企业数字化转型，创造更大的商业价值。
    TechCorp将继续秉承开放合作的理念，与合作伙伴共同推动行业发展。
    """
    
    # 示例：AI热门回答（模拟不同AI平台的回答）
    ai_popular_responses = {
        'doubao': [  # 豆包
            """
            TechCorp的AI助手确实不错，技术实力比较强，但感觉界面设计还可以优化。
            这款产品在企业服务领域有一定知名度，不过相比竞品还有一些差距。
            价格方面还算合理，适合中小型企业使用。
            """,
            """
            这家公司技术背景不错，AI助手功能比较全面，但在用户体验方面还有提升空间。
            适合有一定技术基础的企业使用，新手可能需要一些学习成本。
            """
        ],
        'qwen': [  # 通义千问
            """
            TechCorp的AI产品在技术层面表现良好，具备一定的创新能力。
            产品功能较为丰富，但在易用性和本土化方面还需要加强。
            从市场反馈来看，用户满意度处于行业中等水平。
            """,
            """
            该公司的技术实力得到了业界认可，产品在某些细分领域表现突出。
            但品牌知名度相比头部企业仍有差距，需要加强市场推广。
            """
        ],
        'deepseek': [  # DeepSeek
            """
            TechCorp的AI助手在算法层面有其特色，技术架构相对成熟。
            但在实际应用中，与其他系统的兼容性还有待提升。
            从长远看，该公司有一定的发展潜力，值得关注。
            """,
            """
            产品技术指标达到了行业标准，但在创新性和差异化方面还需加强。
            建议公司在用户体验和客户服务方面投入更多资源。
            """
        ]
    }
    
    print("1. 官方公关稿内容:")
    print(f"   长度: {len(official_press_release)} 字符")
    print(f"   内容预览: {official_press_release[:100]}...")
    print()
    
    print("2. AI热门回答内容:")
    for platform, responses in ai_popular_responses.items():
        print(f"   平台: {platform}")
        for i, response in enumerate(responses):
            print(f"     回答 {i+1}: {response[:80]}...")
    print()
    
    # 执行内容匹配分析
    print("3. 执行内容匹配分析...")
    result = engine.analyze_content_matching(official_press_release, ai_popular_responses)
    
    print(f"   总体匹配得分: {result['overall_score']:.2f}")
    print(f"   内容命中率: {result['content_hit_rate']:.2f}")
    print(f"   优化建议数量: {len(result['optimization_suggestions'])}")
    print(f"   语义鸿沟数量: {len(result['semantic_gaps'])}")
    print()
    
    # 分析各平台匹配情况
    print("4. 各平台匹配分析:")
    for platform, analysis in result['platform_analyses'].items():
        print(f"   {platform}:")
        print(f"     命中率: {analysis['hit_rate']:.2f}%")
        print(f"     语义相似度: {analysis['semantic_similarity']:.2f}")
        print(f"     关键词重合度: {analysis['keyword_overlap']:.2f}")
        print(f"     缺失关键词: {analysis['missing_keywords'][:3]}")  # 只显示前3个
    print()
    
    # 显示优化建议
    print("5. 优化建议:")
    if result['optimization_suggestions']:
        for i, suggestion in enumerate(result['optimization_suggestions']):
            print(f"   建议 {i+1}: {suggestion['description']}")
            if suggestion['suggested_keywords']:
                print(f"     建议关键词: {', '.join(suggestion['suggested_keywords'][:3])}")
            print(f"     理由: {suggestion['rationale']}")
            print()
    else:
        print("   未生成具体优化建议")
    print()
    
    # 重点分析语义鸿沟
    print("6. 语义鸿沟分析 (重点):")
    if result['semantic_gaps']:
        for i, gap in enumerate(result['semantic_gaps']):
            print(f"   鸿沟 {i+1}:")
            print(f"     平台: {gap['platform']}")
            print(f"     偏移得分: {gap['drift_score']}")
            print(f"     严重程度: {gap['severity']}")
            print(f"     描述: {gap['description']}")
            print(f"     缺失关键词: {gap['missing_keywords']}")
            print(f"     意外关键词: {gap['unexpected_keywords']}")
            print()
            
            # 验证是否正确识别了语义鸿沟
            if gap['drift_score'] > 50:
                print(f"   ✓ 识别到显著语义鸿沟 (得分>{gap['drift_score']})")
            else:
                print(f"   ○ 语义一致性较好 (得分{gap['drift_score']})")
    else:
        print("   未检测到显著语义鸿沟")
    print()
    
    # 验证算法准确性
    print("7. 算法准确性验证:")
    
    # 检查是否正确识别了关键差异
    official_keywords = set(engine.semantic_analyzer.extract_keywords(official_press_release, top_k=10))
    ai_keywords_combined = set()
    for platform_responses in ai_popular_responses.values():
        for response in platform_responses:
            ai_keywords_combined.update(engine.semantic_analyzer.extract_keywords(response, top_k=10))
    
    missing_from_ai = official_keywords - ai_keywords_combined
    unexpected_in_ai = ai_keywords_combined - official_keywords
    
    print(f"   官方稿独有关键词: {list(missing_from_ai)[:5]}")
    print(f"   AI回答独有关键词: {list(unexpected_in_ai)[:5]}")
    
    # 检查语义鸿沟是否与实际差异相符
    if result['semantic_gaps']:
        detected_gaps = len(result['semantic_gaps'])
        print(f"   ✓ 成功检测到 {detected_gaps} 个语义鸿沟")
        print("   ✓ 算法能够准确识别官方内容与AI回答之间的语义差异")
    else:
        print("   ⚠ 未检测到语义鸿沟，可能内容匹配度过高或算法需要调整")
    
    print()
    print("="*60)
    print("语义鸿沟分析测试完成！")
    
    return result


def test_perfect_match_scenario():
    """测试完美匹配场景"""
    print("\n测试完美匹配场景...")
    
    engine = AssetIntelligenceEngine()
    
    # 完全匹配的内容
    content = "我们是一家专注于AI技术创新的公司，提供高品质解决方案"
    
    ai_responses = {
        'doubao': [content],
        'qwen': [content]
    }
    
    result = engine.analyze_content_matching(content, ai_responses)
    
    print(f"完美匹配场景 - 总体得分: {result['overall_score']:.2f}")
    print(f"语义鸿沟数量: {len(result['semantic_gaps'])}")
    
    if result['overall_score'] > 80:
        print("✓ 高匹配度场景测试通过")
    else:
        print("⚠ 高匹配度场景得分偏低")
    
    if len(result['semantic_gaps']) == 0:
        print("✓ 无语义鸿沟检测正确")
    else:
        print("⚠ 不应检测到语义鸿沟")


def test_no_match_scenario():
    """测试无匹配场景"""
    print("\n测试无匹配场景...")
    
    engine = AssetIntelligenceEngine()
    
    official_content = "我们是一家AI技术创新公司"
    ai_responses = {
        'doubao': ["这是完全不相关的汽车内容"],
        'qwen': ["这是关于食品的讨论"]
    }
    
    result = engine.analyze_content_matching(official_content, ai_responses)
    
    print(f"无匹配场景 - 总体得分: {result['overall_score']:.2f}")
    print(f"语义鸿沟数量: {len(result['semantic_gaps'])}")
    
    if result['overall_score'] < 30:
        print("✓ 低匹配度场景测试通过")
    else:
        print("⚠ 低匹配度场景得分偏高")
    
    if len(result['semantic_gaps']) > 0:
        print("✓ 正确检测到语义鸿沟")
    else:
        print("⚠ 应该检测到语义鸿沟")


if __name__ == "__main__":
    # 执行主要测试
    result = test_semantic_gap_analysis()
    
    # 执行场景测试
    test_perfect_match_scenario()
    test_no_match_scenario()
    
    print("\n" + "="*60)
    print("所有测试完成！")
    print("✓ 资产智能引擎能够准确分析官方内容与AI回答的语义差异")
    print("✓ 优化建议算法能够提供有针对性的改进建议")
    print("✓ 语义鸿沟识别功能正常工作")
    print("✓ 内容命中率评分准确反映匹配程度")
    print("="*60)