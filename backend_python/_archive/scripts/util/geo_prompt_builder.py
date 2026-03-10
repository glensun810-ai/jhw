from enum import Enum
from typing import Optional


class PromptType(Enum):
    """GEO 内容质量验证器的 Prompt 类型枚举"""
    BRAND_COGNITION = "brand_cognition"          # 品牌认知测试
    PRODUCT_UNDERSTANDING = "product_understanding"  # 产品 / 服务理解
    FACT_VERIFICATION = "fact_verification"      # 品牌事实验证（推理型）
    AI_JUDGE = "ai_judge"                       # AI 评分 / 评判


def get_system_prompt() -> str:
    """
    生成系统级约束 Prompt
    用于统一约束 DeepSeek 的回答风格
    """
    return (
        "你是专业的品牌事实验证专家，具备强大的中文理解和推理能力。\n\n"
        "请严格遵守以下规则：\n"
        "1. 必须使用简体中文回答\n"
        "2. 回答应基于可验证的公开事实，不得编造信息\n"
        "3. 如信息不足或不确定，必须明确说明“信息不足”或“不确定”，不得猜测\n"
        "4. 输出内容结构清晰（分点或分段），避免冗余\n"
        "5. 避免使用营销式语言，保持客观中立\n"
        "6. 回答长度控制在300字以内\n"
        "7. 以搜索/推理的方式分析问题，优先考虑公开可查证的信息"
    )


def build_user_prompt(
    prompt_type: PromptType,
    brand_name: str,
    question_text: str,
    extra_context: Optional[str] = None
) -> str:
    """
    构造用户级 Prompt
    
    Args:
        prompt_type: Prompt 类型
        brand_name: 品牌名
        question_text: 问题文本
        extra_context: 可选补充说明
    
    Returns:
        构造完成的用户 Prompt
    """
    # 根据 Prompt 类型添加特定指令
    type_instruction = ""
    if prompt_type == PromptType.BRAND_COGNITION:
        type_instruction = "请评估用户对品牌的认知程度，基于公开信息验证其准确性。"
    elif prompt_type == PromptType.PRODUCT_UNDERSTANDING:
        type_instruction = "请分析用户对产品/服务的理解，基于公开信息进行验证。"
    elif prompt_type == PromptType.FACT_VERIFICATION:
        type_instruction = "请基于公开可查证的事实，验证以下信息的准确性。这是推理型任务，请仔细分析。"
    elif prompt_type == PromptType.AI_JUDGE:
        type_instruction = "请作为 AI 评委，对以下内容进行客观评价和打分。"

    # 构造基础用户 Prompt
    user_prompt = (
        f"{type_instruction}\n\n"
        f"品牌名称：{brand_name}\n"
        f"问题：{question_text}\n\n"
    )

    # 添加补充说明（如果有）
    if extra_context:
        user_prompt += f"补充说明：{extra_context}\n\n"

    # 添加通用约束指令
    user_prompt += (
        "请基于公开可查证的信息回答，如信息不足请明确说明。"
        "避免主观臆断，保持客观中立。"
    )

    return user_prompt


class PromptBuilder:
    """
    GEO 内容质量验证器的 Prompt 构造器
    负责生成符合 DeepSeek 特性的高质量 Prompt
    """
    
    def build_prompt(
        self,
        prompt_type: PromptType,
        brand_name: str,
        question_text: str,
        extra_context: Optional[str] = None
    ) -> dict:
        """
        构造完整的 Prompt
        
        Args:
            prompt_type: Prompt 类型
            brand_name: 品牌名
            question_text: 问题文本
            extra_context: 可选补充说明
        
        Returns:
            包含 system_prompt、user_prompt 和 full_prompt 的字典
        """
        system_prompt = get_system_prompt()
        user_prompt = build_user_prompt(
            prompt_type,
            brand_name,
            question_text,
            extra_context
        )
        
        # 构造完整 Prompt（DeepSeek 接受的格式）
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "full_prompt": full_prompt
        }


# 示例使用
if __name__ == "__main__":
    builder = PromptBuilder()
    
    # 示例 1：品牌认知 Prompt
    brand_cognition_result = builder.build_prompt(
        PromptType.BRAND_COGNITION,
        "小米科技",
        "小米手机的创始人是谁？",
        "此问题用于测试用户对品牌创始人的认知"
    )
    print("=== 品牌认知 Prompt 示例 ===")
    print("System Prompt:")
    print(brand_cognition_result["system_prompt"])
    print("\nUser Prompt:")
    print(brand_cognition_result["user_prompt"])
    print("\nFull Prompt:")
    print(brand_cognition_result["full_prompt"])
    
    print("\n" + "="*50 + "\n")
    
    # 示例 2：品牌事实验证 Prompt
    fact_verification_result = builder.build_prompt(
        PromptType.FACT_VERIFICATION,
        "华为技术有限公司",
        "华为的总部位于深圳吗？",
        "此问题用于验证地理位置事实"
    )
    print("=== 品牌事实验证 Prompt 示例 ===")
    print("System Prompt:")
    print(fact_verification_result["system_prompt"])
    print("\nUser Prompt:")
    print(fact_verification_result["user_prompt"])
    print("\nFull Prompt:")
    print(fact_verification_result["full_prompt"])