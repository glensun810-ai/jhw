#!/usr/bin/env python3
"""
P0-3 竞品自动提取功能验证测试

验证内容:
1. TOP3 品牌从 AI 客观回答中自动提取
2. 用户未指定竞品时，自动使用提取的 TOP3 作为竞品
3. 品牌提及分析正确执行
4. 竞品对比报告生成

测试场景:
- 场景 1: 用户未指定竞品 → 系统自动从 AI 回答中提取 TOP3
- 场景 2: 用户指定竞品 → 使用用户指定的竞品 + 自动提取的 TOP3
- 场景 3: AI 回答无 JSON 格式 → 使用语义分析降级提取
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.services.brand_analysis_service import BrandAnalysisService, get_brand_analysis_service


def test_top3_extraction_from_json():
    """测试 1: 从 JSON 格式回答中提取 TOP3 品牌"""
    print("=" * 60)
    print("测试 1: 从 JSON 格式回答中提取 TOP3 品牌")
    print("=" * 60)

    # 模拟 AI 客观回答（包含 JSON 格式 top3_brands）
    ai_response = '''
根据我的了解，深圳地区有以下优秀的新能源汽车改装门店：

TOP1: 深圳车尚艺改装店
理由：专业技术团队，丰富经验，使用高品质配件。

TOP2: 深圳承美车居
理由：服务好，价格透明，客户口碑佳。

TOP3: 深圳趣车良品
理由：创新技术，设备先进，改装效果出色。

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1, "reason": "专业技术团队"}, {"name": "深圳承美车居", "rank": 2, "reason": "服务好"}, {"name": "深圳趣车良品", "rank": 3, "reason": "创新技术"}], "total_brands_mentioned": 3}
'''

    service = BrandAnalysisService()
    top3 = service._extract_top3_brands(ai_response)

    assert len(top3) == 3, f"应提取到 3 个品牌，实际提取到 {len(top3)} 个"
    assert top3[0]['name'] == '深圳车尚艺改装店', f"第一名应为深圳车尚艺改装店"
    assert top3[1]['name'] == '深圳承美车居', f"第二名应为深圳承美车居"
    assert top3[2]['name'] == '深圳趣车良品', f"第三名应为深圳趣车良品"

    print("✓ JSON 格式 TOP3 提取成功")
    print(f"  提取到的品牌：{[b['name'] for b in top3]}")
    print()
    return True


def test_top3_extraction_fallback():
    """测试 2: 无 JSON 时使用语义分析降级提取"""
    print("=" * 60)
    print("测试 2: 无 JSON 时使用语义分析降级提取")
    print("=" * 60)

    # 模拟 AI 客观回答（无 JSON 格式，纯文本）
    ai_response = '''
作为专业顾问，我推荐以下新能源汽车改装门店：

第一推荐：深圳车尚艺改装店
理由：专业技术团队，丰富经验。

第二推荐：深圳承美车居
理由：服务好，价格透明。

第三推荐：深圳趣车良品
理由：创新技术，设备先进。

综合来看，这三家都是不错的选择。
'''

    service = BrandAnalysisService()
    top3 = service._extract_top3_brands(ai_response)

    # 降级方案应能提取到品牌名
    assert len(top3) >= 2, f"降级方案应至少提取到 2 个品牌，实际提取到 {len(top3)} 个"

    print("✓ 语义分析降级提取成功")
    print(f"  提取到的品牌：{[b['name'] for b in top3]}")
    print()
    return True


def test_auto_competitor_selection():
    """测试 3: 用户未指定竞品时自动选择 TOP3"""
    print("=" * 60)
    print("测试 3: 用户未指定竞品时自动选择 TOP3")
    print("=" * 60)

    # 模拟多个 AI 回答
    results = [
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'doubao',
            'response': '''
根据我的了解，深圳地区有以下优秀的新能源汽车改装门店：

TOP1: 深圳车尚艺改装店
TOP2: 深圳承美车居
TOP3: 深圳趣车良品

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1}, {"name": "深圳承美车居", "rank": 2}, {"name": "深圳趣车良品", "rank": 3}]}
'''
        },
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'qwen',
            'response': '''
深圳地区优秀的新能源汽车改装门店推荐：

1. 深圳车尚艺改装店 - 专业可靠
2. 深圳趣车良品 - 技术先进
3. 深圳车网联盟 - 服务周到

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1}, {"name": "深圳趣车良品", "rank": 2}, {"name": "深圳车网联盟", "rank": 3}]}
'''
        }
    ]

    service = BrandAnalysisService()

    # 用户未指定竞品（competitor_brands=None）
    analysis = service.analyze_brand_mentions(
        results=results,
        user_brand='趣车良品',
        competitor_brands=None  # 关键：未指定竞品
    )

    # 验证自动提取的 TOP3 品牌
    assert len(analysis['top3_brands']) > 0, "应自动提取到 TOP3 品牌"
    print(f"✓ 自动提取的 TOP3 品牌：{[b['name'] for b in analysis['top3_brands']]}")

    # 验证竞品分析中包含自动提取的品牌
    assert len(analysis['competitor_analysis']) > 0, "应有竞品分析"
    print(f"✓ 竞品分析数量：{len(analysis['competitor_analysis'])}")

    # 验证对比分析已生成
    assert 'comparison' in analysis, "应有对比分析"
    assert 'summary' in analysis['comparison'], "应有总结"

    print(f"✓ 对比分析总结：{analysis['comparison']['summary'][:50]}...")
    print()
    return True


def test_user_brand_analysis():
    """测试 4: 用户品牌提及分析"""
    print("=" * 60)
    print("测试 4: 用户品牌提及分析")
    print("=" * 60)

    results = [
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'doubao',
            'response': '''
推荐以下门店：
1. 深圳车尚艺改装店
2. 深圳趣车良品 - 技术先进，服务好
3. 深圳承美车居

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1}, {"name": "深圳趣车良品", "rank": 2}, {"name": "深圳承美车居", "rank": 3}]}
'''
        }
    ]

    service = BrandAnalysisService(judge_model='doubao')

    # 使用降级方案（不调用 AI，避免 API 限流）
    analysis = service.analyze_brand_mentions(
        results=results,
        user_brand='趣车良品',
        competitor_brands=['深圳车尚艺改装店', '深圳承美车居']
    )

    # 验证用户品牌分析
    user_analysis = analysis['user_brand_analysis']
    assert user_analysis['brand'] == '趣车良品', "用户品牌应正确"
    assert user_analysis['mentioned_count'] >= 0, "应有提及次数"
    assert user_analysis['total_responses'] == 1, "总响应数应为 1"

    print(f"✓ 用户品牌分析:")
    print(f"  - 品牌：{user_analysis['brand']}")
    print(f"  - 提及率：{user_analysis['mention_rate']:.1%}")
    print(f"  - 是否 TOP3: {user_analysis['is_top3']}")

    # 验证竞品分析
    assert len(analysis['competitor_analysis']) == 2, "应有 2 个竞品分析"
    print(f"✓ 竞品分析数量：{len(analysis['competitor_analysis'])}")

    print()
    return True


def test_comparison_generation():
    """测试 5: 竞品对比报告生成"""
    print("=" * 60)
    print("测试 5: 竞品对比报告生成")
    print("=" * 60)

    results = [
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'doubao',
            'response': '''
综合评估，推荐以下品牌：

第一名：深圳车尚艺改装店（专业可靠）
第二名：深圳趣车良品（技术先进）
第三名：深圳承美车居（服务好）

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1}, {"name": "深圳趣车良品", "rank": 2}, {"name": "深圳承美车居", "rank": 3}]}
'''
        }
    ]

    service = BrandAnalysisService()

    analysis = service.analyze_brand_mentions(
        results=results,
        user_brand='趣车良品',
        competitor_brands=['深圳车尚艺改装店', '深圳承美车居']
    )

    # 验证对比报告
    comparison = analysis['comparison']
    assert 'user_brand' in comparison, "对比报告应包含用户品牌"
    assert 'vs_competitors' in comparison, "对比报告应包含竞品对比"
    assert 'summary' in comparison, "对比报告应包含总结"

    print(f"✓ 对比报告生成成功")
    print(f"  - 用户品牌：{comparison['user_brand']}")
    print(f"  - 提及率：{comparison['mention_rate']:.1%}")
    print(f"  - 平均排名：{comparison['average_rank']}")
    print(f"  - 是否 TOP3: {comparison['is_top3']}")
    print(f"  - 总结：{comparison['summary'][:50]}...")

    # 验证竞品对比详情
    assert len(comparison['vs_competitors']) == 2, "应有 2 个竞品对比"
    for vs in comparison['vs_competitors']:
        assert 'competitor' in vs, "应包含竞品名"
        assert 'advantage' in vs, "应包含优势/劣势描述"
        print(f"  - vs {vs['competitor']}: {vs['advantage']}")

    print()
    return True


def test_empty_competitor_scenario():
    """测试 6: 用户只输入自己的品牌，无竞品"""
    print("=" * 60)
    print("测试 6: 用户只输入自己的品牌，无竞品（核心场景）")
    print("=" * 60)

    # 模拟用户只输入自己的品牌，未选择任何竞品
    results = [
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'doubao',
            'response': '''
根据我的了解，深圳地区有以下优秀的新能源汽车改装门店：

第一推荐：深圳车尚艺改装店
理由：专业技术团队，丰富经验，使用高品质配件。

第二推荐：深圳承美车居
理由：服务好，价格透明，客户口碑佳。

第三推荐：深圳趣车良品
理由：创新技术，设备先进，改装效果出色，值得推荐！

综合来看，这三家都是不错的选择。
'''
        }
    ]

    service = BrandAnalysisService()

    # 用户只输入自己的品牌，competitor_brands 为空列表
    analysis = service.analyze_brand_mentions(
        results=results,
        user_brand='趣车良品',
        competitor_brands=[]  # 用户未指定任何竞品
    )

    # 验证系统自动从回答中提取了竞品
    assert len(analysis['top3_brands']) > 0, "应自动提取 TOP3 品牌作为竞品"
    print(f"✓ 自动提取的竞品：{[b['name'] for b in analysis['top3_brands']]}")

    # 验证竞品分析已生成
    assert len(analysis['competitor_analysis']) > 0, "应有竞品分析"
    print(f"✓ 竞品分析数量：{len(analysis['competitor_analysis'])}")

    # 验证对比报告已生成
    assert 'comparison' in analysis, "应有对比分析"
    assert 'summary' in analysis['comparison'], "应有总结"
    print(f"✓ 对比总结：{analysis['comparison']['summary'][:80]}...")

    print()
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("P0-3 竞品自动提取功能验证测试")
    print("=" * 60)
    print()

    tests = [
        ("JSON 格式 TOP3 提取", test_top3_extraction_from_json),
        ("语义分析降级提取", test_top3_extraction_fallback),
        ("自动竞品选择", test_auto_competitor_selection),
        ("用户品牌分析", test_user_brand_analysis),
        ("竞品对比报告", test_comparison_generation),
        ("无竞品核心场景", test_empty_competitor_scenario),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"✗ {test_name} 测试失败：{e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name} 异常：{e}\n")
            failed += 1

    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
