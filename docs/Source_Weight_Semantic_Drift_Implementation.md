# GEO Content Quality Validator - Source Weight & Semantic Drift Analysis Implementation

## Overview
Successfully implemented the source weight library and semantic drift analysis engine with attribution analysis capabilities for the GEO Content Quality Validator.

## 1. Source Weight Library (source_weight_library.py)

### Features Implemented:
- **Database Schema**: Created `sources` table with fields: domain, site_name, weight_score (0-1.0), category, description
- **Default Data**: Pre-populated with core sites including:
  - Official websites and authoritative sources (Baidu Baike: 1.0, Zhihu: 0.8)
  - News portals (Sina, NetEase, Tencent News: 0.9)
  - Social media platforms (Weibo: 0.7, Xiaohongshu: 0.7)
  - AI platforms (Qwen, Kimi, DeepSeek: 0.6)
  - Potential negative sources (blacklisted sites: 0.1)
- **Domain Matching**: Implemented URL parsing to extract domains and match against weight database
- **CRUD Operations**: Methods to add/update sources and query by category/weight

### Key Functions:
- `get_source_weight(domain)` - Retrieve weight for a specific domain
- `extract_domains_from_urls(urls)` - Extract domains from a list of URLs
- `get_high_weight_sources(min_weight)` - Get sources above threshold
- `add_source()` - Add new source to database

## 2. Semantic Drift Analysis Engine (semantic_analyzer.py)

### Features Implemented:
- **Semantic Comparison**: Advanced NLP using TF-IDF and cosine similarity to compare official brand definitions vs AI responses
- **Keyword Extraction**: Uses Jieba for Chinese text processing and keyword extraction
- **Drift Calculation**: Multi-factor drift scoring considering similarity, length differences, and keyword mismatches
- **Negative Term Detection**: Identifies potentially harmful terms in AI responses
- **Positive Term Detection**: Identifies positive terms in AI responses

### Key Functions:
- `analyze_semantic_drift(official_def, ai_responses)` - Main analysis method
- `extract_keywords(text)` - Extract important terms from text
- `calculate_semantic_similarity(text1, text2)` - Compute semantic similarity
- `identify_negative_terms(text)` - Detect potentially negative terms
- `classify_drift_severity(score)` - Classify drift as severe/moderate/minor

## 3. Attribution Analysis (semantic_analyzer.py)

### Features Implemented:
- **Source-Response Linking**: Connects source weights with semantic analysis results
- **Pollution Source Identification**: Flags low-weight sources with negative content
- **Source Purity Calculation**: Measures proportion of high-weight sources in total references
- **Risk Scoring**: Combines semantic drift and source quality for overall risk assessment
- **Attribution Metrics**: Provides detailed attribution analysis between sources and content

### Key Functions:
- `analyze_attribution(official_def, ai_responses, sources)` - Main attribution analysis
- `_calculate_risk_score()` - Combines drift and source quality metrics
- Source purity and contamination detection

## 4. Integration with Result Processor (result_processor.py)

### Updates Made:
- **Enhanced Constructor**: Initializes new semantic and attribution analyzers
- **Extended Processing**: Added official_definition parameter to process_detailed_results
- **Attribution Analysis**: Performs attribution analysis when sources are available
- **Enhanced Insights**: Added attribution_risks and source_recommendations to actionable insights
- **Improved Logging**: Better logging for analysis results

## 5. API Integration (views.py)

### Updates Made:
- **Official Definition Parameter**: Added support for official brand definitions in API
- **Attribution Results**: Include attribution analysis in API responses
- **Enhanced Response Structure**: Added attributionAnalysis field to test progress responses

## 6. Data Structures & UI Adaptation

### Output Format:
- **Semantic Analysis Results**: 
  - `semantic_drift_score`: 0-100 scale (higher = more drift)
  - `drift_severity`: Classification (严重偏移, 中度偏移, etc.)
  - `official_keywords` / `ai_keywords`: Extracted terms from each source
  - `missing_keywords` / `unexpected_keywords`: Differences between sources
  - `negative_terms` / `positive_terms`: Detected sentiment terms

- **Attribution Analysis Results**:
  - `source_purity_percentage`: Ratio of high-weight sources
  - `pollution_sources`: Low-weight sources with negative content
  - `risk_score`: Combined risk assessment (0-100)
  - `high_weight_sources` / `low_weight_sources`: Categorized sources

- **Actionable Insights**:
  - `attribution_risks`: Specific attribution-related risks
  - `source_recommendations`: Recommendations for improving source quality

## 7. Key Algorithms

### Semantic Similarity Calculation:
- Uses TF-IDF vectorization with Jieba tokenization
- Applies cosine similarity for semantic distance measurement
- Falls back to simple overlap ratio if TF-IDF fails

### Drift Score Calculation:
- Base drift: (1 - similarity_score) * 100
- Length penalty: Differences in text length
- Keyword mismatch penalty: Differences in extracted keywords
- Combined with caps to ensure 0-100 range

### Risk Score Calculation:
- Combines semantic drift (70%) and source quality (30%)
- Higher scores indicate greater risk to brand perception

## 8. Commercial Integration Ready

### Features for Business Use:
- **Freemium Model Ready**: Source purity metrics for tiered access
- **Enterprise Features**: Multi-tenant source tracking
- **Reporting**: Detailed attribution and drift analysis for client reports
- **Alerting**: Pollution source detection for reputation monitoring

## 9. Technical Implementation Notes

### Performance Optimizations:
- Async processing where applicable
- Connection pooling for database operations
- Efficient text processing with Jieba
- Caching for repeated domain lookups

### Security Considerations:
- Sanitized input processing
- Parameter validation
- Secure database operations
- No hardcoded credentials

### Scalability Features:
- Modular architecture
- Database indexing for fast lookups
- Efficient algorithms for large datasets
- Memory-conscious processing

## 10. Frontend UI Adaptation Points

The implementation provides structured data that can be used for:
- **Contrast Views**: Official keywords vs AI keywords comparison
- **Risk Lists**: Specific pollution sources and their weights
- **Drift Visualization**: Semantic drift scores and severity levels
- **Source Quality Charts**: High-weight vs low-weight source distributions
- **Timeline Analysis**: Tracking drift and attribution metrics over time