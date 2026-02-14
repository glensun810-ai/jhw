"""
信源情报分析器 - 从AI响应中提取和分析URL引用
"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import logging


class SourceAnalyzer:
    """
    信源提取器 - 从AI返回的raw_response文本中提取URL并进行分类
    """
    
    def __init__(self):
        # 定义域名分类规则
        self.domain_categories = {
            'social': [
                'zhihu.com', 'weibo.com', 'tieba.baidu.com', 'doubao.com', 
                'xiaohongshu.com', 'bilibili.com', 'douyin.com', 'kuaishou.com'
            ],
            'official': [
                'gov.cn', 'edu.cn', 'org.cn', 'com.cn', 'net.cn', 'gov.', 'edu.', 'org.'
            ],
            'news': [
                'news.cn', 'people.com.cn', 'xinhuanet.com', 'gmw.cn', 
                'cctv.com', 'chinanews.com', 'huanqiu.com', 'thepaper.cn'
            ],
            'tech': [
                'csdn.net', 'jianshu.com', 'segmentfault.com', 'oschina.net',
                'github.com', 'stackoverflow.com', 'iteye.com', 'infoq.cn'
            ],
            'business': [
                '36kr.com', 'zhihu.com', 'linkedin.com', 'ycombinator.com',
                'bloomberg.com', 'wsj.com', 'ft.com', 'forbes.com'
            ],
            'finance': [
                'eastmoney.com', 'hexun.com', 'sina.com.cn', 'qq.com',
                'bloomberg.com', 'reuters.com', 'marketwatch.com'
            ]
        }
        
        # 编译URL提取的正则表达式
        self.url_patterns = [
            # 匹配 [数字] URL 格式
            re.compile(r'\[\d+\]\s*(https?://[^\s\)<>\[\]]+)'),
            # 匹配 (URL) 格式
            re.compile(r'\((https?://[^\s\)<>\[\]]+)\)'),
            # 匹配直接的URL
            re.compile(r'https?://[^\s\)<>\[\]]+'),
            # 匹配 markdown 链接格式 [text](URL)
            re.compile(r'\[([^\]]*)\]\((https?://[^\s\)<>\[\]]+)\)')
        ]
        
        # 设置日志
        self.logger = logging.getLogger(__name__)

    def extract_urls(self, text: str) -> List[str]:
        """
        从文本中提取所有URL
        
        Args:
            text: 要分析的文本
            
        Returns:
            提取出的URL列表
        """
        urls = set()  # 使用set避免重复
        
        for pattern in self.url_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # 如果是元组（如markdown链接），第二个元素是URL
                    url = match[1] if len(match) > 1 else match[0]
                else:
                    url = match
                urls.add(url.strip())
        
        # 过滤无效URL
        valid_urls = []
        for url in urls:
            if self._is_valid_url(url):
                valid_urls.append(url)
        
        # 记录提取到的URL
        if valid_urls:
            self.logger.info(f"[SourceAnalyzer] Extracted URLs: {valid_urls}")
        
        return valid_urls

    def _is_valid_url(self, url: str) -> bool:
        """
        验证URL是否有效
        
        Args:
            url: 要验证的URL
            
        Returns:
            是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def classify_source(self, url: str) -> Dict[str, Any]:
        """
        对URL来源进行分类
        
        Args:
            url: 要分类的URL
            
        Returns:
            包含分类信息的字典
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # 检查域名分类
            category = 'other'
            for cat, domains in self.domain_categories.items():
                for dom in domains:
                    if dom in domain:
                        category = cat
                        break
                if category != 'other':
                    break
            
            # 判断权威性
            is_authoritative = any(auth_dom in domain for auth_dom in self.domain_categories['official'])
            
            return {
                'url': url,
                'domain': domain,
                'category': category,
                'is_authoritative': is_authoritative,
                'title': self._extract_title_from_url(url),  # 简单提取标题
                'confidence': self._calculate_confidence(url, category)
            }
        except Exception as e:
            self.logger.error(f"Error classifying source {url}: {str(e)}")
            return {
                'url': url,
                'domain': '',
                'category': 'error',
                'is_authoritative': False,
                'title': 'Error processing URL',
                'confidence': 0.0
            }

    def _extract_title_from_url(self, url: str) -> str:
        """
        从URL中简单提取标题（实际应用中可能需要更复杂的逻辑）
        
        Args:
            url: URL
            
        Returns:
            提取的标题
        """
        # 简单实现：从URL路径中提取最后一段作为标题
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split('/') if part]
        if path_parts:
            title = path_parts[-1].replace('-', ' ').replace('_', ' ')
            return title[:50]  # 限制长度
        else:
            return parsed.netloc

    def _calculate_confidence(self, url: str, category: str) -> float:
        """
        计算信源可信度分数
        
        Args:
            url: URL
            category: 分类
            
        Returns:
            0-1之间的可信度分数
        """
        # 基于分类的可信度
        base_confidence = {
            'official': 0.9,
            'news': 0.8,
            'tech': 0.7,
            'business': 0.7,
            'finance': 0.7,
            'social': 0.5,
            'other': 0.4
        }.get(category, 0.4)
        
        # 检查URL结构
        parsed = urlparse(url)
        if parsed.fragment or 'utm_' in url or 'click' in url:
            # 可能是追踪链接，降低可信度
            base_confidence *= 0.8
        
        return round(base_confidence, 2)

    def analyze_sources(self, text: str) -> Dict[str, Any]:
        """
        分析文本中的信源信息
        
        Args:
            text: 要分析的文本
            
        Returns:
            分析结果
        """
        urls = self.extract_urls(text)
        
        sources = []
        category_distribution = {}
        
        for url in urls:
            source_info = self.classify_source(url)
            sources.append(source_info)
            
            # 统计分类分布
            cat = source_info['category']
            category_distribution[cat] = category_distribution.get(cat, 0) + 1
        
        return {
            'total_sources': len(sources),
            'sources': sources,
            'category_distribution': category_distribution,
            'authoritative_sources': [s for s in sources if s['is_authoritative']],
            'highest_confidence': max([s['confidence'] for s in sources], default=0.0) if sources else 0.0,
            'lowest_confidence': min([s['confidence'] for s in sources], default=0.0) if sources else 0.0
        }


# 简单测试函数
def test_source_analyzer():
    """
    测试信源分析器
    """
    analyzer = SourceAnalyzer()
    
    # 测试文本包含各种URL格式
    test_text = """
    根据知乎[1]和微博[2]上的讨论，以及官方发布的信息(gov.cn)，可以得出以下结论：
    [1] https://www.zhihu.com/question/123456
    [2] https://weibo.com/status/789012
    更多信息请参考：(https://www.example.com/info)
    官方网站：https://www.gov.cn/policies/new_policy.html
    技术分析：[详细技术报告](https://csdn.net/article/tech_report)
    """
    
    result = analyzer.analyze_sources(test_text)
    
    print("信源分析结果:")
    print(f"总信源数: {result['total_sources']}")
    print(f"分类分布: {result['category_distribution']}")
    print(f"权威信源数: {len(result['authoritative_sources'])}")
    print(f"最高可信度: {result['highest_confidence']}")
    print(f"最低可信度: {result['lowest_confidence']}")
    
    print("\n信源详情:")
    for i, source in enumerate(result['sources'], 1):
        print(f"{i}. {source['url']}")
        print(f"   域名: {source['domain']}")
        print(f"   分类: {source['category']}")
        print(f"   权威性: {source['is_authoritative']}")
        print(f"   可信度: {source['confidence']}")
        print()


if __name__ == "__main__":
    test_source_analyzer()