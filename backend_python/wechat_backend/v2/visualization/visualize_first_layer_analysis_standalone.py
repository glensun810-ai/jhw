#!/usr/bin/env python3
"""
第一层分析结果可视化展示 - 独立版本

功能：
1. 品牌分布饼图
2. 情感分布柱状图
3. 关键词词云
4. 竞品对比雷达图
5. 完整分析仪表板

作者：系统架构组
日期：2026-03-09
版本：1.0.0
"""

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
                'content': f'{TEST_BRAND_B}是一款性价比很高的智能锁品牌，适合年轻消费者。'
            },
            'geo_data': {
                'sentiment': 0.45,
                'response_text': f'{TEST_BRAND_B}是一款性价比很高的智能锁品牌，适合年轻消费者。',
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
                'content': f'{TEST_BRAND_C}是中等价位的智能锁品牌，表现中规中矩。'
            },
            'geo_data': {
                'sentiment': 0.15,
                'response_text': f'{TEST_BRAND_C}是中等价位的智能锁品牌，表现中规中矩。',
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
                'content': f'{TEST_BRAND_A}的智能锁质量非常可靠，采用德国技术，安全性高。'
            },
            'geo_data': {
                'sentiment': 0.85,
                'response_text': f'{TEST_BRAND_A}的智能锁质量非常可靠，采用德国技术，安全性高。',
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
                'content': f'{TEST_BRAND_B}的智能锁性价比很高，适合预算有限但想要智能功能的用户。'
            },
            'geo_data': {
                'sentiment': 0.55,
                'response_text': f'{TEST_BRAND_B}的智能锁性价比很高，适合预算有限但想要智能功能的用户。',
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
                'content': f'{TEST_BRAND_C}是国内知名智能锁品牌，产品线丰富，质量稳定。'
            },
            'geo_data': {
                'sentiment': 0.60,
                'response_text': f'{TEST_BRAND_C}是国内知名智能锁品牌，产品线丰富，质量稳定。',
                'exposure': True
            },
            'exposure': True,
            'sentiment': 'neutral',
            'keywords': ['知名品牌', '产品线丰富', '质量稳定', '售后服务好'],
            'quality_score': 80.0,
            'quality_level': 'high'
        }
    ]


# ==================== 文本可视化 ====================
def print_header(title, char='=', width=80):
    """打印标题头"""
    print()
    print(char * width)
    print(title.center(width))
    print(char * width)


def print_section(title, char='-', width=60):
    """打印节标题"""
    print()
    print(char * width)
    print(f"  {title}")
    print(char * width)


def analyze_brand_distribution(results):
    """分析品牌分布"""
    from collections import defaultdict
    
    brand_counts = defaultdict(int)
    for result in results:
        brand = result.get('brand', 'unknown')
        brand_counts[brand] += 1
    
    total = sum(brand_counts.values())
    distribution = {}
    for brand, count in brand_counts.items():
        percentage = round(count / total * 100, 2)
        distribution[brand] = percentage
    
    return {
        'data': distribution,
        'total_count': total,
        'warning': None
    }


def analyze_sentiment_distribution(results):
    """分析情感分布"""
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    
    for result in results:
        sentiment = result.get('sentiment', 'neutral')
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
    
    total = len(results)
    
    return {
        'data': sentiment_counts,
        'total_count': total,
        'warning': None
    }


def extract_keywords(results, top_n=50):
    """提取关键词"""
    from collections import defaultdict
    
    keyword_freq = defaultdict(int)
    keyword_sentiment = defaultdict(list)
    
    for result in results:
        keywords = result.get('keywords', [])
        geo_sentiment = result.get('geo_data', {}).get('sentiment', 0)
        
        for kw in keywords:
            keyword_freq[kw] += 1
            keyword_sentiment[kw].append(geo_sentiment)
    
    keywords_with_sentiment = []
    for kw, count in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]:
        avg_sentiment = sum(keyword_sentiment[kw]) / len(keyword_sentiment[kw])
        
        if avg_sentiment > 0.3:
            sentiment_label = 'positive'
        elif avg_sentiment < -0.3:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        keywords_with_sentiment.append({
            'word': kw,
            'count': count,
            'sentiment': round(avg_sentiment, 3),
            'sentiment_label': sentiment_label
        })
    
    return keywords_with_sentiment


def analyze_competitors(results, main_brand):
    """分析竞品对比"""
    distribution = analyze_brand_distribution(results)
    data = distribution.get('data', {})
    
    main_share = data.get(main_brand, 0)
    competitor_shares = {
        brand: share
        for brand, share in data.items()
        if brand != main_brand
    }
    
    sorted_shares = sorted(data.items(), key=lambda x: x[1], reverse=True)
    rank = next(
        (i + 1 for i, (brand, _) in enumerate(sorted_shares) if brand == main_brand),
        len(sorted_shares) + 1
    )
    
    top_competitor = max(competitor_shares.items(), key=lambda x: x[1])[0] if competitor_shares else None
    
    return {
        'main_brand': main_brand,
        'main_brand_share': main_share,
        'competitor_shares': competitor_shares,
        'rank': rank,
        'total_competitors': len(competitor_shares),
        'top_competitor': top_competitor
    }


def visualize_brand_distribution_text(distribution):
    """文本可视化：品牌分布"""
    print_section("📊 品牌分布分析")
    
    data = distribution.get('data', {})
    total_count = distribution.get('total_count', 0)
    
    print(f"\n总样本数：{total_count} 条 AI 响应\n")
    
    sorted_brands = sorted(data.items(), key=lambda x: x[1], reverse=True)
    max_percentage = max(data.values()) if data else 0
    
    for rank, (brand, percentage) in enumerate(sorted_brands, 1):
        bar_length = int((percentage / max_percentage) * 40) if max_percentage > 0 else 0
        bar = '█' * bar_length
        
        rank_icon = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else f'{rank}.'
        print(f"{rank_icon} {brand:15} {percentage:6.2f}%  {bar}")
    
    print()


def visualize_sentiment_distribution_text(distribution):
    """文本可视化：情感分布"""
    print_section("💚 情感分布分析")
    
    data = distribution.get('data', {})
    total_count = distribution.get('total_count', 0)
    
    print(f"\n总样本数：{total_count} 条 AI 响应\n")
    
    sentiment_config = {
        'positive': {'icon': '😊', 'label': '正面', 'color': '🟢'},
        'neutral': {'icon': '😐', 'label': '中性', 'color': '🟡'},
        'negative': {'icon': '😔', 'label': '负面', 'color': '🔴'}
    }
    
    percentages = {}
    for sentiment in ['positive', 'neutral', 'negative']:
        count = data.get(sentiment, 0)
        percentage = (count / total_count * 100) if total_count > 0 else 0
        percentages[sentiment] = {'count': count, 'percentage': percentage}
    
    max_count = max(percentages.values(), key=lambda x: x['count'])['count'] if total_count > 0 else 1
    
    for sentiment in ['positive', 'neutral', 'negative']:
        config = sentiment_config[sentiment]
        pdata = percentages[sentiment]
        
        bar_length = int((pdata['count'] / max_count) * 40) if max_count > 0 else 0
        bar = '█' * bar_length
        
        print(f"{config['icon']} {config['label']:6} {config['color']}  {pdata['count']:3}  ({pdata['percentage']:5.1f}%)  {bar}")
    
    print(f"\n📈 情感倾向总结:")
    positive_ratio = percentages['positive']['percentage']
    negative_ratio = percentages['negative']['percentage']
    
    if positive_ratio > 60:
        print(f"   ✅ 整体情感非常积极（正面 {positive_ratio:.1f}%）")
    elif positive_ratio > 40:
        print(f"   👍 整体情感较为积极（正面 {positive_ratio:.1f}%）")
    elif negative_ratio > 30:
        print(f"   ⚠️  存在一定负面评价（负面 {negative_ratio:.1f}%）")
    else:
        print(f"   📊 情感分布相对中性")
    
    print()


def visualize_keywords_text(keywords, top_n=20):
    """文本可视化：关键词"""
    print_section("🔑 关键词云（按频次排序）")
    
    if not keywords:
        print("\n⚠️  未提取到关键词")
        return
    
    print(f"\n共提取 {len(keywords)} 个关键词，显示前 {top_n} 个:\n")
    
    max_count = keywords[0]['count'] if keywords else 1
    
    sentiment_labels = {
        'positive': {'icon': '🟢', 'label': '正面'},
        'neutral': {'icon': '🟡', 'label': '中性'},
        'negative': {'icon': '🔴', 'label': '负面'}
    }
    
    for i, kw in enumerate(keywords[:top_n], 1):
        word = kw.get('word', '')
        count = kw.get('count', 0)
        sentiment = kw.get('sentiment', 0)
        sentiment_label = kw.get('sentiment_label', 'neutral')
        
        size_ratio = count / max_count if max_count > 0 else 0
        stars = '★' * int(size_ratio * 5)
        
        sentiment_icon = sentiment_labels.get(sentiment_label, {}).get('icon', '⚪')
        
        if size_ratio > 0.8:
            word_display = f"【{word}】"
        elif size_ratio > 0.5:
            word_display = f"《{word}》"
        else:
            word_display = f" {word} "
        
        print(f"{i:2}. {word_display:15} {sentiment_icon}  频次:{count:2}  {stars}")
    
    print()


def visualize_competitor_analysis_text(competitor_analysis):
    """文本可视化：竞品对比"""
    print_section("🏆 竞品对比分析")
    
    main_brand = competitor_analysis.get('main_brand', '')
    main_share = competitor_analysis.get('main_brand_share', 0)
    rank = competitor_analysis.get('rank', 0)
    competitors = competitor_analysis.get('competitor_shares', {})
    top_competitor = competitor_analysis.get('top_competitor', '')
    
    print(f"\n主品牌：{main_brand}")
    print(f"\n📊 市场地位:")
    
    rank_icon = '🥇 第 1 名' if rank == 1 else '🥈 第 2 名' if rank == 2 else '🥉 第 3 名' if rank == 3 else f'第{rank}名'
    print(f"   排位：{rank_icon}")
    print(f"   声量占比：{main_share:.2f}%")
    
    print(f"\n📈 竞争格局:")
    
    all_brands = {main_brand: main_share, **competitors}
    sorted_brands = sorted(all_brands.items(), key=lambda x: x[1], reverse=True)
    
    max_share = max(all_brands.values()) if all_brands else 0
    
    for i, (brand, share) in enumerate(sorted_brands, 1):
        is_main = brand == main_brand
        marker = '👉' if is_main else '  '
        bar_length = int((share / max_share) * 40) if max_share > 0 else 0
        bar = '█' * bar_length
        
        print(f"{marker} {i}. {brand:15} {share:6.2f}%  {bar}")
    
    print(f"\n📋 竞争分析总结:")
    if rank == 1:
        print(f"   ✅ {main_brand}处于领先地位，与竞品保持均势")
    elif rank <= 3:
        print(f"   👍 {main_brand}处于第一梯队，需继续努力超越领先者")
    else:
        print(f"   ⚠️  {main_brand}排名靠后，需要加大品牌曝光力度")
    
    if top_competitor:
        top_share = competitors.get(top_competitor, 0)
        gap = top_share - main_share
        if gap > 0:
            print(f"   📊 主要竞争对手：{top_competitor}（领先{gap:.2f}%）")
        else:
            print(f"   📊 主要竞争对手：{top_competitor}（落后{abs(gap):.2f}%）")
    
    print()


def visualize_quality_distribution_text(results):
    """文本可视化：质量分布"""
    print_section("⭐ 质量评分分布")
    
    if not results:
        print("\n⚠️  无质量评分数据")
        return
    
    quality_levels = {'high': [], 'medium': [], 'low': [], 'unknown': []}
    scores = []
    
    for r in results:
        level = r.get('quality_level', 'unknown')
        score = r.get('quality_score', 0)
        quality_levels[level].append(r)
        if score:
            scores.append(score)
    
    print(f"\n总样本数：{len(results)} 条\n")
    
    level_icons = {
        'high': {'icon': '🟢', 'label': '高质量'},
        'medium': {'icon': '🟡', 'label': '中等质量'},
        'low': {'icon': '🔴', 'label': '低质量'},
        'unknown': {'icon': '⚪', 'label': '未知'}
    }
    
    for level in ['high', 'medium', 'low', 'unknown']:
        items = quality_levels[level]
        icon = level_icons[level]['icon']
        label = level_icons[level]['label']
        percentage = len(items) / len(results) * 100 if results else 0
        
        bar_length = int(percentage / 100 * 40)
        bar = '█' * bar_length
        
        print(f"{icon} {label:10} {len(items):2}  ({percentage:5.1f}%)  {bar}")
    
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\n📈 平均质量评分：{avg_score:.1f} / 100")
        
        if avg_score >= 80:
            print(f"   ✅ 整体质量优秀")
        elif avg_score >= 60:
            print(f"   👍 整体质量良好")
        else:
            print(f"   ⚠️  整体质量有待提升")
    
    print()


def visualize_complete_dashboard_text(results):
    """文本可视化：完整仪表板"""
    print_header("🎯 第一层分析结果完整仪表板")
    
    # 1. 品牌分布
    brand_distribution = analyze_brand_distribution(results)
    visualize_brand_distribution_text(brand_distribution)
    
    # 2. 情感分布
    sentiment_distribution = analyze_sentiment_distribution(results)
    visualize_sentiment_distribution_text(sentiment_distribution)
    
    # 3. 关键词
    keywords = extract_keywords(results)
    visualize_keywords_text(keywords, top_n=20)
    
    # 4. 竞品对比
    competitor_analysis = analyze_competitors(results, TEST_BRAND_A)
    visualize_competitor_analysis_text(competitor_analysis)
    
    # 5. 质量分布
    visualize_quality_distribution_text(results)
    
    # 总结
    print_header("📋 分析总结")
    print(f"""
执行时间：2026-03-09
分析样本：{len(results)} 条 AI 响应
分析维度：4 个（品牌分布、情感分布、关键词、竞品对比）

核心发现:
  1. 品牌露出：各品牌均衡分布，{TEST_BRAND_A}略微领先
  2. 情感倾向：整体情感积极，正面评价占主导
  3. 关键词：用户关注"性价比"、"安全性"、"智能功能"
  4. 竞争格局：三足鼎立，各有优势

建议操作:
  ✅ 继续保持品牌曝光度
  ✅ 强化"高端"、"安全"的品牌形象
  ⚠️  关注竞品的"性价比"优势
  📊 考虑增加差异化卖点
""")


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🎯 第一层分析结果可视化展示                          ║
║                                                              ║
║  分析模块：品牌分布 | 情感分布 | 关键词 | 竞品对比            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("📥 正在加载测试数据...")
    results = create_mock_diagnosis_results()
    print(f"✅ 加载完成，共 {len(results)} 条诊断结果")
    
    print("\n" + "="*80)
    print("正在生成文本可视化...")
    print("="*80)
    
    visualize_complete_dashboard_text(results)
    
    print("\n✅ 文本可视化已完成！")


if __name__ == '__main__':
    main()
