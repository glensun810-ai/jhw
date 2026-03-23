"""
核心指标计算器

计算品牌在 AI 认知中的核心指标：
1. 声量份额 (SOV - Share of Voice)
2. 情感得分 (Sentiment Score)
3. 物理排名 (Physical Rank)
4. 影响力得分 (Influence Score)

@author: 系统架构组
@date: 2026-03-22
@version: 1.0
"""

from typing import Dict, Any, List
from collections import defaultdict


def calculate_diagnosis_metrics(
    brand_name: str,
    sov_data: Dict[str, Any],
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    计算诊断核心指标
    
    参数:
        brand_name: 品牌名称
        sov_data: SOV 数据（包含各品牌声量份额）
        results: 诊断结果列表
    
    返回:
        {
            'sov': 声量份额 (0-100),
            'sentiment': 情感得分 (0-100),
            'rank': 物理排名 (1, 2, 3...),
            'influence': 影响力得分 (0-100)
        }
    """
    # 1. 计算 SOV
    sov = _calculate_sov(brand_name, sov_data, results)
    
    # 2. 计算情感得分
    sentiment = _calculate_sentiment(results, brand_name)
    
    # 3. 计算物理排名
    rank = _calculate_rank(results, brand_name)
    
    # 4. 计算影响力得分
    influence = _calculate_influence(sov, sentiment, rank)
    
    return {
        'sov': round(sov, 1),
        'sentiment': round(sentiment, 1),
        'rank': rank,
        'influence': round(influence, 1)
    }


def _calculate_sov(
    brand_name: str,
    sov_data: Dict[str, Any],
    results: List[Dict[str, Any]]
) -> float:
    """
    计算声量份额 (Share of Voice)
    
    SOV = (品牌提及数 / 总提及数) × 100
    
    参数:
        brand_name: 品牌名称
        sov_data: SOV 数据
        results: 诊断结果列表
    
    返回:
        SOV 百分比 (0-100)
    """
    # 如果已有 sov_data，直接使用
    if sov_data and 'brandShare' in sov_data:
        return sov_data['brandShare'].get(brand_name, 0)
    
    # 否则从 results 计算
    if not results:
        return 0.0
    
    # 统计各品牌提及次数
    brand_mentions = defaultdict(int)
    for result in results:
        extracted_brand = result.get('extracted_brand', '')
        if extracted_brand:
            brand_mentions[extracted_brand] += 1
    
    # 计算 SOV
    total_mentions = sum(brand_mentions.values())
    if total_mentions == 0:
        return 0.0
    
    brand_mentions_count = brand_mentions.get(brand_name, 0)
    sov = (brand_mentions_count / total_mentions) * 100
    
    return sov


def _calculate_sentiment(results: List[Dict[str, Any]], brand_name: str) -> float:
    """
    计算情感得分
    
    Sentiment = (正面数 - 负面数) / 总提及数 × 100
    
    参数:
        results: 诊断结果列表
        brand_name: 品牌名称
    
    返回:
        情感得分 (0-100)
    """
    if not results:
        return 50.0  # 默认中性分
    
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    brand_result_count = 0
    
    for result in results:
        extracted_brand = result.get('extracted_brand', '')
        if extracted_brand != brand_name:
            continue
        
        brand_result_count += 1
        
        # 获取情感信息
        sentiment = result.get('sentiment', 'neutral')
        sentiment_score = result.get('sentiment_score', 0)
        
        # 根据情感判断
        if sentiment == 'positive' or sentiment_score > 0.3:
            positive_count += 1
        elif sentiment == 'negative' or sentiment_score < -0.3:
            negative_count += 1
        else:
            neutral_count += 1
    
    if brand_result_count == 0:
        return 50.0
    
    # 计算情感得分 (0-100)
    # (正面数 - 负面数) / 总数 * 50 + 50 (映射到 0-100)
    sentiment_score = ((positive_count - negative_count) / brand_result_count) * 50 + 50
    
    # 限制在 0-100 范围
    return max(0, min(100, sentiment_score))


def _calculate_rank(results: List[Dict[str, Any]], brand_name: str) -> int:
    """
    计算物理排名
    
    按品牌在 AI 回答中的提及频率排序
    
    参数:
        results: 诊断结果列表
        brand_name: 品牌名称
    
    返回:
        排名 (1, 2, 3...)
    """
    if not results:
        return 1
    
    # 统计各品牌提及次数
    brand_mentions = defaultdict(int)
    for result in results:
        extracted_brand = result.get('extracted_brand', '')
        if extracted_brand:
            brand_mentions[extracted_brand] += 1
    
    if not brand_mentions:
        return 1
    
    # 按提及次数排序
    sorted_brands = sorted(brand_mentions.items(), key=lambda x: x[1], reverse=True)
    
    # 查找品牌排名
    for i, (brand, _) in enumerate(sorted_brands, 1):
        if brand == brand_name:
            return i
    
    # 如果品牌不在列表中，返回最后
    return len(sorted_brands) + 1


def _calculate_influence(sov: float, sentiment: float, rank: int) -> float:
    """
    计算影响力得分
    
    Influence = SOV×0.4 + 情感×0.3 + (1/排名)×100×0.3
    
    参数:
        sov: 声量份额 (0-100)
        sentiment: 情感得分 (0-100)
        rank: 物理排名 (1, 2, 3...)
    
    返回:
        影响力得分 (0-100)
    """
    # 排名得分 (排名越靠前，得分越高)
    rank_score = (1 / rank) * 100 if rank > 0 else 0
    
    # 加权计算
    influence = sov * 0.4 + sentiment * 0.3 + rank_score * 0.3
    
    # 限制在 0-100 范围
    return max(0, min(100, influence))


def calculate_dimension_scores(
    brand_name: str,
    results: List[Dict[str, Any]],
    sov_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    计算评分维度（兼容旧接口）
    
    参数:
        brand_name: 品牌名称
        results: 诊断结果列表
        sov_data: SOV 数据（可选）
    
    返回:
        {
            'authority': 权威度 (0-100),
            'visibility': 可见度 (0-100),
            'purity': 纯净度 (0-100),
            'consistency': 一致性 (0-100)
        }
    """
    # 使用新的 DimensionScorer
    from wechat_backend.services.dimension_scorer import DimensionScorer
    
    scorer = DimensionScorer()
    
    # 提取排名列表
    ranking_list = _extract_ranking_list_from_results(results, brand_name)
    
    # 计算所有维度
    dimension_data = scorer.calculate_all_dimensions(
        results=results,
        brand_name=brand_name,
        ranking_list=ranking_list
    )
    
    # 映射到前端期望的字段名
    return {
        'authority': dimension_data.get('visibility_score', 50),
        'visibility': dimension_data.get('visibility_score', 50),
        'purity': dimension_data.get('sentiment_score', 50),
        'consistency': dimension_data.get('cross_platform_consistency', 100)
    }


def _extract_ranking_list_from_results(results: List[Dict[str, Any]], brand_name: str) -> List[str]:
    """
    从诊断结果中提取品牌排名列表
    
    参数:
        results: 诊断结果列表
        brand_name: 主品牌名
    
    返回:
        品牌排名列表
    """
    from collections import defaultdict
    
    # 统计各品牌提及次数
    brand_counts = defaultdict(int)
    for result in results:
        extracted_brand = result.get('extracted_brand', '')
        if extracted_brand:
            brand_counts[extracted_brand] += 1
    
    if not brand_counts:
        return [brand_name] if brand_name else []
    
    # 按提及次数排序
    sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
    return [brand for brand, _ in sorted_brands]


def generate_diagnostic_wall(
    brand_name: str,
    metrics: Dict[str, Any],
    dimension_scores: Dict[str, Any],
    results: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成问题诊断墙（兼容旧接口）
    
    参数:
        brand_name: 品牌名称
        metrics: 核心指标 {sov, sentiment, rank, influence}
        dimension_scores: 评分维度 {authority, visibility, purity, consistency}
        results: 诊断结果列表（可选）
    
    返回:
        {
            'risk_levels': {'high': [...], 'medium': [...]},
            'priority_recommendations': [...]
        }
    """
    from wechat_backend.services.diagnostic_wall_generator import DiagnosticWallGenerator
    
    generator = DiagnosticWallGenerator()
    
    # 映射维度得分
    visibility_score = dimension_scores.get('visibility', 50)
    sentiment_score = dimension_scores.get('purity', 50)
    consistency_score = dimension_scores.get('consistency', 100)
    
    # 计算排位得分
    rank = metrics.get('rank', 1)
    if rank == 1:
        rank_score = 100
    elif rank == 2:
        rank_score = 80
    elif rank == 3:
        rank_score = 60
    elif rank == 4:
        rank_score = 40
    else:
        rank_score = 20
    
    # 计算 SOV 得分
    sov = metrics.get('sov', 50)
    if sov >= 40:
        sov_score = 100
    elif sov >= 30:
        sov_score = 80
    elif sov >= 20:
        sov_score = 60
    elif sov >= 10:
        sov_score = 40
    else:
        sov_score = 20
    
    # 计算综合得分
    overall_score = round(
        visibility_score * 0.25 +
        rank_score * 0.35 +
        sov_score * 0.25 +
        sentiment_score * 0.15
    )
    
    # 生成诊断墙
    return generator.generate(
        visibility_score=visibility_score,
        rank_score=rank_score,
        sov_score=sov_score,
        sentiment_score=sentiment_score,
        overall_score=overall_score,
        cross_platform_consistency=consistency_score,
        detailed_data={
            'position': rank,
            'sov': sov,
            'sentiment': metrics.get('sentiment', 0)
        }
    )
