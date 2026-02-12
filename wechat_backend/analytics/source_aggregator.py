"""
信源穿透与引用聚合引擎 - 从AI回复中提取URL、引用排行和证据链关联
"""
import re
import urllib.parse
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict


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

    
    def aggregate(self, ai_response: str, citations: Optional[List[Dict]] = None) -> Dict:
        """
        聚合信源信息，提取URL、生成引用排行并建立证据链

        Args:
            ai_response: AI原始回复文本
            citations: AI返回的引用信息列表（可选）

        Returns:
            符合source_intelligence结构的字典
        """
        # 1. 提取所有URL
        extracted_urls = self._extract_urls(ai_response, citations)

        # 2. 生成信源池和引用排行
        source_pool, citation_rank = self._generate_source_statistics(extracted_urls)

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
    
    def _generate_source_statistics(self, urls: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        生成信源统计数据和引用排行
        
        Args:
            urls: URL列表
            
        Returns:
            (source_pool, citation_rank) 元组
        """
        # 统计每个URL的出现次数
        url_counter = Counter()
        site_counter = Counter()
        
        for url_info in urls:
            normalized_url = url_info['url']
            url_counter[normalized_url] += 1
            site_counter[url_info['site_name']] += 1
        
        # 生成信源池
        source_pool = []
        seen_urls = set()
        for url_info in urls:
            normalized_url = url_info['url']
            if normalized_url in seen_urls:
                continue  # 避免重复添加

            citation_count = url_counter[normalized_url]
            site_name = url_info['site_name']
            domain_authority = self._assess_domain_authority(site_name)

            source_pool.append({
                'id': self._generate_url_id(normalized_url),  # 生成唯一ID
                'url': normalized_url,
                'site_name': site_name,
                'citation_count': citation_count,
                'domain_authority': domain_authority
            })
            seen_urls.add(normalized_url)
        
        # 按引用次数降序排列
        source_pool.sort(key=lambda x: x['citation_count'], reverse=True)

        # 生成引用排行（仅包含ID）
        citation_rank = [item['id'] for item in source_pool]

        return source_pool, citation_rank

    def associate_evidence_chain(self, ai_response: str, source_pool: List[Dict], negative_fragments: List[str]) -> List[Dict]:
        """
        将负面语料片段与相关URL建立证据链关联

        Args:
            ai_response: AI回复文本
            source_pool: 信源池
            negative_fragments: 负面语料片段列表

        Returns:
            证据链关联结果列表
        """
        evidence_chains = []

        for fragment in negative_fragments:
            # 尝试将负面片段与信源关联
            associated_source = self._find_associated_source(fragment, ai_response, source_pool)

            if associated_source:
                # 确定风险等级
                risk_level = self._determine_risk_level(fragment)

                evidence_chains.append({
                    'negative_fragment': fragment,
                    'associated_url': associated_source['url'],
                    'source_name': associated_source['site_name'],
                    'risk_level': risk_level,
                    'citation_count': associated_source['citation_count'],
                    'domain_authority': associated_source['domain_authority']
                })

        return evidence_chains

    def _find_associated_source(self, fragment: str, ai_response: str, source_pool: List[Dict]) -> Optional[Dict]:
        """
        为负面片段寻找相关联的信源

        Args:
            fragment: 负面语料片段
            ai_response: AI回复文本
            source_pool: 信源池

        Returns:
            相关联的信源信息（如果找到）
        """
        # 首先尝试通过引用标记关联（如[1]、[2]等）
        citation_matches = self.citation_pattern.findall(fragment)
        if citation_matches:
            # 如果片段中包含引用标记，尝试找到对应的信源
            for citation_num in citation_matches:
                for source in source_pool:
                    # 检查URL或站点名是否与引用有关联
                    if citation_num in source['id'] or citation_num in source['url']:
                        return source

        # 如果没有通过引用标记找到，尝试通过内容相似性关联
        # 提取片段中的关键词
        keywords = self._extract_keywords(fragment)

        # 检查信源的站点名或URL是否包含关键词
        for keyword in keywords:
            for source in source_pool:
                if keyword.lower() in source['site_name'].lower() or keyword.lower() in source['url'].lower():
                    return source

        # 如果仍然没有找到，返回引用次数最多的信源作为默认关联
        if source_pool:
            return max(source_pool, key=lambda x: x['citation_count'])

        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        # 简单的关键词提取：查找中文词组和品牌相关词汇
        # 在实际应用中，可能需要使用NLP技术进行更精确的关键词提取
        import re

        # 提取中文词汇（2-4个字符的词组）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)

        # 提取可能的品牌相关词汇
        brand_indicators = ['品牌', '产品', '公司', '服务', '质量', '安全', '性能', '功能', '技术', '设计', '外观', '材料', '工艺', '创新', '安全', '可靠', '稳定', '耐用', '易用', '便捷', '智能', '高效', '节能', '环保', '健康', '舒适', '美观', '时尚', '潮流', '经典', '独特', '个性', '定制', '专业']

        # 过滤掉通用词汇，保留可能的特定关键词
        specific_keywords = [word for word in chinese_words if word not in brand_indicators]

        return specific_keywords

    def _determine_risk_level(self, fragment: str) -> str:
        """
        确定负面片段的风险等级

        Args:
            fragment: 负面语料片段

        Returns:
            风险等级（High/Medium/Low）
        """
        # 根据负面词汇的严重程度确定风险等级
        high_risk_keywords = ['泄露', '隐私', '安全漏洞', '欺诈', '虚假', '违法', '犯罪', '倒闭', '破产', '质量问题', '安全隐患', '召回', '投诉', '差评', '负面新闻', '丑闻', '违规', '处罚', '诉讼', '赔偿', '风险', '缺陷', '故障', '损坏', '失效', '不良反应', '危险', '有害', '污染', '有毒', '致癌', '致病', '致死', '爆炸', '燃烧', '漏电', '辐射', '感染', '传染', '病毒', '恶意', '攻击', '黑客', '盗用', '窃取', '篡改', '伪造', '假冒', '劣质', '残次', '不合格', '不达标', '超标', '违规', '违法', '侵权', '违约', '失职', '失误', '错误', '缺陷', '漏洞', '瑕疵', '问题', '麻烦', '困扰', '障碍', '困难', '挑战', '威胁', '危害', '损害', '伤害', '损失', '亏损', '贬值', '贬值', '贬值', '贬值']
        medium_risk_keywords = ['不好', '较差', '一般', '缺点', '不足', '问题', '风险', '隐患', '缺陷', '故障', '不稳定', '不耐用', '不实用', '不美观', '不舒适', '不环保', '不健康', '不安全', '不靠谱', '不推荐', '慎用', '注意', '小心', '警惕', '谨慎', '担忧', '担心', '疑虑', '质疑', '批评', '指责', '抱怨', '不满', '失望', '糟糕', '差劲', '垃圾', '烂', '坑', '骗', '套路', '陷阱', '忽悠', '夸大', '虚假', '误导', '偏见', '歧视', '争议', '纠纷', '矛盾', '冲突', '对立', '敌对', '攻击', '贬低', '诋毁', '诽谤', '造谣', '传谣', '谣言', '假消息', '假新闻', '假信息', '假货', '仿冒', '山寨', '抄袭', '剽窃', '侵权', '盗版', '非法', '违法', '违规', '不当', '不合适', '不宜', '有害', '不利', '负面影响', '消极影响', '不良影响', '负面作用', '副作用', '毒副作用', '过敏反应', '刺激性', '腐蚀性', '毒性', '放射性', '危险性', '风险性', '不确定性', '不稳定性', '不可靠性', '不安全性', '不实用性', '不美观性', '不舒适性', '不环保性', '不健康性', '不经济性', '不划算', '不值得', '不推荐', '不建议', '不适宜', '不适合', '不匹配', '不兼容', '不协调', '不和谐', '不统一', '不一致', '不连贯', '不流畅', '不顺畅', '不顺手', '不顺心', '不顺意', '不顺遂', '不顺当', '不顺利', '不顺手', '不顺眼', '不顺耳', '不顺口', '不顺心', '不顺意', '不顺遂', '不顺当', '不顺利']
        low_risk_keywords = ['小问题', '不太', '稍微', '略显', '有些', '不够', '有待提高', '有待改进', '有待完善', '略有不足', '稍有缺陷', '微小问题', '轻微问题', '小毛病', '小瑕疵', '小缺陷', '小问题', '小毛病', '小瑕疵', '小缺陷', '小问题', '小毛病', '小瑕疵', '小缺陷']

        fragment_lower = fragment.lower()

        # 检查高风险关键词
        for keyword in high_risk_keywords:
            if keyword in fragment_lower:
                return 'High'

        # 检查中等风险关键词
        for keyword in medium_risk_keywords:
            if keyword in fragment_lower:
                return 'Medium'

        # 检查低风险关键词
        for keyword in low_risk_keywords:
            if keyword in fragment_lower:
                return 'Low'

        # 默认返回中等风险
        return 'Medium'
    
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
    
    def associate_negative_fragments(self, ai_response: str, citations: Optional[List[Dict]] = None, 
                                     negative_fragments: List[str] = None) -> List[Dict]:
        """
        将负面语料片段与相关URL建立证据链关联
        
        Args:
            ai_response: AI回复文本
            citations: 引用信息列表
            negative_fragments: 负面语料片段列表
            
        Returns:
            证据链关联结果列表
        """
        if not negative_fragments:
            return []
        
        evidence_chain = []
        
        # 为每个负面片段寻找相关联的URL
        for fragment in negative_fragments:
            associated_url = self._find_associated_url(fragment, ai_response, citations)
            
            if associated_url:
                # 确定风险等级
                risk_level = self._determine_risk_level(fragment)
                
                # 提取信源名称
                source_name = self._extract_site_name(associated_url)
                
                evidence_chain.append({
                    'negative_fragment': fragment,
                    'associated_url': associated_url,
                    'source_name': source_name,
                    'risk_level': risk_level
                })
        
        return evidence_chain
    
    def _find_associated_url(self, fragment: str, ai_response: str, citations: Optional[List[Dict]] = None) -> Optional[str]:
        """
        为负面片段寻找相关联的URL
        
        Args:
            fragment: 负面语料片段
            ai_response: AI回复文本
            citations: 引用信息列表
            
        Returns:
            相关联的URL（如果找到）
        """
        # 如果有引用信息，尝试通过引用索引关联
        if citations:
            # 查找片段中是否包含引用标记（如[1]、[2]等）
            citation_matches = self.citation_pattern.findall(fragment)
            if citation_matches:
                for citation_num in citation_matches:
                    try:
                        idx = int(citation_num) - 1  # 引用索引从1开始
                        if 0 <= idx < len(citations) and 'url' in citations[idx]:
                            return citations[idx]['url']
                    except (ValueError, IndexError):
                        continue
        
        # 如果没有通过引用索引找到，尝试通过关键词匹配
        # 提取片段中的关键词（品牌名、产品名等）
        keywords = self._extract_keywords(fragment)
        
        # 在AI回复中查找包含关键词的引用标记
        for keyword in keywords:
            # 查找关键词附近的引用标记
            pattern = rf'{re.escape(keyword)}[^.!?]*?(\[\d+\])'
            matches = re.findall(pattern, ai_response)
            for match in matches:
                citation_num = match.strip('[]')
                try:
                    idx = int(citation_num) - 1
                    if 0 <= idx < len(citations) and 'url' in citations[idx]:
                        return citations[idx]['url']
                except (ValueError, IndexError):
                    continue
        
        # 如果仍然没有找到，返回第一个可用的URL（如果没有引用信息，返回None）
        if citations:
            for citation in citations:
                if 'url' in citation:
                    return citation['url']
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        # 简单的关键词提取：查找中文词组
        # 在实际应用中，可能需要使用NLP技术进行更精确的关键词提取
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        return chinese_words
    
    def _determine_risk_level(self, fragment: str) -> str:
        """
        确定负面片段的风险等级
        
        Args:
            fragment: 负面语料片段
            
        Returns:
            风险等级（High/Medium/Low）
        """
        # 根据负面词汇的严重程度确定风险等级
        high_risk_keywords = ['泄露', '隐私', '安全漏洞', '欺诈', '虚假', '违法', '犯罪', '倒闭', '破产', '质量问题', '安全隐患', '召回', '投诉', '差评']
        medium_risk_keywords = ['不好', '较差', '一般', '缺点', '不足', '问题', '风险', '隐患', '缺陷', '故障']
        low_risk_keywords = ['小问题', '不太', '稍微', '略显', '有些', '不够', '有待提高']
        
        fragment_lower = fragment.lower()
        
        for keyword in high_risk_keywords:
            if keyword in fragment_lower:
                return 'High'
        
        for keyword in medium_risk_keywords:
            if keyword in fragment_lower:
                return 'Medium'
        
        for keyword in low_risk_keywords:
            if keyword in fragment_lower:
                return 'Low'
        
        # 默认返回中等风险
        return 'Medium'


# 示例使用
if __name__ == "__main__":
    aggregator = SourceAggregator()
    
    # 示例AI回复
    sample_response = """
    德施曼的智能锁技术确实不错，可以参考知乎上的评测[1]。
    但小米的性价比更高，这一点在很多电商平台上都有体现[2]。
    凯迪仕在工程渠道有一定优势，可查看其官网介绍[3]。
    不过需要注意，某些小品牌可能存在安全隐患[4]。
    """
    
    # 示例引用信息
    sample_citations = [
        {"id": "1", "url": "https://zhihu.com/article/123", "title": "智能锁品牌对比评测"},
        {"id": "2", "url": "https://taobao.com/product/456", "title": "小米智能锁销售页面"},
        {"id": "3", "url": "https://kedixi.com/about", "title": "凯迪仕官方介绍"},
        {"id": "4", "url": "https://security-report.com/789", "title": "小品牌安全风险报告"}
    ]
    
    # 执行聚合
    result = aggregator.aggregate(sample_response, sample_citations)
    
    print("信源池:", result['source_pool'])
    print("引用排行:", result['citation_rank'])
    
    # 示例负面片段
    negative_fragments = ["某些小品牌可能存在安全隐患[4]"]
    
    # 建立证据链关联
    evidence_chain = aggregator.associate_negative_fragments(sample_response, sample_citations, negative_fragments)
    
    print("证据链:", evidence_chain)