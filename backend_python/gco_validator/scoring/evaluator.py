"""
Response evaluation and scoring for GEO Content Quality Validator
"""
from dataclasses import dataclass
from typing import Dict, Any, List
import re


@dataclass
class ScoringResult:
    """Result of the scoring process"""
    accuracy: float  # 0-100 scale
    completeness: float  # 0-100 scale
    relevance: float  # 0-100 scale
    coherence: float  # 0-100 scale
    overall_score: float  # 0-100 scale
    detailed_feedback: Dict[str, Any] = None


class ResponseEvaluator:
    """Evaluates AI responses for quality metrics"""
    
    def __init__(self):
        pass
    
    def evaluate_response(self, response: str, question: str, brand_name: str) -> ScoringResult:
        """
        Evaluate an AI response based on multiple quality metrics
        
        Args:
            response: The AI response to evaluate
            question: The original question asked
            brand_name: The brand name being tested
            
        Returns:
            ScoringResult with quality metrics
        """
        # Calculate individual metrics
        accuracy = self._calculate_accuracy(response, brand_name)
        completeness = self._calculate_completeness(response, question)
        relevance = self._calculate_relevance(response, question, brand_name)
        coherence = self._calculate_coherence(response)
        
        # Calculate overall score (average of all metrics)
        overall_score = (accuracy + completeness + relevance + coherence) / 4.0
        
        return ScoringResult(
            accuracy=accuracy,
            completeness=completeness,
            relevance=relevance,
            coherence=coherence,
            overall_score=overall_score,
            detailed_feedback={
                'contains_brand': brand_name.lower() in response.lower(),
                'response_length': len(response),
                'word_count': len(response.split()),
                'sentiment_indicators': self._analyze_sentiment(response)
            }
        )
    
    def _calculate_accuracy(self, response: str, brand_name: str) -> float:
        """Calculate accuracy based on brand recognition and factual correctness"""
        # Simple heuristic: presence of brand name indicates some accuracy
        contains_brand = brand_name.lower() in response.lower()
        
        # Additional heuristics could be added here
        # For now, returning a basic score based on brand presence
        base_score = 70.0 if contains_brand else 30.0
        
        # Normalize to 0-100 scale
        return min(100.0, max(0.0, base_score))
    
    def _calculate_completeness(self, response: str, question: str) -> float:
        """Calculate completeness based on how thoroughly the question is answered"""
        response_length = len(response.strip())
        
        # Very basic heuristic: longer responses tend to be more complete
        # In a real implementation, this would analyze how well the question is addressed
        if response_length < 50:
            return 30.0
        elif response_length < 150:
            return 60.0
        elif response_length < 300:
            return 80.0
        else:
            return 90.0
    
    def _calculate_relevance(self, response: str, question: str, brand_name: str) -> float:
        """Calculate relevance of response to the question and brand"""
        # Check if response addresses the question topic
        question_words = set(question.lower().split())
        response_words = set(response.lower().split())
        
        # Calculate overlap between question and response
        overlap = len(question_words.intersection(response_words))
        max_possible_overlap = min(len(question_words), len(response_words))
        
        relevance_score = (overlap / max_possible_overlap * 100) if max_possible_overlap > 0 else 0.0
        
        # Boost score if brand is mentioned
        if brand_name.lower() in response.lower():
            relevance_score = min(100.0, relevance_score * 1.2)
        
        return min(100.0, relevance_score)
    
    def _calculate_coherence(self, response: str) -> float:
        """Calculate coherence and logical flow of the response"""
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        
        if len(sentences) < 2:
            return 50.0  # Neutral score for single-sentence responses
        
        # Very basic coherence check: sentence length variation and structure
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        if avg_sentence_length < 3:
            return 40.0  # Too short sentences
        elif avg_sentence_length > 30:
            return 50.0  # Too long sentences
        else:
            return 75.0  # Good balance
    
    def _analyze_sentiment(self, response: str) -> Dict[str, float]:
        """Analyze sentiment indicators in the response"""
        positive_indicators = [
            'good', 'great', 'excellent', 'best', 'leading', 'innovative', 
            'reliable', 'trusted', 'professional', 'quality', 'outstanding'
        ]
        
        negative_indicators = [
            'bad', 'poor', 'terrible', 'worst', 'problem', 'issue', 
            'concern', 'flaw', 'defect', 'disappointing', 'inadequate'
        ]
        
        response_lower = response.lower()
        pos_count = sum(1 for indicator in positive_indicators if indicator in response_lower)
        neg_count = sum(1 for indicator in negative_indicators if indicator in response_lower)
        
        return {
            'positive_indicators': pos_count,
            'negative_indicators': neg_count,
            'net_sentiment': pos_count - neg_count
        }


def calculate_accuracy(response: str, brand_name: str) -> float:
    """Convenience function to calculate accuracy"""
    evaluator = ResponseEvaluator()
    result = evaluator.evaluate_response(response, "dummy question", brand_name)
    return result.accuracy


def calculate_completeness(response: str, question: str) -> float:
    """Convenience function to calculate completeness"""
    evaluator = ResponseEvaluator()
    result = evaluator.evaluate_response(response, question, "dummy brand")
    return result.completeness


def calculate_quality_score(response: str, question: str, brand_name: str) -> float:
    """Convenience function to calculate overall quality score"""
    evaluator = ResponseEvaluator()
    result = evaluator.evaluate_response(response, question, brand_name)
    return result.overall_score