#!/usr/bin/env python3
"""
防御性数据重建验证测试

验证点：
1. semanticDrift 字段缺失时能生成有意义的默认值
2. sourcePurity 字段缺失时能生成有意义的默认值
3. recommendations 字段缺失时能根据分数生成建议
4. 所有默认值都能从 results 中提取数据增强

作者：系统架构组
日期：2026-03-17
版本：1.0.0
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python/wechat_backend'))

from wechat_backend.services.report_aggregator import ReportAggregator
from wechat_backend.logging_config import api_logger


def test_semantic_drift_rebuilding():
    """测试语义偏移数据重建"""
    print("\n" + "="*80)
    print("测试 1: semanticDrift 数据重建")
    print("="*80)
    
    aggregator = ReportAggregator()
    
    # 场景 1: 无 results，生成基础默认值
    print("\n  场景 1: 无 results 数据")
    default_drift = aggregator._generate_default_semantic_drift(results=None)
    
    assert 'drift_score' in default_drift, "❌ 应该包含 drift_score"
    assert 'keywords' in default_drift, "❌ 应该包含 keywords"
    assert 'differentiation_gap' in default_drift, "❌ 应该包含 differentiation_gap"
    print(f"    ✅ 基础默认值生成成功：{default_drift['differentiation_gap']}")
    
    # 场景 2: 有 results 但无关键词
    print("\n  场景 2: 有 results 但无关键词")
    mock_results_no_keywords = [
        {'brand': '特斯拉', 'response': '介绍电动汽车'},
        {'brand': '比亚迪', 'response': '新能源汽车'}
    ]
    drift_no_keywords = aggregator._generate_default_semantic_drift(results=mock_results_no_keywords)
    print(f"    ✅ 无关键词时生成默认值：{drift_no_keywords['differentiation_gap']}")
    
    # 场景 3: 有 results 有关键词
    print("\n  场景 3: 有 results 且有关键词")
    mock_results_with_keywords = [
        {
            'brand': '特斯拉',
            'response': '特斯拉在电动汽车市场领先',
            'geo_data': {
                'keywords': [
                    {'word': '电动汽车', 'count': 5},
                    {'word': '自动驾驶', 'count': 3},
                    {'word': '科技创新', 'count': 2},
                    {'word': '高端品牌', 'count': 1}
                ]
            }
        },
        {
            'brand': '比亚迪',
            'response': '比亚迪是新能源汽车领导者',
            'geo_data': {
                'keywords': [
                    {'word': '新能源汽车', 'count': 4},
                    {'word': '电池技术', 'count': 3},
                    {'word': '性价比', 'count': 2}
                ]
            }
        }
    ]
    drift_with_keywords = aggregator._generate_default_semantic_drift(results=mock_results_with_keywords)
    
    print(f"    生成的关键词数据:")
    print(f"      - 总关键词数：{len(drift_with_keywords['keywords'])}")
    print(f"      - 品牌独特关键词：{drift_with_keywords['my_brand_unique_keywords'][:3]}")
    print(f"      - 共同关键词：{drift_with_keywords['common_keywords'][:3]}")
    print(f"      - 认知差异：{drift_with_keywords['differentiation_gap']}")
    
    # 验证
    assert len(drift_with_keywords['keywords']) > 0, "❌ 应该提取到关键词"
    assert len(drift_with_keywords['my_brand_unique_keywords']) > 0, "❌ 应该有品牌独特关键词"
    assert drift_with_keywords['warning'] is None, "❌ 有数据时 warning 应该为 None"
    
    print(f"    ✅ 有数据时生成有意义的默认值")
    return True


def test_source_purity_rebuilding():
    """测试信源纯净度数据重建"""
    print("\n" + "="*80)
    print("测试 2: sourcePurity 数据重建")
    print("="*80)
    
    aggregator = ReportAggregator()
    
    # 场景 1: 无 results，生成基础默认值
    print("\n  场景 1: 无 results 数据")
    default_purity = aggregator._generate_default_source_purity(results=None)
    
    assert 'purity_score' in default_purity, "❌ 应该包含 purity_score"
    assert 'source_types' in default_purity, "❌ 应该包含 source_types"
    assert 'suggestions' in default_purity, "❌ 应该包含 suggestions"
    print(f"    ✅ 基础默认值生成成功：purity_score={default_purity['purity_score']}")
    
    # 场景 2: 有 results 但无信源
    print("\n  场景 2: 有 results 但无信源")
    mock_results_no_sources = [
        {'brand': '特斯拉', 'response': '介绍电动汽车'},
        {'brand': '比亚迪', 'response': '新能源汽车'}
    ]
    purity_no_sources = aggregator._generate_default_source_purity(results=mock_results_no_sources)
    print(f"    ✅ 无信源时生成默认值：purity_score={purity_no_sources['purity_score']}")
    
    # 场景 3: 有 results 有信源
    print("\n  场景 3: 有 results 且有信源")
    mock_results_with_sources = [
        {
            'brand': '特斯拉',
            'response': '特斯拉在电动汽车市场领先',
            'geo_data': {
                'sources': [
                    {'id': 'source1', 'url': 'https://example.com/tesla', 'type': 'media', 'domain_authority': 'high'},
                    {'id': 'source2', 'url': 'https://tesla.com', 'type': 'official', 'domain_authority': 'high'},
                    {'id': 'source3', 'url': 'https://reddit.com/tesla', 'type': 'user_generated', 'domain_authority': 'low'}
                ]
            }
        },
        {
            'brand': '比亚迪',
            'response': '比亚迪是新能源汽车领导者',
            'geo_data': {
                'sources': [
                    {'id': 'source4', 'url': 'https://byd.com', 'type': 'official', 'domain_authority': 'high'},
                    {'id': 'source5', 'url': 'https://example.com/byd', 'type': 'media', 'domain_authority': 'medium'}
                ]
            }
        }
    ]
    purity_with_sources = aggregator._generate_default_source_purity(results=mock_results_with_sources)
    
    print(f"    生成的信源数据:")
    print(f"      - 总信源数：{purity_with_sources['total_sources'] if 'total_sources' in purity_with_sources else len(purity_with_sources['sources'])}")
    print(f"      - 权威信源数：{purity_with_sources['authoritative_sources'] if 'authoritative_sources' in purity_with_sources else 'N/A'}")
    print(f"      - 纯净度分数：{purity_with_sources['purity_score']}")
    print(f"      - 纯净度级别：{purity_with_sources['purity_level']}")
    print(f"      - 信源类型分布：{purity_with_sources['source_types']}")
    
    # 验证
    assert purity_with_sources['purity_score'] >= 0, "❌ purity_score 应该 >= 0"
    assert purity_with_sources['purity_level'] in ['high', 'medium', 'low'], "❌ purity_level 应该有效"
    assert len(purity_with_sources['sources']) > 0, "❌ 应该提取到信源"
    assert purity_with_sources['warning'] is None, "❌ 有数据时 warning 应该为 None"
    
    print(f"    ✅ 有数据时生成有意义的默认值")
    return True


def test_recommendations_rebuilding():
    """测试优化建议数据重建"""
    print("\n" + "="*80)
    print("测试 3: recommendations 数据重建")
    print("="*80)
    
    aggregator = ReportAggregator()
    
    # 场景 1: 低分场景（<60）
    print("\n  场景 1: 低分场景（整体分数 50）")
    low_score_recommendations = aggregator._generate_default_recommendations(
        brand_name='特斯拉',
        brand_scores={'特斯拉': {'overallScore': 50}},
        results=[]
    )
    
    print(f"    生成的建议:")
    for rec in low_score_recommendations:
        print(f"      - [{rec['priority']}] {rec['title']}: {rec['description'][:50]}...")
    
    # 验证低分场景
    high_priority_count = sum(1 for r in low_score_recommendations if r['priority'] == 'high')
    assert high_priority_count >= 1, "❌ 低分场景应该有高优先级建议"
    print(f"    ✅ 低分场景生成{high_priority_count}条高优先级建议")
    
    # 场景 2: 中等分数场景（60-80）
    print("\n  场景 2: 中等分数场景（整体分数 70）")
    medium_score_recommendations = aggregator._generate_default_recommendations(
        brand_name='比亚迪',
        brand_scores={'比亚迪': {'overallScore': 70}},
        results=[]
    )
    
    print(f"    生成的建议:")
    for rec in medium_score_recommendations:
        print(f"      - [{rec['priority']}] {rec['title']}: {rec['description'][:50]}...")
    
    # 验证中等分数场景
    medium_priority_count = sum(1 for r in medium_score_recommendations if r['priority'] == 'medium')
    assert medium_priority_count >= 1, "❌ 中等分数场景应该有中优先级建议"
    print(f"    ✅ 中等分数场景生成{medium_priority_count}条中优先级建议")
    
    # 场景 3: 高分场景（>=80）
    print("\n  场景 3: 高分场景（整体分数 85）")
    high_score_recommendations = aggregator._generate_default_recommendations(
        brand_name='华为',
        brand_scores={'华为': {'overallScore': 85}},
        results=[]
    )
    
    print(f"    生成的建议:")
    for rec in high_score_recommendations:
        print(f"      - [{rec['priority']}] {rec['title']}: {rec['description'][:50]}...")
    
    # 验证高分场景
    low_priority_count = sum(1 for r in high_score_recommendations if r['priority'] == 'low')
    assert low_priority_count >= 1, "❌ 高分场景应该有低优先级建议"
    print(f"    ✅ 高分场景生成{low_priority_count}条低优先级建议")
    
    # 场景 4: 有 results 数据时生成更有针对性的建议
    print("\n  场景 4: 有 results 数据时")
    mock_results = [
        {'brand': '特斯拉', 'response': '介绍电动汽车', 'score': 80}
    ]
    recommendations_with_results = aggregator._generate_default_recommendations(
        brand_name='特斯拉',
        brand_scores={'特斯拉': {'overallScore': 50}},
        results=mock_results
    )
    
    # 验证有 results 时会增加数据量建议
    has_data_sufficiency_rec = any(
        r.get('category') == 'data_sufficiency' 
        for r in recommendations_with_results
    )
    # 注意：只有当 results < 10 时才会生成数据量建议
    if len(mock_results) < 10:
        assert has_data_sufficiency_rec, "❌ results 少时应该有数据量建议"
        print(f"    ✅ 有 results 时生成针对性的数据量建议")
    else:
        print(f"    ✅ 有 results 时生成建议")
    
    return True


def test_end_to_end_report_generation():
    """测试端到端报告生成（包含防御性数据重建）"""
    print("\n" + "="*80)
    print("测试 4: 端到端报告生成（防御性数据重建）")
    print("="*80)
    
    aggregator = ReportAggregator()
    
    # 模拟原始结果（不包含 semantic_drift, source_purity, recommendations）
    mock_results = [
        {
            'brand': '特斯拉',
            'question': '介绍特斯拉',
            'model': 'doubao',
            'score': 85,
            'response': '特斯拉是一家电动汽车公司，在自动驾驶技术方面领先',
            'geo_data': {
                'keywords': [
                    {'word': '电动汽车', 'count': 5},
                    {'word': '自动驾驶', 'count': 3}
                ],
                'sentiment': 0.8,
                'sources': [
                    {'id': 's1', 'url': 'https://example.com', 'type': 'media', 'domain_authority': 'high'}
                ]
            }
        },
        {
            'brand': '特斯拉',
            'question': '特斯拉的特点',
            'model': 'deepseek',
            'score': 78,
            'response': '特斯拉有先进的电池技术和自动驾驶系统',
            'geo_data': {
                'keywords': [
                    {'word': '电池技术', 'count': 4},
                    {'word': '科技创新', 'count': 2}
                ],
                'sentiment': 0.7,
                'sources': [
                    {'id': 's2', 'url': 'https://tesla.com', 'type': 'official', 'domain_authority': 'high'}
                ]
            }
        }
    ]
    
    # 调用 aggregate 方法（不提供 additional_data）
    report = aggregator.aggregate(
        raw_results=mock_results,
        brand_name='特斯拉',
        competitors=['比亚迪', '蔚来'],
        additional_data=None  # 不提供额外数据，测试防御性重建
    )
    
    print("\n  生成的报告数据:")
    
    # 验证 semanticDrift
    print(f"\n  1. semanticDrift:")
    semantic_drift = report.get('semanticDrift')
    assert semantic_drift is not None, "❌ semanticDrift 不应该为 None"
    print(f"     - drift_score: {semantic_drift.get('drift_score')}")
    print(f"     - 关键词数：{len(semantic_drift.get('keywords', []))}")
    print(f"     - 认知差异：{semantic_drift.get('differentiation_gap', 'N/A')[:50]}")
    
    # 验证 sourcePurity
    print(f"\n  2. sourcePurity:")
    source_purity = report.get('sourcePurity')
    assert source_purity is not None, "❌ sourcePurity 不应该为 None"
    print(f"     - purity_score: {source_purity.get('purity_score')}")
    print(f"     - purity_level: {source_purity.get('purity_level')}")
    print(f"     - 信源数：{len(source_purity.get('sources', []))}")
    
    # 验证 recommendations
    print(f"\n  3. recommendations:")
    recommendations = report.get('recommendations')
    assert recommendations is not None, "❌ recommendations 不应该为 None"
    assert len(recommendations) > 0, "❌ recommendations 不应该为空"
    print(f"     - 建议数：{len(recommendations)}")
    for i, rec in enumerate(recommendations[:3]):
        print(f"       {i+1}. [{rec.get('priority')}] {rec.get('title')}")
    
    print("\n  ✅ 端到端报告生成成功，所有缺失字段都已重建")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("防御性数据重建验证测试")
    print("版本：1.0.0 (P0 关键修复)")
    print("="*80)
    
    tests = [
        ("semanticDrift 数据重建", test_semantic_drift_rebuilding),
        ("sourcePurity 数据重建", test_source_purity_rebuilding),
        ("recommendations 数据重建", test_recommendations_rebuilding),
        ("端到端报告生成", test_end_to_end_report_generation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶️  开始测试：{test_name}")
            if test_func():
                passed += 1
                print(f"✅ 测试通过：{test_name}")
            else:
                print(f"❌ 测试失败：{test_name}")
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常：{test_name}")
            print(f"   错误：{str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    print(f"测试总结：")
    print(f"  通过：{passed}/{len(tests)}")
    print(f"  失败：{failed}/{len(tests)}")
    print("="*80)
    
    if failed == 0:
        print("\n✅ 所有测试通过！防御性数据重建验证成功！")
        print("\n关键改进：")
        print("1. ✅ semanticDrift 可从 results 中提取关键词生成默认值")
        print("2. ✅ sourcePurity 可从 results 中提取信源生成默认值")
        print("3. ✅ recommendations 根据分数和 results 生成有意义的建议")
        print("4. ✅ 所有默认值都包含详细的分析和建议，而非空数据")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败，请修复问题")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
