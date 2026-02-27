"""
品牌分析服务

职责：
1. 从 AI 客观回答中提取品牌提及
2. 提取 TOP3 品牌作为竞品
3. 对比用户品牌与竞品表现
"""

import json
import re
from typing import List, Dict, Any
from wechat_backend.ai_adapters.base_adapter import BRAND_ANALYSIS_TEMPLATE
from wechat_backend.ai_adapters.factory import AIAdapterFactory


class BrandAnalysisService:
    """品牌分析服务"""

    def __init__(self):
        self.judge_model = 'doubao'  # 使用 doubao 作为分析模型

    def analyze_brand_mentions(
            self,
            results: List[Dict[str, Any]],
            user_brand: str,
            competitor_brands: List[str] = None
    ) -> Dict[str, Any]:
        """
        分析品牌提及情况

        Args:
            results: AI 回答列表
            user_brand: 用户品牌
            competitor_brands: 竞品品牌（可选，若为 None 则从回答中提取）

        Returns:
            分析结果
        """
        analysis = {
            'user_brand_analysis': {},
            'competitor_analysis': [],
            'comparison': {}
        }

        # 步骤 1: 从每个回答中提取 TOP3 品牌
        all_top3_brands = []
        for result in results:
            top3 = self._extract_top3_brands(result['response'])
            all_top3_brands.extend(top3)

        # 步骤 2: 若未指定竞品，使用 TOP3 品牌作为竞品
        if not competitor_brands:
            competitor_brands = list(set([b['name'] for b in all_top3_brands if b['name'] != user_brand]))[:3]

        # 步骤 3: 分析用户品牌在每个回答中的表现
        user_brand_mentions = []
        for result in results:
            mention = self._analyze_brand_in_response(
                response=result['response'],
                brand=user_brand,
                question=result['question']
            )
            user_brand_mentions.append(mention)

        analysis['user_brand_analysis'] = {
            'brand': user_brand,
            'mentions': user_brand_mentions,
            'mentioned_count': sum(1 for m in user_brand_mentions if m['brand_mentioned']),
            'total_responses': len(results),
            'mention_rate': sum(1 for m in user_brand_mentions if m['brand_mentioned']) / len(results),
            'average_rank': self._calc_average_rank(user_brand_mentions),
            'average_sentiment': self._calc_average_sentiment(user_brand_mentions)
        }

        # 步骤 4: 分析竞品品牌
        for competitor in competitor_brands:
            competitor_mentions = []
            for result in results:
                mention = self._analyze_brand_in_response(
                    response=result['response'],
                    brand=competitor,
                    question=result['question']
                )
                competitor_mentions.append(mention)

            analysis['competitor_analysis'].append({
                'brand': competitor,
                'mentions': competitor_mentions,
                'mentioned_count': sum(1 for m in competitor_mentions if m['brand_mentioned']),
                'average_rank': self._calc_average_rank(competitor_mentions),
                'average_sentiment': self._calc_average_sentiment(competitor_mentions)
            })

        # 步骤 5: 对比分析
        analysis['comparison'] = self._generate_comparison(
            user_analysis=analysis['user_brand_analysis'],
            competitor_analyses=analysis['competitor_analysis']
        )

        return analysis

    def _extract_top3_brands(self, response: str) -> List[Dict[str, Any]]:
        """从回答中提取 TOP3 品牌"""
        # 尝试解析 JSON 格式的 top3_brands
        try:
            # 查找 JSON 部分
            json_match = re.search(r'\{.*"top3_brands".*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('top3_brands', [])
        except:
            pass

        # 降级：使用正则提取
        return []

    def _analyze_brand_in_response(
            self,
            response: str,
            brand: str,
            question: str
    ) -> Dict[str, Any]:
        """分析品牌在回答中的表现"""
        # 使用 AI 分析
        client = AIAdapterFactory.create(self.judge_model)
        prompt = BRAND_ANALYSIS_TEMPLATE.format(
            ai_response=response,
            user_brand=brand,
            question=question
        )

        result = client.send_prompt(prompt)

        # 解析分析结果
        try:
            json_match = re.search(r'\{.*"brand_analysis".*\}', result.data, re.DOTALL)
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
        except:
            pass

        # 降级：简单文本匹配
        mentioned = brand.lower() in response.lower()
        return {
            'brand_mentioned': mentioned,
            'rank': -1 if not mentioned else 0,
            'sentiment': 0,
            'is_top3': False,
            'mention_context': ''
        }

    def _calc_average_rank(self, mentions: List[Dict]) -> float:
        """计算平均排名"""
        ranks = [m['rank'] for m in mentions if m['rank'] > 0]
        return sum(ranks) / len(ranks) if ranks else -1

    def _calc_average_sentiment(self, mentions: List[Dict]) -> float:
        """计算平均情感分"""
        sentiments = [m['sentiment'] for m in mentions if m['brand_mentioned']]
        return sum(sentiments) / len(sentiments) if sentiments else 0

    def _generate_comparison(
            self,
            user_analysis: Dict,
            competitor_analyses: List[Dict]
    ) -> Dict[str, Any]:
        """生成对比分析"""
        return {
            'user_brand': user_analysis['brand'],
            'mention_rate': user_analysis['mention_rate'],
            'average_rank': user_analysis['average_rank'],
            'average_sentiment': user_analysis['average_sentiment'],
            'vs_competitors': [
                {
                    'competitor': comp['brand'],
                    'mention_rate_diff': user_analysis['mention_rate'] - (
                                comp['mentioned_count'] / len(comp['mentions'])),
                    'rank_diff': user_analysis['average_rank'] - comp['average_rank'],
                    'sentiment_diff': user_analysis['average_sentiment'] - comp['average_sentiment']
                }
                for comp in competitor_analyses
            ]
        }


def get_brand_analysis_service() -> BrandAnalysisService:
    """获取品牌分析服务实例"""
    return BrandAnalysisService()