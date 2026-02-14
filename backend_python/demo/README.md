# GEO Content Quality Validator - Demo Suite

This demo suite showcases the implementation of the Source Weight Library and Semantic Drift Analysis features for the GEO Content Quality Validator.

## Features Demonstrated

### 1. Source Weight Library
- **Database Management**: Shows how the system manages source weights in a SQLite database
- **Predefined Sources**: Displays the 26+ default sources with their categories and weights
- **Domain Extraction**: Demonstrates URL to domain extraction functionality
- **Weight Lookup**: Shows how the system retrieves weights for specific domains
- **Custom Source Addition**: Shows how to add new sources to the database

### 2. Semantic Analysis Engine
- **Brand Definition vs AI Response Analysis**: Compares official brand definitions with AI-generated responses
- **Drift Detection**: Calculates semantic drift scores and classifies severity levels
- **Keyword Analysis**: Identifies missing and unexpected keywords between official and AI content
- **Sentiment Analysis**: Detects positive and negative terms in AI responses

### 3. Attribution Analysis
- **Source-Response Linking**: Connects source weights with semantic analysis results
- **Pollution Source Identification**: Flags low-weight sources with negative content
- **Source Purity Calculation**: Measures proportion of high-weight sources
- **Risk Scoring**: Combines semantic drift and source quality for overall risk assessment

### 4. Full Integration
- **End-to-End Processing**: Shows the complete pipeline from brand testing to result analysis
- **Actionable Insights**: Generates optimization tips and priority actions
- **Competitive Analysis**: Integrates competitive analysis with semantic analysis
- **Visualization Data**: Prepares data for frontend visualization

## Key Outputs

### Source Weight Library
- High-weight sources (≥0.8): Authoritative sources like 百度百科 (1.0), 新华网 (0.95), etc.
- Domain extraction and weight lookup for any URL
- Ability to add custom sources with specified weights

### Semantic Analysis
- Semantic drift scores (0-100 scale)
- Drift severity classification (轻微偏移, 中度偏移, 严重偏移)
- Missing vs unexpected keywords analysis
- Positive/negative sentiment detection

### Attribution Analysis
- Source purity percentage
- High vs low weight source distribution
- Risk scores combining semantic and source quality metrics
- Pollution source identification

## Usage

The demo can be run with:
```bash
cd /path/to/project
python3 demo/demo_main.py
```

## Integration Points

The implemented features seamlessly integrate with:
- Brand testing workflows
- Result processing pipelines
- API endpoints
- Frontend visualization components
- Competitive analysis modules

## Commercial Value

These features enable:
- **Brand Protection**: Monitor and protect brand perception in AI responses
- **Source Quality Control**: Identify and mitigate influence of low-quality sources
- **Competitive Intelligence**: Analyze how competitors appear in AI responses
- **Optimization Guidance**: Provide actionable insights for brand improvement