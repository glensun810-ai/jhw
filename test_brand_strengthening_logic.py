"""
专门测试当没有负面信息时，系统自动提供品牌心智强化建议的逻辑
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.recommendation_generator import RecommendationGenerator, RecommendationType


def test_brand_strengthening_when_no_negative():
    """测试当没有负面信息时，系统提供品牌强化建议"""
    
    print("=== 专项测试：无负面信息时的品牌强化建议 ===")
    
    # 创建无负面内容的测试数据
    sample_source_intelligence = {
        "source_pool": [
            {
                "id": "zhihu",
                "url": "https://www.zhihu.com",
                "site_name": "知乎",
                "citation_count": 15,  # 高引用频次
                "domain_authority": "High"
            },
            {
                "id": "baidu_baike",
                "url": "https://baike.baidu.com",
                "site_name": "百度百科",
                "citation_count": 12,
                "domain_authority": "High"
            }
        ],
        "citation_rank": ["zhihu", "baidu_baike"]
    }
    
    # 关键：空的证据链，表示没有负面信息
    sample_evidence_chain = []
    
    brand_name = "德施曼"
    
    # 创建推荐生成器实例
    generator = RecommendationGenerator()
    
    # 生成推荐
    recommendations = generator.generate_recommendations(
        source_intelligence=sample_source_intelligence,
        evidence_chain=sample_evidence_chain,
        brand_name=brand_name
    )
    
    print(f"生成了 {len(recommendations)} 条建议")
    
    # 分析建议类型
    correction_count = 0
    strengthening_count = 0
    source_attack_count = 0
    other_count = 0
    
    for rec in recommendations:
        print(f"- 类型: {rec.type.value}, 标题: {rec.title}")
        if rec.type == RecommendationType.CONTENT_CORRECTION:
            correction_count += 1
        elif rec.type == RecommendationType.BRAND_STRENGTHENING:
            strengthening_count += 1
        elif rec.type == RecommendationType.SOURCE_ATTACK:
            source_attack_count += 1
        else:
            other_count += 1
    
    print(f"\n建议类型统计:")
    print(f"- 内容纠偏建议: {correction_count}")
    print(f"- 品牌强化建议: {strengthening_count}")
    print(f"- 信源攻坚建议: {source_attack_count}")
    print(f"- 其他建议: {other_count}")
    
    # 验证逻辑
    success = True
    
    if correction_count > 0:
        print("\n✗ 错误：在没有负面信息的情况下生成了内容纠偏建议")
        success = False
    else:
        print("\n✓ 正确：在没有负面信息的情况下没有生成内容纠偏建议")
    
    if strengthening_count > 0:
        print("✓ 正确：在没有负面信息的情况下生成了品牌强化建议")
    else:
        print("✗ 错误：在没有负面信息的情况下没有生成品牌强化建议")
        success = False
    
    if success:
        print("\n✓ 专项测试通过：系统正确地在没有负面信息时提供了品牌强化建议")
    else:
        print("\n✗ 专项测试失败")
    
    return success


def test_correction_when_negative_exists():
    """测试当存在负面信息时，系统提供纠偏建议"""
    
    print("\n=== 对比测试：存在负面信息时的纠偏建议 ===")
    
    # 创建有负面内容的测试数据
    sample_source_intelligence = {
        "source_pool": [
            {
                "id": "zhihu",
                "url": "https://www.zhihu.com",
                "site_name": "知乎",
                "citation_count": 15,
                "domain_authority": "High"
            }
        ],
        "citation_rank": ["zhihu"]
    }
    
    # 包含负面信息的证据链
    sample_evidence_chain = [
        {
            "negative_fragment": "德施曼智能锁质量不过关",
            "associated_url": "https://www.zhihu.com/question/123456",
            "source_name": "知乎",
            "risk_level": "High"
        }
    ]
    
    brand_name = "德施曼"
    
    # 创建推荐生成器实例
    generator = RecommendationGenerator()
    
    # 生成推荐
    recommendations = generator.generate_recommendations(
        source_intelligence=sample_source_intelligence,
        evidence_chain=sample_evidence_chain,
        brand_name=brand_name
    )
    
    print(f"生成了 {len(recommendations)} 条建议")
    
    # 分析建议类型
    correction_count = 0
    strengthening_count = 0
    
    for rec in recommendations:
        print(f"- 类型: {rec.type.value}, 标题: {rec.title}")
        if rec.type == RecommendationType.CONTENT_CORRECTION:
            correction_count += 1
        elif rec.type == RecommendationType.BRAND_STRENGTHENING:
            strengthening_count += 1
    
    print(f"\n建议类型统计:")
    print(f"- 内容纠偏建议: {correction_count}")
    print(f"- 品牌强化建议: {strengthening_count}")
    
    # 验证逻辑
    success = True
    
    if correction_count > 0:
        print("\n✓ 正确：在存在负面信息的情况下生成了内容纠偏建议")
    else:
        print("\n✗ 错误：在存在负面信息的情况下没有生成内容纠偏建议")
        success = False
    
    if success:
        print("✓ 对比测试通过：系统正确地在有负面信息时提供了纠偏建议")
    else:
        print("✗ 对比测试失败")
    
    return success


def test_mixed_scenarios():
    """测试混合场景：既有高引用站点又有负面信息"""
    
    print("\n=== 混合场景测试：同时有高引用站点和负面信息 ===")
    
    sample_source_intelligence = {
        "source_pool": [
            {
                "id": "zhihu",
                "url": "https://www.zhihu.com",
                "site_name": "知乎",
                "citation_count": 15,
                "domain_authority": "High"
            },
            {
                "id": "baidu_baike",
                "url": "https://baike.baidu.com",
                "site_name": "百度百科",
                "citation_count": 12,
                "domain_authority": "High"
            }
        ],
        "citation_rank": ["zhihu", "baidu_baike"]
    }
    
    # 同时有负面信息
    sample_evidence_chain = [
        {
            "negative_fragment": "德施曼智能锁质量有问题",
            "associated_url": "https://www.zhihu.com/question/123456",
            "source_name": "知乎",
            "risk_level": "High"
        }
    ]
    
    brand_name = "德施曼"
    
    generator = RecommendationGenerator()
    
    recommendations = generator.generate_recommendations(
        source_intelligence=sample_source_intelligence,
        evidence_chain=sample_evidence_chain,
        brand_name=brand_name
    )
    
    print(f"生成了 {len(recommendations)} 条建议")
    
    correction_count = 0
    strengthening_count = 0
    source_attack_count = 0
    
    for rec in recommendations:
        print(f"- 类型: {rec.type.value}, 标题: {rec.title}, 优先级: {rec.priority.value}")
        if rec.type == RecommendationType.CONTENT_CORRECTION:
            correction_count += 1
        elif rec.type == RecommendationType.BRAND_STRENGTHENING:
            strengthening_count += 1
        elif rec.type == RecommendationType.SOURCE_ATTACK:
            source_attack_count += 1
    
    print(f"\n建议类型统计:")
    print(f"- 内容纠偏建议: {correction_count}")
    print(f"- 品牌强化建议: {strengthening_count}")
    print(f"- 信源攻坚建议: {source_attack_count}")
    
    # 在有负面信息的情况下，主要应该是纠偏和信源攻坚建议
    if correction_count > 0 or source_attack_count > 0:
        print("✓ 混合场景下正确生成了纠偏和信源攻坚建议")
        return True
    else:
        print("✗ 混合场景下未正确生成相应建议")
        return False


def run_comprehensive_verification():
    """运行综合验证"""
    
    print("开始运行综合验证测试...\n")
    
    test1_success = test_brand_strengthening_when_no_negative()
    test2_success = test_correction_when_negative_exists()
    test3_success = test_mixed_scenarios()
    
    print(f"\n=== 综合验证结果 ===")
    print(f"无负面信息测试: {'通过' if test1_success else '失败'}")
    print(f"有负面信息测试: {'通过' if test2_success else '失败'}")
    print(f"混合场景测试: {'通过' if test3_success else '失败'}")
    
    all_passed = test1_success and test2_success and test3_success
    
    if all_passed:
        print("\n✓ 所有验证测试通过！")
        print("系统能够正确区分不同场景并提供相应的建议类型：")
        print("- 无负面信息时：提供品牌强化建议")
        print("- 有负面信息时：提供纠偏和信源攻坚建议")
        print("- 混合场景时：提供多种类型的建议")
    else:
        print("\n✗ 部分验证测试失败")
    
    return all_passed


if __name__ == "__main__":
    run_comprehensive_verification()