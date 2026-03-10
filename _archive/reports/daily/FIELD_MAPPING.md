# API Field Mapping Document

## Overview

This document defines the field naming convention for API data exchange between frontend and backend.

**Convention**: 
- **API Responses**: camelCase (JavaScript friendly)
- **API Requests**: camelCase (from frontend)
- **Internal Processing**: snake_case (Python convention)
- **Database**: snake_case (SQL convention)

## Field Conversion Rules

### snake_case → camelCase

| snake_case | camelCase | Description |
|-----------|-----------|-------------|
| `execution_id` | `executionId` | Execution identifier |
| `report_id` | `reportId` | Report identifier |
| `brand_name` | `brandName` | Brand name |
| `competitor_brands` | `competitorBrands` | Competitor brands list |
| `selected_models` | `selectedModels` | Selected AI models |
| `custom_questions` | `customQuestions` | Custom questions list |
| `is_completed` | `isCompleted` | Completion status |
| `created_at` | `createdAt` | Creation timestamp |
| `completed_at` | `completedAt` | Completion timestamp |
| `should_stop_polling` | `shouldStopPolling` | Polling control flag |
| `user_id` | `userId` | User identifier |
| `brand_list` | `brandList` | Brand list |
| `custom_question` | `customQuestion` | Custom question (singular) |
| `quality_score` | `qualityScore` | Quality score |
| `quality_level` | `qualityLevel` | Quality level |
| `quality_details` | `qualityDetails` | Quality details |
| `geo_data` | `geoData` | GEO analysis data |
| `sentiment_analysis` | `sentimentAnalysis` | Sentiment analysis |
| `brand_scores` | `brandScores` | Brand scores |
| `competitive_analysis` | `competitiveAnalysis` | Competitive analysis |
| `semantic_drift` | `semanticDrift` | Semantic drift data |
| `source_purity` | `sourcePurity` | Source purity data |
| `data_schema_version` | `dataSchemaVersion` | Schema version |
| `server_version` | `serverVersion` | Server version |
| `error_message` | `errorMessage` | Error message |
| `updated_at` | `updatedAt` | Update timestamp |
| `start_time` | `startTime` | Start time |
| `total_count` | `totalCount` | Total count |
| `has_more` | `hasMore` | Pagination flag |
| `is_valid` | `isValid` | Validation flag |
| `checksum_verified` | `checksumVerified` | Checksum verification |

## API Endpoints

### 1. POST /api/perform-brand-test

**Request (camelCase)**:
```json
{
  "brandList": ["Brand A", "Brand B"],
  "selectedModels": ["qwen", "doubao"],
  "customQuestions": ["Question 1?", "Question 2?"],
  "userOpenid": "xxx",
  "userLevel": "Free"
}
```

**Response (camelCase)**:
```json
{
  "status": "success",
  "executionId": "uuid-here",
  "message": "Test started successfully"
}
```

### 2. GET /test/status/{execution_id}

**Response (camelCase)**:
```json
{
  "status": "processing",
  "stage": "ai_fetching",
  "progress": 50,
  "isCompleted": false,
  "shouldStopPolling": false,
  "executionId": "uuid-here",
  "brandName": "Brand A",
  "competitorBrands": ["Brand B"],
  "selectedModels": ["qwen", "doubao"],
  "customQuestions": ["Question 1?"],
  "startTime": "2026-03-04T10:00:00",
  "updatedAt": "2026-03-04T10:02:00",
  "results": []
}
```

### 3. GET /api/diagnosis/history

**Response (camelCase)**:
```json
{
  "reports": [
    {
      "id": 1,
      "executionId": "uuid-here",
      "brandName": "Brand A",
      "status": "completed",
      "progress": 100,
      "stage": "completed",
      "isCompleted": true,
      "createdAt": "2026-03-04T10:00:00",
      "completedAt": "2026-03-04T10:05:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "hasMore": true
  }
}
```

### 4. GET /api/diagnosis/report/{execution_id}

**Response (camelCase)**:
```json
{
  "report": {
    "id": 1,
    "executionId": "uuid-here",
    "brandName": "Brand A",
    "competitorBrands": ["Brand B"],
    "selectedModels": ["qwen", "doubao"],
    "customQuestions": ["Question 1?"],
    "status": "completed",
    "progress": 100,
    "stage": "completed",
    "isCompleted": true,
    "createdAt": "2026-03-04T10:00:00",
    "completedAt": "2026-03-04T10:05:00",
    "dataSchemaVersion": "1.0",
    "serverVersion": "2.0.0"
  },
  "results": [
    {
      "id": 1,
      "brand": "Brand A",
      "question": "Question 1?",
      "model": "qwen",
      "response": "AI response here",
      "geoData": {
        "sentiment": 0.8,
        "keywords": ["keyword1", "keyword2"]
      },
      "qualityScore": 95,
      "qualityLevel": "high",
      "qualityDetails": {}
    }
  ],
  "analysis": {
    "competitiveAnalysis": {...},
    "brandScores": {...},
    "semanticDrift": {...},
    "sourcePurity": {...},
    "recommendations": {...}
  },
  "brandDistribution": {
    "data": {"Brand A": 5, "Brand B": 5},
    "totalCount": 10
  },
  "sentimentDistribution": {
    "data": {"positive": 6, "neutral": 3, "negative": 1},
    "totalCount": 10
  },
  "keywords": [...],
  "meta": {
    "dataSchemaVersion": "1.0",
    "serverVersion": "2.0.0",
    "retrievedAt": "2026-03-04T10:05:00"
  },
  "validation": {
    "isValid": true,
    "errors": [],
    "warnings": [],
    "qualityScore": 95
  },
  "qualityHints": {
    "hasLowQualityResults": false,
    "hasPartialAnalysis": false,
    "warnings": []
  }
}
```

## Implementation Details

### Field Converter Utility

Location: `backend_python/utils/field_converter.py`

```python
from utils.field_converter import convert_response_to_camel
```

### Usage in Views

```python
from utils.field_converter import convert_response_to_camel

@api.route('/endpoint')
def get_data():
    data = get_internal_data()  # snake_case internally
    return jsonify(convert_response_to_camel(data))
```

## Database Schema (snake_case - unchanged)

```sql
-- diagnosis_reports table
CREATE TABLE diagnosis_reports (
    id INTEGER PRIMARY KEY,
    execution_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    competitor_brands TEXT,  -- JSON array
    selected_models TEXT,    -- JSON array
    custom_questions TEXT,   -- JSON array
    status TEXT,
    stage TEXT,
    progress INTEGER,
    is_completed INTEGER,
    error_message TEXT,
    created_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME
);
```

## Migration Notes

### Backend Changes Required

1. **views/diagnosis_api.py** - Convert history and report responses
2. **views/diagnosis_views.py** - Convert status and test responses
3. **views/diagnosis_views_v2.py** - Convert V2 API responses
4. **views/sync_views.py** - Convert sync responses
5. **state_manager.py** - Convert state responses
6. **diagnosis_report_service.py** - Convert report data

### Frontend Changes Required

**None** - Frontend already uses camelCase, no changes needed.

### Cloud Function Changes

Minimal changes - cloud functions should pass through data as-is since they're JavaScript.

## Testing Checklist

- [ ] POST /api/perform-brand-test returns `executionId`
- [ ] GET /test/status/{id} returns all fields in camelCase
- [ ] GET /api/diagnosis/history returns `reports` with camelCase fields
- [ ] GET /api/diagnosis/report/{id} returns complete report in camelCase
- [ ] Frontend can parse new format without errors
- [ ] Historical data is compatible
- [ ] Database queries work unchanged
- [ ] Internal processing uses snake_case

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-04 | System Architect | Initial version |

---

**Status**: In Implementation
**Priority**: P0
**Owner**: Chief Full-Stack Engineer
