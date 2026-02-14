#!/usr/bin/env python3
"""
GEO Content Quality Validator - Demonstration Script
Shows the functionality of Source Weight Library and Semantic Drift Analysis
"""

import json
import os
from datetime import datetime
from wechat_backend.source_weight_library import SourceWeightLibrary
from wechat_backend.semantic_analyzer import SemanticAnalyzer, AttributionAnalyzer
from wechat_backend.result_processor import ResultProcessor


def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"{title:^80}")
    print("="*80)


def print_section(title):
    """Print a section header"""
    print(f"\n--- {title} ---")


def demo_source_weight_library():
    """Demonstrate the Source Weight Library functionality"""
    print_header("DEMONSTRATION: SOURCE WEIGHT LIBRARY")
    
    # Initialize the source weight library
    swl = SourceWeightLibrary()
    
    print_section("1. Available Categories and High-Weight Sources")
    
    # Show available categories
    conn = swl.db_path
    import sqlite3
    conn_obj = sqlite3.connect(conn)
    cursor = conn_obj.cursor()
    
    cursor.execute("SELECT DISTINCT category FROM sources ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    print(f"Available categories: {categories}")
    
    # Show high-weight sources
    high_weight_sources = swl.get_high_weight_sources(min_weight=0.8)
    print(f"\nHigh-weight sources (≥0.8):")
    for i, source in enumerate(high_weight_sources[:10]):  # Show first 10
        print(f"  {i+1:2d}. {source['site_name']:20s} ({source['domain']:25s}) - Weight: {source['weight_score']}")
    
    print_section("2. Domain Extraction and Weight Lookup")
    
    # Test domain extraction
    test_urls = [
        "https://www.baidu.com/some/page",
        "http://zhihu.com/question/123",
        "https://news.qq.com/article/abc",
        "https://example-blacklist.com/bad-content",
        "https://github.com/user/repo"
    ]
    
    print("Testing domain extraction and weight lookup:")
    for url in test_urls:
        domain = swl.extract_domain_from_url(url)
        if domain:
            weight_info = swl.get_source_weight(domain)
            if weight_info:
                weight, site_name, category = weight_info
                print(f"  URL: {url}")
                print(f"    → Domain: {domain}")
                print(f"    → Site: {site_name} | Category: {category} | Weight: {weight}")
            else:
                print(f"  URL: {url}")
                print(f"    → Domain: {domain} | Weight: Not found in database")
        else:
            print(f"  URL: {url}")
            print(f"    → Invalid domain")
    
    print_section("3. Adding Custom Sources")
    
    # Add a custom source for demonstration
    swl.add_source(
        domain="mybrand-official.com",
        site_name="My Brand Official",
        weight_score=0.95,
        category="官方",
        description="Official brand website with highest trust score"
    )
    
    # Verify the addition
    new_source = swl.get_source_weight("mybrand-official.com")
    if new_source:
        weight, site_name, category = new_source
        print(f"Added new source: {site_name} ({weight}) - Category: {category}")
    
    conn_obj.close()
    print("\n✅ Source Weight Library demonstration completed!")


def demo_semantic_analyzer():
    """Demonstrate the Semantic Analyzer functionality"""
    print_header("DEMONSTRATION: SEMANTIC ANALYSIS ENGINE")
    
    # Initialize the semantic analyzer
    sa = SemanticAnalyzer()
    
    print_section("1. Brand Definition vs AI Response Analysis")
    
    # Example brand official definition
    official_definition = """
    我们是一家领先的AI技术公司，专注于提供高质量的人工智能解决方案。
    我们的使命是通过技术创新推动行业发展，为客户提供卓越的服务体验。
    我们坚持诚信、专业、创新的核心价值观，致力于成为行业标杆。
    """
    
    # Example AI responses that may differ from official definition
    ai_responses_good = [
        "这是一家优秀的AI技术公司，专注于高质量的人工智能解决方案，注重技术创新和客户服务。",
        "该公司在AI领域表现出色，以技术创新和专业服务著称，客户满意度很高。"
    ]
    
    ai_responses_bad = [
        "这家公司提供AI服务，但最近有报道称存在一些质量问题和客户服务不佳的情况。",
        "虽然公司在AI领域有一定知名度，但客户服务和技术稳定性方面有待改进。"
    ]
    
    print("Testing with POSITIVE AI responses:")
    print(f"Official Definition: {official_definition[:100]}...")
    print(f"AI Responses: {[r[:50] for r in ai_responses_good]}")
    
    analysis_good = sa.analyze_semantic_drift(
        official_definition=official_definition,
        ai_responses=ai_responses_good,
        brand_name="Example Brand"
    )
    
    print(f"  • Semantic Drift Score: {analysis_good['semantic_drift_score']}")
    print(f"  • Drift Severity: {analysis_good['drift_severity']}")
    print(f"  • Similarity Score: {analysis_good['similarity_score']:.2f}")
    print(f"  • Missing Keywords: {len(analysis_good['missing_keywords'])}")
    print(f"  • Unexpected Keywords: {len(analysis_good['unexpected_keywords'])}")
    print(f"  • Negative Terms Found: {len(analysis_good['negative_terms'])}")
    print(f"  • Positive Terms Found: {len(analysis_good['positive_terms'])}")
    
    print("\nTesting with NEGATIVE AI responses:")
    print(f"Official Definition: {official_definition[:100]}...")
    print(f"AI Responses: {[r[:50] for r in ai_responses_bad]}")
    
    analysis_bad = sa.analyze_semantic_drift(
        official_definition=official_definition,
        ai_responses=ai_responses_bad,
        brand_name="Example Brand"
    )
    
    print(f"  • Semantic Drift Score: {analysis_bad['semantic_drift_score']}")
    print(f"  • Drift Severity: {analysis_bad['drift_severity']}")
    print(f"  • Similarity Score: {analysis_bad['similarity_score']:.2f}")
    print(f"  • Missing Keywords: {len(analysis_bad['missing_keywords'])}")
    print(f"  • Unexpected Keywords: {len(analysis_bad['unexpected_keywords'])}")
    print(f"  • Negative Terms Found: {len(analysis_bad['negative_terms'])}")
    print(f"  • Positive Terms Found: {len(analysis_bad['positive_terms'])}")
    
    print_section("2. Keyword Analysis")
    
    print("Official Definition Keywords:", analysis_good['official_keywords'][:10])
    print("AI Response Keywords:", analysis_good['ai_keywords'][:10])
    print("Missing Keywords:", analysis_good['missing_keywords'][:10])
    print("Unexpected Keywords:", analysis_good['unexpected_keywords'][:10])
    
    print("\n✅ Semantic Analysis Engine demonstration completed!")


def demo_attribution_analyzer():
    """Demonstrate the Attribution Analyzer functionality"""
    print_header("DEMONSTRATION: ATTRIBUTION ANALYSIS")
    
    # Initialize components
    swl = SourceWeightLibrary()
    aa = AttributionAnalyzer(swl)
    
    print_section("1. Attribution Analysis with Source Weights")
    
    # Example brand definition
    official_definition = """
    TechCorp is a leading technology company specializing in AI solutions.
    We are committed to innovation, quality, and customer satisfaction.
    Our core values include integrity, excellence, and technological advancement.
    """
    
    # Example AI responses
    ai_responses = [
        "TechCorp is a great tech company with innovative AI solutions. However, there have been some reports about customer service issues.",
        "The company has good technology but faces challenges with user support quality.",
        "TechCorp's products are solid but they need to improve their customer service."
    ]
    
    # Example sources with different weights
    response_sources = [
        "https://zhihu.com/question/techcorp-review",      # High weight (0.8)
        "https://news.qq.com/article/techcorp-news",       # High weight (0.9) 
        "https://low-quality-blog.com/techcorp-post",      # Low weight (0.2)
        "https://unreliable-forum.com/thread-techcorp"     # Very low weight (0.1)
    ]
    
    print("Performing attribution analysis...")
    print(f"Official Definition: {official_definition[:100]}...")
    print(f"AI Responses: {len(ai_responses)} responses")
    print(f"Sources: {response_sources}")
    
    attribution_result = aa.analyze_attribution(
        official_definition=official_definition,
        ai_responses=ai_responses,
        response_sources=response_sources,
        brand_name="TechCorp"
    )
    
    print(f"\nAttribution Analysis Results:")
    print(f"  • Semantic Drift Score: {attribution_result['semantic_analysis']['semantic_drift_score']}")
    print(f"  • Drift Severity: {attribution_result['semantic_analysis']['drift_severity']}")
    print(f"  • Source Purity: {attribution_result['source_analysis']['source_purity_percentage']:.1f}%")
    print(f"  • Total Sources Analyzed: {attribution_result['source_analysis']['total_sources']}")
    print(f"  • High Weight Sources: {len(attribution_result['source_analysis']['high_weight_sources'])}")
    print(f"  • Low Weight Sources: {len(attribution_result['source_analysis']['low_weight_sources'])}")
    print(f"  • Risk Score: {attribution_result['attribution_metrics']['risk_score']}")
    print(f"  • Pollution Sources: {len(attribution_result['source_analysis']['pollution_sources'])}")
    
    print("\nHigh Weight Sources:")
    for source in attribution_result['source_analysis']['high_weight_sources']:
        print(f"  • {source['site_name']} ({source['domain']}) - Weight: {source['weight_score']}")
    
    print("\nLow Weight Sources:")
    for source in attribution_result['source_analysis']['low_weight_sources']:
        print(f"  • {source['site_name']} ({source['domain']}) - Weight: {source['weight_score']}")
    
    if attribution_result['source_analysis']['pollution_sources']:
        print("\nPollution Sources (Low weight with negative content):")
        for source in attribution_result['source_analysis']['pollution_sources']:
            print(f"  • {source['site_name']} ({source['domain']}) - Weight: {source['weight_score']}")
            print(f"    Negative Contexts: {source.get('negative_contexts', [])}")
    
    print("\n✅ Attribution Analysis demonstration completed!")


def demo_full_integration():
    """Demonstrate full integration with ResultProcessor"""
    print_header("DEMONSTRATION: FULL INTEGRATION")
    
    # Initialize the result processor (which includes all analyzers)
    rp = ResultProcessor()
    
    print_section("1. Full Processing Pipeline")
    
    # Sample test results
    test_results = [
        {
            'aiModel': 'ChatGPT',
            'question': 'What is TechCorp?',
            'response': 'TechCorp is a technology company focusing on AI solutions. They have good products but customer service could be better.',
            'authority_score': 75,
            'visibility_score': 80,
            'sentiment_score': 60,
            'score': 72
        },
        {
            'aiModel': 'Claude',
            'question': 'How does TechCorp compare to competitors?',
            'response': 'TechCorp has solid technology and is known for innovation, though they face strong competition in customer service.',
            'authority_score': 80,
            'visibility_score': 85,
            'sentiment_score': 70,
            'score': 78
        },
        {
            'aiModel': 'Qwen',
            'question': 'What are TechCorp\'s strengths?',
            'response': 'TechCorp excels in AI technology and innovation. Their products are reliable, but customer support needs improvement.',
            'authority_score': 70,
            'visibility_score': 75,
            'sentiment_score': 65,
            'score': 70
        }
    ]
    
    print(f"Processing {len(test_results)} test results...")
    print("Brand: TechCorp")
    print("Competitors: ['AICompetitor', 'TechRival']")
    print("Brand Terms: ['AI', 'technology', 'innovation', 'customer service']")
    print("Official Definition: 'TechCorp is a leading AI technology company focused on innovation and customer satisfaction.'")
    
    # Process results with full analysis
    result = rp.process_detailed_results(
        test_results=test_results,
        brand_name='TechCorp',
        competitor_brands=['AICompetitor', 'TechRival'],
        brand_preset_terms=['AI', 'technology', 'innovation', 'customer service'],
        official_definition='TechCorp is a leading AI technology company focused on innovation and customer satisfaction.'
    )
    
    print(f"\nProcessing Results:")
    print(f"  • Digital Vitality Index: {result['digital_vitality_index']}")
    print(f"  • Semantic Analysis: {'Available' if result['semantic_analysis'] else 'Not Available'}")
    print(f"  • Attribution Analysis: {'Available' if result['attribution_analysis'] else 'Not Available'}")
    print(f"  • Competitive Analysis: {'Available' if result['competitive_analysis'] else 'Not Available'}")
    
    if result['semantic_analysis']:
        sem_analysis = result['semantic_analysis']
        print(f"  • Semantic Drift Score: {sem_analysis['semantic_drift_score']}")
        print(f"  • Drift Severity: {sem_analysis['drift_severity']}")
        print(f"  • Negative Terms: {len(sem_analysis['negative_terms'])}")
        print(f"  • Positive Terms: {len(sem_analysis['positive_terms'])}")
    
    if result['actionable_insights']:
        insights = result['actionable_insights']
        print(f"  • Content Gaps: {len(insights['content_gaps'])}")
        print(f"  • Optimization Tips: {len(insights['optimization_tips'])}")
        print(f"  • Competitor Warnings: {len(insights['competitor_warnings'])}")
        print(f"  • Priority Actions: {len(insights['priority_actions'])}")
        print(f"  • Attribution Risks: {len(insights.get('attribution_risks', []))}")
        print(f"  • Source Recommendations: {len(insights.get('source_recommendations', []))}")
    
    print_section("2. Actionable Insights")
    
    insights = result['actionable_insights']
    
    if insights['optimization_tips']:
        print("Optimization Tips:")
        for tip in insights['optimization_tips'][:3]:  # Show first 3
            print(f"  • {tip}")
    
    if insights['priority_actions']:
        print("\nPriority Actions:")
        for action in insights['priority_actions'][:3]:
            print(f"  • {action['action']}: {action['details']} (Severity: {action['severity']})")
    
    if insights.get('source_recommendations'):
        print("\nSource Recommendations:")
        for rec in insights['source_recommendations'][:2]:
            print(f"  • {rec['action']}: {rec['description']}")
            for sug in rec['suggestions'][:2]:
                print(f"    - {sug}")
    
    print("\n✅ Full Integration demonstration completed!")


def demo_visualization_data():
    """Generate sample data for frontend visualization"""
    print_header("DEMONSTRATION: VISUALIZATION DATA SAMPLES")
    
    # Sample data for frontend visualization
    visualization_samples = {
        "brand_comparison_chart": {
            "official_keywords": ["AI", "Technology", "Innovation", "Quality", "Customer Service"],
            "ai_keywords": ["AI", "Technology", "Innovation", "Products", "Support"],
            "missing_keywords": ["Quality"],
            "unexpected_keywords": ["Products", "Support"]
        },
        "semantic_drift_timeline": [
            {"date": "2024-01-01", "drift_score": 25, "severity": "轻微偏移"},
            {"date": "2024-02-01", "drift_score": 45, "severity": "轻度偏移"},
            {"date": "2024-03-01", "drift_score": 65, "severity": "中度偏移"},
            {"date": "2024-04-01", "drift_score": 85, "severity": "严重偏移"}
        ],
        "source_purity_chart": {
            "high_weight_sources": 70,
            "medium_weight_sources": 20,
            "low_weight_sources": 10,
            "total_sources": 100
        },
        "risk_assessment": {
            "semantic_risk": 85,
            "source_risk": 45,
            "combined_risk": 70,
            "risk_level": "HIGH"
        },
        "attribution_map": [
            {
                "source": "Zhihu",
                "weight": 0.8,
                "sentiment": "NEUTRAL",
                "impact": "MEDIUM"
            },
            {
                "source": "News Portal",
                "weight": 0.9,
                "sentiment": "POSITIVE", 
                "impact": "HIGH"
            },
            {
                "source": "Blog Post",
                "weight": 0.3,
                "sentiment": "NEGATIVE",
                "impact": "LOW"
            }
        ]
    }
    
    print("Sample data for frontend visualization:")
    print(json.dumps(visualization_samples, ensure_ascii=False, indent=2))
    
    print("\n✅ Visualization data samples generated!")


def main():
    """Main demonstration function"""
    print_header("GEO CONTENT QUALITY VALIDATOR - DEMONSTRATION SUITE")
    
    print(f"Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This demonstration showcases the Source Weight Library and Semantic Drift Analysis features.")
    
    try:
        # Run all demonstrations
        demo_source_weight_library()
        demo_semantic_analyzer()
        demo_attribution_analyzer()
        demo_full_integration()
        demo_visualization_data()
        
        print_header("DEMONSTRATION COMPLETE")
        print("All features demonstrated successfully!")
        print(f"Demo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()