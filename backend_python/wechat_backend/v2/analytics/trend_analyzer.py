"""
趋势对比分析器

功能：
- 与历史数据进行对比分析
- 计算趋势变化
- 竞品对比分析
- 时间序列分析

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import AnalyticsDataError


class TrendAnalyzer:
    """
    趋势对比分析器

    分析品牌表现的趋势变化和竞品对比
    """

    def __init__(self):
        """初始化分析器"""
        self.logger = api_logger
    
    def _validate_results(self, results: Any, method_name: str) -> None:
        """
        验证输入参数
        
        参数:
            results: 诊断结果列表
            method_name: 调用方法名（用于错误信息）
            
        raises:
            AnalyticsDataError: 参数验证失败
        """
        if not isinstance(results, list):
            raise AnalyticsDataError(
                f"{method_name}: results 必须是列表类型",
                field='results',
                value=type(results).__name__,
                expected_type='list'
            )
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                raise AnalyticsDataError(
                    f"{method_name}: results[{i}] 必须是字典类型",
                    field=f'results[{i}]',
                    value=type(result).__name__,
                    expected_type='dict'
                )
    
    def compare_with_history(
        self,
        current_results: List[Dict[str, Any]],
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        与历史数据对比

        参数:
            current_results: 当前诊断结果
            historical_data: 历史诊断结果列表（单个历史时期）

        返回:
            趋势对比结果
            
        raises:
            AnalyticsDataError: 输入参数验证失败
        """
        # 【P1-002 修复】添加输入参数验证
        self._validate_results(current_results, 'compare_with_history')
        self._validate_results(historical_data, 'compare_with_history')
        
        if not current_results:
            return {'error': '当前结果为空'}

        if not historical_data:
            return {'error': '历史数据为空'}

        # 计算当前指标
        current_metrics = self._calculate_metrics(current_results)

        # 计算历史指标（单个历史时期）
        historical_metrics = self._calculate_metrics(historical_data)

        # 计算趋势
        trend = self._calculate_trend(current_metrics, historical_metrics)

        return {
            'current': current_metrics,
            'historical': historical_metrics,
            'trend': trend,
        }

    def analyze_competitors(
        self,
        results: List[Dict[str, Any]],
        main_brand: str
    ) -> Dict[str, Any]:
        """
        竞品对比分析

        参数:
            results: 诊断结果列表
            main_brand: 主品牌名称

        返回:
            竞品对比分析结果
            
        raises:
            AnalyticsDataError: 输入参数验证失败
        """
        # 【P1-002 修复】添加输入参数验证
        self._validate_results(results, 'analyze_competitors')
        
        if not results:
            return {'error': '结果为空'}
        
        # 按品牌分组
        brand_results = defaultdict(list)
        for result in results:
            brand = result.get('brand', 'unknown')
            brand_results[brand].append(result)
        
        # 计算各品牌指标
        brand_metrics = {}
        for brand, brand_data in brand_results.items():
            brand_metrics[brand] = self._calculate_metrics(brand_data)
        
        # 主品牌指标
        main_metrics = brand_metrics.get(main_brand, {})
        
        # 竞品指标
        competitor_metrics = {
            brand: metrics
            for brand, metrics in brand_metrics.items()
            if brand != main_brand
        }
        
        # 计算排名
        ranking = self._calculate_ranking(brand_metrics)
        
        # 找出优势劣势
        strengths, weaknesses = self._analyze_swot(main_metrics, competitor_metrics)
        
        return {
            'main_brand': main_brand,
            'main_metrics': main_metrics,
            'competitors': competitor_metrics,
            'ranking': ranking,
            'strengths': strengths,
            'weaknesses': weaknesses
        }
    
    def analyze_time_series(
        self,
        time_series_data: List[Dict[str, Any]],
        metric: str = 'mention_rate'
    ) -> Dict[str, Any]:
        """
        时间序列分析
        
        参数:
            time_series_data: 时间序列数据
                格式：[{'date': '2026-02-01', 'value': 0.35}, ...]
            metric: 分析指标
            
        返回:
            时间序列分析结果
        """
        if not time_series_data:
            return {'error': '时间序列数据为空'}
        
        # 提取数值
        values = [d.get(metric, d.get('value', 0)) for d in time_series_data]
        
        if not values:
            return {'error': '无效数据'}
        
        # 计算趋势
        trend_direction = self._calculate_trend_direction(values)
        trend_strength = self._calculate_trend_strength(values)
        
        # 计算移动平均
        moving_avg = self._calculate_moving_average(values, window=3)
        
        # 计算增长率
        growth_rate = self._calculate_growth_rate(values)
        
        return {
            'metric': metric,
            'data_points': len(values),
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'moving_average': moving_avg,
            'growth_rate': growth_rate,
            'min_value': min(values),
            'max_value': max(values),
            'avg_value': sum(values) / len(values)
        }
    
    def predict_trend(
        self,
        time_series_data: List[Dict[str, Any]],
        periods: int = 3
    ) -> List[Dict[str, Any]]:
        """
        简单趋势预测
        
        参数:
            time_series_data: 时间序列数据
            periods: 预测期数
            
        返回:
            预测结果列表
        """
        if not time_series_data or len(time_series_data) < 2:
            return []
        
        # 提取数值
        values = [d.get('value', 0) for d in time_series_data]
        
        # 计算平均变化量
        changes = [values[i] - values[i-1] for i in range(1, len(values))]
        avg_change = sum(changes) / len(changes) if changes else 0
        
        # 预测
        predictions = []
        last_value = values[-1]
        last_date = time_series_data[-1].get('date', datetime.now().isoformat())
        
        for i in range(periods):
            predicted_value = last_value + avg_change * (i + 1)
            predictions.append({
                'period': i + 1,
                'predicted_value': round(predicted_value, 4),
                'confidence': max(0, 1 - (i * 0.1))  # 置信度递减
            })
        
        return predictions
    
    def calculate_brand_velocity(
        self,
        current_results: List[Dict[str, Any]],
        previous_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        计算品牌变化速度
        
        参数:
            current_results: 当前诊断结果
            previous_results: 上次诊断结果
            
        返回:
            各指标的变化速度
        """
        current_metrics = self._calculate_metrics(current_results)
        previous_metrics = self._calculate_metrics(previous_results)
        
        velocity = {}
        for key in current_metrics:
            if key in previous_metrics and previous_metrics[key] != 0:
                change = current_metrics[key] - previous_metrics[key]
                velocity[key] = round(change, 4)
            else:
                velocity[key] = 0.0
        
        return velocity
    
    def _calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算综合指标"""
        if not results:
            return {}
        
        # 品牌提及率
        brand_counts = defaultdict(int)
        for result in results:
            brand_counts[result.get('brand', 'unknown')] += 1
        
        total = sum(brand_counts.values())
        mention_rates = {
            brand: round(count / total * 100, 2)
            for brand, count in brand_counts.items()
        }
        
        # 平均情感得分
        sentiments = []
        for result in results:
            sentiment = result.get('geo_data', {}).get('sentiment', 0.0)
            if isinstance(sentiment, (int, float)):
                sentiments.append(sentiment)
        
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        # 正面情感比例
        positive_count = sum(1 for s in sentiments if s > 0.3)
        positive_rate = positive_count / len(sentiments) * 100 if sentiments else 0.0
        
        return {
            'total_mentions': total,
            'avg_sentiment': round(avg_sentiment, 3),
            'positive_rate': round(positive_rate, 2),
            'mention_rate': mention_rates
        }
    
    def _average_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算多个指标的平均值"""
        if not metrics_list:
            return {}
        
        avg = {}
        
        # 数值指标平均
        numeric_keys = ['total_mentions', 'avg_sentiment', 'positive_rate']
        for key in numeric_keys:
            values = [m.get(key, 0) for m in metrics_list if key in m]
            if values:
                avg[key] = round(sum(values) / len(values), 3)
        
        # 提及率平均（需要合并字典）
        all_mention_rates = defaultdict(list)
        for metrics in metrics_list:
            mention_rates = metrics.get('mention_rate', {})
            for brand, rate in mention_rates.items():
                all_mention_rates[brand].append(rate)
        
        avg['mention_rate'] = {
            brand: round(sum(rates) / len(rates), 2)
            for brand, rates in all_mention_rates.items()
        }
        
        return avg
    
    def _calculate_trend(
        self,
        current: Dict[str, Any],
        historical: Dict[str, Any]
    ) -> Dict[str, str]:
        """计算趋势方向"""
        trend = {}
        
        # 情感趋势
        if current.get('avg_sentiment', 0) > historical.get('avg_sentiment', 0):
            trend['sentiment'] = 'improving'
        elif current.get('avg_sentiment', 0) < historical.get('avg_sentiment', 0):
            trend['sentiment'] = 'declining'
        else:
            trend['sentiment'] = 'stable'
        
        # 正面率趋势
        if current.get('positive_rate', 0) > historical.get('positive_rate', 0):
            trend['positive_rate'] = 'improving'
        elif current.get('positive_rate', 0) < historical.get('positive_rate', 0):
            trend['positive_rate'] = 'declining'
        else:
            trend['positive_rate'] = 'stable'
        
        return trend
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """计算趋势方向"""
        if len(values) < 2:
            return 'insufficient_data'
        
        # 使用简单线性回归
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        if slope > 0.01:
            return 'upward'
        elif slope < -0.01:
            return 'downward'
        else:
            return 'stable'
    
    def _calculate_trend_strength(self, values: List[float]) -> float:
        """计算趋势强度"""
        if len(values) < 2:
            return 0.0
        
        # 计算变异系数
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        return round(std_dev / abs(mean), 3)
    
    def _calculate_moving_average(
        self,
        values: List[float],
        window: int = 3
    ) -> List[float]:
        """计算移动平均"""
        if len(values) < window:
            return values
        
        moving_avg = []
        for i in range(len(values) - window + 1):
            window_values = values[i:i + window]
            avg = sum(window_values) / window
            moving_avg.append(round(avg, 3))
        
        return moving_avg
    
    def _calculate_growth_rate(self, values: List[float]) -> float:
        """计算增长率"""
        if len(values) < 2 or values[0] == 0:
            return 0.0
        
        return round((values[-1] - values[0]) / values[0] * 100, 2)
    
    def _calculate_ranking(
        self,
        brand_metrics: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """计算品牌排名"""
        rankings = []
        
        for brand, metrics in brand_metrics.items():
            rankings.append({
                'brand': brand,
                'score': metrics.get('avg_sentiment', 0) * 0.5 + 
                        metrics.get('positive_rate', 0) * 0.5
            })
        
        # 按得分排序
        rankings.sort(key=lambda x: x['score'], reverse=True)
        
        # 添加排名
        for i, item in enumerate(rankings):
            item['rank'] = i + 1
        
        return rankings
    
    def _analyze_swot(
        self,
        main_metrics: Dict[str, Any],
        competitor_metrics: Dict[str, Any]
    ) -> tuple:
        """分析优势和劣势"""
        strengths = []
        weaknesses = []
        
        main_sentiment = main_metrics.get('avg_sentiment', 0)
        main_positive_rate = main_metrics.get('positive_rate', 0)
        
        avg_competitor_sentiment = 0
        avg_competitor_positive_rate = 0
        
        if competitor_metrics:
            sentiments = [m.get('avg_sentiment', 0) for m in competitor_metrics.values()]
            positive_rates = [m.get('positive_rate', 0) for m in competitor_metrics.values()]
            avg_competitor_sentiment = sum(sentiments) / len(sentiments)
            avg_competitor_positive_rate = sum(positive_rates) / len(positive_rates)
        
        # 判断优势劣势
        if main_sentiment > avg_competitor_sentiment:
            strengths.append('情感得分高于竞品平均水平')
        else:
            weaknesses.append('情感得分低于竞品平均水平')
        
        if main_positive_rate > avg_competitor_positive_rate:
            strengths.append('正面评价比例高于竞品')
        else:
            weaknesses.append('正面评价比例低于竞品')
        
        return strengths, weaknesses
