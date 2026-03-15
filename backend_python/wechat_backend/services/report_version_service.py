"""
诊断报告版本管理服务

功能:
- 报告版本管理
- 同品牌多报告对比
- 版本差异高亮
- 趋势分析

@author: 系统架构组
@date: 2026-03-14
@version: 1.0.0
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from wechat_backend.logging_config import api_logger


class ReportVersionManager:
    """
    报告版本管理器（P1-07 实现版 - 2026-03-14）
    
    功能:
    1. 报告版本管理
    2. 同品牌多报告对比
    3. 版本差异高亮
    4. 趋势分析
    """
    
    def __init__(self):
        """初始化版本管理器"""
        # 版本缓存
        self.version_cache = {}
        
        api_logger.info("[ReportVersionManager] 初始化完成")
    
    def get_brand_reports(
        self,
        brand_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取某品牌的所有历史报告
        
        参数:
            brand_name: 品牌名称
            limit: 返回数量限制
            
        返回:
            List[Dict]: 报告列表
        """
        # 这里应该从数据库查询
        # 简化实现：返回缓存的版本信息
        return self.version_cache.get(brand_name, [])[:limit]
    
    def compare_reports(
        self,
        report_ids: List[str],
        reports: List[Dict]
    ) -> Dict[str, Any]:
        """
        对比多个报告
        
        参数:
            report_ids: 报告 ID 列表
            reports: 报告数据列表
            
        返回:
            Dict: 对比结果
        """
        if len(reports) < 2:
            return {
                'error': '至少需要 2 个报告进行对比',
                'comparison': None
            }
        
        # 基础信息对比
        base_comparison = self._compare_base_info(reports)
        
        # 品牌分布对比
        brand_comparison = self._compare_brand_distribution(reports)
        
        # 情感分析对比
        sentiment_comparison = self._compare_sentiment(reports)
        
        # 关键词对比
        keyword_comparison = self._compare_keywords(reports)
        
        # 差异高亮
        highlights = self._generate_highlights(reports)
        
        # 趋势分析
        trends = self._analyze_trends(reports)
        
        return {
            'report_count': len(reports),
            'report_ids': report_ids,
            'base_comparison': base_comparison,
            'brand_comparison': brand_comparison,
            'sentiment_comparison': sentiment_comparison,
            'keyword_comparison': keyword_comparison,
            'highlights': highlights,
            'trends': trends,
            'comparison_time': datetime.now().isoformat()
        }
    
    def get_version_diff(
        self,
        old_report: Dict,
        new_report: Dict
    ) -> Dict[str, Any]:
        """
        获取两个版本的差异
        
        参数:
            old_report: 旧版本报告
            new_report: 新版本报告
            
        返回:
            Dict: 差异结果
        """
        diff = {
            'rank_change': self._calculate_rank_change(old_report, new_report),
            'mention_change': self._calculate_mention_change(old_report, new_report),
            'sentiment_change': self._calculate_sentiment_change(old_report, new_report),
            'keyword_changes': self._calculate_keyword_changes(old_report, new_report),
            'new_sources': self._find_new_sources(old_report, new_report),
            'summary': self._generate_diff_summary(old_report, new_report)
        }
        
        return diff
    
    def _compare_base_info(self, reports: List[Dict]) -> Dict[str, Any]:
        """对比基础信息"""
        comparison = []
        
        for report in reports:
            comparison.append({
                'execution_id': report.get('execution_id', ''),
                'brand_name': report.get('brand_name', ''),
                'status': report.get('status', ''),
                'created_at': report.get('created_at', ''),
                'completed_at': report.get('completed_at', ''),
                'result_count': len(report.get('results', []))
            })
        
        return {
            'reports': comparison,
            'date_range': {
                'earliest': min(r['created_at'] for r in comparison) if comparison else '',
                'latest': max(r['created_at'] for r in comparison) if comparison else ''
            }
        }
    
    def _compare_brand_distribution(self, reports: List[Dict]) -> Dict[str, Any]:
        """对比品牌分布"""
        comparison = {}
        
        for i, report in enumerate(reports):
            brand_dist = report.get('brandDistribution', {})
            data = brand_dist.get('data', {})
            total = brand_dist.get('totalCount', 0)
            
            comparison[f'report_{i+1}'] = {
                'distribution': data,
                'total_count': total,
                'top_brand': max(data.items(), key=lambda x: x[1])[0] if data else ''
            }
        
        # 计算变化
        if len(reports) >= 2:
            comparison['changes'] = self._calculate_distribution_changes(
                reports[0].get('brandDistribution', {}),
                reports[-1].get('brandDistribution', {})
            )
        
        return comparison
    
    def _compare_sentiment(self, reports: List[Dict]) -> Dict[str, Any]:
        """对比情感分析"""
        comparison = {}
        
        for i, report in enumerate(reports):
            sentiment_dist = report.get('sentimentDistribution', {})
            data = sentiment_dist.get('data', {})
            
            comparison[f'report_{i+1}'] = {
                'distribution': data,
                'positive_rate': self._calculate_positive_rate(data)
            }
        
        # 计算变化
        if len(reports) >= 2:
            comparison['changes'] = {
                'positive_change': (
                    comparison[f'report_{len(reports)}']['positive_rate'] -
                    comparison['report_1']['positive_rate']
                )
            }
        
        return comparison
    
    def _compare_keywords(self, reports: List[Dict]) -> Dict[str, Any]:
        """对比关键词"""
        comparison = {}
        
        for i, report in enumerate(reports):
            keywords = report.get('keywords', [])
            
            # 提取关键词文本
            if keywords and isinstance(keywords[0], dict):
                kw_list = [kw.get('word', '') for kw in keywords[:10]]
            else:
                kw_list = [str(kw) for kw in keywords[:10]]
            
            comparison[f'report_{i+1}'] = {
                'keywords': kw_list,
                'count': len(keywords)
            }
        
        # 计算共有和独有关键词
        if len(reports) >= 2:
            all_keywords = [set(comparison[f'report_{i+1}']['keywords']) 
                          for i in range(len(reports))]
            
            comparison['common'] = list(set.intersection(*all_keywords))
            comparison['unique'] = {
                f'report_{i+1}': list(all_keywords[i] - set.union(*all_keywords[:i] + all_keywords[i+1:]))
                for i in range(len(reports))
            }
        
        return comparison
    
    def _generate_highlights(self, reports: List[Dict]) -> List[Dict]:
        """生成差异高亮"""
        highlights = []
        
        if len(reports) < 2:
            return highlights
        
        first = reports[0]
        last = reports[-1]
        
        # 排名变化高亮
        rank_change = self._calculate_rank_change(first, last)
        if abs(rank_change) > 0:
            highlights.append({
                'type': 'rank_change',
                'title': '排名变化',
                'description': f'排名 {"上升" if rank_change > 0 else "下降"}了 {abs(rank_change)} 位',
                'severity': 'high' if abs(rank_change) > 2 else 'medium',
                'value': rank_change
            })
        
        # 情感变化高亮
        sentiment_change = self._calculate_sentiment_change(first, last)
        if abs(sentiment_change) > 10:
            highlights.append({
                'type': 'sentiment_change',
                'title': '情感得分变化',
                'description': f'情感得分 {"提升" if sentiment_change > 0 else "下降"}了 {abs(sentiment_change)}%',
                'severity': 'high' if sentiment_change > 20 else 'medium',
                'value': sentiment_change
            })
        
        # 关键词变化高亮
        keyword_changes = self._calculate_keyword_changes(first, last)
        if keyword_changes['new'] or keyword_changes['lost']:
            highlights.append({
                'type': 'keyword_change',
                'title': '关键词变化',
                'description': f'新增 {len(keyword_changes["new"])} 个关键词，丢失 {len(keyword_changes["lost"])} 个关键词',
                'severity': 'medium',
                'new_keywords': keyword_changes['new'],
                'lost_keywords': keyword_changes['lost']
            })
        
        return highlights
    
    def _analyze_trends(self, reports: List[Dict]) -> Dict[str, Any]:
        """分析趋势"""
        if not reports:
            return {}
        
        # 按时间排序
        sorted_reports = sorted(
            reports,
            key=lambda x: x.get('created_at', '')
        )
        
        trends = {
            'rank_trend': [],
            'mention_trend': [],
            'sentiment_trend': []
        }
        
        for report in sorted_reports:
            # 排名趋势
            brand_dist = report.get('brandDistribution', {})
            data = brand_dist.get('data', {})
            total = brand_dist.get('totalCount', 0)
            
            trends['rank_trend'].append({
                'date': report.get('created_at', '')[:10],
                'value': total
            })
            
            # 情感趋势
            sentiment = report.get('sentimentDistribution', {})
            positive_rate = self._calculate_positive_rate(sentiment.get('data', {}))
            
            trends['sentiment_trend'].append({
                'date': report.get('created_at', '')[:10],
                'value': positive_rate
            })
        
        # 计算趋势方向
        if len(trends['rank_trend']) >= 2:
            first = trends['rank_trend'][0]['value']
            last = trends['rank_trend'][-1]['value']
            trends['rank_direction'] = 'up' if last > first else ('down' if last < first else 'stable')
        
        if len(trends['sentiment_trend']) >= 2:
            first = trends['sentiment_trend'][0]['value']
            last = trends['sentiment_trend'][-1]['value']
            trends['sentiment_direction'] = 'up' if last > first else ('down' if last < first else 'stable')
        
        return trends
    
    def _calculate_rank_change(self, old_report: Dict, new_report: Dict) -> int:
        """计算排名变化"""
        old_dist = old_report.get('brandDistribution', {})
        new_dist = new_report.get('brandDistribution', {})
        
        old_total = old_dist.get('totalCount', 0)
        new_total = new_dist.get('totalCount', 0)
        
        # 简化：用提及总数代表排名
        return new_total - old_total
    
    def _calculate_mention_change(self, old_report: Dict, new_report: Dict) -> Dict:
        """计算提及变化"""
        old_dist = old_report.get('brandDistribution', {})
        new_dist = new_report.get('brandDistribution', {})
        
        old_data = old_dist.get('data', {})
        new_data = new_dist.get('data', {})
        
        changes = {}
        all_brands = set(old_data.keys()) | set(new_data.keys())
        
        for brand in all_brands:
            old_count = old_data.get(brand, 0)
            new_count = new_data.get(brand, 0)
            change = new_count - old_count
            change_rate = (change / old_count * 100) if old_count > 0 else 0
            
            changes[brand] = {
                'old': old_count,
                'new': new_count,
                'change': change,
                'change_rate': round(change_rate, 2)
            }
        
        return changes
    
    def _calculate_sentiment_change(self, old_report: Dict, new_report: Dict) -> float:
        """计算情感变化"""
        old_sentiment = old_report.get('sentimentDistribution', {})
        new_sentiment = new_report.get('sentimentDistribution', {})
        
        old_rate = self._calculate_positive_rate(old_sentiment.get('data', {}))
        new_rate = self._calculate_positive_rate(new_sentiment.get('data', {}))
        
        return round(new_rate - old_rate, 2)
    
    def _calculate_keyword_changes(
        self,
        old_report: Dict,
        new_report: Dict
    ) -> Dict[str, List]:
        """计算关键词变化"""
        old_keywords = old_report.get('keywords', [])
        new_keywords = new_report.get('keywords', [])
        
        # 提取关键词文本
        if old_keywords and isinstance(old_keywords[0], dict):
            old_set = set(kw.get('word', '') for kw in old_keywords)
        else:
            old_set = set(str(kw) for kw in old_keywords)
        
        if new_keywords and isinstance(new_keywords[0], dict):
            new_set = set(kw.get('word', '') for kw in new_keywords)
        else:
            new_set = set(str(kw) for kw in new_keywords)
        
        return {
            'new': list(new_set - old_set),
            'lost': list(old_set - new_set),
            'common': list(old_set & new_set)
        }
    
    def _find_new_sources(
        self,
        old_report: Dict,
        new_report: Dict
    ) -> List[Dict]:
        """查找新增信源"""
        # 简化实现
        return []
    
    def _generate_diff_summary(
        self,
        old_report: Dict,
        new_report: Dict
    ) -> str:
        """生成差异摘要"""
        rank_change = self._calculate_rank_change(old_report, new_report)
        sentiment_change = self._calculate_sentiment_change(old_report, new_report)
        
        summary_parts = []
        
        if rank_change > 0:
            summary_parts.append(f'排名上升{rank_change}位')
        elif rank_change < 0:
            summary_parts.append(f'排名下降{abs(rank_change)}位')
        
        if sentiment_change > 5:
            summary_parts.append(f'情感得分提升{sentiment_change}%')
        elif sentiment_change < -5:
            summary_parts.append(f'情感得分下降{abs(sentiment_change)}%')
        
        return '，'.join(summary_parts) if summary_parts else '无明显变化'
    
    def _calculate_distribution_changes(
        self,
        old_dist: Dict,
        new_dist: Dict
    ) -> Dict:
        """计算分布变化"""
        old_data = old_dist.get('data', {})
        new_data = new_dist.get('data', {})
        
        changes = {}
        all_brands = set(old_data.keys()) | set(new_data.keys())
        
        for brand in all_brands:
            old_count = old_data.get(brand, 0)
            new_count = new_data.get(brand, 0)
            change = new_count - old_count
            
            changes[brand] = {
                'change': change,
                'change_rate': round((change / old_count * 100) if old_count > 0 else 0, 2)
            }
        
        return changes
    
    def _calculate_positive_rate(self, sentiment_data: Dict) -> float:
        """计算正面情感比例"""
        if not sentiment_data:
            return 0.0
        
        total = sum(sentiment_data.values())
        if total == 0:
            return 0.0
        
        # 假设"正面"、"positive"等键表示正面情感
        positive = sentiment_data.get('正面', 0) + sentiment_data.get('positive', 0)
        
        return round(positive / total * 100, 2)


# 全局单例
_version_manager: Optional[ReportVersionManager] = None


def get_report_version_manager() -> ReportVersionManager:
    """获取报告版本管理器单例"""
    global _version_manager
    if _version_manager is None:
        _version_manager = ReportVersionManager()
    return _version_manager
