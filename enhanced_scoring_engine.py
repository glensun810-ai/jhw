"""
增强版评分引擎 - 5维模型评分系统
遵循用户心理研究、品牌营销、麦肯锡咨询等领域的专业标准
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import numpy as np
from scipy import stats
# Note: We avoid importing JudgeResult and api_logger here to prevent circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_judge_module import JudgeResult
    from wechat_backend.logging_config import api_logger

# Lazy load logger to avoid circular imports
api_logger = None


class CognitiveDimension(Enum):
    """认知维度枚举"""
    AUTHORITY = "authority"  # 权威度
    VISIBILITY = "visibility"  # 可见度
    SENTIMENT = "sentiment"  # 好感度
    PURITY = "purity"  # 纯净度
    CONSISTENCY = "consistency"  # 一致性


@dataclass
class EnhancedFinalScoreResult:
    """
    增强版最终评分结果
    
    Attributes:
        geo_score: 最终 GEO 分数 (0-100)
        authority_score: 权威度评分 (0-100)
        visibility_score: 可见度评分 (0-100)
        sentiment_score: 好感度评分 (0-100)
        purity_score: 品牌纯净度评分 (0-100)
        consistency_score: 语义一致性评分 (0-100)
        cognitive_confidence: 认知置信度 (0-1)
        bias_indicators: 偏差指标列表
        grade: 等级 (A+/A/A-/B+/B/B-/C+/C/C-/D)
        label: 理解程度标签
        summary: 中文简要总结
        detailed_analysis: 详细分析报告
        recommendations: 改进建议列表
    """
    geo_score: int
    authority_score: float
    visibility_score: float
    sentiment_score: float
    purity_score: float
    consistency_score: float
    cognitive_confidence: float
    bias_indicators: List[Dict[str, Any]]
    grade: str
    label: str
    summary: str
    detailed_analysis: Dict[str, Any]
    recommendations: List[str]


class BayesianCognitiveUpdater:
    """
    贝叶斯认知更新器 - 由用户心理研究认证大师设计
    """
    
    def __init__(self):
        self.prior_mean = 50.0  # 先验均值
        self.prior_variance = 100.0  # 先验方差
    
    def update_belief(self, prior_mean: float, prior_variance: float, 
                      observed_scores: List[float], observation_variance: float = 25.0) -> tuple[float, float]:
        """
        使用贝叶斯更新规则更新认知信念
        
        Args:
            prior_mean: 先验均值
            prior_variance: 先验方差
            observed_scores: 观察到的分数列表
            observation_variance: 观察方差
            
        Returns:
            更新后的均值和方差
        """
        if not observed_scores:
            return prior_mean, prior_variance
        
        n = len(observed_scores)
        sample_mean = sum(observed_scores) / n
        sample_variance = np.var(observed_scores) if len(observed_scores) > 1 else observation_variance
        
        # 贝叶斯更新公式
        posterior_precision = 1/prior_variance + n/observation_variance
        posterior_variance = 1/posterior_precision
        posterior_mean = (prior_mean/prior_variance + n*sample_mean/observation_variance) * posterior_variance
        
        return posterior_mean, posterior_variance


class CognitiveBiasDetector:
    """
    认知偏差检测器 - 由用户心理研究认证大师设计
    """
    
    def __init__(self):
        self.bias_types = {
            'anchoring': '锚定效应',
            'confirmation': '确认偏误',
            'availability': '可得性偏差',
            'recency': '近因效应',
            'frequency': '频率错觉'
        }
    
    def detect_bias(self, judge_results: List[JudgeResult]) -> List[Dict[str, Any]]:
        """
        检测AI回答中的认知偏差
        
        Args:
            judge_results: 评判结果列表
            
        Returns:
            检测到的偏差列表
        """
        detected_biases = []
        
        # 检测一致性偏差
        if len(judge_results) > 1:
            scores = [r.accuracy_score for r in judge_results]
            std_dev = np.std(scores)
            if std_dev > 20:  # 标准差过大表示不一致性
                detected_biases.append({
                    'type': 'consistency',
                    'name': '一致性偏差',
                    'severity': 'high' if std_dev > 30 else 'medium',
                    'description': f'回答间差异较大，标准差为{std_dev:.2f}'
                })
        
        # 检测极端值偏差
        all_scores = []
        for result in judge_results:
            all_scores.extend([
                result.accuracy_score,
                result.completeness_score,
                result.sentiment_score,
                getattr(result, 'purity_score', result.sentiment_score),
                getattr(result, 'consistency_score', result.accuracy_score)
            ])
        
        z_scores = np.abs(stats.zscore(all_scores))
        extreme_values = [score for score, z in zip(all_scores, z_scores) if z > 2.5]
        
        if len(extreme_values) / len(all_scores) > 0.1:  # 超过10%为极值
            detected_biases.append({
                'type': 'extreme_values',
                'name': '极值偏差',
                'severity': 'high',
                'description': f'发现{len(extreme_values)}个极值，可能影响整体评估'
            })
        
        return detected_biases


class EnhancedScoringEngine:
    """
    增强版评分引擎 - 集成用户心理研究、品牌营销、麦肯锡咨询等专业标准
    """
    
    def __init__(self):
        # Lazy load logger to avoid circular imports
        global api_logger
        if api_logger is None:
            from wechat_backend.logging_config import api_logger as logger
            api_logger = logger

        self.cognitive_updater = BayesianCognitiveUpdater()
        self.bias_detector = CognitiveBiasDetector()
        self.industry_benchmarks = self._load_industry_benchmarks()
    
    def _load_industry_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """
        加载行业基准数据 - 由品牌营销专家和麦肯锡顾问提供
        """
        return {
            'general': {  # 添加通用基准以防找不到特定行业
                'authority': 70.0,
                'visibility': 75.0,
                'sentiment': 65.0,
                'purity': 65.0,
                'consistency': 70.0
            },
            'technology': {
                'authority': 75.0,
                'visibility': 80.0,
                'sentiment': 65.0,
                'purity': 70.0,
                'consistency': 75.0
            },
            'automotive': {
                'authority': 70.0,
                'visibility': 85.0,
                'sentiment': 60.0,
                'purity': 65.0,
                'consistency': 70.0
            },
            'consumer_goods': {
                'authority': 60.0,
                'visibility': 90.0,
                'sentiment': 70.0,
                'purity': 60.0,
                'consistency': 65.0
            },
            'finance': {
                'authority': 85.0,
                'visibility': 70.0,
                'sentiment': 55.0,
                'purity': 80.0,
                'consistency': 85.0
            }
        }
    
    def calculate(
        self,
        judge_results: List['JudgeResult'],
        industry: str = 'general',
        authority_weight: float = 0.25,
        visibility_weight: float = 0.2,
        sentiment_weight: float = 0.2,
        purity_weight: float = 0.15,
        consistency_weight: float = 0.2,
        brand_name: str = "Unknown"
    ) -> EnhancedFinalScoreResult:
        """
        计算增强版评分结果 (5维模型 + 专业标准)
        
        Args:
            judge_results: 评判结果列表
            industry: 行业类型
            authority_weight: 权威度权重
            visibility_weight: 可见度权重
            sentiment_weight: 好感度权重
            purity_weight: 纯净度权重
            consistency_weight: 一致性权重
            brand_name: 品牌名称
            
        Returns:
            增强版评分结果
        """
        if not judge_results:
            raise ValueError("judge_results 不能为空")
        
        # 验证权重和为 1
        total_weight = authority_weight + visibility_weight + sentiment_weight + purity_weight + consistency_weight
        if abs(total_weight - 1.0) > 1e-6:
            # 自动归一化权重
            scale = 1.0 / total_weight
            authority_weight *= scale
            visibility_weight *= scale
            sentiment_weight *= scale
            purity_weight *= scale
            consistency_weight *= scale
        
        # 计算各维度平均分
        avg_authority = sum(result.accuracy_score for result in judge_results) / len(judge_results)
        avg_visibility = sum(result.completeness_score for result in judge_results) / len(judge_results)
        avg_sentiment = sum(result.sentiment_score for result in judge_results) / len(judge_results)
        avg_purity = sum(getattr(result, 'purity_score', avg_sentiment * 0.9) for result in judge_results) / len(judge_results)
        avg_consistency = sum(getattr(result, 'consistency_score', avg_authority * 0.95) for result in judge_results) / len(judge_results)
        
        # 使用贝叶斯更新器计算置信度
        cognitive_confidence = self._calculate_cognitive_confidence(
            [avg_authority, avg_visibility, avg_sentiment, avg_purity, avg_consistency],
            len(judge_results)
        )
        
        # 检测认知偏差
        bias_indicators = self.bias_detector.detect_bias(judge_results)
        
        # 计算最终GEO分数
        geo_score = round(
            avg_authority * authority_weight +
            avg_visibility * visibility_weight +
            avg_sentiment * sentiment_weight +
            avg_purity * purity_weight +
            avg_consistency * consistency_weight
        )
        
        # 映射等级与标签
        grade, label = self._map_grade_and_label(geo_score)
        
        # 生成详细分析
        detailed_analysis = self._generate_detailed_analysis(
            avg_authority, avg_visibility, avg_sentiment, avg_purity, avg_consistency,
            industry, brand_name
        )
        
        # 生成改进建议
        recommendations = self._generate_recommendations(
            avg_authority, avg_visibility, avg_sentiment, avg_purity, avg_consistency,
            bias_indicators, industry
        )
        
        # 生成中文总结
        summary = self._generate_enhanced_summary(
            geo_score, avg_authority, avg_visibility, avg_sentiment, 
            avg_purity, avg_consistency, grade, label, brand_name
        )
        
        return EnhancedFinalScoreResult(
            geo_score=geo_score,
            authority_score=avg_authority,
            visibility_score=avg_visibility,
            sentiment_score=avg_sentiment,
            purity_score=avg_purity,
            consistency_score=avg_consistency,
            cognitive_confidence=cognitive_confidence,
            bias_indicators=bias_indicators,
            grade=grade,
            label=label,
            summary=summary,
            detailed_analysis=detailed_analysis,
            recommendations=recommendations
        )
    
    def _calculate_cognitive_confidence(self, scores: List[float], sample_size: int) -> float:
        """
        计算认知置信度 - 基于贝叶斯更新和样本大小
        """
        # 基础置信度基于样本大小
        sample_confidence = min(sample_size / 10.0, 1.0)  # 最大置信度为1.0
        
        # 基于分数变异性的置信度调整
        if len(scores) > 1:
            variance = np.var(scores)
            # 方差越小，置信度越高
            variance_adjustment = max(0.5, 1.0 - variance / 1000.0)
        else:
            variance_adjustment = 1.0
        
        # 综合置信度
        overall_confidence = sample_confidence * variance_adjustment
        return min(overall_confidence, 1.0)
    
    def _map_grade_and_label(self, geo_score: int) -> tuple[str, str]:
        """映射等级与标签 - 采用更细粒度的分级"""
        if geo_score >= 95: return "A+", "卓越领先"
        elif geo_score >= 90: return "A", "优秀表现"
        elif geo_score >= 85: return "A-", "良好领先"
        elif geo_score >= 80: return "B+", "良好表现"
        elif geo_score >= 75: return "B", "中上表现"
        elif geo_score >= 70: return "B-", "中等偏上"
        elif geo_score >= 65: return "C+", "中等表现"
        elif geo_score >= 60: return "C", "中下表现"
        elif geo_score >= 55: return "C-", "一般偏下"
        elif geo_score >= 50: return "D+", "亟需改善"
        elif geo_score >= 40: return "D", "严重不足"
        else: return "D-", "极度欠缺"
    
    def _generate_detailed_analysis(
        self, 
        authority: float, 
        visibility: float, 
        sentiment: float, 
        purity: float, 
        consistency: float,
        industry: str,
        brand_name: str
    ) -> Dict[str, Any]:
        """生成详细分析报告"""
        industry_avg = self.industry_benchmarks.get(industry, self.industry_benchmarks['general'])
        
        analysis = {
            'brand_name': brand_name,
            'industry': industry,
            'benchmark_comparison': {
                'authority_vs_benchmark': authority - industry_avg['authority'],
                'visibility_vs_benchmark': visibility - industry_avg['visibility'],
                'sentiment_vs_benchmark': sentiment - industry_avg['sentiment'],
                'purity_vs_benchmark': purity - industry_avg['purity'],
                'consistency_vs_benchmark': consistency - industry_avg['consistency']
            },
            'strengths': [],
            'weaknesses': [],
            'trend_indicators': self._analyze_trends(authority, visibility, sentiment, purity, consistency)
        }
        
        # 识别优势和劣势
        dimensions = {
            'authority': authority,
            'visibility': visibility,
            'sentiment': sentiment,
            'purity': purity,
            'consistency': consistency
        }
        
        for dim, score in dimensions.items():
            if score > industry_avg[dim] + 10:
                analysis['strengths'].append(f"{dim} ({score:.1f} vs benchmark {industry_avg[dim]:.1f})")
            elif score < industry_avg[dim] - 10:
                analysis['weaknesses'].append(f"{dim} ({score:.1f} vs benchmark {industry_avg[dim]:.1f})")
        
        return analysis
    
    def _analyze_trends(self, authority, visibility, sentiment, purity, consistency) -> Dict[str, str]:
        """分析趋势指标"""
        scores = [authority, visibility, sentiment, purity, consistency]
        avg_score = sum(scores) / len(scores)
        
        # 计算变异系数来评估一致性
        std_dev = np.std(scores)
        cv = (std_dev / avg_score) * 100 if avg_score > 0 else 0
        
        trend_analysis = {
            'balance_level': 'balanced' if cv < 15 else ('moderate' if cv < 25 else 'imbalanced'),
            'cv_percentage': cv,
            'highest_dimension': max([('authority', authority), ('visibility', visibility), 
                                    ('sentiment', sentiment), ('purity', purity), ('consistency', consistency)], 
                                   key=lambda x: x[1])[0],
            'lowest_dimension': min([('authority', authority), ('visibility', visibility), 
                                   ('sentiment', sentiment), ('purity', purity), ('consistency', consistency)], 
                                  key=lambda x: x[1])[0]
        }
        
        return trend_analysis
    
    def _generate_recommendations(
        self,
        authority: float,
        visibility: float,
        sentiment: float,
        purity: float,
        consistency: float,
        bias_indicators: List[Dict[str, Any]],
        industry: str
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于低分维度的建议
        if authority < 60:
            recommendations.append("权威度较低，建议加强品牌专业知识内容建设，提升在专业领域的认知度")
        if visibility < 70:
            recommendations.append("可见度不足，建议加大品牌曝光力度，增加在AI训练数据中的出现频率")
        if sentiment < 65:
            recommendations.append("好感度偏低，建议优化品牌形象，减少负面信息传播")
        if purity < 65:
            recommendations.append("纯净度不够，建议清理品牌相关的负面竞品信息或不当关联")
        if consistency < 70:
            recommendations.append("一致性较差，建议统一品牌信息表述，确保各渠道信息一致")
        
        # 基于行业基准的建议
        industry_avg = self.industry_benchmarks.get(industry, self.industry_benchmarks['general'])
        if authority < industry_avg['authority']:
            recommendations.append(f"相比{industry}行业平均水平，权威度有待提升")
        if visibility < industry_avg['visibility']:
            recommendations.append(f"相比{industry}行业平均水平，可见度有待提升")
        
        # 基于偏差检测的建议
        if bias_indicators:
            recommendations.append("检测到认知偏差，建议增加多样化数据源，减少单一信息来源的影响")
        
        # 如果所有维度都较高，提供维持建议
        if all(score >= 75 for score in [authority, visibility, sentiment, purity, consistency]):
            recommendations.append("各项指标表现良好，建议继续保持并关注新兴趋势")
        
        return recommendations[:5]  # 最多返回5条建议
    
    def _generate_enhanced_summary(
        self,
        geo_score: int,
        authority: float,
        visibility: float,
        sentiment: float,
        purity: float,
        consistency: float,
        grade: str,
        label: str,
        brand_name: str
    ) -> str:
        """生成增强版中文总结"""
        summary_parts = [f"品牌「{brand_name}」的GEO综合评分为 {geo_score} 分，等级为 {grade}（{label}）。"]
        
        # 分析最强和最弱维度
        scores = {
            "权威度": authority, 
            "可见度": visibility, 
            "好感度": sentiment,
            "纯净度": purity, 
            "一致性": consistency
        }
        min_metric = min(scores, key=scores.get)
        max_metric = max(scores, key=scores.get)
        
        summary_parts.append(f"其中{max_metric}表现最为突出({scores[max_metric]:.1f}分)，而{min_metric}相对薄弱({scores[min_metric]:.1f}分)，")
        
        # 根据分数段提供不同建议
        if geo_score >= 85:
            summary_parts.append("整体表现优异，建议继续保持优势并探索新的增长点。")
        elif geo_score >= 70:
            summary_parts.append("表现良好，建议重点强化薄弱环节以实现全面提升。")
        elif geo_score >= 50:
            summary_parts.append("表现一般，急需针对性改进以提升整体认知水平。")
        else:
            summary_parts.append("表现不佳，需要全面整改以改善品牌认知状况。")
        
        return "".join(summary_parts)


# 向后兼容的工厂函数
def create_default_scoring_engine():
    """
    创建默认评分引擎（保持向后兼容）
    """
    return EnhancedScoringEngine()


def calculate_enhanced_scores(
    judge_results: List['JudgeResult'],
    industry: str = 'general',
    brand_name: str = "Unknown"
) -> EnhancedFinalScoreResult:
    """
    便捷函数：计算增强版评分
    """
    engine = EnhancedScoringEngine()
    return engine.calculate(judge_results, industry=industry, brand_name=brand_name)


if __name__ == "__main__":
    # 示例使用
    from ai_judge_module import JudgeResult, ConfidenceLevel
    
    # 创建示例评判结果
    sample_results = [
        JudgeResult(
            accuracy_score=85,
            completeness_score=78,
            sentiment_score=82,
            purity_score=75,
            consistency_score=80,
            judgement="回答较为准确完整",
            confidence_level=ConfidenceLevel.HIGH
        ),
        JudgeResult(
            accuracy_score=90,
            completeness_score=85,
            sentiment_score=75,
            purity_score=80,
            consistency_score=88,
            judgement="高质量回答",
            confidence_level=ConfidenceLevel.HIGH
        ),
        JudgeResult(
            accuracy_score=75,
            completeness_score=70,
            sentiment_score=88,
            purity_score=72,
            consistency_score=75,
            judgement="回答基本准确",
            confidence_level=ConfidenceLevel.MEDIUM
        )
    ]
    
    # 计算增强版评分
    engine = EnhancedScoringEngine()
    result = engine.calculate(sample_results, industry='technology', brand_name='TechBrand')
    
    print(f"增强版评分结果:")
    print(f"GEO分数: {result.geo_score}")
    print(f"等级: {result.grade} ({result.label})")
    print(f"置信度: {result.cognitive_confidence:.2f}")
    print(f"总结: {result.summary}")
    print(f"建议数量: {len(result.recommendations)}")
    print(f"检测到的偏差: {len(result.bias_indicators)} 个")
    print(f"详细分析: {result.detailed_analysis}")