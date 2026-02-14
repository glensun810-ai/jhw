"""
Result Processor for GEO Content Quality Validator
Implements advanced scoring algorithms, semantic analysis, and competitive benchmarking
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jieba
import re
from datetime import datetime
from .logging_config import api_logger
from .competitive_analysis import CompetitiveAnalyzer
from .semantic_analyzer import SemanticAnalyzer, AttributionAnalyzer
from .source_weight_library import SourceWeightLibrary


# Note: We'll use the imported SemanticAnalyzer instead of this class
# The following class is kept for backward compatibility but won't be used
class SemanticAnalyzerOld:
    """Analyzes semantic drift between brand preset terms and AI responses (Legacy)"""

    def __init__(self):
        api_logger.info("Initialized Legacy SemanticAnalyzer")

    def calculate_semantic_drift(
        self,
        brand_preset_terms: List[str],
        ai_responses: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate semantic drift between brand preset terms and AI responses (Legacy)

        Args:
            brand_preset_terms: List of brand preset terms
            ai_responses: List of AI responses to analyze

        Returns:
            Dictionary with semantic drift analysis
        """
        # Combine all responses for analysis
        combined_responses = " ".join(ai_responses)

        # Extract keywords from responses
        response_keywords = self._extract_keywords(combined_responses)

        # Calculate similarity between preset terms and response keywords
        similarities = []
        for term in brand_preset_terms:
            term_similarities = []
            for keyword in response_keywords:
                sim = self._calculate_word_similarity(term, keyword)
                term_similarities.append(sim)

            if term_similarities:
                avg_similarity = sum(term_similarities) / len(term_similarities)
                similarities.append({
                    'term': term,
                    'similarity': avg_similarity,
                    'matched_keywords': [kw for kw, sim in zip(response_keywords, term_similarities) if sim > 0.3]
                })

        # Calculate overall semantic drift score (0-100)
        if similarities:
            avg_similarity = sum(s['similarity'] for s in similarities) / len(similarities)
            drift_score = round((1 - avg_similarity) * 100, 2)  # Higher score = more drift
        else:
            drift_score = 100  # Maximum drift if no terms matched

        return {
            'semantic_drift_score': drift_score,
            'term_analysis': similarities,
            'response_keywords': response_keywords,
            'drift_severity': self._classify_drift_severity(drift_score)
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using jieba segmentation"""
        # Remove punctuation and segment text
        text_clean = re.sub(r'[^\w\s]', ' ', text)
        words = jieba.lcut(text_clean)

        # Filter out short words and non-Chinese characters
        keywords = [word for word in words if len(word) > 1 and re.match(r'[\u4e00-\u9fff]+', word)]

        # Remove duplicates while preserving order
        unique_keywords = list(dict.fromkeys(keywords))

        return unique_keywords[:50]  # Limit to top 50 keywords

    def _calculate_word_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two words using character overlap"""
        set1 = set(word1)
        set2 = set(word2)

        intersection = set1.intersection(set2)
        union = set1.union(set2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _classify_drift_severity(self, drift_score: float) -> str:
        """Classify drift severity based on score"""
        if drift_score >= 80:
            return "严重偏移"
        elif drift_score >= 60:
            return "中度偏移"
        elif drift_score >= 40:
            return "轻度偏移"
        else:
            return "轻微偏移"


class ResultProcessor:
    """Processes test results with advanced analytics"""
    
    def __init__(self):
        # Initialize the new semantic analyzer and attribution analyzer
        self.source_weight_lib = SourceWeightLibrary()
        self.semantic_analyzer = SemanticAnalyzer()
        self.attribution_analyzer = AttributionAnalyzer(self.source_weight_lib)
        self.competitive_analyzer = CompetitiveAnalyzer()
        api_logger.info("Initialized ResultProcessor with new semantic and attribution analyzers")
    
    def process_detailed_results(
        self,
        test_results: List[Dict[str, Any]],
        brand_name: str,
        competitor_brands: List[str] = None,
        brand_preset_terms: List[str] = None,
        official_definition: str = None  # New parameter for official brand definition
    ) -> Dict[str, Any]:
        """
        Process detailed test results with advanced analytics

        Args:
            test_results: Raw test results from AI platforms
            brand_name: Target brand name
            competitor_brands: List of competitor brand names
            brand_preset_terms: Brand preset terms for semantic analysis
            official_definition: Official brand definition for semantic drift analysis

        Returns:
            Dictionary with processed results and analytics
        """
        # Basic scoring
        processed_results = self._process_basic_scoring(test_results)

        # Digital vitality index
        digital_vitality = self._calculate_digital_vitality(processed_results)

        # Semantic drift analysis
        semantic_analysis = None
        attribution_analysis = None

        if official_definition or brand_preset_terms:
            # Prepare AI responses and sources
            ai_responses = [result['response'] for result in test_results]
            response_sources = []  # Extract sources from responses if available

            # Use official definition if provided, otherwise fall back to preset terms
            definition_to_use = official_definition or " ".join(brand_preset_terms or [])

            if definition_to_use.strip():
                # Perform semantic analysis
                semantic_analysis = self.semantic_analyzer.analyze_semantic_drift(
                    official_definition=definition_to_use,
                    ai_responses=ai_responses,
                    brand_name=brand_name
                )

                # Perform attribution analysis if sources are available
                if response_sources:
                    attribution_analysis = self.attribution_analyzer.analyze_attribution(
                        official_definition=definition_to_use,
                        ai_responses=ai_responses,
                        response_sources=response_sources,
                        brand_name=brand_name
                    )

        # Competitive analysis
        competitive_analysis = None
        if competitor_brands:
            ai_responses_formatted = [
                {
                    'aiModel': result['aiModel'],
                    'question': result['question'],
                    'response': result['response']
                }
                for result in test_results
            ]
            competitive_analysis = self.competitive_analyzer.perform_competitive_analysis(
                responses=ai_responses_formatted,
                target_brand=brand_name,
                competitor_brands=competitor_brands
            )

        # Generate actionable insights
        insights = self._generate_actionable_insights(
            processed_results,
            digital_vitality,
            semantic_analysis,
            competitive_analysis,
            attribution_analysis
        )

        result = {
            'processed_results': processed_results,
            'digital_vitality_index': digital_vitality,
            'semantic_analysis': semantic_analysis,
            'attribution_analysis': attribution_analysis,
            'competitive_analysis': competitive_analysis,
            'actionable_insights': insights,
            'processing_timestamp': datetime.now().isoformat()
        }

        # Log analysis results
        if semantic_analysis:
            api_logger.info(f"Semantic analysis completed for {brand_name}: drift_score={semantic_analysis.get('semantic_drift_score', 'N/A')}")

        if attribution_analysis:
            api_logger.info(f"Attribution analysis completed for {brand_name}: risk_score={attribution_analysis.get('attribution_metrics', {}).get('risk_score', 'N/A')}")

        return result
    
    def _process_basic_scoring(self, test_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process basic scoring for each result"""
        processed = []
        
        for result in test_results:
            # Apply advanced evaluation logic
            evaluation = self._evaluate_response_advanced(
                result['response'], 
                result.get('question', ''), 
                result.get('aiModel', 'unknown')
            )
            
            processed_result = {
                **result,
                'authority_score': evaluation['authority_score'],
                'visibility_score': evaluation['visibility_score'],
                'sentiment_score': evaluation['sentiment_score'],
                'individual_score': evaluation['score'],
                'has_brand_mention': evaluation['has_brand_mention'],
                'confidence_level': evaluation['confidence_level']
            }
            
            processed.append(processed_result)
        
        return processed
    
    def _evaluate_response_advanced(
        self, 
        response_content: str, 
        question: str, 
        ai_model: str
    ) -> Dict[str, Any]:
        """Advanced evaluation of AI response"""
        if not response_content or len(response_content) < 10:
            return {
                'authority_score': 0, 
                'visibility_score': 0, 
                'sentiment_score': 0, 
                'score': 0,
                'has_brand_mention': False,
                'confidence_level': 'low'
            }

        # Brand mention detection
        has_brand_mention = bool(re.search(r'.*', response_content))  # Placeholder for actual brand detection
        
        # Authority (权威度): Based on structure, facts, and reliability indicators
        has_facts = bool(re.search(r'\d+', response_content))  # Numbers often indicate facts
        is_structured = '\n' in response_content or '。' in response_content  # Sentence structure
        has_authoritative_indicators = any(indicator in response_content.lower() for indicator in [
            'according', 'research', 'study', 'data', 'report', 'official', 'verified'
        ])
        
        authority_score = 30  # Base score
        if has_brand_mention: authority_score += 20
        if has_facts: authority_score += 15
        if is_structured: authority_score += 10
        if has_authoritative_indicators: authority_score += 15
        
        # Clamp to 0-100 range
        authority_score = min(100, max(0, authority_score))

        # Visibility (可见度): Based on length and richness
        length = len(response_content)
        if length > 500: visibility_score = 95
        elif length > 300: visibility_score = 85
        elif length > 100: visibility_score = 70
        elif length > 50: visibility_score = 50
        else: visibility_score = 30

        # Sentiment (好感度): Based on positive/negative keywords
        positive_keywords = [
            '领先', '优秀', '创新', '好', '强', '推荐', '知名', '卓越', '成功', 'positive', 
            'good', 'great', 'excellent', 'amazing', 'outstanding', 'reliable', 'trustworthy'
        ]
        negative_keywords = [
            '差', '落后', '问题', '投诉', '失败', 'bad', 'poor', 'issue', 'problem', 
            'terrible', 'awful', 'negative', 'worst', 'avoid'
        ]

        pos_count = sum(1 for k in positive_keywords if k in response_content.lower())
        neg_count = sum(1 for k in negative_keywords if k in response_content.lower())

        sentiment_score = 70  # Base neutral
        sentiment_score += pos_count * 5
        sentiment_score -= neg_count * 10
        sentiment_score = max(0, min(100, sentiment_score))

        # Calculate weighted score
        score = round(authority_score * 0.4 + visibility_score * 0.3 + sentiment_score * 0.3)
        
        # Determine confidence level
        confidence_level = 'high' if score >= 70 else 'medium' if score >= 50 else 'low'

        return {
            'authority_score': authority_score,
            'visibility_score': visibility_score,
            'sentiment_score': sentiment_score,
            'score': score,
            'has_brand_mention': has_brand_mention,
            'confidence_level': confidence_level
        }
    
    def _calculate_digital_vitality(self, processed_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate digital vitality index from processed results"""
        if not processed_results:
            return {
                'visibility': 0,
                'authority': 0,
                'sentiment': 0,
                'overall': 0
            }
        
        total_authority = sum(r['authority_score'] for r in processed_results)
        total_visibility = sum(r['visibility_score'] for r in processed_results)
        total_sentiment = sum(r['sentiment_score'] for r in processed_results)
        
        count = len(processed_results)
        
        return {
            'visibility': round(total_visibility / count, 2),
            'authority': round(total_authority / count, 2),
            'sentiment': round(total_sentiment / count, 2),
            'overall': round(
                (total_authority / count) * 0.4 + 
                (total_visibility / count) * 0.3 + 
                (total_sentiment / count) * 0.3, 2
            )
        }
    
    def _generate_actionable_insights(
        self,
        processed_results: List[Dict[str, Any]],
        digital_vitality: Dict[str, float],
        semantic_analysis: Dict[str, Any],
        competitive_analysis: Any,
        attribution_analysis: Dict[str, Any] = None  # New parameter for attribution analysis
    ) -> Dict[str, Any]:
        """Generate actionable insights from analysis results"""
        insights = {
            'content_gaps': [],
            'optimization_tips': [],
            'competitor_warnings': [],
            'priority_actions': [],
            'attribution_risks': [],  # New category for attribution risks
            'source_recommendations': []  # New category for source recommendations
        }

        # Identify content gaps based on low-scoring responses
        low_authority_responses = [r for r in processed_results if r['authority_score'] < 60]
        if low_authority_responses:
            insights['content_gaps'].append({
                'type': '权威度不足',
                'description': f'发现{len(low_authority_responses)}个回应权威度低于60分，可能缺乏事实支撑',
                'suggestions': ['提供更多官方认证信息', '增加数据和案例支撑', '引用权威来源']
            })

        # Generate optimization tips based on digital vitality
        if digital_vitality['visibility'] < 60:
            insights['optimization_tips'].append('提升可见度：增加品牌在AI中的曝光频率和覆盖面')

        if digital_vitality['authority'] < 60:
            insights['optimization_tips'].append('提升权威度：加强官方信息的准确性和专业性')

        if digital_vitality['sentiment'] < 60:
            insights['optimization_tips'].append('改善好感度：优化品牌在AI中的情感倾向')

        # Add semantic drift insights if available
        if semantic_analysis:
            if semantic_analysis['semantic_drift_score'] > 50:
                insights['priority_actions'].append({
                    'action': '处理语义偏移',
                    'severity': semantic_analysis['drift_severity'],
                    'details': f'语义偏移得分为{semantic_analysis["semantic_drift_score"]}，存在明显的品牌认知偏差'
                })

        # Add attribution analysis insights if available
        if attribution_analysis:
            # Add attribution risks
            source_analysis = attribution_analysis.get('source_analysis', {})
            pollution_sources = source_analysis.get('pollution_sources', [])

            if pollution_sources:
                insights['attribution_risks'].append({
                    'type': '污染源风险',
                    'description': f'发现{len(pollution_sources)}个低权重负面信息源影响品牌认知',
                    'sources': pollution_sources
                })

            # Add source recommendations
            source_purity = source_analysis.get('source_purity_percentage', 0)
            if source_purity < 50:
                insights['source_recommendations'].append({
                    'action': '提升信源纯净度',
                    'description': f'当前信源纯净度仅为{source_purity}%，建议加强在高权重平台的内容布局',
                    'suggestions': [
                        '在知乎、百度百科等高权重平台发布官方内容',
                        '与权威媒体合作，增加正面报道',
                        '监控并处理低权重负面信息源'
                    ]
                })

        # Add competitor warnings if available
        if competitive_analysis:
            # Check if competitors are outperforming in any metric
            target_brand = getattr(competitive_analysis, 'target_brand_scores', {})
            competitor_scores = getattr(competitive_analysis, 'competitor_scores', {})

            if target_brand and competitor_scores:
                # Compare scores to identify weaknesses
                for metric in ['authority_score', 'visibility_score', 'sentiment_score']:
                    target_val = target_brand.get(metric, 0)
                    max_competitor_val = max([scores.get(metric, 0) for scores in competitor_scores.values()] or [0])

                    if target_val < max_competitor_val:
                        insights['competitor_warnings'].append({
                            f'在{metric.replace("_score", "")}方面落后于竞争对手',
                            f'您的{metric.replace("_score", "")}为{target_val}，竞争对手最高为{max_competitor_val}'
                        })

        return insights


# Example usage
if __name__ == "__main__":
    processor = ResultProcessor()
    
    # Sample test results
    sample_results = [
        {
            'aiModel': 'ChatGPT',
            'question': '介绍一下测试品牌',
            'response': '测试品牌是一家专注于技术创新的公司，提供高质量的产品和服务。'
        },
        {
            'aiModel': 'Claude', 
            'question': '测试品牌的主要产品是什么',
            'response': '测试品牌主要提供软件解决方案和咨询服务，帮助客户实现数字化转型。'
        }
    ]
    
    # Process results
    result = processor.process_detailed_results(
        test_results=sample_results,
        brand_name='测试品牌',
        competitor_brands=['竞品A', '竞品B'],
        brand_preset_terms=['创新', '高质量', '技术领先']
    )
    
    print("Processed Results:")
    print(f"Digital Vitality Index: {result['digital_vitality_index']}")
    print(f"Semantic Analysis: {result['semantic_analysis']}")
    print(f"Actionable Insights Count: {len(result['actionable_insights'])}")