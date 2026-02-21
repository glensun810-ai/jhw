"""
实时结果分析器 (Realtime Analyzer)

功能:
1. 每个 API 完成后立即分析
2. 实时更新统计
3. 累加到总结果
4. 提供实时进度数据

使用场景:
- TestExecutor 回调中调用
- 实时更新任务状态
- 前端轮询时返回实时统计
"""

from typing import Dict, Any, List
from datetime import datetime
import re


class RealtimeAnalyzer:
    """实时结果分析器"""
    
    def __init__(self, execution_id: str, main_brand: str, all_brands: List[str]):
        """
        初始化分析器
        
        Args:
            execution_id: 执行 ID
            main_brand: 主品牌名称
            all_brands: 所有品牌列表 (包括竞品)
        """
        self.execution_id = execution_id
        self.main_brand = main_brand
        self.all_brands = all_brands
        self.start_time = datetime.now()
        
        # 统计数据
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'success_count': 0,
            'fail_count': 0,
            'brand_stats': {},  # 每个品牌的统计
            'model_stats': {},   # 每个模型的统计
            'question_stats': {} # 每个问题的统计
        }
        
        # 初始化品牌统计
        for brand in all_brands:
            self.stats['brand_stats'][brand] = {
                'count': 0,
                'success_count': 0,
                'total_words': 0,
                'sentiment_sum': 0.0,
                'geo_mentioned_count': 0,
                'rank_sum': 0,
                'responses': []
            }
    
    def analyze_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单个结果
        
        Args:
            result: 测试结果字典
            
        Returns:
            分析结果字典
        """
        # 提取基本信息
        brand = result.get('brand_name', 'unknown')
        model = result.get('ai_model', 'unknown')
        question = result.get('question', '')
        response = result.get('response', '')
        success = result.get('success', False)
        
        # 分析响应内容
        analysis = {
            'brand': brand,
            'model': model,
            'question': question,
            'success': success,
            'word_count': len(response),
            'has_geo_data': self._check_geo_data(response),
            'sentiment': self._estimate_sentiment(response),
            'rank': self._extract_rank(response, brand),
            'competitors_mentioned': self._extract_competitors(response),
            'timestamp': datetime.now().isoformat()
        }
        
        # 更新统计
        self._update_stats(analysis)
        
        return analysis
    
    def _check_geo_data(self, response: str) -> bool:
        """检查是否有 GEO 相关数据"""
        # 简化判断：响应长度>100 且包含品牌名
        return len(response) > 100
    
    def _estimate_sentiment(self, response: str) -> float:
        """
        估算情感分数 (简化版)
        
        Returns:
            情感分数 (0-1)
        """
        # 正面关键词
        positive_words = [
            '好', '优秀', '推荐', '不错', '很好', '最好',
            '领先', '优势', '强大', '可靠', '值得',
            '第一', '首选', '优选', '好评', '认可'
        ]
        
        # 负面关键词
        negative_words = [
            '差', '不好', '问题', '缺点', '不足',
            '落后', '劣势', '弱', '避免', '谨慎',
            '最后', '末位', '差评', '投诉', '风险'
        ]
        
        score = 0.5  # 中性
        
        # 计算情感倾向
        positive_count = sum(1 for word in positive_words if word in response)
        negative_count = sum(1 for word in negative_words if word in response)
        
        # 调整分数
        if positive_count > negative_count:
            score += 0.1 * min(positive_count, 3)  # 最多加 0.3
        elif negative_count > positive_count:
            score -= 0.1 * min(negative_count, 3)  # 最多减 0.3
        
        return min(max(score, 0.0), 1.0)
    
    def _extract_rank(self, response: str, brand: str) -> int:
        """
        提取排名信息 (简化版)
        
        Returns:
            排名 (1-10), -1 表示未找到
        """
        # 尝试提取排名数字
        rank_patterns = [
            r'第 ([1-9][0-9]*) 名',
            r'排名.*?([1-9][0-9]*)',
            r'NO\\.?([1-9][0-9]*)',
            r'No\\.?([1-9][0-9]*)'
        ]
        
        for pattern in rank_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                rank = int(match.group(1))
                return min(rank, 10)  # 限制在 1-10
        
        return -1  # 未找到排名
    
    def _extract_competitors(self, response: str) -> List[str]:
        """提取提及的竞品"""
        mentioned = []
        for brand in self.all_brands:
            if brand != self.main_brand and brand in response:
                mentioned.append(brand)
        return mentioned
    
    def _update_stats(self, analysis: Dict[str, Any]):
        """更新统计数据"""
        brand = analysis['brand']
        model = analysis['model']
        
        # 总任务数
        self.stats['completed_tasks'] += 1
        
        if analysis['success']:
            self.stats['success_count'] += 1
        else:
            self.stats['fail_count'] += 1
        
        # 品牌统计
        if brand in self.stats['brand_stats']:
            brand_stat = self.stats['brand_stats'][brand]
            brand_stat['count'] += 1
            if analysis['success']:
                brand_stat['success_count'] += 1
            brand_stat['total_words'] += analysis['word_count']
            brand_stat['sentiment_sum'] += analysis['sentiment']
            if analysis['rank'] > 0:
                brand_stat['geo_mentioned_count'] += 1
                brand_stat['rank_sum'] += analysis['rank']
            brand_stat['responses'].append({
                'model': model,
                'word_count': analysis['word_count'],
                'sentiment': analysis['sentiment'],
                'rank': analysis['rank'],
                'competitors': analysis['competitors_mentioned']
            })
        
        # 模型统计
        if model not in self.stats['model_stats']:
            self.stats['model_stats'][model] = {
                'count': 0,
                'success_count': 0,
                'avg_word_count': 0
            }
        
        model_stat = self.stats['model_stats'][model]
        model_stat['count'] += 1
        if analysis['success']:
            model_stat['success_count'] += 1
        model_stat['avg_word_count'] = (
            (model_stat['avg_word_count'] * (model_stat['count'] - 1) + analysis['word_count']) 
            / model_stat['count']
        )
    
    def get_realtime_progress(self) -> Dict[str, Any]:
        """
        获取实时进度
        
        Returns:
            实时进度字典
        """
        total = self.stats['total_tasks']
        completed = self.stats['completed_tasks']
        
        # 计算基础进度百分比
        base_progress = int((completed / total) * 100) if total > 0 else 0
        
        # 计算品牌排名
        brand_rankings = self._calculate_brand_rankings()
        
        # 计算 SOV (Share of Voice)
        sov = self._calculate_sov()
        
        # 计算平均情感
        avg_sentiment = self._calculate_avg_sentiment()
        
        return {
            'progress': base_progress,
            'completed': completed,
            'total': total,
            'success': self.stats['success_count'],
            'fail': self.stats['fail_count'],
            'brand_rankings': brand_rankings,
            'sov': sov,
            'avg_sentiment': avg_sentiment,
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds()
        }
    
    def _calculate_brand_rankings(self) -> List[Dict[str, Any]]:
        """计算品牌实时排名"""
        rankings = []
        
        for brand, stats in self.stats['brand_stats'].items():
            if stats['count'] == 0:
                continue
            
            avg_sentiment = stats['sentiment_sum'] / stats['count']
            avg_words = stats['total_words'] / stats['count']
            geo_rate = stats['geo_mentioned_count'] / stats['count'] if stats['count'] > 0 else 0
            avg_rank = stats['rank_sum'] / stats['geo_mentioned_count'] if stats['geo_mentioned_count'] > 0 else -1
            
            rankings.append({
                'brand': brand,
                'is_main_brand': brand == self.main_brand,
                'responses': stats['count'],
                'success_rate': stats['success_count'] / stats['count'] if stats['count'] > 0 else 0,
                'avg_words': round(avg_words, 1),
                'avg_sentiment': round(avg_sentiment, 2),
                'geo_rate': round(geo_rate, 2),
                'avg_rank': round(avg_rank, 1) if avg_rank > 0 else -1
            })
        
        # 按响应数排序，响应数相同按情感排序
        rankings.sort(key=lambda x: (x['responses'], x['avg_sentiment']), reverse=True)
        
        # 添加排名序号
        for i, ranking in enumerate(rankings):
            ranking['rank'] = i + 1
        
        return rankings
    
    def _calculate_sov(self) -> float:
        """计算 SOV (Share of Voice)"""
        if not self.stats['brand_stats']:
            return 0.0
        
        main_brand_stats = self.stats['brand_stats'].get(self.main_brand, {})
        main_responses = main_brand_stats.get('count', 0)
        
        total_responses = sum(stats['count'] for stats in self.stats['brand_stats'].values())
        
        if total_responses == 0:
            return 0.0
        
        return round(main_responses / total_responses * 100, 2)
    
    def _calculate_avg_sentiment(self) -> float:
        """计算平均情感分数"""
        total_sentiment = 0.0
        total_count = 0
        
        for stats in self.stats['brand_stats'].values():
            if stats['count'] > 0:
                total_sentiment += stats['sentiment_sum']
                total_count += stats['count']
        
        if total_count == 0:
            return 0.0
        
        return round(total_sentiment / total_count, 2)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Returns:
            统计摘要字典
        """
        return {
            'execution_id': self.execution_id,
            'main_brand': self.main_brand,
            'total_tasks': self.stats['total_tasks'],
            'completed_tasks': self.stats['completed_tasks'],
            'success_count': self.stats['success_count'],
            'fail_count': self.stats['fail_count'],
            'success_rate': round(self.stats['success_count'] / self.stats['completed_tasks'] * 100, 2) if self.stats['completed_tasks'] > 0 else 0,
            'brands_count': len([b for b, s in self.stats['brand_stats'].items() if s['count'] > 0]),
            'models_count': len(self.stats['model_stats']),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds()
        }


# 全局分析器存储 (用于在 views.py 中访问)
_analyzers: Dict[str, RealtimeAnalyzer] = {}


def get_analyzer(execution_id: str) -> RealtimeAnalyzer:
    """获取指定执行 ID 的分析器"""
    return _analyzers.get(execution_id)


def create_analyzer(execution_id: str, main_brand: str, all_brands: List[str]) -> RealtimeAnalyzer:
    """创建并注册分析器"""
    analyzer = RealtimeAnalyzer(execution_id, main_brand, all_brands)
    _analyzers[execution_id] = analyzer
    return analyzer


def remove_analyzer(execution_id: str):
    """移除分析器"""
    if execution_id in _analyzers:
        del _analyzers[execution_id]
