"""
关键词提取服务（增强版）

功能:
- TF-IDF 关键词提取
- TextRank 关键词提取
- 中文分词优化
- 停用词过滤

@author: 系统架构组
@date: 2026-03-14
@version: 2.0.0
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from pathlib import Path

from wechat_backend.logging_config import api_logger

# 尝试导入中文分词库
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    api_logger.warning("[KeywordExtractor] jieba 未安装，使用基础分词")

try:
    from snownlp import SnowNLP
    SNOWNLP_AVAILABLE = True
except ImportError:
    SNOWNLP_AVAILABLE = False


class KeywordExtractor:
    """
    关键词提取器（P1-04 增强版 - 2026-03-14）
    
    功能:
    1. TF-IDF 关键词提取
    2. TextRank 关键词提取
    3. 中文分词
    4. 停用词过滤
    """
    
    def __init__(self, stop_words_file: str = None):
        """
        初始化关键词提取器
        
        参数:
            stop_words_file: 停用词文件路径
        """
        # 默认停用词
        self.stop_words = set([
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那',
            '他', '她', '它', '们', '这个', '那个', '什么', '怎么',
            '可以', '没', '与', '及', '等', '能', '对', '为', '我们',
            '你们', '他们', '她们', '啊', '呢', '吗', '吧', '哦',
            '嗯', '呀', '哇', '嘿', '哈', '哎', '哟', '啦', '呗'
        ])
        
        # 加载自定义停用词
        if stop_words_file and Path(stop_words_file).exists():
            self._load_stop_words(stop_words_file)
        
        # 品牌相关词（需要保留的）
        self.brand_keywords = {
            '品牌', '产品', '质量', '服务', '价格', '性价比', '口碑',
            '体验', '功能', '性能', '设计', '外观', '包装', '物流',
            '售后', '客服', '推荐', '购买', '使用', '效果', '满意'
        }
        
        api_logger.info(f"[KeywordExtractor] 初始化完成，停用词数量={len(self.stop_words)}")
    
    def _load_stop_words(self, filepath: str):
        """加载停用词文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word:
                        self.stop_words.add(word)
            api_logger.info(f"[KeywordExtractor] 加载停用词：{filepath}")
        except Exception as e:
            api_logger.error(f"[KeywordExtractor] 加载停用词失败：{e}")
    
    def extract_keywords(
        self,
        texts: List[str],
        top_k: int = 20,
        method: str = 'tfidf'
    ) -> List[Dict[str, Any]]:
        """
        提取关键词
        
        参数:
            texts: 文本列表
            top_k: 返回前 K 个关键词
            method: 提取方法 ('tfidf' | 'textrank' | 'hybrid')
            
        返回:
            List[Dict]: 关键词列表，每个包含 word 和 weight
        """
        if not texts:
            return []
        
        # 合并所有文本
        full_text = ' '.join(texts)
        
        # 选择提取方法
        if method == 'tfidf':
            return self._extract_tfidf(full_text, top_k)
        elif method == 'textrank':
            return self._extract_textrank(full_text, top_k)
        elif method == 'hybrid':
            return self._extract_hybrid(full_text, top_k)
        else:
            return self._extract_tfidf(full_text, top_k)
    
    def _extract_tfidf(self, text: str, top_k: int) -> List[Dict[str, Any]]:
        """
        使用 TF-IDF 提取关键词
        
        TF (Term Frequency) = 词频
        IDF (Inverse Document Frequency) = 逆文档频率
        TF-IDF = TF × IDF
        """
        # 分词
        words = self._tokenize(text)
        
        # 计算词频
        word_freq = Counter(words)
        
        # 计算 TF-IDF
        # 简化版：使用词频作为 TF-IDF（单文档场景）
        total_words = sum(word_freq.values())
        tfidf_scores = {}
        
        for word, freq in word_freq.items():
            # TF = 词频 / 总词数
            tf = freq / total_words if total_words > 0 else 0
            
            # 词长加权（2-4 个字的词权重更高）
            length_weight = 1.0
            if 2 <= len(word) <= 4:
                length_weight = 1.5
            elif len(word) > 4:
                length_weight = 1.2
            
            # 品牌关键词加权
            brand_weight = 1.0
            for brand_kw in self.brand_keywords:
                if brand_kw in word:
                    brand_weight = 1.3
                    break
            
            tfidf_scores[word] = tf * length_weight * brand_weight
        
        # 排序并返回 top_k
        sorted_words = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'word': word, 'weight': round(score, 4)}
            for word, score in sorted_words[:top_k]
        ]
    
    def _extract_textrank(self, text: str, top_k: int) -> List[Dict[str, Any]]:
        """
        使用 TextRank 提取关键词
        
        TextRank 是基于 PageRank 的图排序算法
        """
        # 尝试使用 SnowNLP 的 TextRank
        if SNOWNLP_AVAILABLE:
            try:
                s = SnowNLP(text)
                keywords = s.keywords(top_k)
                
                # 计算权重（使用词频）
                words = self._tokenize(text)
                word_freq = Counter(words)
                total = sum(word_freq.values())
                
                return [
                    {'word': kw, 'weight': round(word_freq.get(kw, 0) / total if total > 0 else 0, 4)}
                    for kw in keywords
                ]
            except Exception as e:
                api_logger.warning(f"[KeywordExtractor] SnowNLP TextRank 失败：{e}")
        
        # 降级到 TF-IDF
        return self._extract_tfidf(text, top_k)
    
    def _extract_hybrid(self, text: str, top_k: int) -> List[Dict[str, Any]]:
        """
        混合方法：结合 TF-IDF 和 TextRank
        """
        # 分别提取
        tfidf_keywords = self._extract_tfidf(text, top_k * 2)
        textrank_keywords = self._extract_textrank(text, top_k * 2)
        
        # 合并评分
        combined_scores = {}
        
        # TF-IDF 分数（归一化）
        max_tfidf = max((kw['weight'] for kw in tfidf_keywords), default=1)
        for kw in tfidf_keywords:
            word = kw['word']
            normalized_score = kw['weight'] / max_tfidf if max_tfidf > 0 else 0
            combined_scores[word] = combined_scores.get(word, 0) + normalized_score * 0.6
        
        # TextRank 分数（归一化）
        max_tr = max((kw['weight'] for kw in textrank_keywords), default=1)
        for kw in textrank_keywords:
            word = kw['word']
            normalized_score = kw['weight'] / max_tr if max_tr > 0 else 0
            combined_scores[word] = combined_scores.get(word, 0) + normalized_score * 0.4
        
        # 排序并返回 top_k
        sorted_words = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'word': word, 'weight': round(score, 4)}
            for word, score in sorted_words[:top_k]
        ]
    
    def _tokenize(self, text: str) -> List[str]:
        """
        中文分词
        
        参数:
            text: 输入文本
            
        返回:
            List[str]: 分词结果
        """
        # 预处理
        text = self._preprocess(text)
        
        # 使用 jieba 分词
        if JIEBA_AVAILABLE:
            words = jieba.lcut(text)
        else:
            # 简单分词：按标点和空格分割
            words = re.findall(r'[\w\u4e00-\u9fa5]{2,}', text)
        
        # 过滤停用词和单字
        filtered_words = []
        for word in words:
            word = word.strip().lower()
            if (len(word) >= 2 and
                word not in self.stop_words and
                not self._is_number_or_symbol(word)):
                filtered_words.append(word)
        
        return filtered_words
    
    def _preprocess(self, text: str) -> str:
        """
        文本预处理
        
        参数:
            text: 原始文本
            
        返回:
            str: 预处理后的文本
        """
        # 转小写
        text = text.lower()
        
        # 移除 URL
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # 移除 @提及
        text = re.sub(r'@\w+', '', text)
        
        # 移除特殊符号和表情
        text = re.sub(r'[^\w\u4e00-\u9fa5\s.,!?;:，。！？；：]', '', text)
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _is_number_or_symbol(self, text: str) -> bool:
        """判断是否纯数字或符号"""
        return text.isdigit() or re.match(r'^[^\w\u4e00-\u9fa5]+$', text)
    
    def extract_from_results(self, results: List[Dict], top_k: int = 20) -> List[Dict[str, Any]]:
        """
        从诊断结果中提取关键词
        
        参数:
            results: 诊断结果列表
            top_k: 返回前 K 个关键词
            
        返回:
            List[Dict]: 关键词列表
        """
        # 收集所有响应文本
        texts = []
        for result in results:
            response = result.get('response_content', '') or result.get('response', '')
            if response:
                # 可能 response 是 JSON 字符串
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
        
        # 提取关键词
        return self.extract_keywords(texts, top_k, method='hybrid')


# 全局单例
_keyword_extractor: Optional[KeywordExtractor] = None


def get_keyword_extractor() -> KeywordExtractor:
    """获取关键词提取器单例"""
    global _keyword_extractor
    if _keyword_extractor is None:
        _keyword_extractor = KeywordExtractor()
    return _keyword_extractor
