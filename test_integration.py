"""
测试SourceIntelligenceProcessor与ImpactCalculator集成的测试文件
"""
import sys
import os
import re
from urllib.parse import urlparse
from collections import defaultdict
from typing import List, Dict, Any
import math

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 直接复制ImpactCalculator代码
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


# 直接复制增强版SourceAggregator代码
class SourceAggregator:
    """
    信源穿透与引用聚合引擎
    从AI原始回复和引用信息中提取URL，生成引用排行，并建立负面语料与信源的证据链关联
    输出符合source_intelligence结构的数据
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

    def aggregate(self, ai_response: str, citations: Optional[List[Dict]] = None, model_name: str = "default") -> Dict:
        """
        聚合信源信息，提取URL、生成引用排行并建立证据链

        Args:
            ai_response: AI原始回复文本
            citations: AI返回的引用信息列表（可选）
            model_name: AI模型名称，用于计算模型覆盖度

        Returns:
            符合source_intelligence结构的字典
        """
        # 1. 提取所有URL
        extracted_urls = self._extract_urls(ai_response, citations)

        # 2. 生成信源池和引用排行
        source_pool, citation_rank = self._generate_source_statistics(extracted_urls, model_name=model_name)

        # 3. 生成证据链（暂时为空，将在证据链模块中实现）
        evidence_chain = []

        return {
            'source_pool': source_pool,
            'citation_rank': citation_rank,
            'evidence_chain': evidence_chain
        }

    def _extract_urls(self, ai_response: str, citations: Optional[List[Dict]] = None) -> List[Dict]:
        """
        从AI回复和引用信息中提取所有URL

        Args:
            ai_response: AI回复文本
            citations: 引用信息列表

        Returns:
            提取到的URL列表（包含URL、站点名称等信息）
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

        Args:
            url: URL字符串

        Returns:
            站点名称
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

        Args:
            url: 原始URL

        Returns:
            规范化后的URL
        """
        try:
            parsed = urllib.parse.urlparse(url)
            # 重建URL，只保留协议、域名和路径
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return normalized
        except Exception:
            return url  # 如果解析失败，返回原始URL

    def _generate_source_statistics(self, urls: List[Dict], model_name: str = "default") -> Tuple[List[Dict], List[str]]:
        """
        生成信源统计数据和引用排行

        Args:
            urls: URL列表
            model_name: AI模型名称，用于计算模型覆盖度

        Returns:
            (source_pool, citation_rank) 元组
        """
        # 统计每个URL的出现次数和模型覆盖情况
        url_stats = defaultdict(lambda: {
            'citation_count': 0,
            'models': set(),
            'questions': set()  # 存储引用此URL的问题
        })
        site_counter = Counter()

        for url_info in urls:
            normalized_url = url_info['url']
            url_stats[normalized_url]['citation_count'] += 1
            url_stats[normalized_url]['models'].add(model_name)
            site_counter[url_info['site_name']] += 1

        # 生成信源池
        source_pool = []
        seen_urls = set()
        for url_info in urls:
            normalized_url = url_info['url']
            if normalized_url in seen_urls:
                continue  # 避免重复添加

            stats = url_stats[normalized_url]
            citation_count = stats['citation_count']
            model_coverage = len(stats['models'])
            site_name = url_info['site_name']
            domain_authority = self._assess_domain_authority(site_name)

            source_pool.append({
                'id': self._generate_url_id(normalized_url),  # 生成唯一ID
                'url': normalized_url,
                'site_name': site_name,
                'citation_count': citation_count,
                'cross_model_coverage': model_coverage,  # 新增：模型覆盖度
                'domain_authority': domain_authority
            })
            seen_urls.add(normalized_url)

        # 按引用次数降序排列
        source_pool.sort(key=lambda x: x['citation_count'], reverse=True)

        # 生成引用排行（仅包含ID）
        citation_rank = [item['id'] for item in source_pool]

        return source_pool, citation_rank

    def aggregate_multiple_models(self, model_responses: List[Dict]) -> Dict:
        """
        聚合来自多个AI模型的信源信息

        Args:
            model_responses: 包含多个模型响应的列表，每个元素包含：
                             {
                               'model_name': '模型名称',
                               'ai_response': 'AI回复文本',
                               'citations': '引用信息列表',
                               'question': '提问内容' (可选)
                             }

        Returns:
            符合source_intelligence结构的字典，包含跨模型统计信息
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

    def _generate_url_id(self, url: str) -> str:
        """
        为URL生成唯一ID

        Args:
            url: URL字符串

        Returns:
            唯一ID
        """
        import hashlib
        # 使用URL的MD5哈希值作为唯一ID
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]

    def _assess_domain_authority(self, site_name: str) -> str:
        """
        评估域名权威度

        Args:
            site_name: 站点名称

        Returns:
            权威度等级（High/Medium/Low）
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


# 定义Optional类型
from typing import Optional


class SourceWeightLibrary:
    """
    信源权重库 (模拟实现)
    """
    def __init__(self):
        self.weights = {
            "wikipedia.org": 0.9,
            "zhihu.com": 0.7,
            "baidu.com": 0.8,
            "36kr.com": 0.75,
            "weibo.com": 0.6,
            "xiaohongshu.com": 0.6,
            "default": 0.3,
            "competitor": 0.1
        }
        self.name_weights = {
            "维基百科": 0.9,
            "知乎": 0.7,
            "百度百科": 0.8,
            "财新网": 0.8,
            "第一财经": 0.78,
        }

    def get_weight(self, source_name: str) -> float:
        if source_name in self.name_weights:
            return self.name_weights[source_name]
        for key, weight in self.weights.items():
            if key in source_name:
                return weight
        return self.weights["default"]


class SourceIntelligenceProcessor:
    """
    信源情报解析引擎 (v2.1 - Robust) - 集成ImpactCalculator
    """
    def __init__(self):
        self.weight_library = SourceWeightLibrary()
        self.source_aggregator = SourceAggregator()
        self.impact_calculator = ImpactCalculator()

    def process(self, brand_name: str, ai_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理多平台AI文本数据流，生成信源情报图JSON
        """
        # 准备模型响应数据用于聚合
        model_responses = []
        for resp in ai_responses:
            if not resp.get('success'):
                continue
            
            # 提取模型名称，如果不存在则使用默认值
            model_name = resp.get('aiModel', resp.get('model', 'default'))
            
            # 提取问题，如果存在的话
            question = resp.get('question', '')
            
            # 提取响应文本
            text = resp.get('response', '')
            
            # 提取引用信息，如果存在的话
            citations = resp.get('citations', [])
            
            model_responses.append({
                'model_name': model_name,
                'ai_response': text,
                'citations': citations,
                'question': question
            })

        # 使用增强的SourceAggregator聚合多模型数据
        aggregation_result = self.source_aggregator.aggregate_multiple_models(model_responses)
        
        # 提取聚合后的信源池
        source_pool = aggregation_result['source_pool']
        
        # 为每个信源计算影响力指数
        enhanced_source_pool = []
        for source in source_pool:
            # 估算情感偏向得分（这里使用简化的计算方式）
            # 实际应用中可能需要更复杂的情感分析
            sentiment_score = self._estimate_sentiment_for_source(source, ai_responses)
            
            # 计算影响力指数
            impact_index = self.impact_calculator.calculate_impact_index(
                citation_count=source['citation_count'],
                model_coverage=source['cross_model_coverage'],
                sentiment_score=sentiment_score,
                domain_authority=source['domain_authority']
            )
            
            # 添加影响力指数到信源数据
            enhanced_source = source.copy()
            enhanced_source['impact_index'] = impact_index
            enhanced_source_pool.append(enhanced_source)

        # 构建节点和链接数据
        nodes = [{'id': brand_name, 'name': brand_name, 'level': 0, 'symbolSize': 60, 'category': 'brand'}]
        links = []

        for source in enhanced_source_pool:
            # 使用影响力指数作为节点大小的基础
            symbol_size = 30 + (source['impact_index'] / 100.0) * 50  # 映射到30-80的范围
            
            nodes.append({
                'id': source['id'],
                'name': source['site_name'],
                'level': 1,  # 所有信源都在同一层级
                'symbolSize': symbol_size,
                'category': 'source',
                'value': source['impact_index'],  # 使用影响力指数作为值
                'urls': [source['url']],  # 简化处理，只包含主要URL
                'cross_model_coverage': source['cross_model_coverage'],
                'citation_count': source['citation_count'],
                'impact_index': source['impact_index']
            })

            # 创建从品牌到信源的链接
            links.append({
                'source': brand_name,
                'target': source['id'],
                'contribution_score': source['citation_count'] / max(len(ai_responses), 1),  # 标准化贡献度
                'sentiment_bias': self._estimate_sentiment_for_source(source, ai_responses)  # 估算情感偏向
            })

        return {'nodes': nodes, 'links': links}

    def _estimate_sentiment_for_source(self, source: Dict, ai_responses: List[Dict[str, Any]]) -> float:
        """
        估算特定信源的情感偏向得分
        
        Args:
            source: 信源信息
            ai_responses: AI响应列表
            
        Returns:
            情感偏向得分 (-1.0 到 1.0)
        """
        # 简化的实现：基于信源在AI响应中出现的上下文进行情感分析
        # 这里我们只是简单地返回一个固定值，实际实现中应该进行情感分析
        return 0.1  # 返回一个小的正向情感值作为示例


def test_integration():
    """测试SourceIntelligenceProcessor与ImpactCalculator的集成"""
    print("SourceIntelligenceProcessor与ImpactCalculator集成测试:")

    # 创建处理器实例
    processor = SourceIntelligenceProcessor()

    # 准备测试数据
    ai_responses = [
        {
            'success': True,
            'aiModel': 'qwen',
            'question': '德施曼智能锁怎么样？',
            'response': '德施曼智能锁技术先进，可以参考知乎上的评测[1]。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'response_time': 1.2
        },
        {
            'success': True,
            'aiModel': 'doubao',
            'question': '小米智能锁怎么样？',
            'response': '小米智能锁性价比高，在淘宝上销量很好[1]。',
            'citations': [{'url': 'https://taobao.com/product/456', 'title': '小米智能锁销售页面'}],
            'response_time': 1.5
        },
        {
            'success': True,
            'aiModel': 'deepseek',
            'question': '智能锁品牌对比',
            'response': '知乎上有很多关于智能锁的评测文章[1]，包括德施曼和小米。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'response_time': 1.8
        }
    ]

    # 处理数据
    result = processor.process('德施曼', ai_responses)

    print(f"处理结果 - 节点数量: {len(result['nodes'])}, 链接数量: {len(result['links'])}")

    # 检查品牌节点
    brand_node = result['nodes'][0]
    print(f"品牌节点: {brand_node['name']} (ID: {brand_node['id']})")

    # 检查信源节点
    source_nodes = [node for node in result['nodes'][1:] if node['category'] == 'source']
    print(f"信源节点数量: {len(source_nodes)}")

    for node in source_nodes:
        print(f"  - 站点: {node['name']}")
        print(f"    跨模型覆盖度: {node.get('cross_model_coverage', 'N/A')}")
        print(f"    引用次数: {node.get('citation_count', 'N/A')}")
        print(f"    影响力指数: {node.get('impact_index', 'N/A'):.2f}")
        print(f"    节点大小: {node['symbolSize']:.2f}")
        print()

    # 特别关注知乎链接，它应该被两个模型引用（qwen和deepseek）
    zhihu_nodes = [node for node in source_nodes if 'zhihu' in node['name'].lower()]
    if zhihu_nodes:
        zhihu_node = zhihu_nodes[0]
        print(f"知乎链接分析:")
        print(f"  - 跨模型覆盖度: {zhihu_node.get('cross_model_coverage')} (应该是2，因为qwen和deepseek都引用了)")
        print(f"  - 引用次数: {zhihu_node.get('citation_count')} (应该是2)")
        print(f"  - 影响力指数: {zhihu_node.get('impact_index'):.2f}")
        print(f"  - 节点大小: {zhihu_node['symbolSize']:.2f}")

    # 测试ImpactCalculator直接功能
    print("\nImpactCalculator独立功能测试:")
    calc = ImpactCalculator()
    
    # 测试高引用、高覆盖、正面情感的情况
    high_impact = calc.calculate_impact_index(
        citation_count=10,
        model_coverage=5,
        sentiment_score=0.8,
        domain_authority='High'
    )
    print(f"高影响力场景: {high_impact:.2f}")
    
    # 测试低引用、低覆盖、负面情感的情况
    low_impact = calc.calculate_impact_index(
        citation_count=1,
        model_coverage=1,
        sentiment_score=-0.5,
        domain_authority='Low'
    )
    print(f"低影响力场景: {low_impact:.2f}")
    
    # 测试中等引用、中等覆盖、中性情感的情况
    mid_impact = calc.calculate_impact_index(
        citation_count=5,
        model_coverage=3,
        sentiment_score=0.0,
        domain_authority='Medium'
    )
    print(f"中等影响力场景: {mid_impact:.2f}")


if __name__ == "__main__":
    test_integration()