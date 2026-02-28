"""
品牌分析服务

P0 修复：后置品牌提及分析模块

职责：
1. 从 AI 客观回答中提取品牌提及
2. 提取 TOP3 品牌作为竞品
3. 对比用户品牌与竞品表现

使用场景：
- NxM 执行引擎获取客观回答后
- 需要分析用户品牌在 AI 回答中的表现
- 需要生成竞品对比报告
"""

import json
import re
from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import BRAND_ANALYSIS_TEMPLATE
from wechat_backend.ai_adapters.factory import AIAdapterFactory


class BrandAnalysisService:
    """品牌分析服务"""

    def __init__(self, judge_model: str = 'doubao'):
        """
        初始化品牌分析服务

        Args:
            judge_model: 用于分析的品牌模型，默认使用 doubao
        """
        self.judge_model = judge_model

    def analyze_brand_mentions(
        self,
        results: List[Dict[str, Any]],
        user_brand: str,
        competitor_brands: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        分析品牌提及情况

        Args:
            results: AI 回答列表（客观回答）
            user_brand: 用户品牌
            competitor_brands: 竞品品牌列表（可选，若为 None 则从回答中提取）

        Returns:
            分析结果字典，包含：
            - user_brand_analysis: 用户品牌分析
            - competitor_analysis: 竞品分析
            - comparison: 对比分析
            - top3_brands: 从回答中提取的 TOP3 品牌
        """
        analysis = {
            'user_brand_analysis': {},
            'competitor_analysis': [],
            'comparison': {},
            'top3_brands': []
        }

        # 步骤 1: 从每个回答中提取 TOP3 品牌
        all_top3_brands = []
        for result in results:
            top3 = self._extract_top3_brands(result.get('response', ''))
            if top3:
                all_top3_brands.extend(top3)

        # 去重 TOP3 品牌
        seen_brands = set()
        unique_top3 = []
        for brand in all_top3_brands:
            brand_name = brand.get('name', '')
            if brand_name and brand_name not in seen_brands and brand_name != user_brand:
                seen_brands.add(brand_name)
                unique_top3.append(brand)

        analysis['top3_brands'] = unique_top3[:3]  # 只取前 3 个竞品

        # 步骤 2: 若未指定竞品，使用提取的 TOP3 品牌作为竞品
        if not competitor_brands:
            competitor_brands = [b['name'] for b in unique_top3[:3]]
            api_logger.info(f"[BrandAnalysis] 未指定竞品，使用提取的 TOP3: {competitor_brands}")

        # 步骤 3: 分析用户品牌在每个回答中的表现
        user_brand_mentions = []
        for result in results:
            mention = self._analyze_brand_in_response(
                response=result.get('response', ''),
                brand=user_brand,
                question=result.get('question', '')
            )
            user_brand_mentions.append(mention)

        # 计算用户品牌统计
        mentioned_count = sum(1 for m in user_brand_mentions if m.get('brand_mentioned', False))
        total_responses = len(results)

        analysis['user_brand_analysis'] = {
            'brand': user_brand,
            'mentions': user_brand_mentions,
            'mentioned_count': mentioned_count,
            'total_responses': total_responses,
            'mention_rate': mentioned_count / total_responses if total_responses > 0 else 0,
            'average_rank': self._calc_average_rank(user_brand_mentions),
            'average_sentiment': self._calc_average_sentiment(user_brand_mentions),
            'is_top3': any(m.get('is_top3', False) for m in user_brand_mentions)
        }

        # 步骤 4: 分析竞品品牌
        for competitor in competitor_brands:
            competitor_mentions = []
            for result in results:
                mention = self._analyze_brand_in_response(
                    response=result.get('response', ''),
                    brand=competitor,
                    question=result.get('question', '')
                )
                competitor_mentions.append(mention)

            comp_mentioned_count = sum(1 for m in competitor_mentions if m.get('brand_mentioned', False))
            analysis['competitor_analysis'].append({
                'brand': competitor,
                'mentions': competitor_mentions,
                'mentioned_count': comp_mentioned_count,
                'mention_rate': comp_mentioned_count / total_responses if total_responses > 0 else 0,
                'average_rank': self._calc_average_rank(competitor_mentions),
                'average_sentiment': self._calc_average_sentiment(competitor_mentions),
                'is_top3': any(m.get('is_top3', False) for m in competitor_mentions)
            })

        # 步骤 5: 生成对比分析
        analysis['comparison'] = self._generate_comparison(
            user_analysis=analysis['user_brand_analysis'],
            competitor_analyses=analysis['competitor_analysis']
        )

        api_logger.info(
            f"[BrandAnalysis] 分析完成：{user_brand}, "
            f"提及率={analysis['user_brand_analysis']['mention_rate']:.1%}, "
            f"竞品数={len(analysis['competitor_analysis'])}"
        )

        return analysis

    def _extract_top3_brands(self, response: str) -> List[Dict[str, Any]]:
        """
        从回答中提取 TOP3 品牌

        Args:
            response: AI 回答文本

        Returns:
            TOP3 品牌列表
        """
        # 尝试解析 JSON 格式的 top3_brands
        try:
            # 查找 JSON 部分（支持多种格式）
            json_patterns = [
                r'\{\s*"top3_brands"\s*:\s*\[.*?\]\s*\}',  # 完整 JSON 对象
                r'\[\s*\{.*?"name".*?"rank".*?\}\s*\]',    # 直接是数组
            ]

            for pattern in json_patterns:
                json_match = re.search(pattern, response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)

                    # 如果是完整对象，提取 top3_brands 字段
                    if isinstance(data, dict) and 'top3_brands' in data:
                        return data['top3_brands']
                    # 如果直接是数组，返回
                    elif isinstance(data, list):
                        return data

        except (json.JSONDecodeError, AttributeError) as e:
            api_logger.warning(f"[BrandAnalysis] JSON 解析失败：{e}")

        # 降级：使用正则提取品牌名（简单匹配）
        # 匹配模式："name": "品牌名" 或 "name":"品牌名"
        brand_pattern = r'"name"\s*:\s*"([^"]+)"'
        matches = re.findall(brand_pattern, response)

        if matches:
            api_logger.warning(f"[BrandAnalysis] 使用降级方案提取品牌：{matches[:3]}")
            return [{'name': name, 'rank': i+1, 'reason': ''} for i, name in enumerate(matches[:3])]

        return []

    def _analyze_brand_in_response(
        self,
        response: str,
        brand: str,
        question: str
    ) -> Dict[str, Any]:
        """
        分析品牌在回答中的表现

        Args:
            response: AI 回答文本
            brand: 品牌名称
            question: 原始问题

        Returns:
            品牌分析结果
        """
        # 方案 1: 使用 AI 分析（更准确）
        try:
            client = AIAdapterFactory.create(self.judge_model)
            prompt = BRAND_ANALYSIS_TEMPLATE.format(
                ai_response=response[:2000],  # 限制长度避免超时
                user_brand=brand,
                question=question
            )

            result = client.send_prompt(prompt)

            # 解析分析结果
            if result and hasattr(result, 'data'):
                analysis_data = self._parse_brand_analysis(result.data)
                if analysis_data:
                    return analysis_data

        except Exception as e:
            api_logger.warning(f"[BrandAnalysis] AI 分析失败：{e}，使用降级方案")

        # 方案 2: 简单文本匹配（降级方案）
        mentioned = brand.lower() in response.lower()

        # 尝试提取排名（匹配 "rank": 数字）
        rank = -1
        rank_match = re.search(r'"rank"\s*:\s*(-?\d+)', response)
        if rank_match:
            rank = int(rank_match.group(1))

        # 尝试提取情感（匹配 "sentiment": 数字）
        sentiment = 0.0
        sentiment_match = re.search(r'"sentiment"\s*:\s*(-?[\d.]+)', response)
        if sentiment_match:
            sentiment = float(sentiment_match.group(1))

        # 判断是否在 TOP3 中
        is_top3 = False
        top3_match = re.search(r'"is_top3"\s*:\s*(true|false)', response, re.IGNORECASE)
        if top3_match:
            is_top3 = top3_match.group(1).lower() == 'true'

        return {
            'brand_mentioned': mentioned,
            'rank': rank,
            'sentiment': sentiment,
            'is_top3': is_top3,
            'mention_context': self._extract_mention_context(response, brand) if mentioned else ''
        }

    def _parse_brand_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析品牌分析 AI 响应

        Args:
            text: AI 响应文本

        Returns:
            解析后的分析结果，失败返回 None
        """
        try:
            # 查找 JSON 部分
            json_match = re.search(r'\{.*"brand_analysis".*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                analysis = data.get('brand_analysis', {})
                return {
                    'brand_mentioned': analysis.get('brand_mentioned', False),
                    'rank': analysis.get('rank', -1),
                    'sentiment': analysis.get('sentiment', 0),
                    'is_top3': analysis.get('is_top3', False),
                    'mention_context': analysis.get('mention_context', '')
                }
        except (json.JSONDecodeError, AttributeError) as e:
            api_logger.warning(f"[BrandAnalysis] 解析 AI 分析结果失败：{e}")

        return None

    def _extract_mention_context(self, response: str, brand: str) -> str:
        """
        提取品牌提及的上下文

        Args:
            response: AI 回答文本
            brand: 品牌名称

        Returns:
            提及上下文字符串
        """
        # 查找品牌名出现的位置
        brand_lower = brand.lower()
        response_lower = response.lower()

        index = response_lower.find(brand_lower)
        if index == -1:
            return ''

        # 提取前后各 50 个字符
        start = max(0, index - 50)
        end = min(len(response), index + len(brand) + 50)

        context = response[start:end].strip()
        return f"...{context}..."

    def _calc_average_rank(self, mentions: List[Dict]) -> float:
        """
        计算平均排名

        Args:
            mentions: 品牌提及列表

        Returns:
            平均排名，未提及返回 -1
        """
        ranks = [m['rank'] for m in mentions if m.get('rank', -1) > 0]
        return sum(ranks) / len(ranks) if ranks else -1

    def _calc_average_sentiment(self, mentions: List[Dict]) -> float:
        """
        计算平均情感分

        Args:
            mentions: 品牌提及列表

        Returns:
            平均情感分
        """
        sentiments = [m['sentiment'] for m in mentions if m.get('brand_mentioned', False)]
        return sum(sentiments) / len(sentiments) if sentiments else 0

    def _generate_comparison(
        self,
        user_analysis: Dict,
        competitor_analyses: List[Dict]
    ) -> Dict[str, Any]:
        """
        生成对比分析

        Args:
            user_analysis: 用户品牌分析
            competitor_analyses: 竞品分析列表

        Returns:
            对比分析结果
        """
        user_mention_rate = user_analysis.get('mention_rate', 0)
        user_avg_rank = user_analysis.get('average_rank', -1)
        user_avg_sentiment = user_analysis.get('average_sentiment', 0)

        vs_competitors = []
        for comp in competitor_analyses:
            comp_mention_rate = comp.get('mention_rate', 0)
            comp_avg_rank = comp.get('average_rank', -1)
            comp_avg_sentiment = comp.get('average_sentiment', 0)

            vs_competitors.append({
                'competitor': comp['brand'],
                'mention_rate_diff': user_mention_rate - comp_mention_rate,
                'rank_diff': user_avg_rank - comp_avg_rank if user_avg_rank > 0 and comp_avg_rank > 0 else 0,
                'sentiment_diff': user_avg_sentiment - comp_avg_sentiment,
                'advantage': self._get_advantage_text(
                    user_mention_rate, comp_mention_rate,
                    user_avg_rank, comp_avg_rank,
                    user_avg_sentiment, comp_avg_sentiment
                )
            })

        return {
            'user_brand': user_analysis.get('brand', ''),
            'mention_rate': user_mention_rate,
            'average_rank': user_avg_rank,
            'average_sentiment': user_avg_sentiment,
            'is_top3': user_analysis.get('is_top3', False),
            'vs_competitors': vs_competitors,
            'summary': self._generate_summary(user_analysis, competitor_analyses)
        }

    def _get_advantage_text(
        self,
        user_rate: float, comp_rate: float,
        user_rank: float, comp_rank: float,
        user_sentiment: float, comp_sentiment: float
    ) -> str:
        """
        生成优势劣势描述

        Returns:
            优势/劣势描述文本
        """
        advantages = []
        disadvantages = []

        if user_rate > comp_rate:
            advantages.append(f"提及率高 {int((user_rate - comp_rate) * 100)}%")
        elif user_rate < comp_rate:
            disadvantages.append(f"提及率低 {int((comp_rate - user_rate) * 100)}%")

        if user_rank > 0 and comp_rank > 0:
            if user_rank < comp_rank:
                advantages.append(f"排名靠前 ({int(user_rank)} vs {int(comp_rank)})")
            elif user_rank > comp_rank:
                disadvantages.append(f"排名靠后 ({int(user_rank)} vs {int(comp_rank)})")

        if user_sentiment > comp_sentiment:
            advantages.append(f"情感更积极")
        elif user_sentiment < comp_sentiment:
            disadvantages.append(f"情感较消极")

        if advantages and disadvantages:
            return f"优势：{', '.join(advantages)}；劣势：{', '.join(disadvantages)}"
        elif advantages:
            return f"优势：{', '.join(advantages)}"
        elif disadvantages:
            return f"劣势：{', '.join(disadvantages)}"
        else:
            return "表现相当"

    def _generate_summary(
        self,
        user_analysis: Dict,
        competitor_analyses: List[Dict]
    ) -> str:
        """
        生成总结性描述

        Args:
            user_analysis: 用户品牌分析
            competitor_analyses: 竞品分析列表

        Returns:
            总结文本
        """
        brand = user_analysis.get('brand', '该品牌')
        mention_rate = user_analysis.get('mention_rate', 0)
        avg_rank = user_analysis.get('average_rank', -1)
        is_top3 = user_analysis.get('is_top3', False)

        summary_parts = []

        # 提及率描述
        if mention_rate >= 0.8:
            summary_parts.append(f"{brand}在 AI 推荐中被高频提及（{int(mention_rate * 100)}%）")
        elif mention_rate >= 0.5:
            summary_parts.append(f"{brand}在 AI 推荐中有一定提及（{int(mention_rate * 100)}%）")
        else:
            summary_parts.append(f"{brand}在 AI 推荐中提及较少（{int(mention_rate * 100)}%）")

        # 排名描述
        if is_top3:
            summary_parts.append("并进入 TOP3 推荐")
        elif avg_rank > 0 and avg_rank <= 5:
            summary_parts.append(f"平均排名第{int(avg_rank)}位")
        elif avg_rank > 5:
            summary_parts.append(f"排名相对靠后（平均第{int(avg_rank)}位）")

        return "，".join(summary_parts)


def get_brand_analysis_service(judge_model: str = 'doubao') -> BrandAnalysisService:
    """
    获取品牌分析服务实例

    Args:
        judge_model: 用于分析的品牌模型

    Returns:
        BrandAnalysisService 实例
    """
    return BrandAnalysisService(judge_model=judge_model)
