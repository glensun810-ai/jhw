"""
评分维度计算器

基于 GEO（生成式引擎优化）的核心价值，计算品牌在 AI 认知中的 4 个评分维度：
1. 可见度得分 (Visibility Score) - 权重 25%
2. 排位得分 (Rank Score) - 权重 35%
3. 声量得分 (SOV Score) - 权重 25%
4. 情感得分 (Sentiment Score) - 权重 15%

作者：首席架构师
日期：2026-03-22
版本：1.0
"""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict

# 情感分析词典
POSITIVE_KEYWORDS = [
    # 正面评价词
    '领先', '优质', '推荐', '安全', '可靠', '专业', '出色', '优秀', '卓越',
    '好评', '信赖', '首选', '知名', '权威', '创新', '先进', '高端', '精品',
    '满意', '放心', '值得', '建议', '优选', '畅销', '热门', '流行', '经典',
    '稳定', '耐用', '实用', '方便', '智能', '高效', '精准', '舒适', '美观',
    '性价比', '口碑', '认可', '表彰', '奖项', '认证', '专利', '技术',
]

NEGATIVE_KEYWORDS = [
    # 负面评价词
    '不足', '缺点', '问题', '风险', '谨慎', '注意', '避免', '小心',
    '差评', '投诉', '质疑', '争议', '负面', '劣质的', '不可靠', '危险',
    '昂贵', '昂贵', '过贵', '性价比低', '不推荐', '避免购买', '慎重',
    '故障', '损坏', '失灵', '问题多', '质量差', '服务差', '态度差',
    '落后', '过时', '陈旧', '淘汰', '低端', '廉价感', '粗糙',
]

NEUTRAL_KEYWORDS = [
    # 中性描述词（用于事实陈述）
    '成立于', '总部位于', '位于', '创建于', '创立于',
    '主要产品', '业务范围', '旗下品牌', '属于', '旗下',
    '型号', '规格', '参数', '配置', '功能',
    '价格', '售价', '市场价', '参考价',
]


class DimensionScorer:
    """评分维度计算器"""
    
    # 维度权重
    WEIGHTS = {
        'visibility': 0.25,
        'rank': 0.35,
        'sov': 0.25,
        'sentiment': 0.15
    }
    
    # 平台权威性权重（用于跨平台聚合）
    PLATFORM_WEIGHTS = {
        'deepseek': 1.2,
        'doubao': 1.1,
        'qwen': 1.0,
        'zhipu': 1.0,
        'chatgpt': 1.2,
        'gemini': 1.1,
        'wenxin': 1.0,
    }
    
    def __init__(self):
        """初始化评分计算器"""
        pass
    
    def score_visibility(self, results: List[Dict[str, Any]], brand_name: str) -> int:
        """
        可见度得分 (Visibility Score) - 权重 25%
        
        衡量用户品牌在 AI 回答中是否被提及，以及提及的显著程度
        
        计算公式：
        Visibility = 基础可见分 + 位置加分 + 篇幅加分
        
        其中：
        - 基础可见分：品牌被提及 = 60 分，未提及 = 0 分
        - 位置加分：
          * 出现在回答前 30% 内容中：+20 分（AI 优先提及）
          * 出现在回答中间 30-70% 内容中：+10 分
          * 出现在回答后 30% 内容中：+0 分
        - 篇幅加分：
          * 品牌描述字数 ≥ 200 字：+20 分
          * 品牌描述字数 100-199 字：+10 分
          * 品牌描述字数 < 100 字：+0 分
        
        参数:
        - results: 诊断结果列表，每项包含 model, raw_response, brand_word_count 等
        - brand_name: 用户品牌名
        
        返回:
        - 可见度得分 (0-100)
        """
        if not results:
            return 0
        
        total_score = 0
        valid_count = 0
        
        for result in results:
            raw_response = result.get('raw_response', '')
            if not raw_response:
                continue
            
            valid_count += 1
            
            # 基础可见分：检查品牌是否被提及
            is_mentioned = brand_name in raw_response
            base_score = 60 if is_mentioned else 0
            
            # 位置加分：分析品牌首次出现的位置
            position_bonus = 0
            if is_mentioned:
                first_pos = raw_response.find(brand_name)
                total_length = len(raw_response)
                if total_length > 0:
                    position_ratio = first_pos / total_length
                    if position_ratio <= 0.3:
                        position_bonus = 20  # 前 30%
                    elif position_ratio <= 0.7:
                        position_bonus = 10  # 中间 30-70%
                    else:
                        position_bonus = 0   # 后 30%
            
            # 篇幅加分：分析品牌描述字数
            word_count_bonus = 0
            brand_word_count = result.get('brand_word_count', 0)
            if brand_word_count >= 200:
                word_count_bonus = 20
            elif brand_word_count >= 100:
                word_count_bonus = 10
            else:
                word_count_bonus = 0
            
            # 计算该结果的可见度得分
            result_score = base_score + position_bonus + word_count_bonus
            result_score = min(100, result_score)  # 上限 100 分
            
            total_score += result_score
        
        # 返回平均得分
        if valid_count == 0:
            return 0
        
        return round(total_score / valid_count)
    
    def score_rank(self, ranking_list: List[str], brand_name: str, total_brands: int = None) -> int:
        """
        排位得分 (Rank Score) - 权重 35%
        
        衡量用户品牌在 AI 回答中的物理排名位置（最核心指标）
        
        计算公式：
        - 第 1 名：100 分
        - 第 2 名：80 分
        - 第 3 名：60 分
        - 第 4 名及以后：40 分
        
        或使用平滑公式：
        Rank_Score = max(0, 100 - (position - 1) × 20)
        
        参数:
        - ranking_list: AI 回答中品牌的出现顺序列表
        - brand_name: 用户品牌名
        - total_brands: 参评品牌总数（可选）
        
        返回:
        - 排位得分 (0-100)
        """
        if not ranking_list:
            return 40  # 默认给基础分
        
        # 查找品牌排名（从 1 开始）
        try:
            position = ranking_list.index(brand_name) + 1
        except ValueError:
            # 品牌不在排名列表中
            return 0
        
        # 使用平滑公式计算得分
        # 第 1 名：100 分，第 2 名：80 分，第 3 名：60 分，第 4 名：40 分，第 5 名+：20 分
        if position == 1:
            return 100
        elif position == 2:
            return 80
        elif position == 3:
            return 60
        elif position == 4:
            return 40
        else:
            return 20
    
    def score_sov(self, results: List[Dict[str, Any]], brand_name: str) -> int:
        """
        声量得分 (SOV Score) - 权重 25%
        
        Share of Voice，衡量用户品牌在 AI 回答中的篇幅占比
        
        计算公式：
        SOV = (用户品牌描述字数 / 所有品牌描述总字数) × 100
        
        声量得分转换：
        - SOV ≥ 40%：100 分（绝对主导）
        - SOV 30-39%：80 分（相对优势）
        - SOV 20-29%：60 分（平均水平）
        - SOV 10-19%：40 分（声量偏低）
        - SOV < 10%：20 分（声量过低）
        
        参数:
        - results: 诊断结果列表
        - brand_name: 用户品牌名
        
        返回:
        - 声量得分 (0-100)
        """
        if not results:
            return 0
        
        total_sov_score = 0
        valid_count = 0
        
        for result in results:
            raw_response = result.get('raw_response', '')
            if not raw_response:
                continue
            
            valid_count += 1
            
            # 计算该回答中各品牌的描述字数
            brand_word_counts = self._extract_brand_word_counts(raw_response, brand_name)
            
            # 计算 SOV
            total_words = sum(brand_word_counts.values())
            if total_words == 0:
                sov_percentage = 0
            else:
                brand_words = brand_word_counts.get(brand_name, 0)
                sov_percentage = (brand_words / total_words) * 100
            
            # SOV 得分转换
            if sov_percentage >= 40:
                sov_score = 100
            elif sov_percentage >= 30:
                sov_score = 80
            elif sov_percentage >= 20:
                sov_score = 60
            elif sov_percentage >= 10:
                sov_score = 40
            else:
                sov_score = 20
            
            total_sov_score += sov_score
        
        if valid_count == 0:
            return 0
        
        return round(total_sov_score / valid_count)
    
    def score_sentiment(self, results: List[Dict[str, Any]], brand_name: str) -> int:
        """
        情感得分 (Sentiment Score) - 权重 15%
        
        衡量 AI 回答中对用户品牌的情感倾向
        
        计算公式：
        情感极性 = (正面数 - 负面数) / (正面数 + 负面数 + 中性数)
        
        情感得分转换：
        - 情感极性 ≥ 0.5：100 分（高度正面）
        - 情感极性 0.3-0.49：80 分（较为正面）
        - 情感极性 0-0.29：60 分（中性偏正）
        - 情感极性 -0.29-0：40 分（中性偏负）
        - 情感极性 ≤ -0.3：20 分（负面评价）
        
        参数:
        - results: 诊断结果列表
        - brand_name: 用户品牌名
        
        返回:
        - 情感得分 (0-100)
        """
        if not results:
            return 60  # 默认中性分
        
        total_sentiment_score = 0
        valid_count = 0
        
        for result in results:
            raw_response = result.get('raw_response', '')
            if not raw_response:
                continue
            
            valid_count += 1
            
            # 提取品牌相关的文本段落
            brand_text = self._extract_brand_text(raw_response, brand_name)
            
            # 情感分析
            sentiment_analysis = self._analyze_sentiment(brand_text)
            polarity = sentiment_analysis['polarity']
            
            # 情感得分转换
            if polarity >= 0.5:
                sentiment_score = 100
            elif polarity >= 0.3:
                sentiment_score = 80
            elif polarity >= 0:
                sentiment_score = 60
            elif polarity >= -0.3:
                sentiment_score = 40
            else:
                sentiment_score = 20
            
            total_sentiment_score += sentiment_score
        
        if valid_count == 0:
            return 60
        
        return round(total_sentiment_score / valid_count)
    
    def calculate_overall_score(
        self,
        visibility_score: int,
        rank_score: int,
        sov_score: int,
        sentiment_score: int
    ) -> int:
        """
        计算综合评分
        
        Overall_Score = Visibility × 0.25 + Rank × 0.35 + SOV × 0.25 + Sentiment × 0.15
        
        参数:
        - visibility_score: 可见度得分
        - rank_score: 排位得分
        - sov_score: 声量得分
        - sentiment_score: 情感得分
        
        返回:
        - 综合得分 (0-100)
        """
        overall = (
            visibility_score * self.WEIGHTS['visibility'] +
            rank_score * self.WEIGHTS['rank'] +
            sov_score * self.WEIGHTS['sov'] +
            sentiment_score * self.WEIGHTS['sentiment']
        )
        return round(overall)
    
    def calculate_cross_platform_consistency(self, platform_scores: List[int]) -> int:
        """
        计算跨平台一致性得分
        
        当用户选择多个 AI 平台时，计算各平台评分的一致性
        
        参数:
        - platform_scores: 各平台的综合得分列表
        
        返回:
        - 一致性得分 (0-100)
        """
        if len(platform_scores) < 2:
            return 100  # 单平台无需一致性
        
        # 计算平均值
        avg_score = sum(platform_scores) / len(platform_scores)
        
        # 计算方差
        variance = sum((s - avg_score) ** 2 for s in platform_scores) / len(platform_scores)
        
        # 标准差
        std_dev = variance ** 0.5
        
        # 一致性得分：标准差越小，一致性越高
        # 标准差 0：100 分，标准差 20+：0 分
        consistency_score = max(0, 100 - std_dev * 5)
        
        return round(consistency_score)
    
    def aggregate_platform_scores(
        self,
        platform_results: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        聚合多平台评分
        
        参数:
        - platform_results: {平台名：{各维度得分}}
        
        返回:
        - 聚合后的得分和详细数据
        """
        if not platform_results:
            return {
                'visibility_score': 0,
                'rank_score': 0,
                'sov_score': 0,
                'sentiment_score': 0,
                'overall_score': 0,
                'cross_platform_consistency': 100,
                'platform_details': {}
            }
        
        # 收集各维度得分
        visibility_scores = []
        rank_scores = []
        sov_scores = []
        sentiment_scores = []
        overall_scores = []
        
        platform_details = {}
        
        for platform, scores in platform_results.items():
            # 获取平台权重
            platform_weight = self.PLATFORM_WEIGHTS.get(platform.lower(), 1.0)
            
            # 计算该平台的综合得分
            overall = self.calculate_overall_score(
                scores.get('visibility', 0),
                scores.get('rank', 0),
                scores.get('sov', 0),
                scores.get('sentiment', 0)
            )
            
            platform_details[platform] = {
                'scores': scores,
                'overall': overall,
                'weight': platform_weight
            }
            
            # 收集各维度得分（用于加权平均）
            visibility_scores.append((scores.get('visibility', 0), platform_weight))
            rank_scores.append((scores.get('rank', 0), platform_weight))
            sov_scores.append((scores.get('sov', 0), platform_weight))
            sentiment_scores.append((scores.get('sentiment', 0), platform_weight))
            overall_scores.append((overall, platform_weight))
        
        # 计算加权平均
        def weighted_average(score_weight_list):
            total_score = sum(s * w for s, w in score_weight_list)
            total_weight = sum(w for _, w in score_weight_list)
            return round(total_score / total_weight) if total_weight > 0 else 0
        
        # 计算简单平均（用于一致性计算）
        simple_overall_scores = [s for s, _ in overall_scores]
        cross_platform_consistency = self.calculate_cross_platform_consistency(simple_overall_scores)
        
        return {
            'visibility_score': weighted_average(visibility_scores),
            'rank_score': weighted_average(rank_scores),
            'sov_score': weighted_average(sov_scores),
            'sentiment_score': weighted_average(sentiment_scores),
            'overall_score': weighted_average(overall_scores),
            'cross_platform_consistency': cross_platform_consistency,
            'platform_details': platform_details
        }
    
    def _extract_brand_word_counts(self, text: str, target_brand: str) -> Dict[str, int]:
        """
        提取文本中各品牌的描述字数
        
        参数:
        - text: AI 回答文本
        - target_brand: 目标品牌名
        
        返回:
        - {品牌名：描述字数}
        """
        brand_counts = defaultdict(int)
        
        # 简单实现：按品牌名分割文本，估算各品牌描述字数
        # 实际项目中可能需要更复杂的 NLP 处理
        
        # 常见品牌关键词（实际项目中应从品牌列表获取）
        brand_keywords = [
            target_brand,  # 用户品牌
            '小米', '凯迪仕', '鹿客', '飞利浦', 'TCL', '华为',  # 常见竞品
            '其他品牌', '其他', '竞品'
        ]
        
        # 查找每个品牌在文本中的位置
        brand_positions = []
        for brand in brand_keywords:
            pos = text.find(brand)
            if pos >= 0:
                brand_positions.append((pos, brand))
        
        # 按位置排序
        brand_positions.sort(key=lambda x: x[0])
        
        # 估算各品牌描述字数（到下一个品牌提及位置）
        for i, (pos, brand) in enumerate(brand_positions):
            if i < len(brand_positions) - 1:
                next_pos = brand_positions[i + 1][0]
                word_count = next_pos - pos
            else:
                # 最后一个品牌，计算到文本末尾
                word_count = len(text) - pos
            
            # 限制最大字数（避免过度估算）
            word_count = min(word_count, 500)
            brand_counts[brand] += word_count
        
        return dict(brand_counts)
    
    def _extract_brand_text(self, text: str, brand_name: str) -> str:
        """
        提取文本中与品牌相关的段落
        
        参数:
        - text: AI 回答文本
        - brand_name: 品牌名
        
        返回:
        - 品牌相关文本
        """
        if brand_name not in text:
            return ""
        
        # 简单实现：返回包含品牌名的前后各 200 字
        pos = text.find(brand_name)
        start = max(0, pos - 200)
        end = min(len(text), pos + 200)
        
        return text[start:end]
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        情感分析
        
        参数:
        - text: 待分析文本
        
        返回:
        - {
            'polarity': 情感极性值 (-1 到 1),
            'positive_count': 正面词数量,
            'negative_count': 负面词数量,
            'neutral_count': 中性词数量,
            'positive_keywords': 正面词列表,
            'negative_keywords': 负面词列表
          }
        """
        if not text:
            return {
                'polarity': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'positive_keywords': [],
                'negative_keywords': []
            }
        
        # 统计各类情感词
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        positive_found = []
        negative_found = []
        
        # 查找正面词
        for keyword in POSITIVE_KEYWORDS:
            if keyword in text:
                positive_count += 1
                positive_found.append(keyword)
        
        # 查找负面词
        for keyword in NEGATIVE_KEYWORDS:
            if keyword in text:
                negative_count += 1
                negative_found.append(keyword)
        
        # 查找中性词
        for keyword in NEUTRAL_KEYWORDS:
            if keyword in text:
                neutral_count += 1
        
        # 计算情感极性
        total = positive_count + negative_count + neutral_count
        if total == 0:
            polarity = 0
        else:
            polarity = (positive_count - negative_count) / total
        
        return {
            'polarity': polarity,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_keywords': list(set(positive_found)),
            'negative_keywords': list(set(negative_found))
        }
    
    def calculate_all_dimensions(
        self,
        results: List[Dict[str, Any]],
        brand_name: str,
        ranking_list: List[str] = None
    ) -> Dict[str, Any]:
        """
        计算所有评分维度
        
        参数:
        - results: 诊断结果列表
        - brand_name: 用户品牌名
        - ranking_list: 品牌排名列表（可选）
        
        返回:
        - 包含所有维度得分和详细数据的字典
        """
        # 计算各维度得分
        visibility_score = self.score_visibility(results, brand_name)
        
        if ranking_list is None:
            ranking_list = []
        rank_score = self.score_rank(ranking_list, brand_name)
        
        sov_score = self.score_sov(results, brand_name)
        sentiment_score = self.score_sentiment(results, brand_name)
        
        # 计算综合得分
        overall_score = self.calculate_overall_score(
            visibility_score,
            rank_score,
            sov_score,
            sentiment_score
        )
        
        # 获取详细数据（用于诊断墙）
        detailed_data = self._get_detailed_data(results, brand_name, ranking_list)
        
        return {
            'visibility_score': visibility_score,
            'rank_score': rank_score,
            'sov_score': sov_score,
            'sentiment_score': sentiment_score,
            'overall_score': overall_score,
            'cross_platform_consistency': 100,  # 单平台默认 100
            'detailed_data': detailed_data
        }
    
    def _get_detailed_data(
        self,
        results: List[Dict[str, Any]],
        brand_name: str,
        ranking_list: List[str]
    ) -> Dict[str, Any]:
        """
        获取详细数据（用于诊断墙生成）
        
        参数:
        - results: 诊断结果列表
        - brand_name: 用户品牌名
        - ranking_list: 品牌排名列表
        
        返回:
        - 详细数据字典
        """
        # 计算排名相关数据
        position = 0
        if brand_name in ranking_list:
            position = ranking_list.index(brand_name) + 1
        
        # 计算 SOV 相关数据
        total_words = 0
        brand_words = 0
        for result in results:
            raw_response = result.get('raw_response', '')
            if raw_response:
                brand_word_counts = self._extract_brand_word_counts(raw_response, brand_name)
                total_words += sum(brand_word_counts.values())
                brand_words += brand_word_counts.get(brand_name, 0)
        
        sov_percentage = (brand_words / total_words * 100) if total_words > 0 else 0
        
        # 情感分析
        all_positive = []
        all_negative = []
        for result in results:
            raw_response = result.get('raw_response', '')
            if raw_response:
                brand_text = self._extract_brand_text(raw_response, brand_name)
                sentiment = self._analyze_sentiment(brand_text)
                all_positive.extend(sentiment['positive_keywords'])
                all_negative.extend(sentiment['negative_keywords'])
        
        return {
            'position': position,
            'total_brands': len(ranking_list),
            'competitor_ranks': {b: i + 1 for i, b in enumerate(ranking_list) if b != brand_name},
            'sov': round(sov_percentage, 1),
            'word_count': brand_words,
            'avg_word_count': round(brand_words / len(results)) if results else 0,
            'sentiment': round((len(all_positive) - len(all_negative)) / (len(all_positive) + len(all_negative) + 1), 2),
            'positive_keywords': list(set(all_positive))[:5],
            'negative_keywords': list(set(all_negative))[:5],
        }
