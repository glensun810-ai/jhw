"""
增量结果聚合器 (Incremental Aggregator)

功能:
1. 每个 API 完成后立即聚合
2. 增量计算 SOV
3. 增量计算排名
4. 增量计算健康度
5. 提供完整聚合结果

与 RealtimeAnalyzer 的区别:
- RealtimeAnalyzer: 轻量级，实时统计，用于进度显示
- IncrementalAggregator: 重量级，完整聚合，用于最终结果

使用场景:
- 替代 process_and_aggregate_results_with_ai_judge
- 实时生成最终报告
- 减少 90-100% 阶段等待时间
"""

from typing import Dict, Any, List
from datetime import datetime
import re


class IncrementalAggregator:
    """增量结果聚合器"""
    
    def __init__(self, main_brand: str, all_brands: List[str], questions: List[str]):
        """
        初始化聚合器
        
        Args:
            main_brand: 主品牌名称
            all_brands: 所有品牌列表 (包括竞品)
            questions: 问题列表
        """
        self.main_brand = main_brand
        self.all_brands = all_brands
        self.questions = questions
        
        # 存储所有结果
        self.results: List[Dict[str, Any]] = []
        
        # 聚合统计
        self.aggregated_stats = {
            'main_brand': {
                'total_responses': 0,
                'success_count': 0,
                'total_words': 0,
                'sentiment_sum': 0.0,
                'geo_mentioned_count': 0,
                'rank_sum': 0,
                'sov_share': 0.0,
                'avg_rank': -1
            },
            'competitors': {},
            'models': {},
            'questions': {}
        }
        
        # 初始化竞品统计
        for brand in all_brands:
            if brand != main_brand:
                self.aggregated_stats['competitors'][brand] = {
                    'total_responses': 0,
                    'success_count': 0,
                    'total_words': 0,
                    'sentiment_sum': 0.0
                }
        
        # 初始化模型统计
        self.aggregated_stats['models'] = {}
        
        # 初始化问题统计
        for question in questions:
            self.aggregated_stats['questions'][question] = {
                'total_responses': 0,
                'main_brand_mentions': 0,
                'competitor_mentions': {}
            }
        
        self.start_time = datetime.now()
    
    def add_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加单个结果并更新聚合
        
        Args:
            result: 测试结果字典
            
        Returns:
            当前聚合结果
        """
        # 添加到结果列表
        self.results.append(result)
        
        # 提取信息
        brand = result.get('brand', 'unknown')
        model = result.get('aiModel', result.get('model', 'unknown'))
        question = result.get('question', result.get('question_text', ''))
        response = result.get('response', result.get('content', ''))
        success = result.get('status') == 'success'
        
        # 提取 GEO 数据
        geo_data = self._extract_geo_data(response, brand)
        
        # 更新聚合统计
        self._update_aggregated_stats(brand, model, question, response, success, geo_data)
        
        # 生成当前聚合结果
        return self.get_aggregated_results()
    
    def _extract_geo_data(self, response: str, brand: str) -> Dict[str, Any]:
        """
        提取 GEO 数据
        
        Returns:
            GEO 数据字典
        """
        geo_data = {
            'brand_mentioned': brand in response,
            'rank': -1,
            'sentiment': 0.5,
            'cited_sources': [],
            'interception': ''
        }
        
        # 提取排名
        rank = self._extract_rank(response, brand)
        geo_data['rank'] = rank
        
        # 估算情感
        sentiment = self._estimate_sentiment(response)
        geo_data['sentiment'] = sentiment
        
        # 检查竞品拦截
        competitors_mentioned = self._extract_competitors(response)
        if competitors_mentioned:
            geo_data['interception'] = competitors_mentioned[0]
        
        return geo_data
    
    def _extract_rank(self, response: str, brand: str) -> int:
        """提取排名"""
        rank_patterns = [
            r'第 ([1-9][0-9]*) 名',
            r'排名.*?([1-9][0-9]*)',
            r'NO\\.?([1-9][0-9]*)',
            r'No\\.?([1-9][0-9]*)',
            r'rank.*?([1-9][0-9]*)',
            r'Rank.*?([1-9][0-9]*)'
        ]
        
        for pattern in rank_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                rank = int(match.group(1))
                return min(rank, 10)
        
        return -1
    
    def _estimate_sentiment(self, response: str) -> float:
        """估算情感分数"""
        positive_words = [
            '好', '优秀', '推荐', '不错', '很好', '最好',
            '领先', '优势', '强大', '可靠', '值得',
            '第一', '首选', '优选', '好评', '认可'
        ]
        
        negative_words = [
            '差', '不好', '问题', '缺点', '不足',
            '落后', '劣势', '弱', '避免', '谨慎',
            '最后', '末位', '差评', '投诉', '风险'
        ]
        
        score = 0.5
        
        positive_count = sum(1 for word in positive_words if word in response)
        negative_count = sum(1 for word in negative_words if word in response)
        
        if positive_count > negative_count:
            score += 0.1 * min(positive_count, 3)
        elif negative_count > positive_count:
            score -= 0.1 * min(negative_count, 3)
        
        return min(max(score, 0.0), 1.0)
    
    def _extract_competitors(self, response: str) -> List[str]:
        """提取提及的竞品"""
        mentioned = []
        for brand in self.all_brands:
            if brand != self.main_brand and brand in response:
                mentioned.append(brand)
        return mentioned
    
    def _update_aggregated_stats(
        self, 
        brand: str, 
        model: str, 
        question: str, 
        response: str, 
        success: bool,
        geo_data: Dict[str, Any]
    ):
        """更新聚合统计"""
        word_count = len(response)
        sentiment = geo_data['sentiment']
        rank = geo_data['rank']
        
        # 主品牌统计
        if brand == self.main_brand:
            main_stats = self.aggregated_stats['main_brand']
            main_stats['total_responses'] += 1
            if success:
                main_stats['success_count'] += 1
            main_stats['total_words'] += word_count
            main_stats['sentiment_sum'] += sentiment
            if geo_data['brand_mentioned']:
                main_stats['geo_mentioned_count'] += 1
            if rank > 0:
                main_stats['rank_sum'] += rank
            
            # 更新 SOV
            total_responses = sum(
                stats['total_responses'] 
                for stats in self.aggregated_stats['competitors'].values()
            ) + main_stats['total_responses']
            
            if total_responses > 0:
                main_stats['sov_share'] = round(
                    main_stats['total_responses'] / total_responses * 100, 2
                )
            
            # 更新平均排名
            if main_stats['geo_mentioned_count'] > 0:
                main_stats['avg_rank'] = round(
                    main_stats['rank_sum'] / main_stats['geo_mentioned_count'], 2
                )
        
        # 竞品统计
        if brand in self.aggregated_stats['competitors']:
            comp_stats = self.aggregated_stats['competitors'][brand]
            comp_stats['total_responses'] += 1
            if success:
                comp_stats['success_count'] += 1
            comp_stats['total_words'] += word_count
            comp_stats['sentiment_sum'] += sentiment
        
        # 模型统计
        if model not in self.aggregated_stats['models']:
            self.aggregated_stats['models'][model] = {
                'total_responses': 0,
                'success_count': 0,
                'avg_word_count': 0
            }
        
        model_stats = self.aggregated_stats['models'][model]
        model_stats['total_responses'] += 1
        if success:
            model_stats['success_count'] += 1
        
        # 更新平均字数
        model_stats['avg_word_count'] = (
            (model_stats['avg_word_count'] * (model_stats['total_responses'] - 1) + word_count)
            / model_stats['total_responses']
        )
        
        # 问题统计
        if question in self.aggregated_stats['questions']:
            q_stats = self.aggregated_stats['questions'][question]
            q_stats['total_responses'] += 1
            
            if brand == self.main_brand and geo_data['brand_mentioned']:
                q_stats['main_brand_mentions'] += 1
            
            if brand != self.main_brand:
                if brand not in q_stats['competitor_mentions']:
                    q_stats['competitor_mentions'][brand] = 0
                q_stats['competitor_mentions'][brand] += 1
    
    def get_aggregated_results(self) -> Dict[str, Any]:
        """
        获取聚合结果
        
        Returns:
            完整聚合结果字典
        """
        # 计算品牌排名
        brand_rankings = self._calculate_brand_rankings()
        
        # 计算问题统计
        question_stats = self._calculate_question_stats()
        
        # 计算模型统计
        model_stats = self._calculate_model_stats()
        
        # 构建详细结果
        detailed_results = []
        for result in self.results:
            detailed_results.append({
                'brand': result.get('brand', 'unknown'),
                'aiModel': result.get('aiModel', result.get('model', 'unknown')),
                'question': result.get('question', result.get('question_text', '')),
                'response': result.get('response', result.get('content', '')),
                'status': result.get('status', 'unknown'),
                'geo_data': self._extract_geo_data(
                    result.get('response', ''), 
                    result.get('brand', '')
                )
            })
        
        # 计算主品牌健康度
        main_stats = self.aggregated_stats['main_brand']
        health_score = self._calculate_health_score(main_stats)
        
        return {
            'main_brand': self.main_brand,
            'summary': {
                'healthScore': health_score,
                'sov': main_stats['sov_share'],
                'avgSentiment': round(main_stats['sentiment_sum'] / main_stats['total_responses'], 2) if main_stats['total_responses'] > 0 else 0,
                'totalMentions': main_stats['geo_mentioned_count'],
                'totalTests': len(self.results),
                'successRate': round(main_stats['success_count'] / main_stats['total_responses'] * 100, 2) if main_stats['total_responses'] > 0 else 0
            },
            'brand_rankings': brand_rankings,
            'question_stats': question_stats,
            'model_stats': model_stats,
            'detailed_results': detailed_results,
            'aggregated_stats': self.aggregated_stats,
            'total_results': len(self.results),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds()
        }
    
    def _calculate_brand_rankings(self) -> List[Dict[str, Any]]:
        """计算品牌排名"""
        rankings = []
        
        # 主品牌
        main_stats = self.aggregated_stats['main_brand']
        if main_stats['total_responses'] > 0:
            rankings.append({
                'brand': self.main_brand,
                'is_main_brand': True,
                'responses': main_stats['total_responses'],
                'sov_share': main_stats['sov_share'],
                'avg_sentiment': round(main_stats['sentiment_sum'] / main_stats['total_responses'], 2),
                'avg_rank': main_stats['avg_rank'],
                'geo_rate': round(main_stats['geo_mentioned_count'] / main_stats['total_responses'], 2) if main_stats['total_responses'] > 0 else 0
            })
        
        # 竞品
        for brand, stats in self.aggregated_stats['competitors'].items():
            if stats['total_responses'] > 0:
                rankings.append({
                    'brand': brand,
                    'is_main_brand': False,
                    'responses': stats['total_responses'],
                    'sov_share': round(stats['total_responses'] / sum(
                        s['total_responses'] for s in self.aggregated_stats['competitors'].values()
                    ) * 100, 2),
                    'avg_sentiment': round(stats['sentiment_sum'] / stats['total_responses'], 2),
                    'avg_rank': -1,  # 竞品不计算排名
                    'geo_rate': 0
                })
        
        # 按响应数排序
        rankings.sort(key=lambda x: x['responses'], reverse=True)
        
        # 添加排名序号
        for i, ranking in enumerate(rankings):
            ranking['rank'] = i + 1
        
        return rankings
    
    def _calculate_question_stats(self) -> List[Dict[str, Any]]:
        """计算问题统计"""
        stats = []
        
        for question, q_stats in self.aggregated_stats['questions'].items():
            stats.append({
                'question': question,
                'total_responses': q_stats['total_responses'],
                'main_brand_mentions': q_stats['main_brand_mentions'],
                'mention_rate': round(
                    q_stats['main_brand_mentions'] / q_stats['total_responses'] * 100, 2
                ) if q_stats['total_responses'] > 0 else 0,
                'competitor_mentions': q_stats['competitor_mentions']
            })
        
        return stats
    
    def _calculate_model_stats(self) -> List[Dict[str, Any]]:
        """计算模型统计"""
        stats = []
        
        for model, m_stats in self.aggregated_stats['models'].items():
            stats.append({
                'model': model,
                'total_responses': m_stats['total_responses'],
                'success_count': m_stats['success_count'],
                'success_rate': round(
                    m_stats['success_count'] / m_stats['total_responses'] * 100, 2
                ) if m_stats['total_responses'] > 0 else 0,
                'avg_word_count': round(m_stats['avg_word_count'], 1)
            })
        
        return stats
    
    def _calculate_health_score(self, main_stats: Dict[str, Any]) -> int:
        """
        计算品牌健康度得分
        
        公式:
        - SOV 占 50%
        - 情感占 30%
        - 排名占 20%
        
        Returns:
            健康度得分 (0-100)
        """
        # SOV 得分 (0-50)
        sov_score = min(main_stats['sov_share'] / 100 * 50, 50)
        
        # 情感得分 (0-30)
        avg_sentiment = main_stats['sentiment_sum'] / main_stats['total_responses'] if main_stats['total_responses'] > 0 else 0.5
        sentiment_score = avg_sentiment * 30
        
        # 排名得分 (0-20)
        avg_rank = main_stats['avg_rank']
        if avg_rank > 0:
            rank_score = max(0, (11 - avg_rank) / 10 * 20)
        else:
            rank_score = 10  # 默认中等分数
        
        health_score = int(sov_score + sentiment_score + rank_score)
        
        return min(max(health_score, 0), 100)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        main_stats = self.aggregated_stats['main_brand']
        
        return {
            'main_brand': self.main_brand,
            'total_results': len(self.results),
            'total_responses': main_stats['total_responses'],
            'sov_share': main_stats['sov_share'],
            'avg_sentiment': round(main_stats['sentiment_sum'] / main_stats['total_responses'], 2) if main_stats['total_responses'] > 0 else 0,
            'avg_rank': main_stats['avg_rank'],
            'health_score': self._calculate_health_score(main_stats),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds()
        }


# 全局聚合器存储
_aggregators: Dict[str, IncrementalAggregator] = {}


def get_aggregator(execution_id: str) -> IncrementalAggregator:
    """获取指定执行 ID 的聚合器"""
    return _aggregators.get(execution_id)


def create_aggregator(
    execution_id: str, 
    main_brand: str, 
    all_brands: List[str],
    questions: List[str]
) -> IncrementalAggregator:
    """创建并注册聚合器"""
    aggregator = IncrementalAggregator(main_brand, all_brands, questions)
    _aggregators[execution_id] = aggregator
    return aggregator


def remove_aggregator(execution_id: str):
    """移除聚合器"""
    if execution_id in _aggregators:
        del _aggregators[execution_id]
