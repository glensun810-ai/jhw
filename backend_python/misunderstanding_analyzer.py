from enum import Enum
from dataclasses import dataclass
from typing import List
from ai_judge_module import JudgeResult


class MisunderstandingType(Enum):
    """典型品牌误解类型枚举"""
    FACT_ERROR = "fact_error"                   # 明显事实错误
    BRAND_CONFUSION = "brand_confusion"         # 与其他品牌混淆
    INCOMPLETE_INFO = "incomplete_info"         # 关键信息缺失
    OVER_GENERALIZATION = "over_generalization" # 过度泛化、表述空泛
    OUTDATED_INFO = "outdated_info"             # 使用过时信息
    NO_CLEAR_EVIDENCE = "no_clear_evidence"     # 无法判断真实性、但缺乏依据


@dataclass
class MisunderstandingResult:
    """
    品牌误解分析结果数据结构
    
    Attributes:
        has_issue: 是否存在问题
        issue_types: 误解类型列表
        issue_summary: 中文总结（面向客户）
        risk_level: 风险等级 (high / medium / low)
        improvement_hint: 简要优化方向
    """
    has_issue: bool
    issue_types: List[str]
    issue_summary: str
    risk_level: str
    improvement_hint: str


class MisunderstandingAnalyzer:
    """
    品牌误解分析器
    负责分析 AI 回答中的典型品牌误解与错误类型
    """
    
    def analyze(
        self,
        brand_name: str,
        question_text: str,
        ai_answer: str,
        judge_result: JudgeResult
    ) -> MisunderstandingResult:
        """
        分析 AI 回答中的品牌误解
        
        Args:
            brand_name: 品牌名称
            question_text: 原始问题
            ai_answer: AI 的原始回答
            judge_result: 来自 AI Judge 的评分结果
        
        Returns:
            误解分析结果对象
        """
        # 初始化变量
        issue_types = []
        
        # 1. 基于 JudgeResult 的分数判断
        if judge_result.accuracy_score < 70:
            issue_types.append(MisunderstandingType.FACT_ERROR.value)
        
        if judge_result.completeness_score < 60:
            issue_types.append(MisunderstandingType.INCOMPLETE_INFO.value)
        
        # 2. 基于 JudgeResult 的评价文本判断
        judgement_lower = judge_result.judgement.lower()
        
        if "混淆" in judgement_lower or "误认" in judgement_lower:
            if MisunderstandingType.BRAND_CONFUSION.value not in issue_types:
                issue_types.append(MisunderstandingType.BRAND_CONFUSION.value)
        
        if "过时" in judgement_lower or "旧" in judgement_lower:
            if MisunderstandingType.OUTDATED_INFO.value not in issue_types:
                issue_types.append(MisunderstandingType.OUTDATED_INFO.value)
        
        if "不准确" in judgement_lower or "错误" in judgement_lower:
            if MisunderstandingType.FACT_ERROR.value not in issue_types:
                issue_types.append(MisunderstandingType.FACT_ERROR.value)
        
        if "遗漏" in judgement_lower or "不全" in judgement_lower:
            if MisunderstandingType.INCOMPLETE_INFO.value not in issue_types:
                issue_types.append(MisunderstandingType.INCOMPLETE_INFO.value)
        
        # 3. 基于 AI 回答内容判断
        ai_answer_lower = ai_answer.lower()
        
        # 检查是否过度泛化
        generic_phrases = ["一般来说", "通常认为", "可能", "大概", "据说", "听说"]
        if any(phrase in ai_answer_lower for phrase in generic_phrases):
            if MisunderstandingType.OVER_GENERALIZATION.value not in issue_types:
                issue_types.append(MisunderstandingType.OVER_GENERALIZATION.value)
        
        # 检查是否缺乏明确证据
        uncertain_phrases = ["不确定", "可能", "也许", "应该", "推测", "估计"]
        if any(phrase in ai_answer_lower for phrase in uncertain_phrases):
            if MisunderstandingType.NO_CLEAR_EVIDENCE.value not in issue_types:
                issue_types.append(MisunderstandingType.NO_CLEAR_EVIDENCE.value)
        
        # 检查是否混淆品牌
        # 这里可以加入更复杂的逻辑，比如检查是否提到了其他竞争品牌
        # 为了简化，我们暂时只检查一些常见的混淆信号
        if brand_name.lower() not in ai_answer_lower and "品牌" in ai_answer_lower:
            if MisunderstandingType.BRAND_CONFUSION.value not in issue_types:
                issue_types.append(MisunderstandingType.BRAND_CONFUSION.value)
        
        # 去重
        issue_types = list(set(issue_types))
        
        # 判断是否有问题
        has_issue = len(issue_types) > 0
        
        # 评估风险等级
        risk_level = self._evaluate_risk_level(issue_types, judge_result)
        
        # 生成面向客户的总结
        issue_summary = self._generate_issue_summary(has_issue, issue_types, brand_name, judge_result)
        
        # 生成改进提示
        improvement_hint = self._generate_improvement_hint(issue_types)
        
        return MisunderstandingResult(
            has_issue=has_issue,
            issue_types=issue_types,
            issue_summary=issue_summary,
            risk_level=risk_level,
            improvement_hint=improvement_hint
        )
    
    def _evaluate_risk_level(self, issue_types: List[str], judge_result: JudgeResult) -> str:
        """
        评估风险等级
        
        Args:
            issue_types: 误解类型列表
            judge_result: JudgeResult 对象
        
        Returns:
            风险等级 (high / medium / low)
        """
        # 如果包含事实错误或品牌混淆，风险较高
        if MisunderstandingType.FACT_ERROR.value in issue_types or \
           MisunderstandingType.BRAND_CONFUSION.value in issue_types:
            return "high"
        
        # 如果分数较低或包含多个问题，风险中等
        if judge_result.accuracy_score < 60 or len(issue_types) >= 3:
            return "medium"
        
        # 其他情况风险较低
        return "low"
    
    def _generate_issue_summary(
        self,
        has_issue: bool,
        issue_types: List[str],
        brand_name: str,
        judge_result: JudgeResult
    ) -> str:
        """
        生成面向客户的误解总结
        
        Args:
            has_issue: 是否存在问题
            issue_types: 误解类型列表
            brand_name: 品牌名称
            judge_result: JudgeResult 对象
        
        Returns:
            中文总结文本
        """
        if not has_issue:
            return f"AI 对 {brand_name} 的回答质量良好，未发现明显误解。"
        
        # 映射误解类型到中文描述
        type_mapping = {
            MisunderstandingType.FACT_ERROR.value: "事实错误",
            MisunderstandingType.BRAND_CONFUSION.value: "品牌混淆",
            MisunderstandingType.INCOMPLETE_INFO.value: "信息不完整",
            MisunderstandingType.OVER_GENERALIZATION.value: "表述过于泛化",
            MisunderstandingType.OUTDATED_INFO.value: "信息过时",
            MisunderstandingType.NO_CLEAR_EVIDENCE.value: "缺乏明确依据"
        }
        
        issue_names = [type_mapping.get(t, t) for t in issue_types]
        
        summary_parts = [
            f"AI 对 {brand_name} 的回答存在以下问题：",
            f"{'、'.join(issue_names)}。"
        ]
        
        summary_parts.append(
            f"AI Judge 评分为：准确性 {judge_result.accuracy_score} 分，"
            f"完整性 {judge_result.completeness_score} 分。"
        )
        
        return "".join(summary_parts)
    
    def _generate_improvement_hint(self, issue_types: List[str]) -> str:
        """
        生成改进提示
        
        Args:
            issue_types: 误解类型列表
        
        Returns:
            改进提示文本
        """
        hints = []
        
        if MisunderstandingType.FACT_ERROR.value in issue_types:
            hints.append("核实品牌的基本事实信息，如成立时间、创始人、主营业务等。")
        
        if MisunderstandingType.BRAND_CONFUSION.value in issue_types:
            hints.append("加强品牌辨识度训练，避免与其他品牌混淆。")
        
        if MisunderstandingType.INCOMPLETE_INFO.value in issue_types:
            hints.append("补充品牌的关键信息，确保回答的完整性。")
        
        if MisunderstandingType.OVER_GENERALIZATION.value in issue_types:
            hints.append("减少泛化表述，提供具体、准确的信息。")
        
        if MisunderstandingType.OUTDATED_INFO.value in issue_types:
            hints.append("更新品牌相关信息，确保信息时效性。")
        
        if MisunderstandingType.NO_CLEAR_EVIDENCE.value in issue_types:
            hints.append("基于可验证的事实回答，避免不确定的表述。")
        
        if not hints:
            return "继续保持现有质量水平。"
        
        return " ".join(hints)


# 示例使用
if __name__ == "__main__":
    # 创建分析器实例
    analyzer = MisunderstandingAnalyzer()
    
    # 模拟输入数据
    brand_name = "小米科技"
    question_text = "小米公司的创始人是谁？"
    ai_answer = "小米公司的创始人可能是雷军，也有人说是一群人共同创立的。一般来说，雷军是主要创始人。"
    judge_result = JudgeResult(
        accuracy_score=65,
        completeness_score=55,
        judgement="回答提到雷军是创始人，但表述不够准确，存在‘可能是’等不确定词汇，且遗漏了联合创始人信息。",
        confidence_level="medium"
    )
    
    # 执行分析
    result = analyzer.analyze(
        brand_name=brand_name,
        question_text=question_text,
        ai_answer=ai_answer,
        judge_result=judge_result
    )
    
    print("=== 品牌误解分析结果 ===")
    print(f"存在问题: {result.has_issue}")
    print(f"误解类型: {result.issue_types}")
    print(f"风险等级: {result.risk_level}")
    print(f"问题总结: {result.issue_summary}")
    print(f"改进建议: {result.improvement_hint}")