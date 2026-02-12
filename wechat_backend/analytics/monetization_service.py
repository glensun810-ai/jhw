from enum import Enum
from typing import Dict, Any

class UserLevel(Enum):
    FREE = "Free"
    PRO = "Pro"
    ENTERPRISE = "Enterprise"

class FeatureGate:
    """
    功能门禁，根据用户等级判断功能是否可用
    """
    def __init__(self, user_level: UserLevel):
        self.user_level = user_level
        self.feature_permissions = {
            "view_deep_dive_metrics": [UserLevel.PRO, UserLevel.ENTERPRISE],
            "export_report": [UserLevel.ENTERPRISE],
            "view_competitor_source_path": [UserLevel.PRO, UserLevel.ENTERPRISE],
        }

    def can_access(self, feature_name: str) -> bool:
        """检查用户是否有权限访问某个功能"""
        required_levels = self.feature_permissions.get(feature_name, [])
        return self.user_level in required_levels

class MonetizationService:
    """
    商业化服务，负责根据用户等级剥离数据
    """
    def __init__(self, user_level: UserLevel):
        self.user_level = user_level
        self.gate = FeatureGate(user_level)

    def strip_data_for_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据用户等级，剥离或处理数据
        """
        if self.user_level == UserLevel.FREE:
            # 剥离竞品分析中的深度指标，但仍保留所有字段结构
            if "competitiveAnalysis" in data and "brandScores" in data["competitiveAnalysis"]:
                for brand, scores in data["competitiveAnalysis"]["brandScores"].items():
                    # 确保 scores 是一个字典
                    if isinstance(scores, dict):
                        # 保留所有字段，但将付费用户的详细数据替换为基本数据
                        stripped_scores = {
                            "overallScore": scores.get("overallScore", 0),
                            "overallAuthority": scores.get("overallAuthority", 0),
                            "overallVisibility": scores.get("overallVisibility", 0),
                            "overallSentiment": scores.get("overallSentiment", 0),
                            "overallPurity": scores.get("overallPurity", 0),
                            "overallConsistency": scores.get("overallConsistency", 0),
                            "overallGrade": scores.get("overallGrade", "D"),
                            "overallSummary": scores.get("overallSummary", "免费版用户仅显示基础数据")
                        }

                        # 剥离增强数据（仅付费用户可用）
                        if "enhanced_data" in scores:
                            stripped_scores["enhanced_data"] = {
                                "cognitive_confidence": 0.0,
                                "bias_indicators": [],
                                "detailed_analysis": {},
                                "recommendations": ["升级到付费版以查看详细分析和建议"]
                            }
                        else:
                            stripped_scores["enhanced_data"] = {
                                "cognitive_confidence": 0.0,
                                "bias_indicators": [],
                                "detailed_analysis": {},
                                "recommendations": []
                            }

                        data["competitiveAnalysis"]["brandScores"][brand] = stripped_scores
                    else:
                        # 如果 scores 不是字典，使用默认值
                        data["competitiveAnalysis"]["brandScores"][brand] = {
                            "overallScore": 0,
                            "overallAuthority": 0,
                            "overallVisibility": 0,
                            "overallSentiment": 0,
                            "overallPurity": 0,
                            "overallConsistency": 0,
                            "overallGrade": "D",
                            "overallSummary": "数据格式错误",
                            "enhanced_data": {
                                "cognitive_confidence": 0.0,
                                "bias_indicators": [],
                                "detailed_analysis": {},
                                "recommendations": []
                            }
                        }

            # 剥离信源情报图的深度信息
            if "sourceIntelligenceMap" in data:
                data["sourceIntelligenceMap"] = {
                    "nodes": [{"id": "brand", "name": "品牌核心", "level": 0, "symbolSize": 60, "category": "brand"}],
                    "links": []
                } # 只显示核心节点

        return data
