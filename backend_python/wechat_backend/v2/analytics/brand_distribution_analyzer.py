"""
品牌分布分析器

功能：
- 计算各品牌在 AI 平台的露出占比
- 按 AI 模型分组统计品牌分布
- 竞品对比分析

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import AnalyticsDataError


class BrandDistributionAnalyzer:
    """
    品牌分布分析器

    分析品牌在 AI 平台回答中的露出情况和占比分布
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

    def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        分析品牌频段分布

        参数:
            results: 诊断结果列表，每项包含 brand 字段

        返回:
            品牌分布字典，key 为品牌名，value 为占比（0-100）

        示例:
            >>> analyzer = BrandDistributionAnalyzer()
            >>> results = [
            ...     {'brand': 'Nike', 'model': 'qwen'},
            ...     {'brand': 'Adidas', 'model': 'qwen'},
            ...     {'brand': 'Nike', 'model': 'deepseek'},
            ... ]
            >>> analyzer.analyze(results)
            {'Nike': 66.67, 'Adidas': 33.33}
            
        raises:
            AnalyticsDataError: 输入参数验证失败
        """
        # 【P1-002 修复】添加输入参数验证
        self._validate_results(results, 'analyze')
        
        if not results:
            self.logger.warning("分析结果为空")
            return {
                'data': {},
                'total_count': 0,
                'warning': '分析结果为空'
            }

        # 统计各品牌出现次数
        brand_counts = defaultdict(int)
        for result in results:
            brand = result.get('brand', 'unknown')
            brand_counts[brand] += 1

        # 计算占比
        total = sum(brand_counts.values())
        if total == 0:
            self.logger.warning("品牌总数为 0")
            return {
                'data': {},
                'total_count': 0,
                'warning': '品牌总数为 0'
            }
        
        distribution = {}
        for brand, count in brand_counts.items():
            percentage = round(count / total * 100, 2)
            distribution[brand] = percentage

        # 【P3-002 修复】结构化日志
        self.logger.info("brand_distribution_analyzed", extra={
            'event': 'brand_distribution_analyzed',
            'brand_count': len(distribution),
            'total_count': total,
        })
        return {
            'data': distribution,
            'total_count': total,
            'warning': None
        }
    
    def analyze_by_model(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        按 AI 模型分析品牌分布
        
        参数:
            results: 诊断结果列表
            
        返回:
            嵌套字典，外层 key 为模型名，内层为品牌分布
            
        示例:
            >>> analyzer.analyze_by_model(results)
            {
                'qwen': {'Nike': 60.0, 'Adidas': 40.0},
                'deepseek': {'Nike': 100.0}
            }
        """
        if not results:
            return {}
        
        # 按模型分组统计
        model_brand_counts = defaultdict(lambda: defaultdict(int))
        
        for result in results:
            model = result.get('model', 'unknown')
            brand = result.get('brand', 'unknown')
            model_brand_counts[model][brand] += 1
        
        # 计算每个模型的分布
        distribution = {}
        for model, brand_counts in model_brand_counts.items():
            total = sum(brand_counts.values())
            distribution[model] = {
                brand: round(count / total * 100, 2)
                for brand, count in brand_counts.items()
            }
        
        self.logger.info(f"按模型分析完成：{len(distribution)} 个模型")
        return distribution
    
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
        """
        if not results:
            return {
                'main_brand': main_brand,
                'main_brand_share': 0.0,
                'competitor_shares': {},
                'rank': 0,
                'total_competitors': 0
            }

        # 【P2-003 修复】处理新的返回格式
        distribution_result = self.analyze(results)
        distribution = distribution_result.get('data', {})

        # 分离主品牌和竞品
        main_brand_share = distribution.get(main_brand, 0.0)
        competitor_shares = {
            brand: share
            for brand, share in distribution.items()
            if brand != main_brand
        }

        # 计算主品牌排名
        sorted_shares = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        rank = next(
            (i + 1 for i, (brand, _) in enumerate(sorted_shares) if brand == main_brand),
            len(sorted_shares) + 1
        )
        
        result = {
            'main_brand': main_brand,
            'main_brand_share': main_brand_share,
            'competitor_shares': competitor_shares,
            'rank': rank,
            'total_competitors': len(competitor_shares),
            'top_competitor': max(competitor_shares.items(), key=lambda x: x[1])[0] if competitor_shares else None
        }
        
        self.logger.info(f"竞品对比分析完成：主品牌排名 #{rank}")
        return result
    
    def analyze_mention_trend(
        self,
        results: List[Dict[str, Any]],
        group_by: str = 'model'
    ) -> Dict[str, Dict[str, int]]:
        """
        分析品牌提及趋势
        
        参数:
            results: 诊断结果列表
            group_by: 分组维度 ('model', 'question')
            
        返回:
            按维度分组的品牌提及次数
        """
        if not results:
            return {}
        
        trend_data = defaultdict(lambda: defaultdict(int))
        
        for result in results:
            group_key = result.get(group_by, 'unknown')
            brand = result.get('brand', 'unknown')
            trend_data[group_key][brand] += 1
        
        # 转换为普通字典
        return {k: dict(v) for k, v in trend_data.items()}
    
    def get_brand_details(
        self,
        results: List[Dict[str, Any]],
        brand_name: str
    ) -> Dict[str, Any]:
        """
        获取单个品牌的详细分析
        
        参数:
            results: 诊断结果列表
            brand_name: 品牌名称
            
        返回:
            品牌详细分析结果
        """
        brand_results = [r for r in results if r.get('brand') == brand_name]
        
        if not brand_results:
            return {
                'brand': brand_name,
                'total_mentions': 0,
                'models': {},
                'questions': {}
            }
        
        # 按模型分组
        model_counts = defaultdict(int)
        for r in brand_results:
            model_counts[r.get('model', 'unknown')] += 1
        
        # 按问题分组
        question_counts = defaultdict(int)
        for r in brand_results:
            question_counts[r.get('question', 'unknown')] += 1
        
        return {
            'brand': brand_name,
            'total_mentions': len(brand_results),
            'models': dict(model_counts),
            'questions': dict(question_counts)
        }
