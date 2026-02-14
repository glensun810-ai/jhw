"""
干预建议生成器模块
基于 source_intelligence 中的信源频次和 evidence_chain 中的负面证据，生成行动建议
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from .logging_config import api_logger
from .ai_adapters.factory import AIAdapterFactory
from config_manager import Config as PlatformConfigManager


class RecommendationPriority(Enum):
    """建议优先级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationType(Enum):
    """建议类型枚举"""
    CONTENT_CORRECTION = "content_correction"  # 内容纠偏
    BRAND_STRENGTHENING = "brand_strengthening"  # 品牌强化
    SOURCE_ATTACK = "source_attack"  # 信源攻坚
    RISK_MITIGATION = "risk_mitigation"  # 风险缓解


@dataclass
class Recommendation:
    """单条建议的数据结构"""
    priority: RecommendationPriority
    type: RecommendationType
    title: str
    description: str
    target: str  # 目标对象（如网站URL、负面内容等）
    estimated_impact: str  # 预估影响程度
    action_steps: List[str]  # 行动步骤
    urgency: int  # 紧急程度（1-10）


class RecommendationGenerator:
    """干预建议生成器"""

    def __init__(self):
        self.logger = api_logger
        # 初始化配置管理器以获取AI平台配置
        self.config_manager = PlatformConfigManager()

    def generate_recommendations(
        self,
        source_intelligence: Dict[str, Any],
        evidence_chain: List[Dict[str, Any]],
        brand_name: str
    ) -> List[Recommendation]:
        """
        基于信源情报和证据链生成干预建议

        Args:
            source_intelligence: 信源情报数据
            evidence_chain: 证据链数据
            brand_name: 品牌名称

        Returns:
            List[Recommendation]: 建议列表，按优先级排序
        """
        recommendations = []

        # 1. 分析高优攻坚站点
        high_priority_sources = self._identify_high_priority_sources(source_intelligence, evidence_chain)
        
        # 2. 生成负面内容纠偏建议
        correction_recommendations = self._generate_correction_recommendations(evidence_chain, brand_name)
        recommendations.extend(correction_recommendations)

        # 3. 生成信源攻坚建议
        source_attack_recommendations = self._generate_source_attack_recommendations(high_priority_sources, brand_name)
        recommendations.extend(source_attack_recommendations)

        # 4. 如果没有负面信息，生成品牌心智强化建议
        if not evidence_chain:
            strengthening_recommendations = self._generate_brand_strengthening_recommendations(brand_name)
            recommendations.extend(strengthening_recommendations)

        # 按优先级排序
        recommendations.sort(key=lambda r: self._priority_to_int(r.priority), reverse=True)

        return recommendations

    def _identify_high_priority_sources(
        self,
        source_intelligence: Dict[str, Any],
        evidence_chain: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        识别高优攻坚站点：
        找出引用频次最高但无我方正面内容的 source_url

        Args:
            source_intelligence: 信源情报数据
            evidence_chain: 证据链数据

        Returns:
            List[Dict]: 高优攻坚站点列表
        """
        # 获取信源池和引用排名
        source_pool = source_intelligence.get('source_pool', [])
        citation_rank = source_intelligence.get('citation_rank', [])

        # 创建一个包含引用次数的信源映射
        source_map = {}
        for source in source_pool:
            source_map[source.get('id', '')] = source

        # 找出引用频次最高的信源
        high_freq_sources = []
        for source_id in citation_rank[:5]:  # 取前5个高频信源
            if source_id in source_map:
                source_info = source_map[source_id]
                
                # 检查该信源是否出现在负面证据中
                has_negative_content = any(
                    source_info.get('url', '').lower() in evidence.get('associated_url', '').lower()
                    for evidence in evidence_chain
                )
                
                # 如果引用频次高但存在负面内容，则标记为高优攻坚站点
                if source_info.get('citation_count', 0) > 0 and has_negative_content:
                    high_freq_sources.append(source_info)

        return high_freq_sources

    def _generate_correction_recommendations(
        self,
        evidence_chain: List[Dict[str, Any]],
        brand_name: str
    ) -> List[Recommendation]:
        """
        生成负面内容纠偏建议

        Args:
            evidence_chain: 证据链数据
            brand_name: 品牌名称

        Returns:
            List[Recommendation]: 纠偏建议列表
        """
        recommendations = []

        for evidence in evidence_chain:
            negative_fragment = evidence.get('negative_fragment', '')
            associated_url = evidence.get('associated_url', '')
            risk_level = evidence.get('risk_level', 'Medium')

            if negative_fragment:
                # 调用AI生成公关纠偏话术
                correction_script = self._generate_pr_correction_script(negative_fragment, brand_name)

                # 确定优先级
                priority = RecommendationPriority.HIGH if risk_level.lower() == 'high' else \
                          RecommendationPriority.MEDIUM if risk_level.lower() == 'medium' else \
                          RecommendationPriority.LOW

                recommendation = Recommendation(
                    priority=priority,
                    type=RecommendationType.CONTENT_CORRECTION,
                    title=f"负面内容纠偏 - {risk_level}风险",
                    description=f"检测到关于{brand_name}的负面内容: {negative_fragment[:100]}...",
                    target=associated_url,
                    estimated_impact=f"{risk_level}风险等级",
                    action_steps=[
                        f"使用以下公关话术进行纠偏: {correction_script}",
                        "联系相关平台或作者修正内容",
                        "发布正面内容对冲负面影响"
                    ],
                    urgency=8 if risk_level.lower() == 'high' else 6 if risk_level.lower() == 'medium' else 4
                )
                recommendations.append(recommendation)

        return recommendations

    def _generate_pr_correction_script(self, negative_content: str, brand_name: str) -> str:
        """
        调用AI生成公关纠偏话术

        Args:
            negative_content: 负面内容片段
            brand_name: 品牌名称

        Returns:
            str: 公关纠偏话术
        """
        prompt = f"""
        请为品牌"{brand_name}"生成一段公关纠偏话术，针对以下负面内容进行回应：

        负面内容: {negative_content}

        要求：
        1. 语气专业、客观、诚恳
        2. 承认问题（如有）并提出解决方案
        3. 强调品牌的价值观和承诺
        4. 长度控制在100-200字以内
        """

        try:
            # 尝试使用配置中的默认AI平台
            platform_name = 'qwen'  # 默认使用通义千问
            platform_config = self.config_manager.get_platform_config(platform_name)

            if platform_config and platform_config.api_key:
                # 创建AI适配器
                ai_adapter = AIAdapterFactory.create(platform_name, platform_config.api_key, platform_config.default_model or f"default-{platform_name}")

                # 发送提示
                response = ai_adapter.send_prompt(prompt)

                if response.success:
                    return response.content.strip()
                else:
                    self.logger.warning(f"AI生成纠偏话术失败: {response.error_message}")
            else:
                self.logger.warning(f"未找到{platform_name}平台的API配置，使用默认话术")

        except Exception as e:
            self.logger.error(f"生成纠偏话术时发生错误: {e}")

        # 返回默认话术
        return f"我们注意到有关{brand_name}的某些讨论。我们始终致力于为用户提供优质的产品和服务，并将持续改进以满足用户需求。"

    def _generate_source_attack_recommendations(
        self,
        high_priority_sources: List[Dict[str, Any]],
        brand_name: str
    ) -> List[Recommendation]:
        """
        生成信源攻坚建议

        Args:
            high_priority_sources: 高优攻坚站点列表
            brand_name: 品牌名称

        Returns:
            List[Recommendation]: 信源攻坚建议列表
        """
        recommendations = []

        for source in high_priority_sources:
            source_name = source.get('site_name', source.get('id', '未知信源'))
            url = source.get('url', '')
            citation_count = source.get('citation_count', 0)

            priority = RecommendationPriority.HIGH if citation_count > 10 else \
                      RecommendationPriority.MEDIUM if citation_count > 5 else \
                      RecommendationPriority.LOW

            recommendation = Recommendation(
                priority=priority,
                type=RecommendationType.SOURCE_ATTACK,
                title=f"高优攻坚站点 - {source_name}",
                description=f"{source_name}被引用{citation_count}次，但缺乏我方正面内容",
                target=url,
                estimated_impact="高影响力信源",
                action_steps=[
                    f"在{source_name}上发布高质量正面内容",
                    f"与{source_name}建立合作关系",
                    f"监测{source_name}上关于{brand_name}的讨论"
                ],
                urgency=9 if citation_count > 10 else 7 if citation_count > 5 else 5
            )
            recommendations.append(recommendation)

        return recommendations

    def _generate_brand_strengthening_recommendations(self, brand_name: str) -> List[Recommendation]:
        """
        生成品牌心智强化建议（当没有负面信息时）

        Args:
            brand_name: 品牌名称

        Returns:
            List[Recommendation]: 品牌强化建议列表
        """
        recommendations = []

        recommendation = Recommendation(
            priority=RecommendationPriority.MEDIUM,
            type=RecommendationType.BRAND_STRENGTHENING,
            title=f"{brand_name}品牌心智强化",
            description=f"当前未检测到关于{brand_name}的负面信息，建议加强品牌正面心智建设",
            target="全网",
            estimated_impact="长期品牌价值提升",
            action_steps=[
                f"制作并发布{brand_name}正面内容",
                f"强化{brand_name}核心价值传播",
                f"提升{brand_name}在关键信源的正面曝光"
            ],
            urgency=5
        )
        recommendations.append(recommendation)

        return recommendations

    def _priority_to_int(self, priority: RecommendationPriority) -> int:
        """将优先级转换为整数以便排序"""
        mapping = {
            RecommendationPriority.HIGH: 3,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 1
        }
        return mapping.get(priority, 0)