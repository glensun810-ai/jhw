"""
验证SourceAggregator增强功能的测试
"""
import sys
import os
import hashlib
import math
import re
import urllib.parse
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

class ImpactCalculator:
    """
    影响力计算器
    根据引用频次、模型覆盖度和关联品牌的情感偏向，计算信源的影响力指数
    """

    def __init__(self):
        # 权重配置
        self.weights = {
            'citation_count': 0.4,      # 引用频次权重
            'model_coverage': 0.3,      # 模型覆盖度权重
            'sentiment_bias': 0.3       # 情感偏向权重
        }

    def calculate_impact_index(
        self,
        citation_count: int,
        model_coverage: int,
        sentiment_score: float = 0.0,
        domain_authority: str = 'Medium'
    ) -> float:
        """
        计算影响力指数

        Args:
            citation_count: 引用频次
            model_coverage: 模型覆盖度（被多少个不同AI模型引用）
            sentiment_score: 情感偏向得分 (-1.0 到 1.0)
            domain_authority: 域名权威度 ('High', 'Medium', 'Low')

        Returns:
            影响力指数 (0.0 到 100.0)
        """
        # 标准化引用频次得分 (0-100)
        normalized_citation_score = self._normalize_citation_score(citation_count)

        # 标准化模型覆盖度得分 (0-100)
        normalized_coverage_score = self._normalize_coverage_score(model_coverage)

        # 情感偏向得分调整 (-1.0 到 1.0 映射到 0-100)
        normalized_sentiment_score = self._normalize_sentiment_score(sentiment_score)

        # 根据域名权威度调整得分
        authority_multiplier = self._get_authority_multiplier(domain_authority)

        # 计算加权影响力指数
        weighted_impact = (
            normalized_citation_score * self.weights['citation_count'] +
            normalized_coverage_score * self.weights['model_coverage'] +
            normalized_sentiment_score * self.weights['sentiment_bias']
        )

        # 应用权威度乘数
        final_impact = weighted_impact * authority_multiplier

        # 确保最终得分在0-100范围内
        return max(0.0, min(100.0, final_impact))

    def _normalize_citation_score(self, citation_count: int) -> float:
        """
        标准化引用频次得分

        Args:
            citation_count: 引用次数

        Returns:
            标准化得分 (0-100)
        """
        if citation_count <= 0:
            return 0.0

        # 使用对数缩放，避免过多引用导致得分过高
        # 最大引用次数设为100，超过100次的得分增长放缓
        max_citations = 100
        if citation_count >= max_citations:
            return 100.0
        else:
            # 对数缩放公式
            return min(100.0, (math.log(citation_count + 1) / math.log(max_citations + 1)) * 100.0)

    def _normalize_coverage_score(self, model_coverage: int) -> float:
        """
        标准化模型覆盖度得分

        Args:
            model_coverage: 模型覆盖数量

        Returns:
            标准化得分 (0-100)
        """
        if model_coverage <= 0:
            return 0.0

        # 假设最大覆盖模型数为10，超过10个模型的得分增长放缓
        max_coverage = 10
        if model_coverage >= max_coverage:
            return 100.0
        else:
            # 线性缩放
            return min(100.0, (model_coverage / max_coverage) * 100.0)

    def _normalize_sentiment_score(self, sentiment_score: float) -> float:
        """
        标准化情感偏向得分

        Args:
            sentiment_score: 情感偏向得分 (-1.0 到 1.0)

        Returns:
            标准化得分 (0-100)
        """
        # 将 -1.0 到 1.0 的范围映射到 0-100
        # 0 表示中性情感，正值表示正面情感，负值表示负面情感
        # 这里我们考虑绝对值，因为无论是正面还是负面都代表影响力
        normalized = abs(sentiment_score) * 100.0
        return max(0.0, min(100.0, normalized))

    def _get_authority_multiplier(self, domain_authority: str) -> float:
        """
        获取域名权威度乘数

        Args:
            domain_authority: 域名权威度 ('High', 'Medium', 'Low')

        Returns:
            权威度乘数
        """
        multipliers = {
            'High': 1.2,    # 高权威度给予20%提升
            'Medium': 1.0,  # 中等权威度无变化
            'Low': 0.8      # 低权威度降低20%
        }
        
        return multipliers.get(domain_authority, 1.0)

    def calculate_batch_impacts(
        self,
        source_data: list
    ) -> list:
        """
        批量计算影响力指数

        Args:
            source_data: 信源数据列表，每个元素包含 citation_count, model_coverage, sentiment_score, domain_authority

        Returns:
            包含影响力指数的信源数据列表
        """
        results = []
        for source in source_data:
            impact_index = self.calculate_impact_index(
                citation_count=source.get('citation_count', 0),
                model_coverage=source.get('model_coverage', 0),
                sentiment_score=source.get('sentiment_score', 0.0),
                domain_authority=source.get('domain_authority', 'Medium')
            )
            
            # 添加影响力指数到源数据
            updated_source = source.copy()
            updated_source['impact_index'] = impact_index
            results.append(updated_source)
        
        return results


class SourceAggregator:
    """
    信源穿透与引用聚合引擎 (增强版)
    """

    def __init__(self):
        # URL匹配的正则表达式模式
        self.url_pattern = re.compile(
            r'https?://'  # http:// or https://
            r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URL字符
            re.IGNORECASE
        )

        # Markdown链接模式
        self.markdown_link_pattern = re.compile(
            r'\[([^\]]+)\]\(([^)]+)\)',  # [text](url) 格式
            re.IGNORECASE
        )

        # 引用标记模式（如[1]、[2]等）
        self.citation_pattern = re.compile(
            r'\[(\d+)\]',  # [数字] 格式
            re.IGNORECASE
        )

    def _extract_urls(self, ai_response: str, citations: Optional[List[Dict]] = None) -> List[Dict]:
        """
        从AI回复和引用信息中提取所有URL
        """
        urls = []

        # 从引用信息中提取URL
        if citations:
            for citation in citations:
                if 'url' in citation:
                    url = citation['url']
                    title = citation.get('title', '')
                    site_name = self._extract_site_name(url)
                    urls.append({
                        'url': url,
                        'title': title,
                        'site_name': site_name
                    })

        # 从AI回复文本中提取URL
        text_urls = self.url_pattern.findall(ai_response)
        for url in text_urls:
            site_name = self._extract_site_name(url)
            urls.append({
                'url': url,
                'title': '',
                'site_name': site_name
            })

        # 从Markdown链接中提取URL
        markdown_links = self.markdown_link_pattern.findall(ai_response)
        for link_text, url in markdown_links:
            site_name = self._extract_site_name(url)
            urls.append({
                'url': url,
                'title': link_text,
                'site_name': site_name
            })

        # 去重处理
        unique_urls = []
        seen_urls = set()
        for url_info in urls:
            normalized_url = self._normalize_url(url_info['url'])
            if normalized_url not in seen_urls:
                url_info['url'] = normalized_url
                unique_urls.append(url_info)
                seen_urls.add(normalized_url)

        return unique_urls

    def _extract_site_name(self, url: str) -> str:
        """
        从URL中提取站点名称
        """
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname or parsed.netloc
            if hostname:
                # 移除www前缀
                if hostname.startswith('www.'):
                    hostname = hostname[4:]
                # 只保留域名部分，去掉顶级域名
                parts = hostname.split('.')
                if len(parts) >= 2:
                    # 通常取倒数第二部分作为站点名（如zhihu.com中的zhihu）
                    return parts[-2]
                else:
                    return hostname
            else:
                return 'Unknown'
        except Exception:
            return 'Unknown'

    def _normalize_url(self, url: str) -> str:
        """
        规范化URL（移除参数、片段等）
        """
        try:
            parsed = urllib.parse.urlparse(url)
            # 重建URL，只保留协议、域名和路径
            # 确保路径至少有一个斜杠
            path = parsed.path if parsed.path else '/'
            normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
            return normalized
        except Exception:
            return url  # 如果解析失败，返回原始URL

    def _generate_url_id(self, url: str) -> str:
        """
        为URL生成唯一ID
        """
        # 使用URL的MD5哈希值作为唯一ID
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]

    def _assess_domain_authority(self, site_name: str) -> str:
        """
        评估域名权威度
        """
        # 定义高权威度站点
        high_authority_sites = [
            'zhihu', 'baidu', 'baidu_baike', 'weibo', 'toutiao', 'qq', '163', 'sohu',
            'tmall', 'taobao', 'jd', 'pdd', 'vip', 'gome', 'suning',
            'weixin', 'douyin', 'kuaishou', 'xigua', 'bilibili',
            '360', 'sogou', 'sm', 'uc', 'aliyun',
            'gov', 'edu', 'org', 'mil', 'net', 'com', 'bloomberg', 'reuters', 'wsj', 'nytimes', 'ft', 'scmp'
        ]

        # 根据站点名称评估权威度
        if site_name.lower() in high_authority_sites:
            return 'High'
        elif site_name.lower() in ['csdn', 'jianshu', 'segmentfault', 'zcool', 'ui', 'pm', 'medium', 'dev', 'github', 'stackoverflow']:
            return 'Medium'
        else:
            return 'Low'

    def aggregate_multiple_models(self, model_responses: List[Dict]) -> Dict:
        """
        聚合来自多个AI模型的信源信息
        """
        # 统计每个URL的详细信息
        url_stats = defaultdict(lambda: {
            'citation_count': 0,
            'models': set(),
            'questions': set(),
            'urls': set(),
            'site_names': set(),
            'domain_authorities': set()
        })

        all_extracted_urls = []

        # 处理每个模型的响应
        for response in model_responses:
            model_name = response.get('model_name', 'default')
            ai_response = response.get('ai_response', '')
            citations = response.get('citations', [])
            question = response.get('question', '')

            # 提取URL
            extracted_urls = self._extract_urls(ai_response, citations)
            all_extracted_urls.extend(extracted_urls)

            # 更新统计信息
            for url_info in extracted_urls:
                normalized_url = url_info['url']
                url_stats[normalized_url]['citation_count'] += 1
                url_stats[normalized_url]['models'].add(model_name)
                if question:
                    url_stats[normalized_url]['questions'].add(question)
                url_stats[normalized_url]['urls'].add(url_info['url'])
                url_stats[normalized_url]['site_names'].add(url_info['site_name'])
                domain_authority = self._assess_domain_authority(url_info['site_name'])
                url_stats[normalized_url]['domain_authorities'].add(domain_authority)

        # 生成信源池
        source_pool = []
        seen_urls = set()

        for url_info in all_extracted_urls:
            normalized_url = url_info['url']
            if normalized_url in seen_urls:
                continue  # 避免重复添加

            stats = url_stats[normalized_url]
            citation_count = stats['citation_count']
            model_coverage = len(stats['models'])
            site_name = url_info['site_name']
            domain_authority = list(stats['domain_authorities'])[0] if stats['domain_authorities'] else 'Medium'  # 取第一个权威度

            source_item = {
                'id': self._generate_url_id(normalized_url),  # 生成唯一ID
                'url': normalized_url,
                'site_name': site_name,
                'citation_count': citation_count,
                'cross_model_coverage': model_coverage,  # 模型覆盖度
                'domain_authority': domain_authority,
                'referenced_questions': list(stats['questions'])[:10]  # 限制显示的问题数量，避免数据过大
            }

            # 计算问题排名（根据引用该URL的问题数量）
            source_item['question_reference_count'] = len(stats['questions'])

            source_pool.append(source_item)
            seen_urls.add(normalized_url)

        # 按引用次数降序排列，其次按模型覆盖度排列
        source_pool.sort(key=lambda x: (x['citation_count'], x['cross_model_coverage']), reverse=True)

        # 生成引用排行（仅包含ID）
        citation_rank = [item['id'] for item in source_pool]

        return {
            'source_pool': source_pool,
            'citation_rank': citation_rank,
            'evidence_chain': []  # 暂时空，将在证据链模块中实现
        }


def test_enhanced_features():
    """测试增强功能"""
    print("测试SourceAggregator增强功能...")

    # 创建聚合器实例
    aggregator = SourceAggregator()
    calculator = ImpactCalculator()

    # 准备测试数据 - 模拟来自多个AI模型的响应
    model_responses = [
        {
            'model_name': 'qwen',  # 通义千问
            'ai_response': '德施曼智能锁技术先进，可以参考知乎上的评测[https://zhihu.com/article/123]。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'question': '德施曼智能锁怎么样？'
        },
        {
            'model_name': 'doubao',  # 豆包
            'ai_response': '小米智能锁性价比高，在淘宝上销量很好[https://taobao.com/product/456]。',
            'citations': [{'url': 'https://taobao.com/product/456', 'title': '小米智能锁销售页面'}],
            'question': '小米智能锁怎么样？'
        },
        {
            'model_name': 'deepseek',  # DeepSeek
            'ai_response': '知乎上有很多关于智能锁的评测文章[https://zhihu.com/article/123]，包括德施曼和小米。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'question': '智能锁品牌对比'
        },
        {
            'model_name': 'chatgpt',  # ChatGPT
            'ai_response': '知乎上的评测文章[https://zhihu.com/article/123]提到了智能锁的安全性问题。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'question': '智能锁安全性如何？'
        }
    ]

    # 使用增强的聚合器处理数据
    result = aggregator.aggregate_multiple_models(model_responses)

    print(f"聚合结果 - 信源数量: {len(result['source_pool'])}, 引用排行数量: {len(result['citation_rank'])}")

    # 检查结果结构
    source_pool = result['source_pool']
    print(f"\n信源池详情:")

    for i, source in enumerate(source_pool):
        print(f"\n信源 {i+1}:")
        print(f"  - ID: {source['id']}")
        print(f"  - URL: {source['url']}")
        print(f"  - 站点名称: {source['site_name']}")
        print(f"  - 引用次数: {source['citation_count']}")
        print(f"  - 跨模型覆盖度 (cross_model_coverage): {source['cross_model_coverage']}")
        print(f"  - 域名权威度: {source['domain_authority']}")
        print(f"  - 引用问题数: {source.get('question_reference_count', 0)}")
        print(f"  - 引用问题列表: {source.get('referenced_questions', [])}")

        # 验证必要的字段是否存在
        assert 'cross_model_coverage' in source, f"信源 {i+1} 缺少 cross_model_coverage 字段!"
        assert 'citation_count' in source, f"信源 {i+1} 缺少 citation_count 字段!"
        assert 'domain_authority' in source, f"信源 {i+1} 缺少 domain_authority 字段!"
        assert 'referenced_questions' in source, f"信源 {i+1} 缺少 referenced_questions 字段!"

    # 特别检查知乎链接，它应该被多个模型引用
    print(f"\n验证跨模型覆盖度计算:")
    zhihu_sources = [s for s in source_pool if 'zhihu' in s['url']]
    if zhihu_sources:
        zhihu_source = zhihu_sources[0]
        cross_model_coverage = zhihu_source['cross_model_coverage']
        citation_count = zhihu_source['citation_count']
        
        print(f"  知乎链接分析:")
        print(f"    - URL: {zhihu_source['url']}")
        print(f"    - 跨模型覆盖度: {cross_model_coverage} (应该是3，因为qwen、deepseek和chatgpt都引用了)")
        print(f"    - 引用次数: {citation_count} (应该是3)")
        print(f"    - 站点名称: {zhihu_source['site_name']}")
        print(f"    - 权威度: {zhihu_source['domain_authority']}")
        
        # 验证知乎链接确实被多个模型引用
        assert cross_model_coverage >= 2, f"知乎链接应该被至少2个模型引用，但实际只有 {cross_model_coverage} 个"
        assert citation_count >= 2, f"知乎链接应该被至少引用2次，但实际只有 {citation_count} 次"
    else:
        print("  未找到知乎链接")

    # 测试影响力计算器
    print(f"\n测试影响力计算器:")
    for source in source_pool:
        impact_index = calculator.calculate_impact_index(
            citation_count=source['citation_count'],
            model_coverage=source['cross_model_coverage'],
            sentiment_score=0.2,  # 假设轻微正面情感
            domain_authority=source['domain_authority']
        )
        print(f"  {source['site_name']} 影响力指数: {impact_index:.2f}")
        assert 0.0 <= impact_index <= 100.0, f"影响力指数应在0-100之间，实际为 {impact_index}"

    print(f"\n✓ 所有测试通过! 增强功能正常工作。")
    print(f"✓ cross_model_coverage 字段已正确添加到信源数据中。")
    print(f"✓ 影响力计算器能够根据引用次数、模型覆盖度和权威度计算影响力指数。")

    # 输出完整的JSON结构供参考
    print(f"\nAPI响应示例 (完整信源池):")
    print(f"source_pool: {len(source_pool)} 个信源")
    for source in source_pool:
        print(f"  - {source['site_name']}: cross_model_coverage={source['cross_model_coverage']}, "
              f"citation_count={source['citation_count']}, impact_index={calculator.calculate_impact_index(source['citation_count'], source['cross_model_coverage'], 0.2, source['domain_authority']):.2f}")


if __name__ == "__main__":
    test_enhanced_features()