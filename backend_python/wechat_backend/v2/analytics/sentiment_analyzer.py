"""
情感分析器

功能：
- 统计情感倾向分布（正面/中性/负面）
- 按品牌分组分析情感
- 按模型分组分析情感
- 计算情感得分

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

from typing import List, Dict, Any
from collections import defaultdict
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import AnalyticsDataError


class SentimentAnalyzer:
    """
    情感分析器

    分析 AI 回答中对品牌的情感倾向
    """

    # 情感标签
    SENTIMENT_LABELS = ['positive', 'neutral', 'negative']

    # 情感标签中文映射
    SENTIMENT_LABEL_CN = {
        'positive': '正面',
        'neutral': '中性',
        'negative': '负面'
    }
    
    # 情感分类阈值常量【P2-002 修复】
    SENTIMENT_POSITIVE_THRESHOLD = 0.3
    SENTIMENT_NEGATIVE_THRESHOLD = -0.3

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

    def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        分析情感倾向分布

        参数:
            results: 诊断结果列表，每项包含 geo_data.sentiment 字段

        返回:
            情感分布字典，key 为情感标签，value 为占比（0-100）

        示例:
            >>> analyzer = SentimentAnalyzer()
            >>> results = [
            ...     {'geo_data': {'sentiment': 0.8}},  # 正面
            ...     {'geo_data': {'sentiment': 0.0}},  # 中性
            ...     {'geo_data': {'sentiment': -0.6}}, # 负面
            ...     {'geo_data': {'sentiment': 0.5}},  # 正面
            ... ]
            >>> analyzer.analyze(results)
            {'positive': 50.0, 'neutral': 25.0, 'negative': 25.0}
            
        raises:
            AnalyticsDataError: 输入参数验证失败
        """
        # 【P1-002 修复】添加输入参数验证
        self._validate_results(results, 'analyze')
        
        if not results:
            self.logger.warning("分析结果为空")
            return {
                'data': {label: 0.0 for label in self.SENTIMENT_LABELS},
                'total_count': 0,
                'warning': '分析结果为空'
            }

        # 统计各情感标签出现次数
        sentiment_counts = defaultdict(int)
        for result in results:
            sentiment = self._extract_sentiment(result)
            sentiment_counts[sentiment] += 1

        # 确保所有标签都有值
        for label in self.SENTIMENT_LABELS:
            if label not in sentiment_counts:
                sentiment_counts[label] = 0

        # 计算占比
        total = sum(sentiment_counts.values())
        distribution = {}
        for label in self.SENTIMENT_LABELS:
            percentage = round(
                sentiment_counts[label] / total * 100 if total > 0 else 0,
                2
            )
            distribution[label] = percentage

        # 【P3-002 修复】结构化日志
        self.logger.info("sentiment_analyzed", extra={
            'event': 'sentiment_analyzed',
            'total_count': total,
            'distribution': distribution,
        })
        return {
            'data': distribution,
            'total_count': total,
            'warning': None
        }
    
    def analyze_by_brand(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        按品牌分析情感分布
        
        参数:
            results: 诊断结果列表
            
        返回:
            嵌套字典，外层 key 为品牌名，内层为情感分布
            
        示例:
            >>> analyzer.analyze_by_brand(results)
            {
                'Nike': {'positive': 60.0, 'neutral': 30.0, 'negative': 10.0},
                'Adidas': {'positive': 40.0, 'neutral': 40.0, 'negative': 20.0}
            }
        """
        if not results:
            return {}
        
        # 按品牌分组统计
        brand_sentiment_counts = defaultdict(lambda: defaultdict(int))
        
        for result in results:
            brand = result.get('brand', 'unknown')
            sentiment = self._extract_sentiment(result)
            brand_sentiment_counts[brand][sentiment] += 1
        
        # 计算每个品牌的情感分布
        distribution = {}
        for brand, sentiment_counts in brand_sentiment_counts.items():
            total = sum(sentiment_counts.values())
            distribution[brand] = {
                label: round(
                    sentiment_counts.get(label, 0) / total * 100 if total > 0 else 0,
                    2
                )
                for label in self.SENTIMENT_LABELS
            }
        
        self.logger.info(f"按品牌分析完成：{len(distribution)} 个品牌")
        return distribution
    
    def analyze_by_model(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        按 AI 模型分析情感分布
        
        参数:
            results: 诊断结果列表
            
        返回:
            嵌套字典，外层 key 为模型名，内层为情感分布
        """
        if not results:
            return {}
        
        # 按模型分组统计
        model_sentiment_counts = defaultdict(lambda: defaultdict(int))
        
        for result in results:
            model = result.get('model', 'unknown')
            sentiment = self._extract_sentiment(result)
            model_sentiment_counts[model][sentiment] += 1
        
        # 计算每个模型的情感分布
        distribution = {}
        for model, sentiment_counts in model_sentiment_counts.items():
            total = sum(sentiment_counts.values())
            distribution[model] = {
                label: round(
                    sentiment_counts.get(label, 0) / total * 100 if total > 0 else 0,
                    2
                )
                for label in self.SENTIMENT_LABELS
            }
        
        self.logger.info(f"按模型分析完成：{len(distribution)} 个模型")
        return distribution
    
    def calculate_sentiment_score(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        计算情感得分
        
        参数:
            results: 诊断结果列表
            
        返回:
            情感得分字典，包含平均分、最高分、最低分
            
        情感得分说明:
            - 1.0: 完全正面
            - 0.0: 中性
            - -1.0: 完全负面
        """
        if not results:
            return {
                'avg_score': 0.0,
                'max_score': 0.0,
                'min_score': 0.0,
                'total_count': 0
            }
        
        scores = []
        for result in results:
            geo_data = result.get('geo_data', {})
            sentiment = geo_data.get('sentiment', 0.0)
            if isinstance(sentiment, (int, float)):
                scores.append(sentiment)
        
        if not scores:
            return {
                'avg_score': 0.0,
                'max_score': 0.0,
                'min_score': 0.0,
                'total_count': 0
            }
        
        return {
            'avg_score': round(sum(scores) / len(scores), 3),
            'max_score': round(max(scores), 3),
            'min_score': round(min(scores), 3),
            'total_count': len(scores)
        }
    
    def get_positive_rate(
        self,
        results: List[Dict[str, Any]],
        threshold: float = 0.5
    ) -> float:
        """
        计算正面情感比例
        
        参数:
            results: 诊断结果列表
            threshold: 正面情感阈值（默认 0.5）
            
        返回:
            正面情感比例（0-100）
        """
        if not results:
            return 0.0
        
        positive_count = 0
        for result in results:
            sentiment = result.get('geo_data', {}).get('sentiment', 0.0)
            if sentiment > threshold:
                positive_count += 1
        
        return round(positive_count / len(results) * 100, 2)
    
    def get_negative_rate(
        self,
        results: List[Dict[str, Any]],
        threshold: float = -0.5
    ) -> float:
        """
        计算负面情感比例
        
        参数:
            results: 诊断结果列表
            threshold: 负面情感阈值（默认 -0.5）
            
        返回:
            负面情感比例（0-100）
        """
        if not results:
            return 0.0
        
        negative_count = 0
        for result in results:
            sentiment = result.get('geo_data', {}).get('sentiment', 0.0)
            if sentiment < threshold:
                negative_count += 1
        
        return round(negative_count / len(results) * 100, 2)
    
    def compare_sentiment(
        self,
        results: List[Dict[str, Any]],
        brand1: str,
        brand2: str
    ) -> Dict[str, Any]:
        """
        比较两个品牌的情感倾向
        
        参数:
            results: 诊断结果列表
            brand1: 品牌 1
            brand2: 品牌 2
            
        返回:
            情感对比结果
        """
        brand1_results = [r for r in results if r.get('brand') == brand1]
        brand2_results = [r for r in results if r.get('brand') == brand2]
        
        brand1_score = self.calculate_sentiment_score(brand1_results)
        brand2_score = self.calculate_sentiment_score(brand2_results)
        
        brand1_distribution = self.analyze_by_brand(brand1_results).get(brand1, {})
        brand2_distribution = self.analyze_by_brand(brand2_results).get(brand2, {})
        
        return {
            'brand1': {
                'name': brand1,
                'avg_score': brand1_score['avg_score'],
                'distribution': brand1_distribution,
                'positive_rate': self.get_positive_rate(brand1_results)
            },
            'brand2': {
                'name': brand2,
                'avg_score': brand2_score['avg_score'],
                'distribution': brand2_distribution,
                'positive_rate': self.get_positive_rate(brand2_results)
            },
            'comparison': {
                'winner': brand1 if brand1_score['avg_score'] > brand2_score['avg_score'] else brand2,
                'score_diff': round(abs(brand1_score['avg_score'] - brand2_score['avg_score']), 3)
            }
        }
    
    def _extract_sentiment(self, result: Dict[str, Any]) -> str:
        """
        从结果中提取情感标签

        参数:
            result: 诊断结果

        返回:
            情感标签 ('positive', 'neutral', 'negative')
        """
        geo_data = result.get('geo_data', {})
        sentiment = geo_data.get('sentiment', 0.0)

        if not isinstance(sentiment, (int, float)):
            return 'neutral'

        # 【P2-002 修复】使用常量定义情感分类阈值
        if sentiment > self.SENTIMENT_POSITIVE_THRESHOLD:
            return 'positive'
        elif sentiment < self.SENTIMENT_NEGATIVE_THRESHOLD:
            return 'negative'
        else:
            return 'neutral'
