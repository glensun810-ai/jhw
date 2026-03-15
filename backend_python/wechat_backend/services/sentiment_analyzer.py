"""
多维度情感分析服务

功能:
- 6 种基础情感分类（喜悦、愤怒、悲伤、恐惧、惊讶、厌恶）
- 情感强度评分
- 情感趋势分析
- 情感分布可视化

@author: 系统架构组
@date: 2026-03-14
@version: 1.0.0
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from wechat_backend.logging_config import api_logger

# 尝试导入 SnowNLP
try:
    from snownlp import SnowNLP
    SNOWNLP_AVAILABLE = True
except ImportError:
    SNOWNLP_AVAILABLE = False
    api_logger.warning("[SentimentAnalyzer] SnowNLP 未安装，使用基础情感分析")


class MultiDimensionalSentimentAnalyzer:
    """
    多维度情感分析器（P1-05 实现版 - 2026-03-14）
    
    功能:
    1. 6 种基础情感分类
    2. 情感强度评分
    3. 情感趋势分析
    """
    
    # 6 种基础情感词库
    EMOTION_WORDS = {
        'joy': [  # 喜悦
            '开心', '高兴', '快乐', '满意', '喜欢', '爱', '棒', '好', '优秀',
            '出色', '推荐', '值得', '惊喜', '愉快', '幸福', '美好', '赞',
            '给力', '靠谱', '完美', '超值', '放心', '舒心', '暖心'
        ],
        'anger': [  # 愤怒
            '生气', '愤怒', '恼火', '气愤', '可恶', '混蛋', '垃圾', '差劲',
            '失望', '坑人', '骗子', '后悔', '投诉', '举报', '维权', '曝光'
        ],
        'sadness': [  # 悲伤
            '难过', '伤心', '悲伤', '失落', '沮丧', '郁闷', '纠结', '无奈',
            '遗憾', '可惜', '心疼', '泪', '哭', '痛苦', '折磨'
        ],
        'fear': [  # 恐惧
            '害怕', '恐惧', '担心', '担忧', '危险', '安全', '隐患', '问题',
            '故障', '坏了', '失灵', '风险', '可怕', '吓人'
        ],
        'surprise': [  # 惊讶
            '惊讶', '吃惊', '震惊', '意外', '没想到', '居然', '竟然',
            '不可思议', '出乎意料', '惊奇', '诧异'
        ],
        'disgust': [  # 厌恶
            '恶心', '讨厌', '厌烦', '嫌弃', '受不了', '糟糕', '烂', '差',
            '劣质', '假冒', '山寨', '劣质', '低俗'
        ]
    }
    
    # 程度副词（用于加权）
    DEGREE_WORDS = {
        'high': ['非常', '特别', '极其', '十分', '太', '最', '超级', '格外', '尤为'],
        'medium': ['比较', '相当', '挺', '蛮', '较为', '颇'],
        'low': ['有点', '有些', '稍微', '略微', '稍', '略']
    }
    
    # 否定词
    NEGATION_WORDS = ['不', '没', '没有', '别', '勿', '莫', '非', '无']
    
    def __init__(self):
        """初始化情感分析器"""
        self.emotion_categories = list(self.EMOTION_WORDS.keys())
        
        api_logger.info("[SentimentAnalyzer] 初始化完成")
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本情感
        
        参数:
            text: 输入文本
            
        返回:
            Dict: 情感分析结果
        """
        if not text:
            return self._create_empty_result()
        
        # 预处理
        text = self._preprocess(text)
        
        # 基础情感分析
        emotion_scores = self._analyze_emotions(text)
        
        # 计算情感强度
        intensity = self._calculate_intensity(text, emotion_scores)
        
        # 计算综合得分
        composite_score = self._calculate_composite_score(emotion_scores)
        
        # 确定主导情感
        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        
        # SnowNLP 补充分析（如果可用）
        snownlp_result = None
        if SNOWNLP_AVAILABLE:
            try:
                s = SnowNLP(text)
                snownlp_result = {
                    'sentiment': s.sentiments,  # 综合情感得分 (0-1)
                    'tags': s.tags  # 词性标注
                }
            except Exception as e:
                api_logger.debug(f"[SentimentAnalyzer] SnowNLP 分析失败：{e}")
        
        return {
            'emotions': emotion_scores,
            'intensity': intensity,
            'composite_score': composite_score,
            'dominant_emotion': dominant_emotion,
            'dominant_score': emotion_scores[dominant_emotion],
            'snownlp': snownlp_result,
            'analysis_time': datetime.now().isoformat()
        }
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        批量分析文本情感
        
        参数:
            texts: 文本列表
            
        返回:
            Dict: 批量分析结果
        """
        if not texts:
            return {
                'summary': {},
                'distribution': {},
                'trend': []
            }
        
        results = []
        emotion_distribution = defaultdict(float)
        
        for text in texts:
            result = self.analyze(text)
            results.append(result)
            
            # 累加情感分布
            for emotion, score in result['emotions'].items():
                emotion_distribution[emotion] += score
        
        # 计算平均情感
        avg_emotions = {
            emotion: round(total / len(texts), 4)
            for emotion, total in emotion_distribution.items()
        }
        
        # 确定整体情感倾向
        overall_emotion = max(avg_emotions, key=avg_emotions.get)
        
        return {
            'results': results,
            'summary': {
                'total_count': len(texts),
                'overall_emotion': overall_emotion,
                'average_emotions': avg_emotions,
                'composite_score': round(sum(r['composite_score'] for r in results) / len(texts), 2)
            },
            'distribution': self._calculate_distribution(results),
            'trend': self._calculate_trend(results)
        }
    
    def analyze_from_results(
        self,
        diagnosis_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        从诊断结果中分析情感
        
        参数:
            diagnosis_results: 诊断结果列表
            
        返回:
            Dict: 情感分析结果
        """
        # 提取所有响应文本
        texts = []
        for result in diagnosis_results:
            response = result.get('response_content', '') or result.get('response', '')
            if response:
                # 处理 JSON 格式的响应
                try:
                    if isinstance(response, str) and response.strip().startswith('{'):
                        response_data = json.loads(response)
                        content = response_data.get('content', '') or response_data.get('text', '')
                        if content:
                            texts.append(content)
                    else:
                        texts.append(response)
                except:
                    texts.append(response)
        
        return self.analyze_batch(texts)
    
    def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """分析 6 种基础情感得分"""
        scores = {emotion: 0.0 for emotion in self.emotion_categories}
        
        # 分词（简单按字符分割）
        words = self._tokenize(text)
        
        # 检测程度副词
        degree_multipliers = self._detect_degree_words(text)
        
        # 检测否定词
        negations = self._detect_negations(text)
        
        for emotion, emotion_words in self.EMOTION_WORDS.items():
            for word in emotion_words:
                if word in text:
                    # 基础得分
                    score = 1.0
                    
                    # 检查是否有程度副词
                    for degree, multiplier in degree_multipliers.items():
                        if degree in degree_multipliers:
                            score *= multiplier
                            break
                    
                    # 检查是否有否定词（情感反转）
                    if self._has_negation_nearby(text, word, negations):
                        score = -score * 0.5
                    
                    scores[emotion] += score
        
        # 归一化到 0-100
        total = sum(abs(s) for s in scores.values())
        if total > 0:
            scores = {
                emotion: round((score / total) * 100, 2)
                for emotion, score in scores.items()
            }
        
        return scores
    
    def _calculate_intensity(self, text: str, emotion_scores: Dict) -> float:
        """计算情感强度"""
        # 基于情感得分的总和
        total_emotion = sum(emotion_scores.values())
        
        # 基于感叹号数量
        exclamation_count = text.count('!') + text.count('！')
        
        # 基于程度副词
        degree_count = sum(
            len([w for w in words if w in text])
            for words in self.DEGREE_WORDS.values()
        )
        
        # 计算强度 (0-100)
        intensity = min(100, (
            total_emotion * 0.5 +
            exclamation_count * 5 +
            degree_count * 3
        ))
        
        return round(intensity, 2)
    
    def _calculate_composite_score(self, emotion_scores: Dict) -> float:
        """
        计算综合情感得分
        
        正面情感：joy, surprise
        负面情感：anger, sadness, fear, disgust
        """
        positive = emotion_scores.get('joy', 0) + emotion_scores.get('surprise', 0)
        negative = (
            emotion_scores.get('anger', 0) +
            emotion_scores.get('sadness', 0) +
            emotion_scores.get('fear', 0) +
            emotion_scores.get('disgust', 0)
        )
        
        # 综合得分 = (正面 - 负面) / 总和 * 100
        total = positive + negative
        if total > 0:
            return round((positive - negative) / total * 100, 2)
        return 0.0
    
    def _calculate_distribution(self, results: List[Dict]) -> Dict[str, Any]:
        """计算情感分布"""
        distribution = {
            'joy': {'count': 0, 'percentage': 0},
            'anger': {'count': 0, 'percentage': 0},
            'sadness': {'count': 0, 'percentage': 0},
            'fear': {'count': 0, 'percentage': 0},
            'surprise': {'count': 0, 'percentage': 0},
            'disgust': {'count': 0, 'percentage': 0}
        }
        
        total = len(results)
        for result in results:
            dominant = result.get('dominant_emotion', '')
            if dominant in distribution:
                distribution[dominant]['count'] += 1
        
        for emotion in distribution:
            distribution[emotion]['percentage'] = round(
                distribution[emotion]['count'] / total * 100 if total > 0 else 0, 2
            )
        
        return distribution
    
    def _calculate_trend(self, results: List[Dict]) -> List[Dict]:
        """计算情感趋势（简化版）"""
        if not results:
            return []
        
        # 按批次计算趋势（每 10 个为一组）
        batch_size = 10
        trends = []
        
        for i in range(0, len(results), batch_size):
            batch = results[i:i + batch_size]
            avg_composite = sum(r['composite_score'] for r in batch) / len(batch)
            trends.append({
                'batch': len(trends) + 1,
                'composite_score': round(avg_composite, 2),
                'sample_count': len(batch)
            })
        
        return trends
    
    def _preprocess(self, text: str) -> str:
        """文本预处理"""
        # 转小写
        text = text.lower()
        
        # 移除 URL
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # 移除特殊符号
        text = re.sub(r'[^\w\u4e00-\u9fa5\s.,!?;:，。！？；：]', '', text)
        
        return text.strip()
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 使用 SnowNLP 如果可用
        if SNOWNLP_AVAILABLE:
            try:
                s = SnowNLP(text)
                return s.words
            except:
                pass
        
        # 降级到简单分词
        return list(text)
    
    def _detect_degree_words(self, text: str) -> Dict[str, float]:
        """检测程度副词"""
        multipliers = {}
        
        for degree, words in self.DEGREE_WORDS.items():
            for word in words:
                if word in text:
                    if degree == 'high':
                        multipliers[word] = 1.5
                    elif degree == 'medium':
                        multipliers[word] = 1.2
                    else:
                        multipliers[word] = 0.8
        
        return multipliers
    
    def _detect_negations(self, text: str) -> List[str]:
        """检测否定词"""
        return [word for word in self.NEGATION_WORDS if word in text]
    
    def _has_negation_nearby(self, text: str, target_word: str, negations: List[str]) -> bool:
        """检查目标词附近是否有否定词"""
        target_index = text.find(target_word)
        if target_index < 0:
            return False
        
        # 检查前后 5 个字符
        start = max(0, target_index - 5)
        end = min(len(text), target_index + len(target_word) + 5)
        nearby_text = text[start:end]
        
        return any(neg in nearby_text for neg in negations)
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            'emotions': {emotion: 0.0 for emotion in self.emotion_categories},
            'intensity': 0.0,
            'composite_score': 0.0,
            'dominant_emotion': 'joy',
            'dominant_score': 0.0,
            'snownlp': None,
            'analysis_time': datetime.now().isoformat()
        }


# 全局单例
_sentiment_analyzer: Optional[MultiDimensionalSentimentAnalyzer] = None


def get_sentiment_analyzer() -> MultiDimensionalSentimentAnalyzer:
    """获取情感分析器单例"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = MultiDimensionalSentimentAnalyzer()
    return _sentiment_analyzer
