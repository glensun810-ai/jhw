from dataclasses import dataclass
from typing import List
# Note: We avoid importing JudgeResult here to prevent circular imports
# Instead, we use forward references and type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_judge_module import JudgeResult


@dataclass
class FinalScoreResult:
    """
    GEO 内容质量验证器的最终评分结果
    
    Attributes:
        geo_score: 最终 GEO 分数 (0-100)
        authority_score: 权威度评分
        visibility_score: 可见度评分
        sentiment_score: 好感度评分
        purity_score: 品牌纯净度评分 (新增)
        consistency_score: 语义一致性评分 (新增)
        grade: 等级 (A/B/C/D)
        label: 理解程度标签
        summary: 中文简要总结
    """
    geo_score: int
    authority_score: float
    visibility_score: float
    sentiment_score: float
    purity_score: float
    consistency_score: float
    grade: str
    label: str
    summary: str


class ScoringEngine:
    """
    GEO 内容质量验证器的评分引擎
    """
    
    def calculate(
        self,
        judge_results: List['JudgeResult'],
        authority_weight: float = 0.25,
        visibility_weight: float = 0.2,
        sentiment_weight: float = 0.2,
        purity_weight: float = 0.15,
        consistency_weight: float = 0.2
    ) -> FinalScoreResult:
        """
        计算最终评分结果 (5维模型)
        """
        if not judge_results:
            raise ValueError("judge_results 不能为空")
        
        # 验证权重和为 1
        total_weight = authority_weight + visibility_weight + sentiment_weight + purity_weight + consistency_weight
        if abs(total_weight - 1.0) > 1e-6:
            # 自动归一化权重，防止报错
            scale = 1.0 / total_weight
            authority_weight *= scale
            visibility_weight *= scale
            sentiment_weight *= scale
            purity_weight *= scale
            consistency_weight *= scale
        
        # 计算聚合分数
        avg_authority = sum(result.accuracy_score for result in judge_results) / len(judge_results)
        avg_visibility = sum(result.completeness_score for result in judge_results) / len(judge_results)
        avg_sentiment = sum(result.sentiment_score for result in judge_results) / len(judge_results)
        
        # 对于新增维度，如果 JudgeResult 中没有（旧代码兼容），则基于其他分数估算
        # 在实际生产中，JudgeResult 应该包含这些字段
        avg_purity = sum(getattr(result, 'purity_score', avg_sentiment * 0.9) for result in judge_results) / len(judge_results)
        avg_consistency = sum(getattr(result, 'consistency_score', avg_authority * 0.95) for result in judge_results) / len(judge_results)
        
        # 计算最终 GEO Score
        geo_score = round(
            avg_authority * authority_weight + 
            avg_visibility * visibility_weight + 
            avg_sentiment * sentiment_weight +
            avg_purity * purity_weight +
            avg_consistency * consistency_weight
        )
        
        # 映射等级与标签
        grade, label = self._map_grade_and_label(geo_score)
        
        # 生成中文总结
        summary = self._generate_summary(geo_score, avg_authority, avg_visibility, avg_sentiment, avg_purity, avg_consistency, grade, label)
        
        return FinalScoreResult(
            geo_score=geo_score,
            authority_score=avg_authority,
            visibility_score=avg_visibility,
            sentiment_score=avg_sentiment,
            purity_score=avg_purity,
            consistency_score=avg_consistency,
            grade=grade,
            label=label,
            summary=summary
        )
    
    def _map_grade_and_label(self, geo_score: int) -> tuple[str, str]:
        if geo_score >= 85: return "A", "卓越表现"
        elif geo_score >= 70: return "B", "良好表现"
        elif geo_score >= 50: return "C", "一般表现"
        else: return "D", "亟待优化"
    
    def _generate_summary(
        self,
        geo_score: int,
        authority: float,
        visibility: float,
        sentiment: float,
        purity: float,
        consistency: float,
        grade: str,
        label: str
    ) -> str:
        summary_parts = [f"GEO 综合评分为 {geo_score} 分，等级为 {grade}。"]
        
        # 简要分析短板
        scores = {
            "权威度": authority, "可见度": visibility, "好感度": sentiment,
            "纯净度": purity, "一致性": consistency
        }
        min_metric = min(scores, key=scores.get)
        max_metric = max(scores, key=scores.get)
        
        summary_parts.append(f"您的{max_metric}表现最佳({scores[max_metric]:.1f})，但{min_metric}相对薄弱({scores[min_metric]:.1f})，建议重点优化。")
        
        return "".join(summary_parts)