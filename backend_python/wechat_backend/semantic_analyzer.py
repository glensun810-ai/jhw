"""
Semantic Analyzer for GEO Content Quality Validator
Implements semantic drift detection and analysis between brand official definitions and AI responses
"""
import re
from typing import Dict, List, Tuple, Optional
import jieba
import jieba.analyse
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .logging_config import api_logger


class SemanticAnalyzer:
    """
    Analyzes semantic drift between brand official definitions and AI responses
    """
    
    def __init__(self):
        api_logger.info("SemanticAnalyzer initialized")
        
        # Initialize Jieba with custom dictionary if available
        # Add common brand-related terms to improve segmentation
        jieba.add_word("人工智能", freq=10000)
        jieba.add_word("品牌认知", freq=10000)
        jieba.add_word("品牌声誉", freq=10000)
        jieba.add_word("品牌定位", freq=10000)
        jieba.add_word("品牌价值", freq=10000)
        jieba.add_word("品牌故事", freq=10000)
        jieba.add_word("品牌理念", freq=10000)
        jieba.add_word("品牌战略", freq=10000)
        jieba.add_word("品牌传播", freq=10000)
        jieba.add_word("品牌营销", freq=10000)
        
        # Common stop words for Chinese text
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', 
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', 
            '好', '自己', '这', '那', '它', '他', '她', '们', '这个', '那个', '什么', 
            '怎么', '为什么', '哪里', '谁', '哪个', '哪些', '这样', '那样', '如此', 
            '这么', '那么', '但是', '或者', '如果', '因为', '所以', '而且', '虽然', 
            '但是', '然而', '因此', '于是', '然后', '接着', '最后', '首先', '其次', 
            '另外', '此外', '总之', '综上所述', '例如', '比如', '像', '如同', '关于', 
            '对于', '至于', '针对', '通过', '根据', '按照', '依据', '由于', '鉴于', 
            '为了', '以便', '以免', '以防', '如果', '要是', '假如', '假使', '倘若', 
            '万一', '要是', '如果', '的话', '而言', '来说', '来看', '来讲', '而', '以', 
            '与', '跟', '同', '和', '及', '以及', '或', '或者', '还是', '即', '就是', 
            '便是', '算是', '谓', '为', '是', '乃', '即', '就是', '便是', '算是', '谓'
        }
    
    def analyze_semantic_drift(
        self, 
        official_definition: str, 
        ai_responses: List[str],
        brand_name: str = None
    ) -> Dict[str, any]:
        """
        Analyze semantic drift between official definition and AI responses
        
        Args:
            official_definition: Brand's official definition/description
            ai_responses: List of AI responses to analyze
            brand_name: Brand name for context (optional)
            
        Returns:
            Dictionary with semantic analysis results
        """
        # Combine all AI responses for analysis
        combined_ai_response = " ".join(ai_responses)
        
        # Extract keywords from both texts
        official_keywords = self.extract_keywords(official_definition, top_k=20)
        ai_keywords = self.extract_keywords(combined_ai_response, top_k=20)
        
        # Calculate semantic similarity
        similarity_score = self.calculate_semantic_similarity(official_definition, combined_ai_response)
        
        # Find missing keywords (in official but not in AI)
        missing_keywords = [kw for kw in official_keywords if kw not in ai_keywords]
        
        # Find unexpected keywords (in AI but not in official)
        unexpected_keywords = [kw for kw in ai_keywords if kw not in official_keywords]
        
        # Calculate semantic drift score (0-100, higher means more drift)
        drift_score = self.calculate_drift_score(
            official_definition, 
            combined_ai_response, 
            similarity_score
        )
        
        # Classify drift severity
        drift_severity = self.classify_drift_severity(drift_score)
        
        # Identify potential negative terms in AI responses
        negative_terms = self.identify_negative_terms(combined_ai_response)
        
        # Identify positive terms in AI responses
        positive_terms = self.identify_positive_terms(combined_ai_response)
        
        return {
            'semantic_drift_score': drift_score,
            'drift_severity': drift_severity,
            'similarity_score': similarity_score,
            'official_keywords': official_keywords,
            'ai_keywords': ai_keywords,
            'missing_keywords': missing_keywords,
            'unexpected_keywords': unexpected_keywords,
            'negative_terms': negative_terms,
            'positive_terms': positive_terms,
            'detailed_analysis': {
                'official_text_length': len(official_definition),
                'ai_response_length': len(combined_ai_response),
                'official_keyword_count': len(official_keywords),
                'ai_keyword_count': len(ai_keywords),
                'missing_count': len(missing_keywords),
                'unexpected_count': len(unexpected_keywords)
            }
        }
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        Extract keywords from text using TF-IDF and Jieba
        
        Args:
            text: Input text to extract keywords from
            top_k: Number of top keywords to return
            
        Returns:
            List of extracted keywords
        """
        if not text or len(text.strip()) < 5:
            return []
        
        # Clean text
        cleaned_text = self.clean_text(text)
        
        # Use Jieba to extract keywords
        keywords = jieba.analyse.extract_tags(cleaned_text, topK=top_k*2, withWeight=False)
        
        # Filter out stop words and short words
        filtered_keywords = [
            kw for kw in keywords 
            if len(kw) >= 2 and kw not in self.stop_words
        ][:top_k]
        
        return filtered_keywords
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using TF-IDF and cosine similarity
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0
        
        # Clean texts
        cleaned_text1 = self.clean_text(text1)
        cleaned_text2 = self.clean_text(text2)
        
        # If texts are too short, return low similarity
        if len(cleaned_text1) < 10 or len(cleaned_text2) < 10:
            return 0.1
        
        # Create TF-IDF vectors
        try:
            vectorizer = TfidfVectorizer(
                tokenizer=self.tokenize_chinese,
                lowercase=False,
                stop_words=None
            )
            
            tfidf_matrix = vectorizer.fit_transform([cleaned_text1, cleaned_text2])
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            similarity = float(similarity_matrix[0][0])
            
            # Ensure similarity is between 0 and 1
            similarity = max(0.0, min(1.0, similarity))
            
            return similarity
        except Exception as e:
            api_logger.error(f"Error calculating semantic similarity: {e}")
            # Fallback: simple overlap ratio
            return self.simple_overlap_ratio(cleaned_text1, cleaned_text2)
    
    def tokenize_chinese(self, text: str) -> List[str]:
        """
        Tokenize Chinese text using Jieba
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens
        """
        tokens = jieba.lcut(text)
        # Filter out stop words and short tokens
        return [token for token in tokens if len(token) >= 2 and token not in self.stop_words]
    
    def simple_overlap_ratio(self, text1: str, text2: str) -> float:
        """
        Calculate simple overlap ratio as fallback
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Overlap ratio between 0 and 1
        """
        words1 = set(self.tokenize_chinese(text1))
        words2 = set(self.tokenize_chinese(text2))
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_drift_score(self, official_text: str, ai_text: str, similarity_score: float) -> float:
        """
        Calculate semantic drift score based on multiple factors
        
        Args:
            official_text: Official brand definition
            ai_text: AI response text
            similarity_score: Pre-calculated similarity score
            
        Returns:
            Drift score between 0 and 100 (higher means more drift)
        """
        # Base drift on inverse of similarity (1 - similarity)
        base_drift = (1 - similarity_score) * 100
        
        # Factor 1: Length difference penalty
        len_ratio = min(len(official_text), len(ai_text)) / max(len(official_text), len(ai_text))
        length_penalty = (1 - len_ratio) * 20  # Up to 20 points penalty
        
        # Factor 2: Keyword mismatch penalty
        official_keywords = self.extract_keywords(official_text, top_k=15)
        ai_keywords = self.extract_keywords(ai_text, top_k=15)
        
        if official_keywords and ai_keywords:
            keyword_overlap = len(set(official_keywords) & set(ai_keywords)) / len(set(official_keywords) | set(ai_keywords))
            keyword_penalty = (1 - keyword_overlap) * 30  # Up to 30 points penalty
        else:
            keyword_penalty = 30  # Maximum penalty if no keywords extracted
        
        # Combine penalties (capped at 100)
        total_drift = min(100, base_drift + length_penalty + keyword_penalty)
        
        return round(total_drift, 2)
    
    def classify_drift_severity(self, drift_score: float) -> str:
        """
        Classify drift severity based on score
        
        Args:
            drift_score: Semantic drift score (0-100)
            
        Returns:
            Severity classification
        """
        if drift_score >= 80:
            return "严重偏移"
        elif drift_score >= 60:
            return "中度偏移"
        elif drift_score >= 40:
            return "轻度偏移"
        else:
            return "轻微偏移"
    
    def identify_negative_terms(self, text: str) -> List[str]:
        """
        Identify potentially negative terms in the text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of negative terms found
        """
        negative_indicators = [
            '差', '烂', '坏', '糟糕', '失望', '问题', '缺陷', '不足', '失败', '错误',
            '投诉', '负面', '不好', '不满意', '糟糕', '差劲', '劣质', '低劣', '缺陷',
            'bug', 'issue', 'problem', 'error', 'failure', 'disappointment', 'poor',
            'terrible', 'awful', 'bad', 'wrong', 'incorrect', 'faulty', 'defective',
            'flawed', 'inadequate', 'insufficient', 'lacking', 'missing', 'absent',
            'nonexistent', 'deficient', 'inferior', 'substandard', 'unsatisfactory'
        ]
        
        text_lower = text.lower()
        found_negatives = []
        
        for indicator in negative_indicators:
            if indicator in text_lower:
                # Extract context around the negative term
                pattern = r'(?:\w+\s+){0,3}' + re.escape(indicator) + r'(?:\s+\w+){0,3}'
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_negatives.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_negatives = []
        for item in found_negatives:
            if item not in seen:
                seen.add(item)
                unique_negatives.append(item)
        
        return unique_negatives[:10]  # Return top 10 negative contexts
    
    def identify_positive_terms(self, text: str) -> List[str]:
        """
        Identify potentially positive terms in the text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of positive terms found
        """
        positive_indicators = [
            '好', '优秀', '棒', '赞', '满意', '出色', '卓越', '完美', '优质', '精品',
            '推荐', '首选', '领先', '第一', '顶级', '高端', '专业', '权威', '可信',
            'good', 'great', 'excellent', 'amazing', 'outstanding', 'superb', 'perfect',
            'recommended', 'top', 'leading', 'premium', 'professional', 'authoritative',
            'reliable', 'trusted', 'reputable', 'established', 'proven', 'effective',
            'efficient', 'reliable', 'dependable', 'solid', 'strong', 'robust'
        ]
        
        text_lower = text.lower()
        found_positives = []
        
        for indicator in positive_indicators:
            if indicator in text_lower:
                # Extract context around the positive term
                pattern = r'(?:\w+\s+){0,3}' + re.escape(indicator) + r'(?:\s+\w+){0,3}'
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_positives.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_positives = []
        for item in found_positives:
            if item not in seen:
                seen.add(item)
                unique_positives.append(item)
        
        return unique_positives[:10]  # Return top 10 positive contexts
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing special characters and extra whitespace
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Chinese characters, letters, numbers, and basic punctuation
        text = re.sub(r'[^\u4e00-\u9fff\w\s\-.,!?;:]', ' ', text)
        
        return text.strip()


class AttributionAnalyzer:
    """
    Analyzes attribution between source weights and semantic analysis
    """
    
    def __init__(self, source_weight_lib):
        self.source_weight_lib = source_weight_lib
        self.semantic_analyzer = SemanticAnalyzer()
        api_logger.info("AttributionAnalyzer initialized")
    
    def analyze_attribution(
        self, 
        official_definition: str, 
        ai_responses: List[str], 
        response_sources: List[str],  # List of source URLs from AI responses
        brand_name: str = None
    ) -> Dict[str, any]:
        """
        Analyze attribution between source weights and semantic drift
        
        Args:
            official_definition: Brand's official definition
            ai_responses: List of AI responses
            response_sources: List of source URLs from AI responses
            brand_name: Brand name for context (optional)
            
        Returns:
            Dictionary with attribution analysis results
        """
        # Perform semantic analysis
        semantic_analysis = self.semantic_analyzer.analyze_semantic_drift(
            official_definition, ai_responses, brand_name
        )
        
        # Extract domains from sources
        domains = self.source_weight_lib.extract_domains_from_urls(response_sources)
        
        # Get weights for domains
        domain_weights = self.source_weight_lib.get_multiple_source_weights(domains)
        
        # Separate high and low weight sources
        high_weight_sources = []
        low_weight_sources = []
        
        for domain, weight_info in domain_weights.items():
            if weight_info:
                weight_score, site_name, category = weight_info
                source_info = {
                    'domain': domain,
                    'site_name': site_name,
                    'weight_score': weight_score,
                    'category': category
                }
                
                if weight_score >= 0.7:
                    high_weight_sources.append(source_info)
                else:
                    low_weight_sources.append(source_info)
        
        # Calculate source purity (ratio of high weight sources)
        total_sources = len([w for w in domain_weights.values() if w is not None])
        high_weight_count = len(high_weight_sources)
        source_purity = (high_weight_count / total_sources * 100) if total_sources > 0 else 0
        
        # Identify potential pollution sources (low weight sources with negative terms)
        pollution_sources = []
        for source_info in low_weight_sources:
            # Check if any AI response contains negative terms and this source was referenced
            for response in ai_responses:
                negative_terms = self.semantic_analyzer.identify_negative_terms(response)
                if negative_terms and self._source_referenced_in_response(response, source_info['domain']):
                    pollution_sources.append({
                        **source_info,
                        'negative_contexts': negative_terms
                    })
        
        # Calculate risk score based on semantic drift and source weights
        risk_score = self._calculate_risk_score(semantic_analysis, high_weight_count, total_sources)
        
        return {
            'semantic_analysis': semantic_analysis,
            'source_analysis': {
                'total_sources': total_sources,
                'high_weight_sources': high_weight_sources,
                'low_weight_sources': low_weight_sources,
                'source_purity_percentage': round(source_purity, 2),
                'pollution_sources': pollution_sources
            },
            'attribution_metrics': {
                'risk_score': risk_score,
                'high_weight_ratio': round(high_weight_count / total_sources if total_sources > 0 else 0, 3),
                'semantic_drift_impact': semantic_analysis['semantic_drift_score'] * (1 - source_purity/100)
            }
        }
    
    def _source_referenced_in_response(self, response: str, domain: str) -> bool:
        """
        Check if a domain is referenced in the response
        
        Args:
            response: AI response text
            domain: Domain to check for
            
        Returns:
            True if domain is referenced in response
        """
        return domain.lower() in response.lower()
    
    def _calculate_risk_score(self, semantic_analysis: Dict, high_weight_count: int, total_sources: int) -> float:
        """
        Calculate overall risk score based on semantic drift and source quality
        
        Args:
            semantic_analysis: Results from semantic analysis
            high_weight_count: Number of high weight sources
            total_sources: Total number of sources
            
        Returns:
            Risk score (0-100, higher means higher risk)
        """
        # Base risk on semantic drift
        drift_risk = semantic_analysis['semantic_drift_score']
        
        # Factor in source quality (lower quality = higher risk)
        source_quality_factor = 1.0 - (high_weight_count / total_sources if total_sources > 0 else 0)
        
        # Combined risk score (weighted combination)
        risk_score = (drift_risk * 0.7) + (source_quality_factor * 100 * 0.3)
        
        return min(100, max(0, round(risk_score, 2)))


# Example usage
if __name__ == "__main__":
    from .source_weight_library import SourceWeightLibrary
    
    # Initialize components
    swl = SourceWeightLibrary()
    attribution_analyzer = AttributionAnalyzer(swl)
    
    # Example brand official definition
    official_def = """
    我们的品牌致力于提供高品质的人工智能解决方案，
    专注于技术创新和用户体验，以诚信和专业著称，
    致力于为客户创造长期价值。
    """
    
    # Example AI responses
    ai_responses = [
        "这是一个高科技公司，提供AI服务，但最近有一些质量问题的报道。",
        "该公司在AI领域有一定知名度，但客户服务有待改进。",
        "品牌技术实力不错，不过市场竞争激烈，面临挑战。"
    ]
    
    # Example sources from AI responses
    sources = [
        "https://zhihu.com/question/123",
        "https://news.qq.com/article/abc",
        "https://example-low-quality.com/info"
    ]
    
    # Perform attribution analysis
    result = attribution_analyzer.analyze_attribution(
        official_definition=official_def,
        ai_responses=ai_responses,
        response_sources=sources,
        brand_name="Example Brand"
    )
    
    print("Attribution Analysis Results:")
    print(f"Semantic Drift Score: {result['semantic_analysis']['semantic_drift_score']}")
    print(f"Drift Severity: {result['semantic_analysis']['drift_severity']}")
    print(f"Source Purity: {result['source_analysis']['source_purity_percentage']}%")
    print(f"Risk Score: {result['attribution_metrics']['risk_score']}")
    print(f"Pollution Sources: {len(result['source_analysis']['pollution_sources'])}")