"""
第一层分析结果可视化展示

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

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wechat_backend.v2.analytics.brand_distribution_analyzer import BrandDistributionAnalyzer
from wechat_backend.v2.analytics.sentiment_analyzer import SentimentAnalyzer
from wechat_backend.v2.analytics.keyword_extractor import KeywordExtractor
from wechat_backend.logging_config import api_logger

# 尝试导入可视化库
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️ 未安装 matplotlib，将使用文本可视化")

try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False


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


def visualize_brand_distribution_text(distribution):
    """文本可视化：品牌分布"""
    print_section("📊 品牌分布分析")
    
    data = distribution.get('data', {})
    total_count = distribution.get('total_count', 0)
    
    print(f"\n总样本数：{total_count} 条 AI 响应\n")
    
    # 排序
    sorted_brands = sorted(data.items(), key=lambda x: x[1], reverse=True)
    
    # 找到最大值用于缩放
    max_percentage = max(data.values()) if data else 0
    
    for rank, (brand, percentage) in enumerate(sorted_brands, 1):
        # 计算条形长度（最大 40 个字符）
        bar_length = int((percentage / max_percentage) * 40) if max_percentage > 0 else 0
        bar = '█' * bar_length
        
        # 排名图标
        rank_icon = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else f'{rank}.'
        
        print(f"{rank_icon} {brand:15} {percentage:6.2f}%  {bar}")
    
    print()


def visualize_sentiment_distribution_text(distribution):
    """文本可视化：情感分布"""
    print_section("💚 情感分布分析")
    
    data = distribution.get('data', {})
    total_count = distribution.get('total_count', 0)
    
    print(f"\n总样本数：{total_count} 条 AI 响应\n")
    
    # 情感图标和颜色
    sentiment_config = {
        'positive': {'icon': '😊', 'label': '正面', 'color': '🟢'},
        'neutral': {'icon': '😐', 'label': '中性', 'color': '🟡'},
        'negative': {'icon': '😔', 'label': '负面', 'color': '🔴'}
    }
    
    # 计算百分比
    percentages = {}
    for sentiment in ['positive', 'neutral', 'negative']:
        count = data.get(sentiment, 0)
        percentage = (count / total_count * 100) if total_count > 0 else 0
        percentages[sentiment] = {'count': count, 'percentage': percentage}
    
    # 显示情感分布
    max_count = max(percentages.values(), key=lambda x: x['count'])['count'] if total_count > 0 else 1
    
    for sentiment in ['positive', 'neutral', 'negative']:
        config = sentiment_config[sentiment]
        pdata = percentages[sentiment]
        
        # 计算条形长度
        bar_length = int((pdata['count'] / max_count) * 40) if max_count > 0 else 0
        bar = '█' * bar_length
        
        print(f"{config['icon']} {config['label']:6} {config['color']}  {pdata['count']:3}  ({pdata['percentage']:5.1f}%)  {bar}")
    
    # 情感倾向总结
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
    
    # 找到最大频次用于缩放
    max_count = keywords[0]['count'] if keywords else 1
    
    # 情感标签映射
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
        
        # 计算显示大小（基于频次）
        size_ratio = count / max_count if max_count > 0 else 0
        stars = '★' * int(size_ratio * 5)
        
        # 情感图标
        sentiment_icon = sentiment_labels.get(sentiment_label, {}).get('icon', '⚪')
        
        # 根据频次调整词的大小
        if size_ratio > 0.8:
            word_display = f"【{word}】"  # 高频词加框
        elif size_ratio > 0.5:
            word_display = f"《{word}》"  # 中频词加书名号
        else:
            word_display = f" {word} "  # 低频词正常显示
        
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
    
    # 排名图标
    rank_icon = '🥇 第 1 名' if rank == 1 else '🥈 第 2 名' if rank == 2 else '🥉 第 3 名' if rank == 3 else f'第{rank}名'
    print(f"   排位：{rank_icon}")
    print(f"   声量占比：{main_share:.2f}%")
    
    print(f"\n📈 竞争格局:")
    
    # 所有品牌（包括主品牌）
    all_brands = {main_brand: main_share, **competitors}
    sorted_brands = sorted(all_brands.items(), key=lambda x: x[1], reverse=True)
    
    max_share = max(all_brands.values()) if all_brands else 0
    
    for i, (brand, share) in enumerate(sorted_brands, 1):
        is_main = brand == main_brand
        marker = '👉' if is_main else '  '
        bar_length = int((share / max_share) * 40) if max_share > 0 else 0
        bar = '█' * bar_length
        
        print(f"{marker} {i}. {brand:15} {share:6.2f}%  {bar}")
    
    # 竞争分析总结
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
    
    # 按质量等级分组
    quality_levels = {'high': [], 'medium': [], 'low': [], 'unknown': []}
    scores = []
    
    for r in results:
        level = r.get('quality_level', 'unknown')
        score = r.get('quality_score', 0)
        quality_levels[level].append(r)
        if score:
            scores.append(score)
    
    print(f"\n总样本数：{len(results)} 条\n")
    
    # 质量等级图标
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
    
    # 平均质量评分
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
    
    # 执行所有分析
    brand_analyzer = BrandDistributionAnalyzer()
    sentiment_analyzer = SentimentAnalyzer()
    keyword_extractor = KeywordExtractor()
    
    # 1. 品牌分布
    brand_distribution = brand_analyzer.analyze(results)
    visualize_brand_distribution_text(brand_distribution)
    
    # 2. 情感分布
    sentiment_distribution = sentiment_analyzer.analyze(results)
    visualize_sentiment_distribution_text(sentiment_distribution)
    
    # 3. 关键词
    keywords = keyword_extractor.extract(results)
    visualize_keywords_text(keywords, top_n=20)
    
    # 4. 竞品对比
    competitor_analysis = brand_analyzer.analyze_competitors(results, TEST_BRAND_A)
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


# ==================== 图形可视化（如果有 matplotlib）====================
def visualize_brand_distribution_chart(distribution, save_path=None):
    """图形可视化：品牌分布饼图"""
    if not HAS_MATPLOTLIB:
        return
    
    data = distribution.get('data', {})
    if not data:
        return
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # 饼图
    colors = plt.cm.Set3(range(len(data)))
    wedges, texts, autotexts = ax1.pie(
        data.values(),
        labels=data.keys(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    
    # 美化饼图
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
    
    ax1.set_title('品牌分布占比', fontsize=14, fontweight='bold')
    
    # 柱状图
    brands = list(data.keys())
    percentages = list(data.values())
    bars = ax2.bar(brands, percentages, color=colors)
    
    ax2.set_ylabel('占比 (%)', fontsize=12)
    ax2.set_title('品牌声量对比', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, max(percentages) * 1.2)
    
    # 在柱子上添加数值标签
    for bar, pct in zip(bars, percentages):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f'{pct:.2f}%',
            ha='center',
            va='bottom',
            fontsize=10
        )
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 品牌分布图已保存：{save_path}")
    else:
        plt.show()
    
    plt.close()


def visualize_sentiment_distribution_chart(distribution, save_path=None):
    """图形可视化：情感分布柱状图"""
    if not HAS_MATPLOTLIB:
        return
    
    data = distribution.get('data', {})
    total_count = distribution.get('total_count', 0)
    
    if not data:
        return
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # 柱状图
    sentiments = ['positive', 'neutral', 'negative']
    labels = ['正面 😊', '中性 😐', '负面 😔']
    colors = ['#4CAF50', '#FFC107', '#F44336']
    counts = [data.get(s, 0) for s in sentiments]
    percentages = [(c / total_count * 100) if total_count > 0 else 0 for c in counts]
    
    bars = ax1.bar(labels, counts, color=colors)
    ax1.set_ylabel('数量', fontsize=12)
    ax1.set_title('情感分布（数量）', fontsize=14, fontweight='bold')
    
    # 添加数值标签
    for bar, count, pct in zip(bars, counts, percentages):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f'{count}\n({pct:.1f}%)',
            ha='center',
            va='bottom',
            fontsize=11
        )
    
    # 环形图
    ax2.pie(
        counts,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.85
    )
    
    # 添加白色圆心（形成环形图）
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    ax2.add_artist(centre_circle)
    ax2.set_title('情感分布（占比）', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 情感分布图已保存：{save_path}")
    else:
        plt.show()
    
    plt.close()


def visualize_keywords_chart(keywords, top_n=30, save_path=None):
    """图形可视化：关键词条形图"""
    if not HAS_MATPLOTLIB:
        return
    
    if not keywords:
        return
    
    # 取前 N 个关键词
    top_keywords = keywords[:top_n]
    
    words = [kw['word'] for kw in top_keywords]
    counts = [kw['count'] for kw in top_keywords]
    sentiments = [kw.get('sentiment', 0) for kw in top_keywords]
    
    # 根据情感设置颜色
    colors = []
    for s in sentiments:
        if s > 0.3:
            colors.append('#4CAF50')  # 绿色 - 正面
        elif s < -0.3:
            colors.append('#F44336')  # 红色 - 负面
        else:
            colors.append('#FFC107')  # 黄色 - 中性
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 10))
    
    bars = ax.barh(range(len(words)), counts, color=colors)
    
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words, fontsize=11)
    ax.set_xlabel('频次', fontsize=12)
    ax.set_title('关键词频次 Top 30（按情感着色）', fontsize=14, fontweight='bold')
    
    # 反转 y 轴（让高频词在上面）
    ax.invert_yaxis()
    
    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#4CAF50', label='正面'),
        Patch(facecolor='#FFC107', label='中性'),
        Patch(facecolor='#F44336', label='负面')
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    # 在柱子上添加数值
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 0.1,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va='center',
            fontsize=10
        )
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 关键词图已保存：{save_path}")
    else:
        plt.show()
    
    plt.close()


def visualize_competitor_analysis_chart(competitor_analysis, save_path=None):
    """图形可视化：竞品对比雷达图"""
    if not HAS_MATPLOTLIB:
        return
    
    main_brand = competitor_analysis.get('main_brand', '')
    main_share = competitor_analysis.get('main_brand_share', 0)
    competitors = competitor_analysis.get('competitor_shares', {})
    
    if not main_brand:
        return
    
    # 准备数据
    brands = [main_brand] + list(competitors.keys())
    shares = [main_share] + list(competitors.values())
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # 柱状图
    colors = ['#FF5722'] + ['#9E9E9E'] * (len(brands) - 1)
    bars = ax1.bar(brands, shares, color=colors)
    
    ax1.set_ylabel('声量占比 (%)', fontsize=12)
    ax1.set_title('品牌声量对比', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, max(shares) * 1.2)
    
    # 添加数值标签
    for bar, share in zip(bars, shares):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f'{share:.2f}%',
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='bold'
        )
    
    # 雷达图
    ax2 = fig.add_subplot(122, polar=True)
    
    # 计算角度
    angles = [n / float(len(brands)) * 2 * 3.14159 for n in range(len(brands))]
    angles += angles[:1]
    
    # 数据
    values = shares[:]
    values += values[:1]
    
    # 绘制雷达图
    ax2.plot(angles, values, 'o-', linewidth=2, color='#FF5722')
    ax2.fill(angles, values, alpha=0.25, color='#FF5722')
    
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(brands, fontsize=11)
    ax2.set_ylim(0, max(shares) * 1.2)
    ax2.set_title('竞争格局雷达图', fontsize=14, fontweight='bold', pad=20)
    
    # 添加网格
    ax2.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 竞品对比图已保存：{save_path}")
    else:
        plt.show()
    
    plt.close()


def visualize_complete_dashboard_chart(results, save_dir=None):
    """图形可视化：完整仪表板"""
    if not HAS_MATPLOTLIB:
        print("⚠️  未安装 matplotlib，使用文本可视化")
        visualize_complete_dashboard_text(results)
        return
    
    # 执行所有分析
    brand_analyzer = BrandDistributionAnalyzer()
    sentiment_analyzer = SentimentAnalyzer()
    keyword_extractor = KeywordExtractor()
    
    brand_distribution = brand_analyzer.analyze(results)
    sentiment_distribution = sentiment_analyzer.analyze(results)
    keywords = keyword_extractor.extract(results)
    competitor_analysis = brand_analyzer.analyze_competitors(results, TEST_BRAND_A)
    
    # 创建 2x2 的仪表板
    fig = plt.figure(figsize=(20, 16))
    fig.suptitle('🎯 第一层分析结果完整仪表板', fontsize=16, fontweight='bold')
    
    # 1. 品牌分布饼图（左上）
    ax1 = fig.add_subplot(221)
    data = brand_distribution.get('data', {})
    colors = plt.cm.Set3(range(len(data)))
    ax1.pie(
        data.values(),
        labels=data.keys(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    ax1.set_title('📊 品牌分布占比', fontsize=14, fontweight='bold')
    
    # 2. 情感分布环形图（右上）
    ax2 = fig.add_subplot(222)
    sentiment_data = sentiment_distribution.get('data', {})
    sentiments = ['positive', 'neutral', 'negative']
    labels = ['正面 😊', '中性 😐', '负面 😔']
    sentiment_colors = ['#4CAF50', '#FFC107', '#F44336']
    counts = [sentiment_data.get(s, 0) for s in sentiments]
    
    wedges, texts, autotexts = ax2.pie(
        counts,
        labels=labels,
        colors=sentiment_colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.85
    )
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    ax2.add_artist(centre_circle)
    ax2.set_title('💚 情感分布', fontsize=14, fontweight='bold')
    
    # 3. 关键词条形图（左下）
    ax3 = fig.add_subplot(223)
    if keywords:
        top_keywords = keywords[:15]
        words = [kw['word'] for kw in top_keywords]
        word_counts = [kw['count'] for kw in top_keywords]
        kw_colors = ['#4CAF50' if kw.get('sentiment', 0) > 0.3 else 
                     '#F44336' if kw.get('sentiment', 0) < -0.3 else 
                     '#FFC107' for kw in top_keywords]
        
        ax3.barh(range(len(words)), word_counts, color=kw_colors)
        ax3.set_yticks(range(len(words)))
        ax3.set_yticklabels(words, fontsize=10)
        ax3.set_xlabel('频次')
        ax3.set_title('🔑 关键词 Top 15', fontsize=14, fontweight='bold')
        ax3.invert_yaxis()
    
    # 4. 竞品对比（右下）
    ax4 = fig.add_subplot(224)
    main_brand = competitor_analysis.get('main_brand', '')
    main_share = competitor_analysis.get('main_brand_share', 0)
    competitors = competitor_analysis.get('competitor_shares', {})
    
    brands = [main_brand] + list(competitors.keys())
    shares = [main_share] + list(competitors.values())
    comp_colors = ['#FF5722'] + ['#9E9E9E'] * (len(brands) - 1)
    
    bars = ax4.bar(brands, shares, color=comp_colors)
    ax4.set_ylabel('声量占比 (%)')
    ax4.set_title('🏆 竞品对比', fontsize=14, fontweight='bold')
    ax4.set_ylim(0, max(shares) * 1.2)
    
    # 旋转 x 轴标签
    plt.setp(ax4.get_xticklabels(), rotation=15, ha='right')
    
    # 添加数值标签
    for bar, share in zip(bars, shares):
        ax4.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f'{share:.1f}%',
            ha='center',
            va='bottom',
            fontsize=10,
            fontweight='bold'
        )
    
    plt.tight_layout()
    
    if save_dir:
        save_path = Path(save_dir) / 'analysis_dashboard.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 完整仪表板已保存：{save_path}")
    else:
        plt.show()
    
    plt.close()


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
    
    # 创建模拟数据
    print("📥 正在加载测试数据...")
    results = create_mock_diagnosis_results()
    print(f"✅ 加载完成，共 {len(results)} 条诊断结果")
    
    # 检查是否有 matplotlib
    if HAS_MATPLOTLIB:
        print("✅ 检测到 matplotlib，将显示图形可视化")
    else:
        print("⚠️  未检测到 matplotlib，将使用文本可视化")
    
    # 执行文本可视化
    print("\n" + "="*80)
    print("正在生成文本可视化...")
    print("="*80)
    
    visualize_complete_dashboard_text(results)
    
    # 询问是否生成图形
    if HAS_MATPLOTLIB:
        print("\n" + "="*80)
        response = input("是否生成图形可视化？(y/n): ").strip().lower()
        
        if response == 'y':
            print("\n正在生成图形可视化...")
            visualize_complete_dashboard_chart(results, save_dir='.')
            print("\n✅ 所有可视化已完成！")
        else:
            print("\n✅ 文本可视化已完成！")
    else:
        print("\n✅ 文本可视化已完成！")
        print("\n💡 提示：安装 matplotlib 可获得图形可视化体验")
        print("   命令：pip install matplotlib wordcloud")


if __name__ == '__main__':
    main()
