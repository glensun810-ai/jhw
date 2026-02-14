# prompt13_optimizer_enhanced.py
# -*- coding: utf-8 -*-

from typing import Dict, Any, List, Optional
import json

class Prompt13OptimizerEnhanced:
    """
    Prompt 13｜优化建议生成模块（增强版）
    生成可直接对接 Content / SEO / GEO / PR 团队的优化建议
    输出 JSON schema 结构，方便 DeepSeek/PromptBuilder 无缝接入
    包含 A/B 方案、优先级评分、负责人字段等可扩展功能
    """

    def __init__(self, content_draft: str, keywords: List[str], target_region: str,
                 target_audience: str, publish_platforms: List[str] = None):
        self.content_draft = content_draft
        self.keywords = keywords
        self.target_region = target_region
        self.target_audience = target_audience
        self.publish_platforms = publish_platforms or []

    def generate(self) -> Dict[str, Any]:
        """
        主方法：生成符合 JSON schema 的结构化优化建议
        """
        schema_output = {
            "overview": self._generate_overview(),
            "modules": {
                "content": self._generate_content_suggestions(),
                "seo": self._generate_seo_suggestions(),
                "geo": self._generate_geo_suggestions(),
                "pr": self._generate_pr_suggestions()
            }
        }
        return schema_output

    def _generate_overview(self) -> Dict[str, Any]:
        return {
            "goal": "提升内容吸引力、搜索表现、地域化效果及公关传播影响力",
            "kpi": ["内容阅读量", "SEO 排名", "地域用户覆盖", "媒体曝光量"],
            "priority_order": ["content", "seo", "geo", "pr"],
            "timeline": "1-2 周完成初步优化建议",
            "responsible_team": "内容策略团队"
        }

    def _generate_content_suggestions(self) -> Dict[str, Any]:
        return {
            "title_optimization": {
                "description": "建议标题含核心关键词",
                "examples": [f"包含关键词 {self.keywords[0]} 的标题示例 1",
                             f"包含关键词 {self.keywords[0]} 的标题示例 2"],
                "ab_tests": [
                    {"version": "A", "title": f"探索 {self.keywords[0]} 的无限可能", "expected_ctr": 0.05},
                    {"version": "B", "title": f"如何利用 {self.keywords[0]} 提升效率", "expected_ctr": 0.07}
                ],
                "priority_score": 9,
                "responsible_person": "内容编辑"
            },
            "structure": {
                "description": "H2/H3 分层结构，增加 FAQ、图表、案例",
                "priority": "high",
                "priority_score": 8,
                "responsible_person": "内容编辑"
            },
            "depth": {
                "description": "补充数据、引用或案例，提高权威性",
                "priority": "medium",
                "priority_score": 7,
                "responsible_person": "研究分析师"
            },
            "engagement": {
                "description": "增加互动内容，如评论提问、CTA",
                "priority": "medium",
                "priority_score": 6,
                "responsible_person": "社区运营"
            },
            "cross_platform": {
                "description": "内容可迁移到社媒/邮件等平台",
                "platforms": self.publish_platforms,
                "adaptation_notes": "根据不同平台特性调整内容形式和长度",
                "priority_score": 5,
                "responsible_person": "社交媒体专员"
            }
        }

    def _generate_seo_suggestions(self) -> Dict[str, Any]:
        return {
            "seo_title": {
                "description": "SEO 标题建议，包含核心关键词",
                "examples": [f"{self.keywords[0]} 最新推荐", f"{self.keywords[0]} 应用案例"],
                "ab_tests": [
                    {"version": "A", "title": f"{self.keywords[0]} 完整指南", "expected_rank": 5},
                    {"version": "B", "title": f"为什么选择 {self.keywords[0]}", "expected_rank": 7}
                ],
                "priority_score": 10,
                "responsible_person": "SEO 专员"
            },
            "meta_description": {
                "description": "150-160 字 Meta 描述，包含核心关键词和长尾词",
                "priority_score": 9,
                "responsible_person": "SEO 专员"
            },
            "long_tail_keywords": {
                "description": "可拓展的长尾关键词列表",
                "keywords": self.keywords[1:],
                "search_volume": {"智能匹配": 1200, "企业管理优化": 800},
                "priority_score": 8,
                "responsible_person": "SEO 专员"
            },
            "content_structure": {
                "description": "合理布局 H2/H3 标签，增加内部链接",
                "priority": "high",
                "priority_score": 9,
                "responsible_person": "内容编辑"
            },
            "link_strategy": {
                "internal": {
                    "description": "增加相关内容内部链接",
                    "target_pages": ["相关产品页面", "使用案例", "FAQ"],
                    "priority_score": 7
                },
                "external": {
                    "description": "建议高权重站点外链及 Anchor 文案",
                    "target_domains": ["行业报告网站", "权威媒体", "合作伙伴"],
                    "priority_score": 8
                },
                "responsible_person": "SEO 专员"
            }
        }

    def _generate_geo_suggestions(self) -> Dict[str, Any]:
        return {
            "regional_keywords": {
                "description": f"结合 {self.target_region} 用户习惯优化关键词",
                "local_variations": [f"{self.target_region} {self.keywords[0]}", f"{self.keywords[0]} {self.target_region}版"],
                "priority_score": 8,
                "responsible_person": "本地化专员"
            },
            "localized_content": {
                "description": "调整文化参考、货币、法规说明，增加本地用户痛点",
                "specific_examples": ["本地案例", "本地法规", "本地文化元素"],
                "priority_score": 9,
                "responsible_person": "本地化专员"
            },
            "channel_recommendations": {
                "description": "本地优先发布渠道",
                "channels": self.publish_platforms,
                "priority_rankings": {platform: idx+1 for idx, platform in enumerate(self.publish_platforms)},
                "priority_score": 7,
                "responsible_person": "渠道经理"
            },
            "audience_alignment": {
                "description": f"内容贴合 {self.target_region} 地区 {self.target_audience} 用户关注点",
                "pain_points": ["效率提升", "成本控制", "合规性"],
                "priority_score": 10,
                "responsible_person": "用户研究员"
            }
        }

    def _generate_pr_suggestions(self) -> Dict[str, Any]:
        return {
            "press_release_titles": {
                "description": "新闻稿标题建议，至少 3 个版本",
                "examples": [
                    f"{self.keywords[0]} 最新动态推荐",
                    f"{self.target_region} 用户关注的 {self.keywords[0]} 话题",
                    f"企业品牌价值与 {self.keywords[0]} 结合案例"
                ],
                "ab_tests": [
                    {"version": "A", "title": f"{self.keywords[0]} 引领行业变革", "expected_coverage": 0.6},
                    {"version": "B", "title": f"{self.target_region} 企业采用 {self.keywords[0]} 成效显著", "expected_coverage": 0.8}
                ],
                "priority_score": 9,
                "responsible_person": "公关专员"
            },
            "media_list_priority": {
                "description": "媒体投放清单与优先级建议",
                "examples": ["行业媒体", "本地媒体", "社交媒体意见领袖"],
                "priority_rankings": {"行业媒体": 1, "本地媒体": 2, "社交媒体意见领袖": 3},
                "priority_score": 8,
                "responsible_person": "公关专员"
            },
            "social_media_templates": {
                "description": "针对不同平台生成短文案、图文、视频脚本模板",
                "templates_by_platform": {
                    "微博": "简短有力的观点+话题标签",
                    "微信": "深度解读+引导关注",
                    "抖音": "视觉冲击+音乐+BGM"
                },
                "priority_score": 7,
                "responsible_person": "社交媒体专员"
            },
            "risk_handling": {
                "description": "常见负面舆情 FAQ 及应对方案",
                "common_questions": ["安全性问题", "价格争议", "竞品比较"],
                "response_templates": {
                    "安全性问题": "我们严格遵循行业安全标准...",
                    "价格争议": "我们的定价基于价值和服务质量...",
                    "竞品比较": "我们专注于自身优势..."
                },
                "priority_score": 10,
                "responsible_person": "法务/公关专员"
            },
            "kpi_tracking": {
                "description": "KPI 指标与评估机制",
                "metrics": ["媒体曝光量", "社媒互动率", "品牌正面情绪占比"],
                "tracking_tools": ["Google Analytics", "社交媒体分析工具", "舆情监控系统"],
                "priority_score": 8,
                "responsible_person": "数据分析员"
            }
        }

# -------------------------------
# Example usage
# -------------------------------
if __name__ == "__main__":
    content = "这里是内容草稿示例"
    keywords = ["数智员工推荐", "智能匹配", "企业管理优化"]
    target_region = "中国大陆"
    target_audience = "HR经理/企业管理者"
    publish_platforms = ["微信公众号", "知乎", "小红书"]

    optimizer = Prompt13OptimizerEnhanced(
        content_draft=content,
        keywords=keywords,
        target_region=target_region,
        target_audience=target_audience,
        publish_platforms=publish_platforms
    )

    suggestions = optimizer.generate()
    print(json.dumps(suggestions, ensure_ascii=False, indent=2))