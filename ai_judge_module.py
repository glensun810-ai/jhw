import json
import re
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import os

# Delay import to avoid circular dependencies
AIAdapterFactory = None
api_logger = None

class ConfidenceLevel(Enum):
    """置信度等级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class JudgeResult:
    """
    AI Judge 评分结果数据结构 (5维模型)
    """
    accuracy_score: int      # 权威度
    completeness_score: int  # 可见度
    sentiment_score: int     # 好感度
    purity_score: int        # 品牌纯净度
    consistency_score: int   # 语义一致性
    judgement: str
    confidence_level: ConfidenceLevel


class JudgePromptBuilder:
    """
    AI Judge Prompt 构造器
    """
    def build_judge_prompt(
        self,
        brand_name: str,
        question_text: str,
        ai_answer: str,
        reference_facts: Optional[str] = None
    ) -> str:
        prompt_parts = [
            "你是专业的 AI 回答质量评估专家，具备强大的中文理解、事实判断和情感分析能力。",
            f"你的任务是对以下关于“{brand_name}”品牌的 AI 回答进行多维度客观评估：",
            f"原始问题：{question_text}",
            f"AI 回答：\n---\n{ai_answer}\n---",
            "",
            "请按照以下五大核心维度进行评估，并以JSON格式输出：",
            "1. 权威度（accuracy_score）：回答内容与事实的符合程度，是否专业、准确。0-100分",
            "2. 可见度（completeness_score）：回答覆盖问题要点的程度，信息量是否丰富。0-100分",
            "3. 好感度（sentiment_score）：回答对品牌的情感倾向。0-100分（0=极度负面，50=中性，100=极度正面）",
            "4. 品牌纯净度（purity_score）：回答中是否包含无关或负面的竞品信息、垃圾广告等。0-100分（100=完全纯净）",
            "5. 语义一致性（consistency_score）：回答的品牌定位、核心价值是否与官方定义一致。0-100分（100=完全一致）",
            "",
            "评分标准参考：",
            "- 纯净度：90+（无任何杂质），70-89（少量无关信息），<70（包含竞品或负面信息）",
            "- 一致性：90+（与官方定义高度一致），70-89（基本一致），<70（存在语义偏移）",
            "",
            "最后，请给出一个简短的中文评价（judgement），并评估你本次判断的置信度（confidence_level: 'high', 'medium', 'low'）。",
            "请严格按照以下 JSON 格式输出评估结果，不得包含任何其他文本或解释：",
            json.dumps({
                "accuracy_score": 0,
                "completeness_score": 0,
                "sentiment_score": 0,
                "purity_score": 0,
                "consistency_score": 0,
                "judgement": "简短评价",
                "confidence_level": "high"
            }, indent=2, ensure_ascii=False)
        ]
        return "\n".join(prompt_parts)


class JudgeResultParser:
    """
    AI Judge 结果解析器
    """
    def parse(self, judge_output: str) -> Optional[JudgeResult]:
        try:
            json_match = re.search(r'\{.*\}', judge_output, re.DOTALL)
            if not json_match: return None
            
            parsed_data = json.loads(json_match.group())
            
            required_fields = ["accuracy_score", "completeness_score", "sentiment_score", "purity_score", "consistency_score", "judgement", "confidence_level"]
            if not all(field in parsed_data for field in required_fields): return None
            
            for score_field in ["accuracy_score", "completeness_score", "sentiment_score", "purity_score", "consistency_score"]:
                if not isinstance(parsed_data[score_field], int) or not (0 <= parsed_data[score_field] <= 100):
                    return None
            
            return JudgeResult(
                accuracy_score=parsed_data["accuracy_score"],
                completeness_score=parsed_data["completeness_score"],
                sentiment_score=parsed_data["sentiment_score"],
                purity_score=parsed_data["purity_score"],
                consistency_score=parsed_data["consistency_score"],
                judgement=parsed_data["judgement"],
                confidence_level=ConfidenceLevel(parsed_data["confidence_level"])
            )
        except (json.JSONDecodeError, ValueError, Exception) as e:
            api_logger.error(f"解析 JudgeResult 失败: {e}")
            return None

class AIJudgeClient:
    """
    用于调用"裁判LLM"的客户端
    """
    def __init__(self):
        # Lazy load imports to avoid circular dependencies
        global AIAdapterFactory, api_logger
        if AIAdapterFactory is None or api_logger is None:
            from wechat_backend.ai_adapters.factory import AIAdapterFactory as AF
            from wechat_backend.logging_config import api_logger as al
            AIAdapterFactory = AF
            api_logger = al

        self.judge_platform = os.getenv("JUDGE_LLM_PLATFORM", "deepseek")
        self.judge_model = os.getenv("JUDGE_LLM_MODEL", "deepseek-chat")
        self.api_key = os.getenv("JUDGE_LLM_API_KEY")

        # 如果没有配置专用的裁判API密钥，尝试使用现有的API密钥
        if not self.api_key:
            # 尝试从配置管理器获取可用的API密钥
            try:
                from config_manager import Config as PlatformConfigManager
                config_manager = PlatformConfigManager()

                # 按优先级顺序尝试获取API密钥
                platforms_to_try = [self.judge_platform, 'deepseek', 'qwen', 'zhipu', 'doubao']

                for platform in platforms_to_try:
                    config = config_manager.get_platform_config(platform)
                    if config and config.api_key:
                        self.api_key = config.api_key
                        api_logger.info(f"Using {platform} API key for AI Judge")
                        break

                if not self.api_key:
                    api_logger.warning("No API key available for AI Judge. AI Judge functionality will be disabled.")
                    self.ai_client = None
                    return
            except Exception as e:
                api_logger.error(f"Error getting API key for AI Judge: {e}")
                api_logger.warning("AI Judge functionality will be disabled.")
                self.ai_client = None
                return

        self.prompt_builder = JudgePromptBuilder()
        self.parser = JudgeResultParser()

        try:
            self.ai_client = AIAdapterFactory.create(self.judge_platform, self.api_key, self.judge_model)
            api_logger.info(f"AIJudgeClient initialized with model: {self.judge_model} on platform: {self.judge_platform}")
        except Exception as e:
            api_logger.error(f"Failed to initialize AIJudgeClient: {e}")
            self.ai_client = None  # 即使初始化失败也不抛出异常，只是禁用功能

    def evaluate_response(self, brand_name: str, question: str, ai_answer: str) -> Optional[JudgeResult]:
        """
        调用裁判LLM评估一个AI回答
        """
        # Lazy load imports to avoid circular dependencies
        global AIAdapterFactory, api_logger
        if AIAdapterFactory is None or api_logger is None:
            from wechat_backend.ai_adapters.factory import AIAdapterFactory as AF
            from wechat_backend.logging_config import api_logger as al
            AIAdapterFactory = AF
            api_logger = al

        # 如果AI客户端未初始化，返回None
        if not self.ai_client:
            api_logger.warning("AI Judge is not initialized due to missing API key. Skipping evaluation.")
            return None

        if not ai_answer or not ai_answer.strip():
            api_logger.warning("AI answer is empty, skipping evaluation.")
            return None

        prompt = self.prompt_builder.build_judge_prompt(brand_name, question, ai_answer)

        try:
            ai_response = self.ai_client.send_prompt(prompt)

            if ai_response.success:
                parsed_result = self.parser.parse(ai_response.content)
                if parsed_result:
                    api_logger.info(f"Successfully evaluated response for brand '{brand_name}' on question '{question}'")
                    return parsed_result
                else:
                    api_logger.error(f"Failed to parse judge LLM's response: {ai_response.content}")
                    return None
            else:
                api_logger.error(f"Judge LLM failed to respond: {ai_response.error_message}")
                return None
        except Exception as e:
            api_logger.error(f"An exception occurred during evaluation: {e}")
            return None
