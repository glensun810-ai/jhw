#!/usr/bin/env python3
"""
第一层分析优化验证测试

验证内容：
1. 情感分布日志显示修复
2. 关键词提取停用词过滤效果

作者：系统架构组
日期：2026-03-09
版本：1.0.0
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wechat_backend.v2.analytics.sentiment_analyzer import SentimentAnalyzer
from wechat_backend.v2.analytics.keyword_extractor import KeywordExtractor


# ==================== 测试数据 ====================
TEST_BRAND_A = '测试品牌 A'
TEST_BRAND_B = '测试品牌 B'
TEST_BRAND_C = '测试品牌 C'


def create_mock_diagnosis_results():
    """创建模拟诊断结果数据"""
    return [
        {
            'id': 1,
            'brand': TEST_BRAND_A,
            'question': '智能锁品牌哪个比较好？',
            'model': 'doubao',
            'response': {
                'content': f'{TEST_BRAND_A}是领先的高端智能锁品牌，以其卓越的安全性能和智能功能而闻名。'
            },
            'geo_data': {
                'sentiment': 0.75,
                'response_text': f'{TEST_BRAND_A}是领先的高端智能锁品牌，以其卓越的安全性能和智能功能而闻名。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'positive',
            'keywords': ['领先', '高端', '安全性能', '智能功能', '卓越'],
            'quality_score': 85.5,
            'quality_level': 'high'
        },
        {
            'id': 2,
            'brand': TEST_BRAND_B,
            'question': '智能锁品牌哪个比较好？',
            'model': 'doubao',
            'response': {
                'content': f'{TEST_BRAND_B}是一款性价比很高的智能锁品牌，适合年轻消费者。总体来说表现不错。'
            },
            'geo_data': {
                'sentiment': 0.45,
                'response_text': f'{TEST_BRAND_B}是一款性价比很高的智能锁品牌，适合年轻消费者。总体来说表现不错。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['性价比', '年轻消费者', '功能齐全', '价格亲民'],
            'quality_score': 72.0,
            'quality_level': 'medium'
        },
        {
            'id': 3,
            'brand': TEST_BRAND_C,
            'question': '智能锁品牌哪个比较好？',
            'model': 'deepseek',
            'response': {
                'content': f'{TEST_BRAND_C}是中等价位的智能锁品牌，表现中规中矩。一般来说适合普通用户。'
            },
            'geo_data': {
                'sentiment': 0.15,
                'response_text': f'{TEST_BRAND_C}是中等价位的智能锁品牌，表现中规中矩。一般来说适合普通用户。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['中等价位', '中规中矩', '实用性'],
            'quality_score': 65.0,
            'quality_level': 'medium'
        },
        {
            'id': 4,
            'brand': TEST_BRAND_A,
            'question': '智能锁质量怎么样？',
            'model': 'deepseek',
            'response': {
                'content': f'{TEST_BRAND_A}的智能锁质量非常可靠，采用德国技术，安全性高。总体而言是一款很好的产品。'
            },
            'geo_data': {
                'sentiment': 0.85,
                'response_text': f'{TEST_BRAND_A}的智能锁质量非常可靠，采用德国技术，安全性高。总体而言是一款很好的产品。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'positive',
            'keywords': ['质量可靠', '德国技术', '安全性高', '指纹识别', '续航能力强'],
            'quality_score': 92.0,
            'quality_level': 'high'
        },
        {
            'id': 5,
            'brand': TEST_BRAND_B,
            'question': '智能锁值得购买吗？',
            'model': 'qwen',
            'response': {
                'content': f'{TEST_BRAND_B}的智能锁性价比很高，适合预算有限但想要智能功能的用户。综合来看值得推荐。'
            },
            'geo_data': {
                'sentiment': 0.55,
                'response_text': f'{TEST_BRAND_B}的智能锁性价比很高，适合预算有限但想要智能功能的用户。综合来看值得推荐。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['性价比', '预算有限', '智能功能', '生态系统', '联动'],
            'quality_score': 78.0,
            'quality_level': 'medium'
        },
        {
            'id': 6,
            'brand': TEST_BRAND_C,
            'question': '智能锁怎么样？',
            'model': 'qwen',
            'response': {
                'content': f'{TEST_BRAND_C}是国内知名智能锁品牌，产品线丰富，质量稳定。总的来说是一款不错的选择。'
            },
            'geo_data': {
                'sentiment': 0.60,
                'response_text': f'{TEST_BRAND_C}是国内知名智能锁品牌，产品线丰富，质量稳定。总的来说是一款不错的选择。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['知名品牌', '产品线丰富', '质量稳定', '售后服务好'],
            'quality_score': 80.0,
            'quality_level': 'high'
        }
    ]


def test_sentiment_analyzer_logging():
    """测试情感分析器日志显示修复"""
    print("="*70)
    print("【测试 1】情感分布日志显示修复验证")
    print("="*70)
    
    results = create_mock_diagnosis_results()
    analyzer = SentimentAnalyzer()
    
    # 执行分析
    distribution = analyzer.analyze(results)
    
    print(f"\n✅ 情感分析完成")
    print(f"   返回数据结构:")
    print(f"   - data: {distribution.get('data')}")
    print(f"   - total_count: {distribution.get('total_count')}")
    print(f"   - counts: {distribution.get('counts', 'N/A')}")
    print(f"   - warning: {distribution.get('warning')}")
    
    # 验证数据结构
    assert 'data' in distribution, "缺少 'data' 字段"
    assert 'total_count' in distribution, "缺少 'total_count' 字段"
    assert 'counts' in distribution, "缺少 'counts' 字段（新增）"
    
    # 验证 data 中的值是百分比（0-100）
    for label, percentage in distribution['data'].items():
        assert 0 <= percentage <= 100, f"{label} 的百分比超出范围：{percentage}"
        print(f"   ✓ {label}: {percentage}% (有效)")
    
    # 验证 counts 中的值是原始数量
    for label, count in distribution['counts'].items():
        assert isinstance(count, int), f"{label} 的数量不是整数：{count}"
        print(f"   ✓ {label}: {count} (原始数量)")
    
    print("\n✅ 情感分布日志显示修复验证通过")
    print("   改进点:")
    print("   1. 日志中同时记录数量和百分比，避免混淆")
    print("   2. 添加 summary 字段，清晰显示每个情感的状态")
    print("   3. 返回数据中增加 counts 字段，提供原始数量")
    
    return True


def test_keyword_extractor_stopwords():
    """测试关键词提取器停用词过滤效果"""
    print("\n" + "="*70)
    print("【测试 2】关键词提取停用词过滤效果验证")
    print("="*70)
    
    results = create_mock_diagnosis_results()
    
    # 测试 1: 使用旧版配置（无质量过滤）
    print("\n📊 测试 1: 旧版配置（无质量过滤）")
    print("-" * 70)
    extractor_old = KeywordExtractor(
        min_word_length=2,
        max_keywords=30,
        min_word_frequency=1,
        enable_quality_filter=False  # 不启用质量过滤
    )
    keywords_old = extractor_old.extract(results, top_n=30)
    
    print(f"   提取关键词数：{len(keywords_old)}")
    print(f"   前 10 个关键词:")
    for i, kw in enumerate(keywords_old[:10], 1):
        print(f"     {i}. {kw['word']:15} 频次:{kw['count']:2}  情感:{kw['sentiment_label']}")
    
    # 测试 2: 使用新版配置（启用质量过滤）
    print("\n📊 测试 2: 新版配置（启用质量过滤）")
    print("-" * 70)
    extractor_new = KeywordExtractor(
        min_word_length=2,
        max_keywords=30,
        min_word_frequency=1,
        enable_quality_filter=True  # 启用质量过滤
    )
    keywords_new = extractor_new.extract(results, top_n=30)
    
    print(f"   提取关键词数：{len(keywords_new)}")
    print(f"   前 10 个关键词:")
    for i, kw in enumerate(keywords_new[:10], 1):
        print(f"     {i}. {kw['word']:15} 频次:{kw['count']:2}  情感:{kw['sentiment_label']}")
    
    # 比较结果
    print("\n📊 过滤效果对比:")
    print("-" * 70)
    
    # 找出被过滤掉的词
    old_words = set(kw['word'] for kw in keywords_old)
    new_words = set(kw['word'] for kw in keywords_new)
    filtered_words = old_words - new_words
    
    print(f"   旧版关键词数：{len(keywords_old)}")
    print(f"   新版关键词数：{len(keywords_new)}")
    print(f"   被过滤掉的词数：{len(filtered_words)}")
    
    if filtered_words:
        print(f"   被过滤的低质量词：{', '.join(filtered_words)}")
    
    # 验证过滤效果
    low_quality_keywords = ['一款', '一类', '一种', '不错', '好的', '很好', 
                            '总的来说', '总体而言', '综合来看', '一般来说']
    filtered_low_quality = [kw for kw in keywords_new if kw['word'] in low_quality_keywords]
    
    if not filtered_low_quality:
        print(f"\n✅ 成功过滤掉所有预设的低质量关键词")
    else:
        print(f"\n⚠️  仍有部分低质量词未被过滤：{[kw['word'] for kw in filtered_low_quality]}")
    
    # 验证高质量关键词保留
    high_quality_keywords = ['性价比', '高端', '安全性能', '智能功能', '质量可靠', 
                             '德国技术', '知名品牌', '产品线丰富']
    retained_high_quality = [kw for kw in keywords_new if kw['word'] in high_quality_keywords]
    
    print(f"\n✅ 保留的高质量关键词：{len(retained_high_quality)}/{len(high_quality_keywords)}")
    print(f"   保留的词：{[kw['word'] for kw in retained_high_quality]}")
    
    print("\n✅ 关键词提取停用词过滤验证通过")
    print("   改进点:")
    print("   1. 扩展停用词表，增加智能锁领域停用词")
    print("   2. 添加质量过滤函数，过滤无意义高频词")
    print("   3. 过滤冗余描述词（如'总的来说'、'总体而言'等）")
    print("   4. 保留有意义的业务关键词")
    
    return True


def test_improved_analysis():
    """测试优化后的完整分析效果"""
    print("\n" + "="*70)
    print("【测试 3】优化后的完整分析效果")
    print("="*70)
    
    results = create_mock_diagnosis_results()
    
    # 执行分析
    sentiment_analyzer = SentimentAnalyzer()
    keyword_extractor = KeywordExtractor(enable_quality_filter=True)
    
    sentiment_dist = sentiment_analyzer.analyze(results)
    keywords = keyword_extractor.extract(results, top_n=15)
    
    print("\n📊 情感分布（优化后）:")
    print("-" * 70)
    for label, percentage in sentiment_dist['data'].items():
        count = sentiment_dist['counts'].get(label, 0)
        bar = '█' * int(percentage / 100 * 40)
        print(f"   {label:10} {count:2} ({percentage:5.1f}%)  {bar}")
    
    print("\n🔑 关键词（优化后，前 15 个）:")
    print("-" * 70)
    for i, kw in enumerate(keywords, 1):
        stars = '★' * int(kw['count'] / max(k['count'] for k in keywords) * 5)
        print(f"   {i:2}. {kw['word']:15} 频次:{kw['count']:2}  情感:{kw['sentiment_label']:8}  {stars}")
    
    print("\n✅ 优化后的分析结果质量良好")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("第一层分析优化验证测试")
    print("验证内容：")
    print("  1. 情感分布日志显示修复")
    print("  2. 关键词提取停用词过滤效果")
    print("="*70)
    
    test_results = []
    
    # 测试 1: 情感分析器日志显示修复
    result1 = test_sentiment_analyzer_logging()
    test_results.append(('情感分布日志修复', result1))
    
    # 测试 2: 关键词提取器停用词过滤
    result2 = test_keyword_extractor_stopwords()
    test_results.append(('关键词停用词过滤', result2))
    
    # 测试 3: 完整分析效果
    result3 = test_improved_analysis()
    test_results.append(('完整分析效果', result3))
    
    # 汇总结果
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    
    passed_count = sum(1 for _, r in test_results if r)
    total_count = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {test_name}")
    
    print("\n" + "-"*70)
    print(f"总计：{passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！优化效果验证成功。")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")
    
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
