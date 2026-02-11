# prompt13_optimizer.py
# -*- coding: utf-8 -*-

from typing import Dict, Any, List

class Prompt13Optimizer:
    """
    Prompt 13｜优化建议生成模块
    作用：根据内容草稿、关键词、目标地域和受众，
    生成可直接对接内容 / SEO / GEO / PR 团队的优化建议。
    完全独立运行，可丢给 Qwen Code 执行。
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
        主方法：生成四大模块优化建议
        """
        return {
            "overview": self._generate_overview(),
            "content": self._generate_content_suggestions(),
            "seo": self._generate_seo_suggestions(),
            "geo": self._generate_geo_suggestions(),
            "pr": self._generate_pr_suggestions()
        }

    def _generate_overview(self) -> Dict[str, Any]:
        """
        总体优化策略概览
        """
        return {
            "goal": "提升内容吸引力、搜索表现、地域化效果及公关传播影响力",
            "kpi": ["内容阅读量", "SEO 排名", "地域用户覆盖", "媒体曝光量"],
            "priority_order": ["content", "seo", "geo", "pr"],
            "timeline": "1-2 周完成初步优化建议"
        }

    def _generate_content_suggestions(self) -> Dict[str, Any]:
        """
        内容优化建议
        """
        return {
            "title_optimization": f"建议标题含关键词 {self.keywords[0]}，长度控制在 15-60 字",
            "structure": "建议使用 H2/H3 分层结构，添加 FAQ、图表、案例",
            "depth": "补充数据、引用或案例，提高权威性",
            "engagement": "建议增加互动内容，如评论提问、CTA",
            "cross_platform": f"内容可迁移到社媒/邮件等平台：{', '.join(self.publish_platforms)}"
        }

    def _generate_seo_suggestions(self) -> Dict[str, Any]:
        """
        SEO 优化建议
        """
        return {
            "seo_title": f"包含核心关键词 {self.keywords[0]}，可生成 3 个候选版本",
            "meta_description": "150-160 字，包含核心关键词和长尾词",
            "long_tail_keywords": self.keywords[1:],
            "content_structure": "合理布局 H2/H3 标签，增加内部链接",
            "link_strategy": {
                "internal": "增加相关内容内部链接",
                "external": "建议高权重站点外链及 Anchor 文案"
            }
        }

    def _generate_geo_suggestions(self) -> Dict[str, Any]:
        """
        GEO / 区域化优化建议
        """
        return {
            "regional_keywords": f"结合 {self.target_region} 用户习惯优化关键词",
            "localized_content": "调整文化参考、货币、法规说明，增加本地用户痛点",
            "channel_recommendations": f"优先平台：{', '.join(self.publish_platforms)}",
            "audience_alignment": f"内容贴合 {self.target_region} 地区 {self.target_audience} 用户关注点"
        }

    def _generate_pr_suggestions(self) -> Dict[str, Any]:
        """
        PR / 公关传播优化建议
        """
        return {
            "press_release_titles": [
                f"{self.keywords[0]} 最新动态推荐",
                f"{self.target_region} 用户关注的 {self.keywords[0]} 话题",
                f"企业品牌价值与 {self.keywords[0]} 结合案例"
            ],
            "media_list_priority": ["行业媒体", "本地媒体", "社交媒体意见领袖"],
            "social_media_templates": "针对不同平台生成短文案、图文、视频脚本模板",
            "risk_handling": "提供常见负面舆情 FAQ 及应对方案",
            "kpi_tracking": ["媒体曝光量", "社媒互动率", "品牌正面情绪占比"]
        }

# -------------------------------
# Example usage (直接运行即可)
# -------------------------------
if __name__ == "__main__":
    content = "这里是内容草稿示例"
    keywords = ["数智员工推荐", "智能匹配", "企业管理优化"]
    target_region = "中国大陆"
    target_audience = "HR经理/企业管理者"
    publish_platforms = ["微信公众号", "知乎", "小红书"]

    optimizer = Prompt13Optimizer(
        content_draft=content,
        keywords=keywords,
        target_region=target_region,
        target_audience=target_audience,
        publish_platforms=publish_platforms
    )

    suggestions = optimizer.generate()
    import json
    print(json.dumps(suggestions, ensure_ascii=False, indent=2))