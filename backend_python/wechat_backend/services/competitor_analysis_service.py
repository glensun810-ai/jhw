"""
竞品对比分析服务（增强版）

功能:
- 竞品趋势分析
- 拦截风险预警
- 竞品动态追踪
- 差异化分析

@author: 系统架构组
@date: 2026-03-14
@version: 2.0.0
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from wechat_backend.logging_config import api_logger


class CompetitorAnalysisService:
    """
    竞品对比分析服务（P1-03 增强版 - 2026-03-14）
    
    功能:
    1. 竞品趋势分析
    2. 拦截风险预警
    3. 竞品动态追踪
    4. 差异化分析
    """
    
    def __init__(self):
        """初始化竞品分析服务"""
        # 风险阈值配置
        self.risk_thresholds = {
            'rank_drop': 3,           # 排名下降超过 3 位
            'mention_drop': 0.3,       # 提及率下降超过 30%
            'sentiment_drop': 0.2,     # 情感得分下降超过 20%
            'competitor_surge': 2.0    # 竞品提及率激增超过 2 倍
        }
        
        api_logger.info("[CompetitorAnalysis] 初始化完成")
    
    def analyze_competitor_trend(
        self,
        current_results: List[Dict],
        historical_results: List[Dict],
        brand_name: str,
        competitor_names: List[str]
    ) -> Dict[str, Any]:
        """
        分析竞品趋势
        
        参数:
            current_results: 当前诊断结果
            historical_results: 历史诊断结果
            brand_name: 主品牌名称
            competitor_names: 竞品名称列表
            
        返回:
            Dict: 趋势分析结果
        """
        # 计算当前数据
        current_stats = self._calculate_brand_stats(current_results, [brand_name] + competitor_names)
        
        # 计算历史数据
        historical_stats = self._calculate_brand_stats(historical_results, [brand_name] + competitor_names)
        
        # 趋势分析
        trends = {}
        
        for brand in [brand_name] + competitor_names:
            current = current_stats.get(brand, {})
            historical = historical_stats.get(brand, {})
            
            if not current or not historical:
                continue
            
            # 排名变化
            rank_change = historical.get('rank', 0) - current.get('rank', 0)
            
            # 提及率变化
            mention_change = current.get('mention_count', 0) - historical.get('mention_count', 0)
            mention_rate_change = (
                (current.get('mention_rate', 0) - historical.get('mention_rate', 0)) / 
                historical.get('mention_rate', 1) if historical.get('mention_rate', 0) > 0 else 0
            )
            
            # 情感得分变化
            sentiment_change = current.get('sentiment_score', 0) - historical.get('sentiment_score', 0)
            
            trends[brand] = {
                'rank_change': rank_change,
                'rank_trend': 'up' if rank_change > 0 else ('down' if rank_change < 0 else 'stable'),
                'mention_change': mention_change,
                'mention_rate_change': round(mention_rate_change * 100, 2),
                'mention_trend': 'up' if mention_change > 0 else ('down' if mention_change < 0 else 'stable'),
                'sentiment_change': round(sentiment_change, 2),
                'sentiment_trend': 'up' if sentiment_change > 0 else ('down' if sentiment_change < 0 else 'stable'),
                'current_rank': current.get('rank'),
                'current_mentions': current.get('mention_count'),
                'current_sentiment': current.get('sentiment_score')
            }
        
        return {
            'trends': trends,
            'main_brand': brand_name,
            'competitors': competitor_names,
            'analysis_time': datetime.now().isoformat()
        }
    
    def detect_interception_risk(
        self,
        current_results: List[Dict],
        brand_name: str,
        competitor_names: List[str]
    ) -> Dict[str, Any]:
        """
        检测拦截风险
        
        参数:
            current_results: 当前诊断结果
            brand_name: 主品牌名称
            competitor_names: 竞品名称列表
            
        返回:
            Dict: 风险检测结果
        """
        stats = self._calculate_brand_stats(current_results, [brand_name] + competitor_names)
        
        main_brand_stats = stats.get(brand_name, {})
        main_rank = main_brand_stats.get('rank', 999)
        
        risks = []
        
        for competitor in competitor_names:
            comp_stats = stats.get(competitor, {})
            comp_rank = comp_stats.get('rank', 999)
            
            risk_item = {
                'competitor': competitor,
                'risk_level': 'low',
                'risk_factors': [],
                'risk_score': 0
            }
            
            # 风险因子 1: 竞品排名超过主品牌
            if comp_rank < main_rank:
                risk_item['risk_factors'].append({
                    'type': 'rank_higher',
                    'description': f'{competitor} 排名 ({comp_rank}) 超过 {brand_name} ({main_rank})',
                    'severity': 'high'
                })
                risk_item['risk_score'] += 30
            
            # 风险因子 2: 竞品提及率远高于主品牌
            comp_mentions = comp_stats.get('mention_count', 0)
            main_mentions = main_brand_stats.get('mention_count', 0)
            
            if main_mentions > 0 and comp_mentions > main_mentions * self.risk_thresholds['competitor_surge']:
                risk_item['risk_factors'].append({
                    'type': 'mention_surge',
                    'description': f'{competitor} 提及率 ({comp_mentions}) 远超 {brand_name} ({main_mentions})',
                    'severity': 'medium'
                })
                risk_item['risk_score'] += 20
            
            # 风险因子 3: 竞品情感得分远高于主品牌
            comp_sentiment = comp_stats.get('sentiment_score', 0)
            main_sentiment = main_brand_stats.get('sentiment_score', 0)
            
            if comp_sentiment > main_sentiment + 20:
                risk_item['risk_factors'].append({
                    'type': 'sentiment_higher',
                    'description': f'{competitor} 情感得分 ({comp_sentiment}) 高于 {brand_name} ({main_sentiment})',
                    'severity': 'medium'
                })
                risk_item['risk_score'] += 15
            
            # 确定风险等级
            if risk_item['risk_score'] >= 50:
                risk_item['risk_level'] = 'high'
            elif risk_item['risk_score'] >= 30:
                risk_item['risk_level'] = 'medium'
            
            if risk_item['risk_factors']:
                risks.append(risk_item)
        
        # 按风险分数排序
        risks.sort(key=lambda x: x['risk_score'], reverse=True)
        
        return {
            'risks': risks,
            'main_brand': brand_name,
            'total_risks': len(risks),
            'high_risks': sum(1 for r in risks if r['risk_level'] == 'high'),
            'analysis_time': datetime.now().isoformat()
        }
    
    def analyze_differentiation(
        self,
        current_results: List[Dict],
        brand_name: str,
        competitor_names: List[str]
    ) -> Dict[str, Any]:
        """
        分析差异化
        
        参数:
            current_results: 当前诊断结果
            brand_name: 主品牌名称
            competitor_names: 竞品名称列表
            
        返回:
            Dict: 差异化分析结果
        """
        # 提取各品牌的关键词
        brand_keywords = self._extract_brand_keywords(current_results, brand_name)
        competitor_keywords = {}
        
        for competitor in competitor_names:
            competitor_keywords[competitor] = self._extract_brand_keywords(current_results, competitor)
        
        # 计算共有关键词
        common_keywords = set(brand_keywords.keys())
        for comp_kws in competitor_keywords.values():
            common_keywords &= set(comp_kws.keys())
        
        # 计算主品牌独有关键词
        my_unique_keywords = set(brand_keywords.keys())
        for comp_kws in competitor_keywords.values():
            my_unique_keywords -= set(comp_kws.keys())
        
        # 计算竞品独有关键词
        competitor_unique_keywords = {}
        for competitor, comp_kws in competitor_keywords.items():
            unique = set(comp_kws.keys()) - set(brand_keywords.keys())
            competitor_unique_keywords[competitor] = list(unique)
        
        # 差异化分析
        differentiation = {
            'common_keywords': list(common_keywords),
            'my_unique_keywords': list(my_unique_keywords),
            'competitor_unique_keywords': competitor_unique_keywords,
            'differentiation_score': self._calculate_differentiation_score(
                brand_keywords, competitor_keywords
            ),
            'suggestions': self._generate_differentiation_suggestions(
                brand_name, brand_keywords, competitor_keywords
            )
        }
        
        return differentiation
    
    def _calculate_brand_stats(
        self,
        results: List[Dict],
        brands: List[str]
    ) -> Dict[str, Dict]:
        """计算品牌统计数据"""
        stats = {}
        total_mentions = 0
        
        # 统计提及次数
        for result in results:
            brand = result.get('brand', '') or result.get('extracted_brand', '')
            if brand in brands:
                if brand not in stats:
                    stats[brand] = {
                        'mention_count': 0,
                        'positive_count': 0,
                        'negative_count': 0,
                        'neutral_count': 0
                    }
                stats[brand]['mention_count'] += 1
                total_mentions += 1
                
                # 简单情感分析
                response = result.get('response_content', '') or result.get('response', '')
                if self._is_positive(response):
                    stats[brand]['positive_count'] += 1
                elif self._is_negative(response):
                    stats[brand]['negative_count'] += 1
                else:
                    stats[brand]['neutral_count'] += 1
        
        # 计算排名和提及率
        sorted_brands = sorted(
            stats.items(),
            key=lambda x: x[1]['mention_count'],
            reverse=True
        )
        
        for rank, (brand, data) in enumerate(sorted_brands, 1):
            stats[brand]['rank'] = rank
            stats[brand]['mention_rate'] = round(
                data['mention_count'] / total_mentions if total_mentions > 0 else 0, 4
            )
            stats[brand]['sentiment_score'] = round(
                (data['positive_count'] - data['negative_count']) / 
                data['mention_count'] * 100 if data['mention_count'] > 0 else 0, 2
            )
        
        return stats
    
    def _extract_brand_keywords(
        self,
        results: List[Dict],
        brand_name: str
    ) -> Dict[str, int]:
        """提取品牌关键词"""
        keywords = defaultdict(int)
        
        for result in results:
            brand = result.get('brand', '') or result.get('extracted_brand', '')
            if brand == brand_name:
                response = result.get('response_content', '') or result.get('response', '')
                # 简单关键词提取（按逗号、句号分割）
                if isinstance(response, str):
                    words = response.replace('，', ',').replace('。', '.').split(',')
                    for word in words:
                        word = word.strip()
                        if 2 <= len(word) <= 6:
                            keywords[word] += 1
        
        return dict(keywords)
    
    def _calculate_differentiation_score(
        self,
        brand_keywords: Dict[str, int],
        competitor_keywords: Dict[str, Dict[str, int]]
    ) -> float:
        """计算差异化得分"""
        if not brand_keywords:
            return 0.0
        
        all_competitor_keywords = set()
        for kws in competitor_keywords.values():
            all_competitor_keywords.update(kws.keys())
        
        brand_unique = set(brand_keywords.keys()) - all_competitor_keywords
        brand_total = set(brand_keywords.keys())
        
        if not brand_total:
            return 0.0
        
        return round(len(brand_unique) / len(brand_total) * 100, 2)
    
    def _generate_differentiation_suggestions(
        self,
        brand_name: str,
        brand_keywords: Dict[str, int],
        competitor_keywords: Dict[str, Dict[str, int]]
    ) -> List[str]:
        """生成差异化建议"""
        suggestions = []
        
        # 找出竞品高频但主品牌没有的词
        competitor_strong = defaultdict(int)
        for comp, kws in competitor_keywords.items():
            for kw, count in kws.items():
                if kw not in brand_keywords:
                    competitor_strong[kw] += count
        
        # 取前 5 个
        top_competitor_kws = sorted(
            competitor_strong.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        if top_competitor_kws:
            suggestions.append(
                f"建议加强以下方面的宣传：{', '.join(kw for kw, _ in top_competitor_kws)}"
            )
        
        # 找出主品牌独有的优势
        brand_unique = set(brand_keywords.keys())
        for kws in competitor_keywords.values():
            brand_unique -= set(kws.keys())
        
        if brand_unique:
            suggestions.append(
                f"保持并强化独特优势：{', '.join(list(brand_unique)[:5])}"
            )
        
        return suggestions
    
    def _is_positive(self, text: str) -> bool:
        """简单判断正面情感"""
        positive_words = ['好', '优秀', '出色', '推荐', '满意', '喜欢', '棒', '不错', '值得']
        return any(word in text for word in positive_words)
    
    def _is_negative(self, text: str) -> bool:
        """简单判断负面情感"""
        negative_words = ['差', '不好', '失望', '避免', '后悔', '糟糕', '垃圾', '问题', '投诉']
        return any(word in text for word in negative_words)


# 全局单例
_competitor_service: Optional[CompetitorAnalysisService] = None


def get_competitor_analysis_service() -> CompetitorAnalysisService:
    """获取竞品分析服务单例"""
    global _competitor_service
    if _competitor_service is None:
        _competitor_service = CompetitorAnalysisService()
    return _competitor_service
