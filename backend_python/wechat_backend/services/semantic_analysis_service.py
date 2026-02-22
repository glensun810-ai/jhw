"""
语义分析服务

功能：
- 语义偏移检测
- 关键词提取
- 情感分析
"""

from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger


class SemanticAnalysisService:
    """
    语义分析服务类
    
    功能：
    - 语义偏移检测
    - 关键词提取
    - 情感分析
    """
    
    @staticmethod
    def analyze_semantic_drift(
        official_keywords: List[str],
        ai_generated_keywords: List[str],
        responses: List[str]
    ) -> Dict[str, Any]:
        """
        分析语义偏移
        
        参数：
        - official_keywords: 官方关键词
        - ai_generated_keywords: AI 生成的关键词
        - responses: AI 响应列表
        
        返回：
        - analysis: 语义分析结果
        """
        try:
            # 计算偏移分数
            drift_score = SemanticAnalysisService._calculate_drift_score(
                official_keywords,
                ai_generated_keywords
            )
            
            # 判断偏移严重程度
            if drift_score >= 60:
                severity = 'high'
                text = '严重偏移'
            elif drift_score >= 30:
                severity = 'medium'
                text = '中度偏移'
            else:
                severity = 'low'
                text = '偏移轻微'
            
            # 提取缺失和意外的关键词
            missing = SemanticAnalysisService._find_missing_keywords(
                official_keywords,
                ai_generated_keywords
            )
            unexpected = SemanticAnalysisService._find_unexpected_keywords(
                official_keywords,
                ai_generated_keywords
            )
            
            analysis = {
                'drift_score': drift_score,
                'drift_severity': severity,
                'drift_severity_text': text,
                'missing_keywords': missing,
                'unexpected_keywords': unexpected,
                'similarity_score': 100 - drift_score
            }
            
            api_logger.info(f'[SemanticAnalysisService] 语义偏移分析完成：偏移分数 {drift_score}')
            
            return analysis
            
        except Exception as e:
            api_logger.error(f'[SemanticAnalysisService] 语义偏移分析失败：{e}')
            return {'error': str(e)}
    
    @staticmethod
    def _calculate_drift_score(
        official_keywords: List[str],
        ai_generated_keywords: List[str]
    ) -> int:
        """
        计算偏移分数
        
        参数：
        - official_keywords: 官方关键词
        - ai_generated_keywords: AI 生成的关键词
        
        返回：
        - score: 偏移分数
        """
        if not official_keywords or not ai_generated_keywords:
            return 0
        
        # 计算 Jaccard 相似度
        official_set = set(official_keywords)
        ai_set = set(ai_generated_keywords)
        
        intersection = len(official_set & ai_set)
        union = len(official_set | ai_set)
        
        if union == 0:
            return 0
        
        similarity = intersection / union
        
        # 转换为偏移分数（1 - 相似度）
        return round((1 - similarity) * 100)
    
    @staticmethod
    def _find_missing_keywords(
        official_keywords: List[str],
        ai_generated_keywords: List[str]
    ) -> List[str]:
        """
        查找缺失的关键词
        
        参数：
        - official_keywords: 官方关键词
        - ai_generated_keywords: AI 生成的关键词
        
        返回：
        - missing: 缺失的关键词
        """
        official_set = set(official_keywords)
        ai_set = set(ai_generated_keywords)
        
        return list(official_set - ai_set)
    
    @staticmethod
    def _find_unexpected_keywords(
        official_keywords: List[str],
        ai_generated_keywords: List[str]
    ) -> List[str]:
        """
        查找意外的关键词
        
        参数：
        - official_keywords: 官方关键词
        - ai_generated_keywords: AI 生成的关键词
        
        返回：
        - unexpected: 意外的关键词
        """
        official_set = set(official_keywords)
        ai_set = set(ai_generated_keywords)
        
        return list(ai_set - official_set)
    
    @staticmethod
    def extract_keywords(text: str, top_n: int = 20) -> List[str]:
        """
        提取关键词
        
        参数：
        - text: 文本
        - top_n: 返回前 N 个关键词
        
        返回：
        - keywords: 关键词列表
        """
        # 简化实现：按词频统计
        words = text.split()
        word_count = {}
        
        for word in words:
            if len(word) > 1:
                word_count[word] = word_count.get(word, 0) + 1
        
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, count in sorted_words[:top_n]]


# 导出服务实例
semantic_analysis_service = SemanticAnalysisService()
