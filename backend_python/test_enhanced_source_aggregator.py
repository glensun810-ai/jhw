"""
测试增强版SourceAggregator的测试文件
"""
import sys
import os
import re
import urllib.parse
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 直接复制增强版SourceAggregator代码 to avoid import issues
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


def test_enhanced_source_aggregator():
    """测试增强版SourceAggregator"""
    aggregator = SourceAggregator()

    print("增强版SourceAggregator测试结果:")

    # 测试单个模型的聚合
    sample_response = """
    德施曼的智能锁技术确实不错，可以参考知乎上的评测[1]。
    但小米的性价比更高，这一点在很多电商平台上都有体现[2]。
    凯迪仕在工程渠道有一定优势，可查看其官网介绍[3]。
    不过需要注意，某些小品牌可能存在安全隐患[4]。
    """

    sample_citations = [
        {"id": "1", "url": "https://zhihu.com/article/123", "title": "智能锁品牌对比评测"},
        {"id": "2", "url": "https://taobao.com/product/456", "title": "小米智能锁销售页面"},
        {"id": "3", "url": "https://kedixi.com/about", "title": "凯迪仕官方介绍"},
        {"id": "4", "url": "https://security-report.com/789", "title": "小品牌安全风险报告"}
    ]

    result = aggregator.aggregate(sample_response, sample_citations, model_name="qwen")
    
    print(f"单模型聚合结果 - 信源数量: {len(result['source_pool'])}")
    for source in result['source_pool']:
        print(f"  - URL: {source['url'][:30]}..., 引用次数: {source['citation_count']}, "
              f"跨模型覆盖度: {source['cross_model_coverage']}, 权威度: {source['domain_authority']}")

    # 测试多模型聚合
    model_responses = [
        {
            'model_name': 'qwen',
            'ai_response': '德施曼智能锁在知乎上有很好的评测[1]，技术先进。',
            'citations': [{"id": "1", "url": "https://zhihu.com/article/123", "title": "智能锁品牌对比评测"}],
            'question': '德施曼智能锁怎么样？'
        },
        {
            'model_name': 'doubao',
            'ai_response': '小米智能锁性价比高，在淘宝上销量很好[1]。',
            'citations': [{"id": "1", "url": "https://taobao.com/product/456", "title": "小米智能锁销售页面"}],
            'question': '小米智能锁怎么样？'
        },
        {
            'model_name': 'deepseek',
            'ai_response': '知乎上有很多关于智能锁的评测文章[1]，包括德施曼和小米。',
            'citations': [{"id": "1", "url": "https://zhihu.com/article/123", "title": "智能锁品牌对比评测"}],
            'question': '智能锁品牌对比'
        }
    ]

    multi_result = aggregator.aggregate_multiple_models(model_responses)
    
    print(f"\n多模型聚合结果 - 信源数量: {len(multi_result['source_pool'])}")
    for source in multi_result['source_pool']:
        print(f"  - URL: {source['url'][:30]}..., 引用次数: {source['citation_count']}, "
              f"跨模型覆盖度: {source['cross_model_coverage']}, 权威度: {source['domain_authority']}, "
              f"引用问题数: {source.get('question_reference_count', 0)}")

    # 特别关注知乎链接的跨模型覆盖度
    zhihu_sources = [s for s in multi_result['source_pool'] if 'zhihu' in s['url']]
    if zhihu_sources:
        zhihu_source = zhihu_sources[0]
        print(f"\n知乎链接分析:")
        print(f"  - URL: {zhihu_source['url']}")
        print(f"  - 引用次数: {zhihu_source['citation_count']}")
        print(f"  - 跨模型覆盖度: {zhihu_source['cross_model_coverage']} (应为2，因为qwen和deepseek都引用了)")
        print(f"  - 权威度: {zhihu_source['domain_authority']}")
        print(f"  - 引用问题数: {zhihu_source.get('question_reference_count', 0)}")


if __name__ == "__main__":
    test_enhanced_source_aggregator()