"""
Competitive Analysis Module for GEO Content Quality Validator
Implements market share of mind, competitor intelligence, and recommendation weight analysis
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import re
from datetime import datetime
from wechat_backend.logging_config import api_logger


class MentionType(Enum):
    """Types of brand mentions in AI responses"""
    DIRECT_MENTION = "direct_mention"
    INDIRECT_REFERENCE = "indirect_reference"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"


@dataclass
class BrandMention:
    """Represents a mention of a brand in an AI response"""
    brand_name: str
    mention_type: MentionType
    context: str  # The surrounding text where the brand was mentioned
    position: int  # Position in the response (0-indexed)
    sentiment_score: float  # Sentiment associated with the mention (-1 to 1)
    strength: float  # Strength of the mention (0-1)
    source_indicators: List[str]  # Indicators of where the info might come from


@dataclass
class CompetitorAnalysisResult:
    """Result of competitor analysis"""
    brand_mentions: List[BrandMention]
    market_share_distribution: Dict[str, float]  # Brand name to percentage
    recommendation_weights: Dict[str, float]  # Brand name to recommendation weight
    competitor_intelligence: Dict[str, Any]  # Detailed info about competitors
    category_performance: Dict[str, Any]  # Performance by category
    summary_insights: List[str]  # Key insights from the analysis


class MarketShareAnalyzer:
    """Analyzes market share of mind in AI responses"""
    
    def __init__(self):
        api_logger.info("Initialized MarketShareAnalyzer")
    
    def analyze_market_share(
        self, 
        responses: List[Dict[str, Any]], 
        brand_names: List[str]
    ) -> Dict[str, float]:
        """
        Analyze market share distribution among brands in AI responses
        
        Args:
            responses: List of AI responses with brand mentions
            brand_names: List of brand names to analyze
            
        Returns:
            Dictionary mapping brand names to their market share percentages
        """
        mention_counts = {brand: 0 for brand in brand_names}
        total_mentions = 0
        
        for response_data in responses:
            response_text = response_data.get('response', '')
            
            # Count mentions for each brand
            for brand in brand_names:
                # Case-insensitive search for brand mentions
                mentions = len(re.findall(re.escape(brand), response_text, re.IGNORECASE))
                mention_counts[brand] += mentions
                total_mentions += mentions
                
                # Also check for variations (e.g., "Apple" vs "Apple Inc.")
                if ' ' in brand:
                    brand_variations = brand.split()
                    for variation in brand_variations:
                        if len(variation) > 2:  # Skip short words
                            additional_mentions = len(re.findall(r'\b' + re.escape(variation) + r'\b', response_text, re.IGNORECASE))
                            # Avoid double counting by checking context
                            if additional_mentions > mentions:
                                mention_counts[brand] += (additional_mentions - mentions)
                                total_mentions += (additional_mentions - mentions)
        
        # Calculate percentages
        market_share = {}
        for brand, count in mention_counts.items():
            if total_mentions > 0:
                market_share[brand] = round((count / total_mentions) * 100, 2)
            else:
                market_share[brand] = 0.0
        
        api_logger.info(f"Market share analysis completed: {market_share}")
        return market_share


class RecommendationWeightAnalyzer:
    """Analyzes why AI recommends certain brands over others"""
    
    def __init__(self):
        api_logger.info("Initialized RecommendationWeightAnalyzer")
    
    def analyze_recommendation_weights(
        self, 
        responses: List[Dict[str, Any]], 
        brand_names: List[str]
    ) -> Dict[str, float]:
        """
        Analyze the weights/reasons behind AI recommendations
        
        Args:
            responses: List of AI responses
            brand_names: List of brand names to analyze
            
        Returns:
            Dictionary mapping brand names to their recommendation weights
        """
        weights = {brand: 0.0 for brand in brand_names}
        
        # Keywords that indicate recommendation or preference
        recommendation_keywords = [
            'recommend', 'suggest', 'prefer', 'better', 'best', 'top', 'leading',
            'superior', 'outperform', 'advantage', 'choice', 'option', 'alternative',
            'go-to', 'first pick', 'winner', 'champion', 'leader', 'premium'
        ]
        
        # Positive sentiment indicators
        positive_indicators = [
            'excellent', 'amazing', 'outstanding', 'superb', 'fantastic', 'great',
            'good', 'awesome', 'impressive', 'reliable', 'trustworthy', 'quality',
            'innovative', 'advanced', 'cutting-edge', 'modern', 'efficient'
        ]
        
        for response_data in responses:
            response_text = response_data.get('response', '').lower()
            ai_model = response_data.get('aiModel', 'unknown')
            
            for brand in brand_names:
                brand_lower = brand.lower()
                
                # Check if brand is mentioned in the response
                if brand_lower in response_text:
                    weight = 0.0
                    
                    # Check for recommendation keywords near the brand mention
                    for keyword in recommendation_keywords:
                        if keyword in response_text:
                            # Find positions of brand and keyword
                            brand_pos = response_text.find(brand_lower)
                            keyword_pos = response_text.find(keyword)
                            
                            # If they're close to each other, increase weight
                            if abs(brand_pos - keyword_pos) < 100:  # Within 100 characters
                                weight += 0.3
                    
                    # Check for positive indicators near the brand mention
                    for indicator in positive_indicators:
                        if indicator in response_text:
                            brand_pos = response_text.find(brand_lower)
                            indicator_pos = response_text.find(indicator)
                            
                            if abs(brand_pos - indicator_pos) < 100:
                                weight += 0.2
                    
                    # Check if the brand appears in a comparative context
                    comparative_contexts = [
                        'compared to', 'vs', 'versus', 'rather than', 'instead of',
                        'more than', 'less than', 'over', 'than'
                    ]
                    
                    for context in comparative_contexts:
                        if context in response_text:
                            brand_pos = response_text.find(brand_lower)
                            context_pos = response_text.find(context)
                            
                            if abs(brand_pos - context_pos) < 150:  # Within 150 characters
                                weight += 0.25
                    
                    # Increase weight based on response length and brand prominence
                    response_length = len(response_text)
                    brand_frequency = response_text.count(brand_lower)
                    
                    if response_length > 0:
                        prominence_factor = (brand_frequency * 10) / response_length
                        weight += prominence_factor
                    
                    weights[brand] += weight
        
        # Normalize weights to 0-100 scale
        max_weight = max(weights.values()) if weights.values() else 1
        if max_weight > 0:
            for brand in weights:
                weights[brand] = round((weights[brand] / max_weight) * 100, 2)
        
        api_logger.info(f"Recommendation weight analysis completed: {weights}")
        return weights


class CompetitorIntelligenceAnalyzer:
    """Analyzes competitor intelligence from AI responses"""
    
    def __init__(self):
        api_logger.info("Initialized CompetitorIntelligenceAnalyzer")
    
    def analyze_competitor_intelligence(
        self, 
        responses: List[Dict[str, Any]], 
        brand_names: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze competitor intelligence from AI responses
        
        Args:
            responses: List of AI responses
            brand_names: List of brand names to analyze
            
        Returns:
            Dictionary with detailed competitor intelligence
        """
        intelligence = {}
        
        # Patterns that indicate source information
        source_patterns = [
            r'based on ([^,.]+)',
            r'according to ([^,.]+)',
            r'from ([^,.]+)',
            r'cited in ([^,.]+)',
            r'mentioned by ([^,.]+)',
            r'reported by ([^,.]+)',
            r'stated in ([^,.]+)'
        ]
        
        for brand in brand_names:
            brand_intel = {
                'mentions': [],
                'source_indicators': [],
                'positive_contexts': [],
                'negative_contexts': [],
                'comparative_statements': [],
                'strengths_identified': [],
                'weaknesses_identified': []
            }
            
            for response_data in responses:
                response_text = response_data.get('response', '')
                
                # Check if this brand is mentioned
                if re.search(re.escape(brand), response_text, re.IGNORECASE):
                    # Extract source indicators
                    for pattern in source_patterns:
                        matches = re.findall(pattern, response_text, re.IGNORECASE)
                        brand_intel['source_indicators'].extend(matches)
                    
                    # Look for comparative statements
                    comparative_patterns = [
                        rf'{re.escape(brand)}.*?(?:but|however|while|whereas).*?(\w+)',
                        rf'(\w+).*?(?:but|however|while|whereas).*?{re.escape(brand)}',
                        rf'{re.escape(brand)}.*?(?:compared to|vs|versus)\s+([^,.]+)',
                        rf'([^,.]+).*?(?:compared to|vs|versus)\s+{re.escape(brand)}'
                    ]
                    
                    for pattern in comparative_patterns:
                        matches = re.findall(pattern, response_text, re.IGNORECASE)
                        brand_intel['comparative_statements'].extend(matches)
                    
                    # Identify positive and negative contexts
                    positive_keywords = [
                        'excellent', 'amazing', 'outstanding', 'superb', 'fantastic', 'great',
                        'good', 'reliable', 'trustworthy', 'quality', 'innovative', 'advanced',
                        'leading', 'top', 'best', 'premier', 'premium', 'award-winning'
                    ]
                    
                    negative_keywords = [
                        'poor', 'terrible', 'awful', 'bad', 'inferior', 'subpar',
                        'problematic', 'issues', 'concerns', 'flaws', 'disappointing',
                        'outdated', 'obsolete', 'deficient', 'lacking', 'inadequate'
                    ]
                    
                    for keyword in positive_keywords:
                        if re.search(rf'{re.escape(brand)}.*?{keyword}|{keyword}.*?{re.escape(brand)}', 
                                   response_text, re.IGNORECASE):
                            brand_intel['positive_contexts'].append(keyword)
                    
                    for keyword in negative_keywords:
                        if re.search(rf'{re.escape(brand)}.*?{keyword}|{keyword}.*?{re.escape(brand)}', 
                                   response_text, re.IGNORECASE):
                            brand_intel['negative_contexts'].append(keyword)
                    
                    # Add the full context of the mention
                    brand_intel['mentions'].append({
                        'context': response_text[:200] + '...' if len(response_text) > 200 else response_text,
                        'ai_model': response_data.get('aiModel', 'unknown'),
                        'question': response_data.get('question', 'unknown')
                    })
            
            intelligence[brand] = brand_intel
        
        api_logger.info(f"Competitor intelligence analysis completed for brands: {list(intelligence.keys())}")
        return intelligence


class CompetitiveAnalyzer:
    """Main class for performing competitive analysis"""
    
    def __init__(self):
        self.market_share_analyzer = MarketShareAnalyzer()
        self.recommendation_analyzer = RecommendationWeightAnalyzer()
        self.intelligence_analyzer = CompetitorIntelligenceAnalyzer()
        api_logger.info("Initialized CompetitiveAnalyzer")
    
    def perform_competitive_analysis(
        self,
        responses: List[Dict[str, Any]],
        target_brand: str,
        competitor_brands: List[str]
    ) -> CompetitorAnalysisResult:
        """
        Perform comprehensive competitive analysis
        
        Args:
            responses: List of AI responses to analyze
            target_brand: The main brand being analyzed
            competitor_brands: List of competitor brand names
            
        Returns:
            CompetitorAnalysisResult with all analysis data
        """
        all_brands = [target_brand] + competitor_brands
        
        # Perform individual analyses
        market_share = self.market_share_analyzer.analyze_market_share(responses, all_brands)
        recommendation_weights = self.recommendation_analyzer.analyze_recommendation_weights(responses, all_brands)
        competitor_intelligence = self.intelligence_analyzer.analyze_competitor_intelligence(responses, all_brands)
        
        # Generate category performance (basic implementation)
        category_performance = self._analyze_category_performance(responses, all_brands)
        
        # Generate summary insights
        summary_insights = self._generate_summary_insights(
            market_share, 
            recommendation_weights, 
            competitor_intelligence,
            target_brand,
            competitor_brands
        )
        
        result = CompetitorAnalysisResult(
            brand_mentions=[],  # Placeholder - would need more detailed parsing
            market_share_distribution=market_share,
            recommendation_weights=recommendation_weights,
            competitor_intelligence=competitor_intelligence,
            category_performance=category_performance,
            summary_insights=summary_insights
        )
        
        api_logger.info(f"Competitive analysis completed for target brand: {target_brand}")
        return result
    
    def _analyze_category_performance(
        self, 
        responses: List[Dict[str, Any]], 
        brands: List[str]
    ) -> Dict[str, Any]:
        """Analyze performance by category/aspect"""
        # Basic implementation - would be enhanced in a full version
        categories = {
            'performance': 0,
            'price': 0,
            'quality': 0,
            'innovation': 0,
            'reliability': 0,
            'customer_service': 0
        }
        
        category_keywords = {
            'performance': ['performance', 'speed', 'efficiency', 'power', 'capability'],
            'price': ['price', 'cost', 'affordable', 'expensive', 'value', 'cheap', 'premium'],
            'quality': ['quality', 'build', 'material', 'craftsmanship', 'durability'],
            'innovation': ['innovative', 'innovation', 'cutting-edge', 'new', 'revolutionary'],
            'reliability': ['reliable', 'dependable', 'stable', 'consistent', 'trustworthy'],
            'customer_service': ['service', 'support', 'help', 'assistance', 'customer care']
        }
        
        for response in responses:
            response_text = response.get('response', '').lower()
            
            for category, keywords in category_keywords.items():
                for keyword in keywords:
                    if keyword in response_text:
                        categories[category] += 1
        
        return categories
    
    def _generate_summary_insights(
        self,
        market_share: Dict[str, float],
        recommendation_weights: Dict[str, float],
        competitor_intelligence: Dict[str, Any],
        target_brand: str,
        competitor_brands: List[str]
    ) -> List[str]:
        """Generate summary insights from the analysis"""
        insights = []
        
        # Market share insights
        target_share = market_share.get(target_brand, 0)
        max_competitor_share = max([market_share.get(comp, 0) for comp in competitor_brands], default=0)
        
        if target_share > max_competitor_share:
            insights.append(f"{target_brand} leads in market share of mind ({target_share}% vs max competitor {max_competitor_share}%)")
        elif target_share < max_competitor_share:
            insights.append(f"{target_brand} trails competitors in market share of mind ({target_share}% vs max competitor {max_competitor_share}%)")
        else:
            insights.append(f"{target_brand} is tied with top competitor in market share of mind ({target_share}%)")
        
        # Recommendation weight insights
        target_weight = recommendation_weights.get(target_brand, 0)
        max_competitor_weight = max([recommendation_weights.get(comp, 0) for comp in competitor_brands], default=0)
        
        if target_weight > max_competitor_weight:
            insights.append(f"{target_brand} has stronger recommendation weight ({target_weight} vs max competitor {max_competitor_weight})")
        elif target_weight < max_competitor_weight:
            insights.append(f"{target_brand} has weaker recommendation weight ({target_weight} vs max competitor {max_competitor_weight})")
        
        # Intelligence insights
        target_positive = len(competitor_intelligence.get(target_brand, {}).get('positive_contexts', []))
        target_negative = len(competitor_intelligence.get(target_brand, {}).get('negative_contexts', []))
        
        if target_positive > target_negative:
            insights.append(f"{target_brand} has more positive than negative mentions ({target_positive} vs {target_negative})")
        elif target_negative > target_positive:
            insights.append(f"{target_brand} has more negative than positive mentions ({target_negative} vs {target_positive})")
        
        return insights


# Example usage and testing
if __name__ == "__main__":
    # Sample data for testing
    sample_responses = [
        {
            "aiModel": "ChatGPT",
            "question": "Which smartphone brand is the best in 2024?",
            "response": "Based on market analysis, Apple continues to lead with innovative features, though Samsung offers strong competition with their Galaxy series. Google's Pixel phones are gaining traction with excellent camera technology."
        },
        {
            "aiModel": "Claude",
            "question": "Compare iPhone vs Samsung Galaxy",
            "response": "iPhone is known for its premium build quality and ecosystem integration, while Samsung Galaxy offers more customization options. Both are excellent choices, but iPhone tends to hold value better."
        }
    ]
    
    analyzer = CompetitiveAnalyzer()
    result = analyzer.perform_competitive_analysis(
        responses=sample_responses,
        target_brand="Apple",
        competitor_brands=["Samsung", "Google"]
    )
    
    print("Market Share Distribution:", result.market_share_distribution)
    print("Recommendation Weights:", result.recommendation_weights)
    print("Summary Insights:", result.summary_insights)