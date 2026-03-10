"""
第一层分析输出验证测试

目的：
1. 验证结果验证阶段（阶段 4）完成后，数据库中的结果数据是否完整可用
2. 验证第一层分析（品牌分布、情感分布、关键词提取）是否能正常执行并输出结果
3. 识别可能的阻塞点和数据流转问题

测试场景：
- 模拟诊断结果数据
- 执行结果验证
- 执行第一层分析
- 验证分析结果输出

作者：系统架构组
日期：2026-03-09
版本：1.0.0
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wechat_backend.v2.analytics.brand_distribution_analyzer import BrandDistributionAnalyzer
from wechat_backend.v2.analytics.sentiment_analyzer import SentimentAnalyzer
from wechat_backend.v2.analytics.keyword_extractor import KeywordExtractor
from wechat_backend.logging_config import api_logger


# ==================== 测试数据常量 ====================
TEST_BRAND_A = '测试品牌 A'
TEST_BRAND_B = '测试品牌 B'
TEST_BRAND_C = '测试品牌 C'


def create_mock_diagnosis_results():
    """
    创建模拟诊断结果数据
    
    模拟阶段 3（结果保存）完成后的数据库中的数据
    
    返回:
        List[Dict]: 模拟的诊断结果列表
    """
    return [
        {
            'id': 1,
            'report_id': 1,
            'execution_id': 'test-exec-001',
            'brand': TEST_BRAND_A,
            'question': '智能锁品牌哪个比较好？',
            'model': 'doubao',
            'response': {
                'content': f'{TEST_BRAND_A}是领先的高端智能锁品牌，以其卓越的安全性能和智能功能而闻名。{TEST_BRAND_B}和{TEST_BRAND_C}也是不错的选择，性价比更高。',
                'usage': {'total_tokens': 150}
            },
            'geo_data': {
                'sentiment': 0.75,
                'response_text': f'{TEST_BRAND_A}是领先的高端智能锁品牌，以其卓越的安全性能和智能功能而闻名。',
                'exposure': True,
                'sources': [
                    {'url': 'https://example.com/review1', 'site_name': '知乎'}
                ]
            },
            'exposure': True,
            'sentiment': 'positive',
            'keywords': ['领先', '高端', '安全性能', '智能功能', '卓越'],
            'quality_score': 85.5,
            'quality_level': 'high',
            'latency_ms': 1250
        },
        {
            'id': 2,
            'report_id': 1,
            'execution_id': 'test-exec-001',
            'brand': TEST_BRAND_B,
            'question': '智能锁品牌哪个比较好？',
            'model': 'doubao',
            'response': {
                'content': f'{TEST_BRAND_B}是一款性价比很高的智能锁品牌，适合年轻消费者。虽然知名度不如{TEST_BRAND_A}，但功能齐全，价格更亲民。',
                'usage': {'total_tokens': 120}
            },
            'geo_data': {
                'sentiment': 0.45,
                'response_text': f'{TEST_BRAND_B}是一款性价比很高的智能锁品牌，适合年轻消费者。',
                'exposure': True,
                'sources': [
                    {'url': 'https://example.com/review2', 'site_name': '小红书'}
                ]
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['性价比', '年轻消费者', '功能齐全', '价格亲民'],
            'quality_score': 72.0,
            'quality_level': 'medium',
            'latency_ms': 980
        },
        {
            'id': 3,
            'report_id': 1,
            'execution_id': 'test-exec-001',
            'brand': TEST_BRAND_C,
            'question': '智能锁品牌哪个比较好？',
            'model': 'deepseek',
            'response': {
                'content': f'{TEST_BRAND_C}是中等价位的智能锁品牌，表现中规中矩。相比{TEST_BRAND_A}的高端定位，{TEST_BRAND_C}更注重实用性。',
                'usage': {'total_tokens': 100}
            },
            'geo_data': {
                'sentiment': 0.15,
                'response_text': f'{TEST_BRAND_C}是中等价位的智能锁品牌，表现中规中矩。',
                'exposure': True,
                'sources': [
                    {'url': 'https://example.com/review3', 'site_name': '什么值得买'}
                ]
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['中等价位', '中规中矩', '实用性'],
            'quality_score': 65.0,
            'quality_level': 'medium',
            'latency_ms': 1500
        },
        {
            'id': 4,
            'report_id': 1,
            'execution_id': 'test-exec-001',
            'brand': TEST_BRAND_A,
            'question': '德施曼的智能锁质量怎么样？',
            'model': 'deepseek',
            'response': {
                'content': f'{TEST_BRAND_A}的智能锁质量非常可靠，采用德国技术，安全性高。用户普遍反映其指纹识别速度快，续航能力强。',
                'usage': {'total_tokens': 180}
            },
            'geo_data': {
                'sentiment': 0.85,
                'response_text': f'{TEST_BRAND_A}的智能锁质量非常可靠，采用德国技术，安全性高。',
                'exposure': True,
                'sources': [
                    {'url': 'https://example.com/review4', 'site_name': '京东'}
                ]
            },
            'exposure': True,
            'sentiment': 'positive',
            'keywords': ['质量可靠', '德国技术', '安全性高', '指纹识别', '续航能力强'],
            'quality_score': 92.0,
            'quality_level': 'high',
            'latency_ms': 1100
        },
        {
            'id': 5,
            'report_id': 1,
            'execution_id': 'test-exec-001',
            'brand': TEST_BRAND_B,
            'question': '小米的智能锁值得购买吗？',
            'model': 'qwen',
            'response': {
                'content': f'{TEST_BRAND_B}（小米）的智能锁性价比很高，适合预算有限但想要智能功能的用户。生态系统完善，可以与其他小米设备联动。',
                'usage': {'total_tokens': 140}
            },
            'geo_data': {
                'sentiment': 0.55,
                'response_text': f'{TEST_BRAND_B}（小米）的智能锁性价比很高，适合预算有限但想要智能功能的用户。',
                'exposure': True,
                'sources': [
                    {'url': 'https://example.com/review5', 'site_name': '天猫'}
                ]
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['性价比', '预算有限', '智能功能', '生态系统', '联动'],
            'quality_score': 78.0,
            'quality_level': 'medium',
            'latency_ms': 890
        },
        {
            'id': 6,
            'report_id': 1,
            'execution_id': 'test-exec-001',
            'brand': TEST_BRAND_C,
            'question': '凯迪仕的智能锁怎么样？',
            'model': 'qwen',
            'response': {
                'content': f'{TEST_BRAND_C}（凯迪仕）是国内知名智能锁品牌，产品线丰富，从低端到高端都有覆盖。质量稳定，售后服务好。',
                'usage': {'total_tokens': 130}
            },
            'geo_data': {
                'sentiment': 0.60,
                'response_text': f'{TEST_BRAND_C}（凯迪仕）是国内知名智能锁品牌，产品线丰富。',
                'exposure': True,
                'sources': [
                    {'url': 'https://example.com/review6', 'site_name': '苏宁易购'}
                ]
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['知名品牌', '产品线丰富', '质量稳定', '售后服务好'],
            'quality_score': 80.0,
            'quality_level': 'high',
            'latency_ms': 950
        }
    ]


def test_brand_distribution_analysis(results):
    """
    测试品牌分布分析
    
    参数:
        results: 诊断结果列表
    
    返回:
        Dict: 分析结果
    """
    print("\n" + "="*60)
    print("【测试 1】品牌分布分析")
    print("="*60)
    
    try:
        analyzer = BrandDistributionAnalyzer()
        
        # 执行分析
        distribution = analyzer.analyze(results)
        
        # 验证结果
        assert 'data' in distribution, "结果缺少 'data' 字段"
        assert 'total_count' in distribution, "结果缺少 'total_count' 字段"
        assert 'warning' in distribution, "结果缺少 'warning' 字段"
        
        print(f"✅ 品牌分布分析成功")
        print(f"   总结果数：{distribution['total_count']}")
        print(f"   品牌分布:")
        for brand, percentage in distribution['data'].items():
            print(f"     - {brand}: {percentage}%")
        
        # 验证具体数值
        expected_counts = {
            TEST_BRAND_A: 2,
            TEST_BRAND_B: 2,
            TEST_BRAND_C: 2
        }
        
        total = sum(expected_counts.values())
        for brand, expected_count in expected_counts.items():
            expected_percentage = round(expected_count / total * 100, 2)
            actual_percentage = distribution['data'].get(brand, 0)
            assert abs(actual_percentage - expected_percentage) < 0.1, \
                f"{brand} 的占比不正确：期望{expected_percentage}%, 实际{actual_percentage}%"
        
        print(f"✅ 数值验证通过")
        
        return {
            'success': True,
            'data': distribution,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ 品牌分布分析失败：{e}")
        api_logger.error(f"品牌分布分析失败：{e}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': str(e)
        }


def test_sentiment_distribution_analysis(results):
    """
    测试情感分布分析
    
    参数:
        results: 诊断结果列表
    
    返回:
        Dict: 分析结果
    """
    print("\n" + "="*60)
    print("【测试 2】情感分布分析")
    print("="*60)
    
    try:
        analyzer = SentimentAnalyzer()
        
        # 执行分析
        distribution = analyzer.analyze(results)
        
        # 验证结果
        assert 'data' in distribution, "结果缺少 'data' 字段"
        assert 'total_count' in distribution, "结果缺少 'total_count' 字段"
        assert 'warning' in distribution, "结果缺少 'warning' 字段"
        
        print(f"✅ 情感分布分析成功")
        print(f"   总结果数：{distribution['total_count']}")
        print(f"   情感分布:")
        for sentiment, count in distribution['data'].items():
            percentage = round(count / distribution['total_count'] * 100, 2) if distribution['total_count'] > 0 else 0
            print(f"     - {sentiment}: {count} ({percentage}%)")
        
        # 验证情感分类
        positive_count = sum(1 for r in results if r.get('geo_data', {}).get('sentiment', 0) > 0.3)
        negative_count = sum(1 for r in results if r.get('geo_data', {}).get('sentiment', 0) < -0.3)
        neutral_count = len(results) - positive_count - negative_count
        
        print(f"   预期分布：正面={positive_count}, 中性={neutral_count}, 负面={negative_count}")
        
        return {
            'success': True,
            'data': distribution,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ 情感分布分析失败：{e}")
        api_logger.error(f"情感分布分析失败：{e}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': str(e)
        }


def test_keyword_extraction(results):
    """
    测试关键词提取
    
    参数:
        results: 诊断结果列表
    
    返回:
        Dict: 分析结果
    """
    print("\n" + "="*60)
    print("【测试 3】关键词提取")
    print("="*60)
    
    try:
        extractor = KeywordExtractor()
        
        # 执行提取
        keywords = extractor.extract(results)
        
        # 验证结果
        assert isinstance(keywords, list), "关键词应该是列表"
        
        print(f"✅ 关键词提取成功")
        print(f"   提取关键词数：{len(keywords)}")
        
        if keywords:
            print(f"   前 10 个关键词:")
            for i, kw in enumerate(keywords[:10], 1):
                assert 'word' in kw, f"关键词{i} 缺少 'word' 字段"
                assert 'count' in kw, f"关键词{i} 缺少 'count' 字段"
                assert 'sentiment' in kw, f"关键词{i} 缺少 'sentiment' 字段"
                print(f"     {i}. {kw.get('word')} (频次={kw.get('count')}, 情感={kw.get('sentiment')})")
        
        return {
            'success': True,
            'data': keywords,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ 关键词提取失败：{e}")
        api_logger.error(f"关键词提取失败：{e}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': str(e)
        }


def test_competitor_analysis(results):
    """
    测试竞品对比分析（依赖品牌分布）
    
    参数:
        results: 诊断结果列表
    
    返回:
        Dict: 分析结果
    """
    print("\n" + "="*60)
    print("【测试 4】竞品对比分析（依赖品牌分布）")
    print("="*60)
    
    try:
        analyzer = BrandDistributionAnalyzer()
        
        # 执行竞品分析
        competitor_analysis = analyzer.analyze_competitors(results, TEST_BRAND_A)
        
        # 验证结果
        assert 'main_brand' in competitor_analysis, "结果缺少 'main_brand' 字段"
        assert 'main_brand_share' in competitor_analysis, "结果缺少 'main_brand_share' 字段"
        assert 'competitor_shares' in competitor_analysis, "结果缺少 'competitor_shares' 字段"
        assert 'rank' in competitor_analysis, "结果缺少 'rank' 字段"
        
        print(f"✅ 竞品对比分析成功")
        print(f"   主品牌：{competitor_analysis['main_brand']}")
        print(f"   主品牌占比：{competitor_analysis['main_brand_share']}%")
        print(f"   主品牌排名：#{competitor_analysis['rank']}")
        print(f"   竞品数量：{competitor_analysis['total_competitors']}")
        
        if competitor_analysis['competitor_shares']:
            print(f"   竞品分布:")
            for brand, share in competitor_analysis['competitor_shares'].items():
                print(f"     - {brand}: {share}%")
        
        return {
            'success': True,
            'data': competitor_analysis,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ 竞品对比分析失败：{e}")
        api_logger.error(f"竞品对比分析失败：{e}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': str(e)
        }


def run_all_tests():
    """
    运行所有测试
    
    返回:
        Dict: 测试结果汇总
    """
    print("\n" + "="*60)
    print("第一层分析输出验证测试")
    print("目的：验证结果验证阶段完成后，第一层分析是否能顺利输出")
    print("="*60)
    
    # 1. 创建模拟数据
    print("\n【步骤 0】创建模拟诊断结果数据...")
    mock_results = create_mock_diagnosis_results()
    print(f"✅ 创建成功，共 {len(mock_results)} 条结果")
    
    # 2. 执行各项分析测试
    test_results = []
    
    # 测试 1: 品牌分布分析（独立）
    result1 = test_brand_distribution_analysis(mock_results)
    test_results.append(('品牌分布分析', result1))
    
    # 测试 2: 情感分布分析（独立）
    result2 = test_sentiment_distribution_analysis(mock_results)
    test_results.append(('情感分布分析', result2))
    
    # 测试 3: 关键词提取（独立）
    result3 = test_keyword_extraction(mock_results)
    test_results.append(('关键词提取', result3))
    
    # 测试 4: 竞品对比分析（依赖品牌分布）
    result4 = test_competitor_analysis(mock_results)
    test_results.append(('竞品对比分析', result4))
    
    # 3. 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed_count = sum(1 for _, r in test_results if r['success'])
    total_count = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result['success'] else "❌ 失败"
        print(f"  {status} - {test_name}")
        if not result['success']:
            print(f"       错误：{result['error']}")
    
    print("\n" + "-"*60)
    print(f"总计：{passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！第一层分析可以顺利输出结果。")
        print("\n结论:")
        print("  1. 品牌分布分析 ✓ 可独立执行并输出结果")
        print("  2. 情感分布分析 ✓ 可独立执行并输出结果")
        print("  3. 关键词提取 ✓ 可独立执行并输出结果")
        print("  4. 竞品对比分析 ✓ 可在品牌分布基础上执行并输出结果")
        print("\n  第一层分析（独立分析模块）可以并行执行，互不依赖。")
        print("  第二层分析（竞品对比）依赖第一层的品牌分布结果。")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息。")
    
    return {
        'total': total_count,
        'passed': passed_count,
        'failed': total_count - passed_count,
        'results': test_results
    }


if __name__ == '__main__':
    result = run_all_tests()
    
    # 退出码
    sys.exit(0 if result['passed'] == result['total'] else 1)
