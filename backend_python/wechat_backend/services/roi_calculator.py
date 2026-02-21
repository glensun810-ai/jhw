#!/usr/bin/env python3
"""
ROI 指标计算器 - 增强版
基于诊断结果计算详细的 ROI 指标

版本：v2.0
日期：2026-02-21
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from wechat_backend.logging_config import api_logger


class ROICalculator:
    """
    ROI 指标计算器
    基于诊断结果计算详细的 ROI 指标
    """
    
    # 行业基准数据
    INDUSTRY_BENCHMARKS = {
        'general': {
            'exposure_roi': 2.5,
            'sentiment_roi': 0.6,
            'ranking_roi': 50,
            'cost_per_impression': 0.5,  # 每次曝光成本（元）
            'value_per_positive_mention': 100  # 每次正面提及价值（元）
        },
        'technology': {
            'exposure_roi': 3.5,
            'sentiment_roi': 0.65,
            'ranking_roi': 55,
            'cost_per_impression': 0.8,
            'value_per_positive_mention': 150
        },
        'retail': {
            'exposure_roi': 2.8,
            'sentiment_roi': 0.55,
            'ranking_roi': 45,
            'cost_per_impression': 0.4,
            'value_per_positive_mention': 80
        },
        'finance': {
            'exposure_roi': 4.2,
            'sentiment_roi': 0.7,
            'ranking_roi': 60,
            'cost_per_impression': 1.0,
            'value_per_positive_mention': 200
        }
    }
    
    def __init__(self, industry: str = 'general'):
        self.logger = api_logger
        self.industry = industry
        self.benchmarks = self.INDUSTRY_BENCHMARKS.get(industry, self.INDUSTRY_BENCHMARKS['general'])
    
    def calculate_roi(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算 ROI 指标
        
        Args:
            report_data: 完整报告数据
        
        Returns:
            ROI 指标字典
        """
        brand_name = report_data.get('reportMetadata', {}).get('brandName', '品牌')
        health_data = report_data.get('brandHealth', {})
        platform_data = report_data.get('platformAnalysis', [])
        negative_data = report_data.get('negativeSources', {})
        
        # 1. 计算曝光 ROI
        exposure_metrics = self._calculate_exposure_roi(brand_name, platform_data)
        
        # 2. 计算情感 ROI
        sentiment_metrics = self._calculate_sentiment_roi(brand_name, health_data, negative_data)
        
        # 3. 计算排名 ROI
        ranking_metrics = self._calculate_ranking_roi(brand_name, platform_data)
        
        # 4. 计算综合 ROI
        overall_metrics = self._calculate_overall_roi(
            exposure_metrics,
            sentiment_metrics,
            ranking_metrics
        )
        
        # 5. 行业对比
        industry_comparison = self._calculate_industry_comparison(
            overall_metrics,
            exposure_metrics,
            sentiment_metrics,
            ranking_metrics
        )
        
        # 6. 确定等级
        roi_grade = self._determine_roi_grade(overall_metrics.get('overall_roi', 0))
        
        return {
            'exposure_roi': exposure_metrics['exposure_roi'],
            'total_impressions': exposure_metrics['total_impressions'],
            'estimated_value': exposure_metrics['estimated_value'],
            'sentiment_roi': sentiment_metrics['sentiment_roi'],
            'positive_mentions': sentiment_metrics['positive_mentions'],
            'negative_mentions': sentiment_metrics['negative_mentions'],
            'neutral_mentions': sentiment_metrics['neutral_mentions'],
            'sentiment_score': sentiment_metrics['sentiment_score'],
            'ranking_roi': ranking_metrics['ranking_roi'],
            'avg_ranking': ranking_metrics['avg_ranking'],
            'top_3_count': ranking_metrics['top_3_count'],
            'top_10_count': ranking_metrics['top_10_count'],
            'overall_roi': overall_metrics['overall_roi'],
            'roi_grade': roi_grade,
            'industry_comparison': industry_comparison,
            'calculated_at': datetime.now().isoformat()
        }
    
    def _calculate_exposure_roi(self, brand_name: str, 
                                platform_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算曝光 ROI"""
        # 估算总曝光
        total_impressions = 0
        for platform in platform_data:
            rank = platform.get('rank', 10)
            # 排名越靠前，曝光越多（简化模型）
            impressions = max(0, (11 - rank) * 1000)
            total_impressions += impressions
        
        # 估算价值
        estimated_value = total_impressions * self.benchmarks['cost_per_impression']
        
        # 假设投入 1000 元
        investment = 1000
        exposure_roi = round(estimated_value / investment, 2) if investment > 0 else 0
        
        return {
            'exposure_roi': exposure_roi,
            'total_impressions': total_impressions,
            'estimated_value': round(estimated_value, 2),
            'investment': investment
        }
    
    def _calculate_sentiment_roi(self, brand_name: str, 
                                 health_data: Dict[str, Any],
                                 negative_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算情感 ROI"""
        # 从健康度获取情感得分
        dimension_scores = health_data.get('dimension_scores', {})
        purity_score = dimension_scores.get('purity', 50)
        
        # 从负面信源获取负面提及
        negative_summary = negative_data.get('summary', {})
        negative_count = negative_summary.get('total_count', 0)
        
        # 估算正面/中性/负面提及
        total_mentions = 100  # 标准化为 100 次提及
        positive_ratio = (purity_score / 100) * 0.7  # 70% 最大正面率
        negative_ratio = (negative_count / 10) * 0.3  # 最多 30% 负面
        
        positive_mentions = int(total_mentions * positive_ratio)
        negative_mentions = int(total_mentions * negative_ratio)
        neutral_mentions = total_mentions - positive_mentions - negative_mentions
        
        # 情感得分
        sentiment_score = (positive_mentions - negative_mentions) / total_mentions
        
        # 情感 ROI
        sentiment_roi = round((sentiment_score + 1) * 0.5, 2)  # 归一化到 0-1
        
        return {
            'sentiment_roi': sentiment_roi,
            'positive_mentions': positive_mentions,
            'negative_mentions': negative_mentions,
            'neutral_mentions': neutral_mentions,
            'sentiment_score': round(sentiment_score, 2),
            'total_mentions': total_mentions
        }
    
    def _calculate_ranking_roi(self, brand_name: str,
                               platform_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算排名 ROI"""
        if not platform_data:
            return {
                'ranking_roi': 0,
                'avg_ranking': 10,
                'top_3_count': 0,
                'top_10_count': 0
            }
        
        # 计算平均排名
        rankings = [p.get('rank', 10) for p in platform_data]
        avg_ranking = sum(rankings) / len(rankings)
        
        # 计算前 3 和前 10 数量
        top_3_count = sum(1 for r in rankings if r <= 3)
        top_10_count = sum(1 for r in rankings if r <= 10)
        
        # 排名 ROI（排名越靠前分数越高）
        ranking_roi = round(max(0, 100 - avg_ranking * 5), 1)
        
        return {
            'ranking_roi': ranking_roi,
            'avg_ranking': round(avg_ranking, 1),
            'top_3_count': top_3_count,
            'top_10_count': top_10_count,
            'total_platforms': len(platform_data)
        }
    
    def _calculate_overall_roi(self, exposure: Dict[str, Any],
                               sentiment: Dict[str, Any],
                               ranking: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合 ROI"""
        # 加权平均
        exposure_weight = 0.4
        sentiment_weight = 0.3
        ranking_weight = 0.3
        
        overall_roi = (
            exposure['exposure_roi'] * 10 * exposure_weight +  # 放大到 0-100 尺度
            sentiment['sentiment_roi'] * 100 * sentiment_weight +
            ranking['ranking_roi'] * ranking_weight
        )
        
        return {
            'overall_roi': round(overall_roi, 1),
            'weights': {
                'exposure': exposure_weight,
                'sentiment': sentiment_weight,
                'ranking': ranking_weight
            }
        }
    
    def _calculate_industry_comparison(self, overall: Dict[str, Any],
                                       exposure: Dict[str, Any],
                                       sentiment: Dict[str, Any],
                                       ranking: Dict[str, Any]) -> Dict[str, Any]:
        """计算行业对比"""
        return {
            'exposure_roi_vs_industry': round(
                exposure['exposure_roi'] - self.benchmarks['exposure_roi'], 2
            ),
            'sentiment_roi_vs_industry': round(
                sentiment['sentiment_roi'] - self.benchmarks['sentiment_roi'], 2
            ),
            'ranking_roi_vs_industry': round(
                ranking['ranking_roi'] - self.benchmarks['ranking_roi'], 1
            ),
            'overall_vs_industry': round(
                overall['overall_roi'] - (
                    self.benchmarks['exposure_roi'] * 4 +
                    self.benchmarks['sentiment_roi'] * 30 +
                    self.benchmarks['ranking_roi'] * 0.3
                ) / 3, 1
            ),
            'industry': self.industry,
            'industry_benchmarks': self.benchmarks
        }
    
    def _determine_roi_grade(self, overall_roi: float) -> str:
        """确定 ROI 等级"""
        if overall_roi >= 80:
            return 'A+'
        elif overall_roi >= 70:
            return 'A'
        elif overall_roi >= 60:
            return 'B'
        elif overall_roi >= 50:
            return 'C'
        else:
            return 'D'


# 全局计算器实例
_roi_calculator = None


def get_roi_calculator(industry: str = 'general') -> ROICalculator:
    """获取 ROI 计算器实例"""
    global _roi_calculator
    if _roi_calculator is None:
        _roi_calculator = ROICalculator(industry)
    return _roi_calculator
