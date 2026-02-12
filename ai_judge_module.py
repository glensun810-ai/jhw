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
            f"你的任务是对以下 AI 回答进行多维度客观评估：",
            f"原始问题：{question_text}",
            f"AI 回答：\n---\n{ai_answer}\n---",
            "",
            "请按照以下五大核心维度进行评估，并以JSON格式输出：",
            "1. 权威度（accuracy_score）：回答内容与事实的符合程度，是否专业、准确。0-100分",
            "2. 可见度（completeness_score）：回答覆盖问题要点的程度，信息量是否丰富。0-100分",
            "3. 好感度（sentiment_score）：回答对主题的情感倾向。0-100分（0=极度负面，50=中性，100=极度正面）",
            "4. 内容纯净度（purity_score）：回答中是否包含无关或负面的信息、垃圾广告等。0-100分（100=完全纯净）",
            "5. 语义一致性（consistency_score）：回答的内容是否前后一致、逻辑清晰。0-100分（100=完全一致）",
            "",
            "评分标准参考：",
            "- 纯净度：90+（无任何杂质），70-89（少量无关信息），<70（包含无关或负面信息）",
            "- 一致性：90+（内容高度一致），70-89（基本一致），<70（存在逻辑矛盾）",
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
    def __init__(self, judge_platform=None, judge_model=None, api_key=None):
        # Lazy load imports to avoid circular dependencies
        global AIAdapterFactory, api_logger
        if AIAdapterFactory is None or api_logger is None:
            from wechat_backend.ai_adapters.factory import AIAdapterFactory as AF
            from wechat_backend.logging_config import api_logger as al
            AIAdapterFactory = AF
            api_logger = al

        # Use provided parameters or fall back to environment variables or defaults
        self.judge_platform = judge_platform or os.getenv("JUDGE_LLM_PLATFORM", "deepseek")
        self.judge_model = judge_model or os.getenv("JUDGE_LLM_MODEL", "deepseek-chat")
        self.api_key = api_key or os.getenv("JUDGE_LLM_API_KEY")

        # 如果没有提供API密钥，尝试从环境变量或配置管理器获取
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
                    api_logger.warning(f"Failed to parse judge LLM's response: {ai_response.content[:200]}...")  # Limit log length
                    # Instead of returning None, create a default result for this case
                    return JudgeResult(
                        accuracy_score=0,
                        completeness_score=0,
                        sentiment_score=50,  # Neutral sentiment
                        purity_score=0,
                        consistency_score=0,
                        judgement=f"AI Judge failed to parse response for question: {question[:50]}...",
                        confidence_level=ConfidenceLevel.LOW
                    )
            else:
                # 检查是否是认证失败错误，如果是则记录并返回None
                if ai_response.error_message and ('Authentication' in ai_response.error_message or
                                                  'api key' in ai_response.error_message.lower() or
                                                  '401' in str(ai_response.error_message)):
                    api_logger.error(f"Judge LLM authentication failed: {ai_response.error_message}. Disabling judge temporarily.")
                    # 在实际应用中，这里可以设置一个标志来暂时禁用该API
                    return None
                else:
                    api_logger.warning(f"Judge LLM failed to respond: {ai_response.error_message}")
                    # Return a default result instead of None to prevent cascading failures
                    return JudgeResult(
                        accuracy_score=0,
                        completeness_score=0,
                        sentiment_score=50,  # Neutral sentiment
                        purity_score=0,
                        consistency_score=0,
                        judgement=f"AI Judge failed to respond to question: {question[:50]}... Error: {ai_response.error_message}",
                        confidence_level=ConfidenceLevel.LOW
                    )
        except Exception as e:
            # 检查异常信息中是否包含认证失败相关内容
            error_str = str(e)
            if ('Authentication' in error_str or
                'api key' in error_str.lower() or
                '401' in error_str):
                api_logger.error(f"Judge LLM authentication error: {e}. Disabling judge temporarily.")
                return None
            else:
                api_logger.warning(f"An exception occurred during evaluation: {e}")
                # Return a default result instead of None to prevent cascading failures
                return JudgeResult(
                    accuracy_score=0,
                    completeness_score=0,
                    sentiment_score=50,  # Neutral sentiment
                    purity_score=0,
                    consistency_score=0,
                    judgement=f"AI Judge exception for question: {question[:50]}... Error: {str(e)}",
                    confidence_level=ConfidenceLevel.LOW
                )
