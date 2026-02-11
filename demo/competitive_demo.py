#!/usr/bin/env python3
"""
Competitive Analysis Demonstration for GEO Content Quality Validator
Demonstrates the complete competitive analysis functionality with realistic data
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.competitive_analysis import CompetitiveAnalyzer
from wechat_backend.result_processor import ResultProcessor


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"{title:^80}")
    print("="*80)


def print_section(title: str):
    """Print a section header"""
    print(f"\n--- {title} ---")


def demo_competitive_analyzer():
    """Demonstrate the Competitive Analyzer functionality"""
    print_header("DEMONSTRATION: COMPETITIVE ANALYSIS ENGINE")
    
    # Initialize the competitive analyzer
    ca = CompetitiveAnalyzer()
    
    print_section("1. Competitive Analysis Setup")
    
    # Example AI responses that mention multiple brands
    ai_responses = [
        {
            'aiModel': 'ChatGPT',
            'question': 'Compare TechBrand with CompetitorA and CompetitorB',
            'response': 'TechBrand has good technology but CompetitorA leads in innovation. CompetitorB offers better customer service.'
        },
        {
            'aiModel': 'Claude', 
            'question': 'Which brand is better for AI solutions?',
            'response': 'CompetitorA is known for cutting-edge technology, but TechBrand has solid reputation. CompetitorB is more affordable.'
        },
        {
            'aiModel': 'Qwen',
            'question': 'What are the strengths of TechBrand?',
            'response': 'TechBrand focuses on reliability and quality. However, CompetitorA has more advanced features and CompetitorB is more user-friendly.'
        },
        {
            'aiModel': 'ChatGPT',
            'question': 'Market leader in AI technology?',
            'response': 'CompetitorA is currently the market leader with innovative solutions. TechBrand is a strong contender with good stability.'
        }
    ]
    
    print(f"AI Responses to analyze: {len(ai_responses)}")
    for i, resp in enumerate(ai_responses, 1):
        print(f"  {i}. {resp['aiModel']}: {resp['response'][:80]}...")
    
    print_section("2. Performing Competitive Analysis")
    
    # Perform competitive analysis
    analysis_result = ca.perform_competitive_analysis(
        responses=ai_responses,
        target_brand="TechBrand",
        competitor_brands=["CompetitorA", "CompetitorB"]
    )
    
    print("Competitive Analysis Completed!")
    print(f"  • Market Share Distribution: {analysis_result.market_share_distribution}")
    print(f"  • Recommendation Weights: {analysis_result.recommendation_weights}")
    print(f"  • Total Brands Analyzed: {len(analysis_result.competitor_intelligence)}")

    print_section("3. Market Share Distribution")

    print("Brand Mention Distribution:")
    for brand, percentage in analysis_result.market_share_distribution.items():
        print(f"  • {brand}: {percentage}% market share")

    print_section("4. Recommendation Weights")

    print("Recommendation Weights (higher = more likely to be recommended):")
    for brand, weight in analysis_result.recommendation_weights.items():
        print(f"  • {brand}: {weight:.2f}")

    print_section("5. Competitor Intelligence")

    for brand, intelligence in analysis_result.competitor_intelligence.items():
        print(f"\n{brand} Intelligence:")
        print(f"  • Mentions: {intelligence.get('mentions', [])[:2]}...")  # Show first 2 mentions
        print(f"  • Source Indicators: {intelligence.get('source_indicators', [])}")
        print(f"  • Positive Contexts: {intelligence.get('positive_contexts', [])}")
        print(f"  • Negative Contexts: {intelligence.get('negative_contexts', [])}")
        print(f"  • Comparative Statements: {intelligence.get('comparative_statements', [])}")

    print_section("6. Summary Insights")

    for insight in analysis_result.summary_insights:
        print(f"  • {insight}")

    print("\n✅ Competitive Analysis Engine demonstration completed!")

    return analysis_result


def demo_competitive_integration():
    """Demonstrate competitive analysis integrated with the full result processor"""
    print_header("DEMONSTRATION: COMPETITIVE ANALYSIS INTEGRATION")
    
    # Initialize the result processor (which includes competitive analysis)
    rp = ResultProcessor()
    
    print_section("1. Full Competitive Analysis Pipeline")
    
    # Sample test results with multiple brands mentioned
    test_results = [
        {
            'aiModel': 'ChatGPT',
            'question': 'Compare TechBrand with competitors',
            'response': 'TechBrand has solid technology but CompetitorA leads in innovation. CompetitorB offers better pricing.',
            'authority_score': 75,
            'visibility_score': 80,
            'sentiment_score': 70,
            'score': 75
        },
        {
            'aiModel': 'Claude',
            'question': 'Who is the market leader in AI?',
            'response': 'CompetitorA is currently the leader with advanced features. TechBrand is catching up with solid reliability.',
            'authority_score': 80,
            'visibility_score': 85,
            'sentiment_score': 65,
            'score': 77
        },
        {
            'aiModel': 'Qwen', 
            'question': 'What makes TechBrand unique?',
            'response': 'TechBrand focuses on stability and quality. However, CompetitorA has more innovative features and CompetitorB is more user-friendly.',
            'authority_score': 70,
            'visibility_score': 75,
            'sentiment_score': 75,
            'score': 73
        },
        {
            'aiModel': 'Gemini',
            'question': 'Best AI solution provider?',
            'response': 'For innovation, CompetitorA wins. For reliability, TechBrand is solid. For affordability, CompetitorB leads.',
            'authority_score': 85,
            'visibility_score': 90,
            'sentiment_score': 70,
            'score': 82
        }
    ]
    
    print(f"Processing {len(test_results)} test results with competitive analysis...")
    print("Target Brand: TechBrand")
    print("Competitors: ['CompetitorA', 'CompetitorB']")
    
    # Process results with competitive analysis
    result = rp.process_detailed_results(
        test_results=test_results,
        brand_name='TechBrand',
        competitor_brands=['CompetitorA', 'CompetitorB'],
        brand_preset_terms=['AI', 'technology', 'innovation', 'reliability'],
        official_definition='TechBrand is a leading AI technology company focused on innovation and reliability.'
    )
    
    print_section("2. Processing Results")
    
    print(f"  • Digital Vitality Index: {result['digital_vitality_index']}")
    print(f"  • Semantic Analysis: {'Available' if result.get('semantic_analysis') else 'Not Available'}")
    print(f"  • Attribution Analysis: {'Available' if result.get('attribution_analysis') else 'Not Available'}")
    print(f"  • Competitive Analysis: {'Available' if result.get('competitive_analysis') else 'Not Available'}")
    
    if result.get('competitive_analysis'):
        comp_analysis = result.get('competitive_analysis')
        if hasattr(comp_analysis, 'market_share_distribution'):  # Check if it's an object with attributes
            print_section("3. Competitive Analysis Results")

            print("Market Share Distribution:")
            for brand, share in comp_analysis.market_share_distribution.items():
                print(f"  • {brand}: {share}%")

            print("\nRecommendation Weights:")
            for brand, weight in comp_analysis.recommendation_weights.items():
                print(f"  • {brand}: {weight}")

            print("\nCompetitor Intelligence:")
            intelligence = comp_analysis.competitor_intelligence
            for brand, data in intelligence.items():
                print(f"\n  {brand}:")
                for key, value in data.items():
                    if value:  # Only show non-empty values
                        print(f"    • {key}: {value}")

            print("\nSummary Insights:")
            for insight in comp_analysis.summary_insights:
                print(f"  • {insight}")
        else:
            print("  • No competitive analysis available")
    
    if result.get('actionable_insights'):
        insights = result['actionable_insights']
        print_section("4. Actionable Insights")
        
        print(f"  • Content Gaps: {len(insights.get('content_gaps', []))}")
        print(f"  • Optimization Tips: {len(insights.get('optimization_tips', []))}")
        print(f"  • Competitor Warnings: {len(insights.get('competitor_warnings', []))}")
        print(f"  • Priority Actions: {len(insights.get('priority_actions', []))}")
        
        if insights.get('competitor_warnings'):
            print("\nCompetitor Warnings:")
            for warning in insights['competitor_warnings']:
                print(f"  • {warning}")
    
    print("\n✅ Competitive Analysis Integration demonstration completed!")
    
    return result


def demo_comprehensive_scenario():
    """Demonstrate a comprehensive competitive scenario"""
    print_header("DEMONSTRATION: COMPREHENSIVE COMPETITIVE SCENARIO")
    
    print_section("1. Simulating Real-World Competitive Analysis")
    
    # Simulate a real-world scenario with multiple AI models and competitive responses
    scenario_data = {
        "brand_name": "TechBrand",
        "competitors": ["AICompetitor", "TechRival", "InnovateCo"],
        "ai_responses": [
            {
                "aiModel": "ChatGPT",
                "question": "Which AI platform is best for enterprise solutions?",
                "response": "AICompetitor leads in enterprise features with robust APIs. TechBrand offers good stability but lacks advanced customization. TechRival has competitive pricing."
            },
            {
                "aiModel": "Claude",
                "question": "Compare customer support quality",
                "response": "TechRival is known for excellent customer support. TechBrand has decent support but AICompetitor's is more technical-focused."
            },
            {
                "aiModel": "Qwen", 
                "question": "Innovation leader in AI?",
                "response": "AICompetitor consistently releases cutting-edge features. TechBrand focuses on stability over innovation. InnovateCo is emerging with promising solutions."
            },
            {
                "aiModel": "Gemini",
                "question": "Most reliable AI platform?",
                "response": "TechBrand has the most stable platform with minimal downtime. AICompetitor has more features but occasional stability issues. TechRival balances features and reliability."
            },
            {
                "aiModel": "Perplexity",
                "question": "Best value for money?",
                "response": "TechRival offers the best value proposition. TechBrand is mid-tier pricing with good features. AICompetitor is premium priced."
            }
        ]
    }
    
    print(f"Scenario: {scenario_data['brand_name']} vs {', '.join(scenario_data['competitors'])}")
    print(f"AI Models Analyzed: {[r['aiModel'] for r in scenario_data['ai_responses']]}")
    
    print_section("2. Competitive Intelligence Results")
    
    # Simulate analysis results
    analysis_results = {
        "target_brand": scenario_data["brand_name"],
        "competitors": scenario_data["competitors"],
        "market_share": {
            "TechBrand": 25,
            "AICompetitor": 40, 
            "TechRival": 25,
            "InnovateCo": 10
        },
        "recommendation_weights": {
            "TechBrand": 65,
            "AICompetitor": 85,
            "TechRival": 75, 
            "InnovateCo": 40
        },
        "strengths_weaknesses": {
            "TechBrand": {
                "strengths": ["Reliability", "Stability", "Good support"],
                "weaknesses": ["Less innovative", "Higher pricing than rivals"]
            },
            "AICompetitor": {
                "strengths": ["Innovation", "Feature-rich", "Technical support"],
                "weaknesses": ["Stability issues", "Premium pricing"]
            },
            "TechRival": {
                "strengths": ["Value for money", "Customer support", "Balanced features"],
                "weaknesses": ["Less innovative", "Smaller feature set"]
            },
            "InnovateCo": {
                "strengths": ["Emerging technology", "Promising solutions"],
                "weaknesses": ["New player", "Limited track record"]
            }
        },
        "positioning_map": {
            "innovation_axis": {
                "high_innovation": ["AICompetitor", "InnovateCo"],
                "moderate_innovation": ["TechRival"],
                "stability_focus": ["TechBrand"]
            },
            "value_axis": {
                "high_value": ["TechRival"],
                "balanced": ["TechBrand"],
                "premium": ["AICompetitor"],
                "emerging": ["InnovateCo"]
            }
        },
        "actionable_insights": [
            "TechBrand should emphasize stability advantage over competitors",
            "Consider introducing more innovative features to compete with AICompetitor",
            "Position as the reliable alternative to feature-heavy competitors",
            "Highlight value proposition compared to premium competitors"
        ]
    }
    
    # Display results
    print("Market Share Distribution:")
    for brand, share in analysis_results["market_share"].items():
        marker = "🎯" if brand == scenario_data["brand_name"] else "  "
        print(f"  {marker} {brand}: {share}% market share")
    
    print("\nRecommendation Weights (0-100 scale):")
    for brand, weight in analysis_results["recommendation_weights"].items():
        marker = "🎯" if brand == scenario_data["brand_name"] else "  "
        print(f"  {marker} {brand}: {weight}/100")
    
    print("\nBrand Positioning:")
    print(f"  Innovation Focus: {analysis_results['positioning_map']['innovation_axis']['high_innovation']} > {analysis_results['positioning_map']['innovation_axis']['moderate_innovation']} > {analysis_results['positioning_map']['innovation_axis']['stability_focus']}")
    print(f"  Value Proposition: {analysis_results['positioning_map']['value_axis']['high_value']} > {analysis_results['positioning_map']['value_axis']['balanced']} > {analysis_results['positioning_map']['value_axis']['premium']}")
    
    print("\nTechBrand Strengths vs Weaknesses:")
    brand_swot = analysis_results["strengths_weaknesses"]["TechBrand"]
    print(f"  Strengths: {', '.join(brand_swot['strengths'])}")
    print(f"  Weaknesses: {', '.join(brand_swot['weaknesses'])}")
    
    print("\nActionable Insights for TechBrand:")
    for insight in analysis_results["actionable_insights"]:
        print(f"  • {insight}")
    
    print_section("3. Competitive Risk Assessment")
    
    # Calculate competitive risk
    target_share = analysis_results["market_share"][scenario_data["brand_name"]]
    max_competitor_share = max(v for k, v in analysis_results["market_share"].items() if k != scenario_data["brand_name"])
    target_weight = analysis_results["recommendation_weights"][scenario_data["brand_name"]]
    max_competitor_weight = max(v for k, v in analysis_results["recommendation_weights"].items() if k != scenario_data["brand_name"])
    
    risk_factors = []
    if target_share < max_competitor_share:
        risk_factors.append(f"Market share lag: {target_share}% vs competitor's {max_competitor_share}%")
    if target_weight < max_competitor_weight:
        risk_factors.append(f"Recommendation weight lag: {target_weight} vs competitor's {max_competitor_weight}")
    
    if risk_factors:
        print("⚠️  Risk Factors Identified:")
        for factor in risk_factors:
            print(f"  • {factor}")
    else:
        print("✅ TechBrand is competitive in both market share and recommendation weight")
    
    print("\n✅ Comprehensive Competitive Scenario demonstration completed!")
    
    return analysis_results


def main():
    """Main demonstration function"""
    print_header("GEO CONTENT QUALITY VALIDATOR - COMPETITIVE ANALYSIS DEMO")
    
    print(f"Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This demonstration showcases the Competitive Analysis features.")
    
    try:
        # Run all competitive analysis demonstrations
        comp_analysis_result = demo_competitive_analyzer()
        integration_result = demo_competitive_integration()
        scenario_result = demo_comprehensive_scenario()
        
        print_header("DEMONSTRATION COMPLETE")
        print("All competitive analysis features demonstrated successfully!")
        print(f"Demo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Summary
        print("\nSUMMARY OF DEMONSTRATED FEATURES:")
        print("✅ Competitive Analysis Engine - Brand comparison and market share analysis")
        print("✅ Integration with Result Processor - Full pipeline processing") 
        print("✅ Real-world Scenario - Comprehensive competitive intelligence")
        print("✅ Risk Assessment - Competitive threat identification")
        print("✅ Actionable Insights - Strategic recommendations")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()