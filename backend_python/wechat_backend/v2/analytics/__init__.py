"""
统计算法模块

提供品牌诊断数据分析的核心统计算法：
- 品牌分布分析
- 情感分析
- 关键词提取
- 趋势对比

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

from wechat_backend.v2.analytics.brand_distribution_analyzer import BrandDistributionAnalyzer
from wechat_backend.v2.analytics.sentiment_analyzer import SentimentAnalyzer
from wechat_backend.v2.analytics.keyword_extractor import KeywordExtractor
from wechat_backend.v2.analytics.trend_analyzer import TrendAnalyzer
from wechat_backend.v2.exceptions import (
    AnalyticsError,
    AnalyticsDataError,
    AnalyticsConfigurationError,
    AnalyticsProcessingError,
)

__all__ = [
    'BrandDistributionAnalyzer',
    'SentimentAnalyzer',
    'KeywordExtractor',
    'TrendAnalyzer',
    'AnalyticsError',
    'AnalyticsDataError',
    'AnalyticsConfigurationError',
    'AnalyticsProcessingError',
]
