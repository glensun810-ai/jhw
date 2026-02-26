"""
质量评分服务

P2-011 优化：将质量评分逻辑从执行引擎中提取为独立服务
便于测试、维护和调整权重
"""

from typing import List, Dict, Any


class QualityScorer:
    """
    质量评分器
    
    评分标准：
    - 完成率（40 分）：结果数/预期任务数
    - 数据完整度（30 分）：每个结果的字段完整性
    - 信源质量（20 分）：引用信源的数量和质量
    - 情感分析（10 分）：情感值的有效性
    """
    
    # 权重配置（可调整）
    WEIGHTS = {
        'completion': 0.4,      # 完成率权重
        'completeness': 0.3,    # 完整度权重
        'sources': 0.2,         # 信源权重
        'sentiment': 0.1        # 情感权重
    }
    
    # 质量等级阈值
    LEVEL_THRESHOLDS = {
        'excellent': 90,  # 优秀
        'good': 75,       # 良好
        'fair': 60,       # 一般
        'poor': 0         # 较差
    }
    
    def calculate(self, results: List[Dict[str, Any]], completion_rate: int) -> Dict[str, Any]:
        """
        计算质量评分
        
        参数:
        - results: 结果列表
        - completion_rate: 完成率（0-100）
        
        返回:
        - quality_score: 0-100 分
        - quality_level: 'excellent', 'good', 'fair', 'poor'
        - details: 详细评分信息
        """
        if not results:
            return {
                'quality_score': 0,
                'quality_level': 'poor',
                'details': {
                    'completion_score': 0,
                    'completeness_score': 0,
                    'source_score': 0,
                    'sentiment_score': 0
                }
            }
        
        # 1. 完成率得分（40 分）
        completion_score = int(completion_rate * self.WEIGHTS['completion'])
        
        # 2. 数据完整度得分（30 分）
        completeness_score = self._calculate_completeness(results)
        
        # 3. 信源质量得分（20 分）
        source_score = self._calculate_source_quality(results)
        
        # 4. 情感分析得分（10 分）
        sentiment_score = self._calculate_sentiment_validity(results)
        
        # 总分
        quality_score = completion_score + completeness_score + source_score + sentiment_score
        quality_score = min(quality_score, 100)  # 不超过 100
        
        # 质量等级
        quality_level = self._get_level(quality_score)
        
        return {
            'quality_score': quality_score,
            'quality_level': quality_level,
            'details': {
                'completion_score': completion_score,
                'completeness_score': int(completeness_score),
                'source_score': int(source_score),
                'sentiment_score': int(sentiment_score)
            }
        }
    
    def _calculate_completeness(self, results: List[Dict[str, Any]]) -> float:
        """
        计算数据完整度得分（30 分）
        
        检查字段：
        - brand_mentioned: 品牌提及
        - rank: 排名
        - sentiment: 情感
        - cited_sources: 引用信源
        - interception: 拦截分析
        """
        completeness_scores = []

        for result in results:
            # 【P0 修复】处理 geo_data 为 None 的情况
            geo_data = result.get('geo_data') or {}

            fields = [
                geo_data.get('brand_mentioned', False),
                geo_data.get('rank') is not None and geo_data.get('rank') >= 0,
                geo_data.get('sentiment') is not None,
                len(geo_data.get('cited_sources', [])) > 0,
                geo_data.get('interception') is not None
            ]

            field_score = sum(fields) / len(fields) * 100
            completeness_scores.append(field_score)

        avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
        return avg_completeness * self.WEIGHTS['completeness']
    
    def _calculate_source_quality(self, results: List[Dict[str, Any]]) -> float:
        """
        计算信源质量得分（20 分）

        每个结果最多 5 个信源，每个信源 4 分
        """
        source_counts = []

        for result in results:
            # 【P0 修复】处理 geo_data 为 None 的情况
            geo_data = result.get('geo_data') or {}
            source_count = len(geo_data.get('cited_sources', []))
            # 最多 5 个信源，每个 20 分
            source_score = min(source_count, 5) / 5 * 100
            source_counts.append(source_score)

        avg_sources = sum(source_counts) / len(source_counts) if source_counts else 0
        return avg_sources * self.WEIGHTS['sources']

    def _calculate_sentiment_validity(self, results: List[Dict[str, Any]]) -> float:
        """
        计算情感分析有效性得分（10 分）

        检查情感值是否在有效范围 [-1, 1]
        """
        sentiment_valid = 0

        for result in results:
            # 【P0 修复】处理 geo_data 为 None 的情况
            geo_data = result.get('geo_data') or {}
            sentiment = geo_data.get('sentiment')

            if sentiment is not None and -1 <= sentiment <= 1:
                sentiment_valid += 1

        validity_rate = sentiment_valid / len(results) if results else 0
        return validity_rate * 100 * self.WEIGHTS['sentiment']
    
    def _get_level(self, score: int) -> str:
        """
        根据评分获取质量等级
        """
        if score >= self.LEVEL_THRESHOLDS['excellent']:
            return 'excellent'
        elif score >= self.LEVEL_THRESHOLDS['good']:
            return 'good'
        elif score >= self.LEVEL_THRESHOLDS['fair']:
            return 'fair'
        else:
            return 'poor'
    
    def get_level_text(self, level: str) -> str:
        """
        获取质量等级文本（中文）
        """
        level_map = {
            'excellent': '优秀',
            'good': '良好',
            'fair': '一般',
            'poor': '较差'
        }
        return level_map.get(level, '未知')


# 单例实例
_quality_scorer = None

def get_quality_scorer() -> QualityScorer:
    """
    获取质量评分器单例
    """
    global _quality_scorer
    if _quality_scorer is None:
        _quality_scorer = QualityScorer()
    return _quality_scorer
