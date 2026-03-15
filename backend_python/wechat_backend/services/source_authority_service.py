"""
信源权威性评估服务

功能:
- 信源权威性评分（0-100）
- 信源类型分类（官方、媒体、用户、其他）
- 信源可信度可视化
- 信源引用频次统计

@author: 系统架构组
@date: 2026-03-14
@version: 1.0.0
"""

import re
import json
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

from wechat_backend.logging_config import api_logger


class SourceAuthorityEvaluator:
    """
    信源权威性评估器（P1-06 实现版 - 2026-03-14）
    
    功能:
    1. 信源权威性评分
    2. 信源类型分类
    3. 信源可信度可视化
    """
    
    # 权威域名列表（中国）
    AUTHORITY_DOMAINS = {
        'government': [  # 政府网站
            'gov.cn', 'gov', '12345.gov', 'people.com.cn',
            'xinhuanet.com', 'chinanews.com', 'cctv.com'
        ],
        'media': [  # 主流媒体
            'sina.com.cn', 'sohu.com', '163.com', 'qq.com',
            'ifeng.com', 'thepaper.cn', 'jiemian.com'
        ],
        'academic': [  # 学术机构
            'edu.cn', 'ac.cn', 'sciencedirect.com', 'ieee.org',
            'springer.com', 'nature.com', 'science.org'
        ],
        'platform': [  # 知名平台
            'zhihu.com', 'weibo.com', 'xiaohongshu.com',
            'douyin.com', 'bilibili.com', 'jd.com', 'tmall.com'
        ]
    }
    
    # 信源类型关键词
    SOURCE_TYPE_KEYWORDS = {
        'official': ['官方', '官网', '认证', '授权', '指定', '唯一'],
        'media': ['报道', '新闻', '记者', '媒体', '采访'],
        'user': ['体验', '分享', '使用', '个人', '网友', '用户'],
        'expert': ['专家', '教授', '博士', '研究员', '分析师']
    }
    
    def __init__(self):
        """初始化信源评估器"""
        # 信源缓存
        self.source_cache = {}
        
        api_logger.info("[SourceAuthority] 初始化完成")
    
    def evaluate(self, url: str, content: str = None, context: Dict = None) -> Dict[str, Any]:
        """
        评估单个信源的权威性
        
        参数:
            url: 信源 URL
            content: 信源内容（可选）
            context: 上下文信息（可选）
            
        返回:
            Dict: 评估结果
        """
        if not url:
            return self._create_empty_result()
        
        # 解析 URL
        parsed = self._parse_url(url)
        domain = parsed.get('domain', '')
        
        # 1. 域名权威性评分（0-40 分）
        domain_score = self._evaluate_domain(domain)
        
        # 2. 内容质量评分（0-30 分）
        content_score = self._evaluate_content(content) if content else 15
        
        # 3. 引用频次评分（0-20 分）
        citation_score = self._evaluate_citation(url, context)
        
        # 4. 时效性评分（0-10 分）
        freshness_score = self._evaluate_freshness(url, context)
        
        # 计算总分
        total_score = domain_score + content_score + citation_score + freshness_score
        
        # 确定信源类型
        source_type = self._classify_source_type(domain, content)
        
        # 确定权威性等级
        authority_level = self._get_authority_level(total_score)
        
        result = {
            'url': url,
            'domain': domain,
            'total_score': round(total_score, 2),
            'authority_level': authority_level,
            'source_type': source_type,
            'scores': {
                'domain': round(domain_score, 2),
                'content': round(content_score, 2),
                'citation': round(citation_score, 2),
                'freshness': round(freshness_score, 2)
            },
            'analysis_time': datetime.now().isoformat()
        }
        
        # 缓存结果
        self.source_cache[url] = result
        
        return result
    
    def evaluate_batch(self, sources: List[Dict]) -> Dict[str, Any]:
        """
        批量评估信源
        
        参数:
            sources: 信源列表，每个包含 url, content 等
            
        返回:
            Dict: 批量评估结果
        """
        if not sources:
            return {
                'summary': {},
                'sources': [],
                'distribution': {},
                'top_sources': []
            }
        
        results = []
        type_distribution = defaultdict(int)
        level_distribution = defaultdict(int)
        total_score = 0
        
        for source in sources:
            url = source.get('url', '')
            content = source.get('content', '')
            context = source.get('context', {})
            
            result = self.evaluate(url, content, context)
            result['citation_count'] = source.get('citation_count', 1)
            results.append(result)
            
            # 统计
            type_distribution[result['source_type']] += 1
            level_distribution[result['authority_level']] += 1
            total_score += result['total_score']
        
        # 计算平均分
        avg_score = total_score / len(results) if results else 0
        
        # 按权威性排序
        sorted_results = sorted(results, key=lambda x: x['total_score'], reverse=True)
        
        return {
            'summary': {
                'total_count': len(results),
                'average_score': round(avg_score, 2),
                'high_authority_count': level_distribution.get('high', 0),
                'medium_authority_count': level_distribution.get('medium', 0),
                'low_authority_count': level_distribution.get('low', 0)
            },
            'sources': results,
            'distribution': {
                'by_type': dict(type_distribution),
                'by_level': dict(level_distribution)
            },
            'top_sources': sorted_results[:5],
            'analysis_time': datetime.now().isoformat()
        }
    
    def evaluate_from_results(self, diagnosis_results: List[Dict]) -> Dict[str, Any]:
        """
        从诊断结果中提取并评估信源
        
        参数:
            diagnosis_results: 诊断结果列表
            
        返回:
            Dict: 信源评估结果
        """
        sources = self._extract_sources_from_results(diagnosis_results)
        return self.evaluate_batch(sources)
    
    def _parse_url(self, url: str) -> Dict[str, Any]:
        """解析 URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 移除 www.
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # 提取主域名
            parts = domain.split('.')
            if len(parts) >= 2:
                main_domain = '.'.join(parts[-2:])
            else:
                main_domain = domain
            
            return {
                'domain': domain,
                'main_domain': main_domain,
                'path': parsed.path,
                'scheme': parsed.scheme
            }
        except Exception as e:
            api_logger.debug(f"[SourceAuthority] 解析 URL 失败：{e}")
            return {'domain': '', 'main_domain': '', 'path': '', 'scheme': ''}
    
    def _evaluate_domain(self, domain: str) -> float:
        """
        评估域名权威性（0-40 分）
        """
        if not domain:
            return 0
        
        domain = domain.lower()
        
        # 检查权威域名
        for category, domains in self.AUTHORITY_DOMAINS.items():
            for auth_domain in domains:
                if auth_domain in domain:
                    if category == 'government':
                        return 40  # 政府网站最高
                    elif category == 'academic':
                        return 35  # 学术机构
                    elif category == 'media':
                        return 30  # 主流媒体
                    elif category == 'platform':
                        return 25  # 知名平台
        
        # 常见平台
        platform_score = {
            'zhihu.com': 25,
            'weibo.com': 20,
            'xiaohongshu.com': 20,
            'douyin.com': 20,
            'bilibili.com': 22,
            'jd.com': 25,
            'tmall.com': 25,
            'taobao.com': 20
        }
        
        for plat, score in platform_score.items():
            if plat in domain:
                return score
        
        # 未知域名
        return 10
    
    def _evaluate_content(self, content: str) -> float:
        """
        评估内容质量（0-30 分）
        """
        if not content:
            return 15  # 默认分
        
        score = 15  # 基础分
        
        # 内容长度评分（最多 +5 分）
        if len(content) > 500:
            score += 5
        elif len(content) > 200:
            score += 3
        elif len(content) > 100:
            score += 2
        
        # 包含数据/事实（最多 +5 分）
        if re.search(r'\d+%|\d+元|\d+人', content):
            score += 3
        if re.search(r'根据|数据显示|统计', content):
            score += 2
        
        # 包含引用/来源（最多 +5 分）
        if re.search(r'据.*报道|.*表示|.*指出', content):
            score += 3
        
        # 逻辑连贯性（最多 +2 分）
        if re.search(r'首先.*其次.*最后|因为.*所以|虽然.*但是', content):
            score += 2
        
        return min(30, score)
    
    def _evaluate_citation(self, url: str, context: Dict) -> float:
        """
        评估引用频次（0-20 分）
        """
        if not context:
            return 10  # 默认分
        
        citation_count = context.get('citation_count', 1)
        
        # 根据引用次数评分
        if citation_count >= 10:
            return 20
        elif citation_count >= 5:
            return 15
        elif citation_count >= 3:
            return 12
        elif citation_count >= 2:
            return 10
        else:
            return 5
    
    def _evaluate_freshness(self, url: str, context: Dict) -> float:
        """
        评估时效性（0-10 分）
        """
        if not context:
            return 5  # 默认分
        
        # 尝试从上下文获取时间
        publish_date = context.get('publish_date')
        
        if publish_date:
            try:
                from datetime import timedelta
                if isinstance(publish_date, str):
                    publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                
                days_old = (datetime.now() - publish_date).days
                
                if days_old <= 7:
                    return 10
                elif days_old <= 30:
                    return 8
                elif days_old <= 90:
                    return 6
                elif days_old <= 365:
                    return 4
                else:
                    return 2
            except:
                pass
        
        return 5
    
    def _classify_source_type(self, domain: str, content: str) -> str:
        """
        分类信源类型
        """
        # 基于域名分类
        for category, domains in self.AUTHORITY_DOMAINS.items():
            for auth_domain in domains:
                if auth_domain in domain:
                    if category == 'government':
                        return 'official'
                    elif category == 'media':
                        return 'media'
        
        # 基于内容分类
        if content:
            content_lower = content.lower()
            for source_type, keywords in self.SOURCE_TYPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in content_lower:
                        return source_type
        
        # 默认用户生成内容
        if any(p in domain for p in ['zhihu', 'weibo', 'xiaohongshu', 'douyin', 'bilibili']):
            return 'user'
        
        return 'other'
    
    def _get_authority_level(self, score: float) -> str:
        """
        获取权威性等级
        """
        if score >= 80:
            return 'high'
        elif score >= 60:
            return 'medium'
        else:
            return 'low'
    
    def _extract_sources_from_results(self, results: List[Dict]) -> List[Dict]:
        """从诊断结果中提取信源"""
        sources = []
        source_map = defaultdict(lambda: {'url': '', 'content': '', 'citation_count': 0})
        
        for result in results:
            response = result.get('response_content', '') or result.get('response', '')
            
            if not response:
                continue
            
            try:
                # 尝试解析 JSON 响应
                if isinstance(response, str) and response.strip().startswith('{'):
                    response_data = json.loads(response)
                    geo_data = response_data.get('geo_analysis', {})
                    cited_sources = geo_data.get('cited_sources', [])
                    
                    for source in cited_sources:
                        url = source.get('url', '')
                        if url:
                            source_map[url]['url'] = url
                            source_map[url]['content'] = source.get('site_name', '')
                            source_map[url]['citation_count'] += 1
            except:
                pass
        
        sources = list(source_map.values())
        return sources
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            'url': '',
            'domain': '',
            'total_score': 0,
            'authority_level': 'low',
            'source_type': 'other',
            'scores': {
                'domain': 0,
                'content': 0,
                'citation': 0,
                'freshness': 0
            },
            'analysis_time': datetime.now().isoformat()
        }


# 全局单例
_source_evaluator: Optional[SourceAuthorityEvaluator] = None


def get_source_authority_evaluator() -> SourceAuthorityEvaluator:
    """获取信源权威性评估器单例"""
    global _source_evaluator
    if _source_evaluator is None:
        _source_evaluator = SourceAuthorityEvaluator()
    return _source_evaluator
