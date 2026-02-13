"""
影响力计算器 - 根据引用频次、模型覆盖度和关联品牌的情感偏向计算信源的影响力指数
"""
from typing import Dict, List, Tuple
import math


class ImpactCalculator:
    """
    影响力计算器
    根据引用频次、模型覆盖度和关联品牌的情感偏向，计算信源的影响力指数
    """

    def __init__(self):
        # 权重配置
        self.weights = {
            'citation_count': 0.4,      # 引用频次权重
            'model_coverage': 0.3,      # 模型覆盖度权重
            'sentiment_bias': 0.3       # 情感偏向权重
        }

    def calculate_impact_index(
        self,
        citation_count: int,
        model_coverage: int,
        sentiment_score: float = 0.0,
        domain_authority: str = 'Medium'
    ) -> float:
        """
        计算影响力指数

        Args:
            citation_count: 引用频次
            model_coverage: 模型覆盖度（被多少个不同AI模型引用）
            sentiment_score: 情感偏向得分 (-1.0 到 1.0)
            domain_authority: 域名权威度 ('High', 'Medium', 'Low')

        Returns:
            影响力指数 (0.0 到 100.0)
        """
        # 标准化引用频次得分 (0-100)
        normalized_citation_score = self._normalize_citation_score(citation_count)

        # 标准化模型覆盖度得分 (0-100)
        normalized_coverage_score = self._normalize_coverage_score(model_coverage)

        # 情感偏向得分调整 (-1.0 到 1.0 映射到 0-100)
        normalized_sentiment_score = self._normalize_sentiment_score(sentiment_score)

        # 根据域名权威度调整得分
        authority_multiplier = self._get_authority_multiplier(domain_authority)

        # 计算加权影响力指数
        weighted_impact = (
            normalized_citation_score * self.weights['citation_count'] +
            normalized_coverage_score * self.weights['model_coverage'] +
            normalized_sentiment_score * self.weights['sentiment_bias']
        )

        # 应用权威度乘数
        final_impact = weighted_impact * authority_multiplier

        # 确保最终得分在0-100范围内
        return max(0.0, min(100.0, final_impact))

    def _normalize_citation_score(self, citation_count: int) -> float:
        """
        标准化引用频次得分

        Args:
            citation_count: 引用次数

        Returns:
            标准化得分 (0-100)
        """
        if citation_count <= 0:
            return 0.0

        # 使用对数缩放，避免过多引用导致得分过高
        # 最大引用次数设为100，超过100次的得分增长放缓
        max_citations = 100
        if citation_count >= max_citations:
            return 100.0
        else:
            # 对数缩放公式
            return min(100.0, (math.log(citation_count + 1) / math.log(max_citations + 1)) * 100.0)

    def _normalize_coverage_score(self, model_coverage: int) -> float:
        """
        标准化模型覆盖度得分

        Args:
            model_coverage: 模型覆盖数量

        Returns:
            标准化得分 (0-100)
        """
        if model_coverage <= 0:
            return 0.0

        # 假设最大覆盖模型数为10，超过10个模型的得分增长放缓
        max_coverage = 10
        if model_coverage >= max_coverage:
            return 100.0
        else:
            # 线性缩放
            return min(100.0, (model_coverage / max_coverage) * 100.0)

    def _normalize_sentiment_score(self, sentiment_score: float) -> float:
        """
        标准化情感偏向得分

        Args:
            sentiment_score: 情感偏向得分 (-1.0 到 1.0)

        Returns:
            标准化得分 (0-100)
        """
        # 将 -1.0 到 1.0 的范围映射到 0-100
        # 0 表示中性情感，正值表示正面情感，负值表示负面情感
        # 这里我们考虑绝对值，因为无论是正面还是负面都代表影响力
        normalized = abs(sentiment_score) * 100.0
        return max(0.0, min(100.0, normalized))

    def _get_authority_multiplier(self, domain_authority: str) -> float:
        """
        获取域名权威度乘数

        Args:
            domain_authority: 域名权威度 ('High', 'Medium', 'Low')

        Returns:
            权威度乘数
        """
        multipliers = {
            'High': 1.2,    # 高权威度给予20%提升
            'Medium': 1.0,  # 中等权威度无变化
            'Low': 0.8      # 低权威度降低20%
        }
        
        return multipliers.get(domain_authority, 1.0)

    def calculate_batch_impacts(
        self,
        source_data: List[Dict]
    ) -> List[Dict]:
        """
        批量计算影响力指数

        Args:
            source_data: 信源数据列表，每个元素包含 citation_count, model_coverage, sentiment_score, domain_authority

        Returns:
            包含影响力指数的信源数据列表
        """
        results = []
        for source in source_data:
            impact_index = self.calculate_impact_index(
                citation_count=source.get('citation_count', 0),
                model_coverage=source.get('model_coverage', 0),
                sentiment_score=source.get('sentiment_score', 0.0),
                domain_authority=source.get('domain_authority', 'Medium')
            )
            
            # 添加影响力指数到源数据
            updated_source = source.copy()
            updated_source['impact_index'] = impact_index
            results.append(updated_source)
        
        return results


# 测试函数
def test_impact_calculator():
    """测试影响力计算器"""
    calculator = ImpactCalculator()

    # 测试用例
    test_cases = [
        # 高引用、高覆盖、正面情感
        {
            'citation_count': 10,
            'model_coverage': 5,
            'sentiment_score': 0.8,
            'domain_authority': 'High'
        },
        # 低引用、低覆盖、负面情感
        {
            'citation_count': 1,
            'model_coverage': 1,
            'sentiment_score': -0.5,
            'domain_authority': 'Low'
        },
        # 中等引用、中等覆盖、中性情感
        {
            'citation_count': 5,
            'model_coverage': 3,
            'sentiment_score': 0.0,
            'domain_authority': 'Medium'
        }
    ]

    print("影响力计算器测试结果:")
    for i, case in enumerate(test_cases):
        impact = calculator.calculate_impact_index(
            citation_count=case['citation_count'],
            model_coverage=case['model_coverage'],
            sentiment_score=case['sentiment_score'],
            domain_authority=case['domain_authority']
        )
        print(f"测试用例 {i+1}: 影响力指数 = {impact:.2f}")
        print(f"  - 引用次数: {case['citation_count']}")
        print(f"  - 模型覆盖: {case['model_coverage']}")
        print(f"  - 情感得分: {case['sentiment_score']}")
        print(f"  - 权威度: {case['domain_authority']}")
        print()


if __name__ == "__main__":
    test_impact_calculator()