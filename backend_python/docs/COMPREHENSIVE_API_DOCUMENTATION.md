# WeChat Mini Program Backend - Comprehensive API Documentation

## Overview
This document provides a comprehensive overview of all API endpoints available in the WeChat Mini Program backend system. The backend provides brand cognition testing services across multiple AI platforms, with advanced analytics, reporting, and automation features.

## Base URL
```
http://localhost:5001/api
```

## Authentication
Most endpoints support optional JWT-based authentication using the `require_auth_optional` decorator. Some endpoints require authentication using the `require_auth` decorator.

## Rate Limiting
Most endpoints implement rate limiting using the `rate_limit` decorator with different limits per IP address or endpoint.

## API Endpoints

### 1. Health Check Endpoints

#### GET /
**Description:** Root endpoint to check server status  
**Rate Limit:** 100 requests per minute per IP  
**Response:**
```json
{
  "message": "WeChat Mini Program Backend Server",
  "status": "running",
  "app_id": "your_app_id"
}
```

#### GET /health
**Description:** Health check endpoint  
**Rate Limit:** 1000 requests per minute per IP  
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T12:00:00"
}
```

### 2. WeChat Integration Endpoints

#### GET/POST /wechat/verify
**Description:** Handle WeChat server verification  
**Method:** GET (verification), POST (messages)  
**Response (GET):** Echo string for verification

#### POST /api/login
**Description:** Handle login with WeChat Mini Program code  
**Rate Limit:** 10 requests per minute per IP  
**Request:**
```json
{
  "code": "weChatCode"
}
```
**Response:**
```json
{
  "status": "success",
  "data": {
    "openid": "user_openid",
    "session_key": "session_key",
    "unionid": "unionid",
    "login_time": "timestamp"
  },
  "token": "jwt_token"
}
```

### 3. Brand Testing Endpoints

#### POST /api/perform-brand-test
**Description:** Perform brand cognition test across multiple AI platforms (Async)  
**Auth:** Optional  
**Rate Limit:** 5 requests per minute per endpoint  
**Request:**
```json
{
  "brand_list": ["brand1", "brand2"],
  "selectedModels": ["model1", "model2"],
  "customQuestions": ["question1", "question2"],
  "userOpenid": "user_id",
  "userLevel": "Free|Premium",
  "judgePlatform": "platform_name",
  "judgeModel": "model_name",
  "judgeApiKey": "api_key"
}
```
**Response:**
```json
{
  "status": "success",
  "executionId": "uuid",
  "message": "Test started successfully"
}
```

#### POST /test/submit
**Description:** Submit brand AI diagnosis task  
**Auth:** Optional  
**Rate Limit:** 5 requests per minute per endpoint  
**Request:**
```json
{
  "brand_list": ["brand1", "brand2"],
  "selectedModels": ["model1", "model2"],
  "customQuestions": ["question1", "question2"]
}
```
**Response:**
```json
{
  "task_id": "uuid",
  "message": "任务已接收并加入队列"
}
```

#### GET /test/status/<task_id>
**Description:** Poll task progress and stage status  
**Rate Limit:** 20 requests per minute per endpoint  
**Response:**
```json
{
  "task_id": "uuid",
  "progress": 50,
  "stage": "ai_fetching",
  "status_text": "正在调取AI数据...",
  "is_completed": false,
  "created_at": "timestamp"
}
```

#### GET /test/result/<task_id>
**Description:** Get diagnostic task's deep intelligence results  
**Rate Limit:** 20 requests per minute per endpoint  
**Response:**
```json
{
  "exposure_analysis": {
    "ranking_list": ["brand1", "brand2"],
    "brand_details": {
      "brand1": {
        "rank": 1,
        "word_count": 100,
        "sov_share": 0.75,
        "sentiment_score": 80
      }
    },
    "unlisted_competitors": ["competitor1"]
  },
  "source_intelligence": {
    "source_pool": [
      {
        "id": "source_id",
        "url": "https://source.com",
        "site_name": "Source Name",
        "citation_count": 10,
        "domain_authority": "High"
      }
    ],
    "citation_rank": ["source1", "source2"]
  },
  "evidence_chain": [
    {
      "negative_fragment": "fragment text...",
      "associated_url": "https://example.com",
      "source_name": "Source Name",
      "risk_level": "Medium"
    }
  ]
}
```

#### GET /api/test-progress
**Description:** Get progress of a test execution  
**Query Params:** `executionId`  
**Response:**
```json
{
  "progress": 75,
  "completed": 15,
  "total": 20,
  "status": "processing",
  "results": [],
  "should_stop_polling": false
}
```

### 4. Data and History Endpoints

#### GET /api/test-history
**Description:** Get user's test history  
**Query Params:** `userOpenid`, `limit`, `offset`  
**Response:**
```json
{
  "status": "success",
  "history": [],
  "count": 0
}
```

#### GET /api/test-record/<record_id>
**Description:** Get specific test record  
**Response:**
```json
{
  "status": "success",
  "record": {}
}
```

### 5. Platform and Configuration Endpoints

#### GET /api/config
**Description:** Return basic configuration info  
**Auth:** Optional  
**Rate Limit:** 10 requests per minute per IP  
**Response:**
```json
{
  "app_id": "your_app_id",
  "server_time": "timestamp",
  "status": "active",
  "user_id": "user_id"
}
```

#### GET /api/ai-platforms
**Description:** Get available AI platforms  
**Response:**
```json
{
  "domestic": [
    {"name": "DeepSeek", "checked": false, "available": true},
    {"name": "豆包", "checked": false, "available": true}
  ],
  "overseas": [
    {"name": "ChatGPT", "checked": true, "available": true}
  ]
}
```

#### GET /api/platform-status
**Description:** Get status of all AI platforms  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Response:**
```json
{
  "status": "success",
  "platforms": {
    "deepseek": {
      "status": "active",
      "has_api_key": true,
      "quota": {
        "daily_limit": 1000,
        "used_today": 200,
        "remaining": 800
      },
      "cost_per_request": 0.02,
      "rate_limit": 10
    }
  }
}
```

### 6. Intelligence and Analytics Endpoints

#### GET /api/source-intelligence
**Description:** Get source intelligence map  
**Query Params:** `brandName`  
**Response:**
```json
{
  "status": "success",
  "data": {
    "nodes": [
      {
        "id": "brand",
        "name": "brand_name",
        "level": 0,
        "symbolSize": 60,
        "category": "brand"
      }
    ],
    "links": [
      {
        "source": "brand",
        "target": "source_name",
        "contribution_score": 0.8,
        "sentiment_bias": 0.5
      }
    ]
  }
}
```

#### POST /action/recommendations
**Description:** Get intervention action recommendations  
**Auth:** Optional  
**Rate Limit:** 10 requests per minute per endpoint  
**Request:**
```json
{
  "source_intelligence": {},
  "evidence_chain": [],
  "brand_name": "brand_name"
}
```
**Response:**
```json
{
  "status": "success",
  "recommendations": [
    {
      "priority": "high",
      "type": "content_optimization",
      "title": "Recommendation Title",
      "description": "Recommendation Description",
      "target": "target_audience",
      "estimated_impact": 0.85,
      "action_steps": ["step1", "step2"],
      "urgency": 9
    }
  ],
  "count": 1
}
```

### 7. Scheduling and Automation Endpoints

#### POST /cruise/config
**Description:** Configure scheduled diagnostic tasks  
**Auth:** Optional  
**Rate Limit:** 10 requests per minute per endpoint  
**Request:**
```json
{
  "user_openid": "user_id",
  "brand_name": "brand_name",
  "interval_hours": 24,
  "ai_models": ["model1", "model2"],
  "questions": ["question1", "question2"],
  "job_id": "optional_job_id"
}
```
**Response:**
```json
{
  "status": "success",
  "message": "Cruise task scheduled successfully",
  "job_id": "generated_job_id",
  "brand_name": "brand_name",
  "interval_hours": 24
}
```

#### DELETE /cruise/config
**Description:** Cancel scheduled diagnostic task  
**Auth:** Optional  
**Rate Limit:** 10 requests per minute per endpoint  
**Request:**
```json
{
  "job_id": "job_id_to_cancel"
}
```
**Response:**
```json
{
  "status": "success",
  "message": "Cruise task cancelled successfully",
  "job_id": "cancelled_job_id"
}
```

#### GET /cruise/tasks
**Description:** Get all scheduled cruise tasks  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Response:**
```json
{
  "status": "success",
  "tasks": [],
  "count": 0
}
```

#### GET /cruise/trends
**Description:** Get trend data for a brand  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Query Params:** `brand_name` (required), `days` (default: 30)  
**Response:**
```json
{
  "status": "success",
  "brand_name": "brand_name",
  "days": 30,
  "trend_data": [],
  "count": 0
}
```

### 8. Market Intelligence Endpoints

#### GET /market/benchmark
**Description:** Get market benchmark comparison data  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Query Params:** `brand_name` (required), `category` (optional), `days` (default: 30)  
**Response:**
```json
{
  "status": "success",
  "brand_name": "brand_name",
  "category": "category_name",
  "days": 30,
  "benchmark_data": {}
}
```

#### GET /predict/forecast
**Description:** Get brand perception trend predictions and risk factors  
**Auth:** Optional  
**Rate Limit:** 10 requests per minute per endpoint  
**Query Params:** `brand_name` (required), `days` (default: 7), `history_days` (default: 30)  
**Response:**
```json
{
  "status": "success",
  "brand_name": "brand_name",
  "forecast_period": 7,
  "prediction_result": {}
}
```

### 9. Asset Optimization Endpoints

#### POST /assets/optimization
**Description:** Asset optimization - analyze match between official assets and AI preferences  
**Auth:** Optional  
**Rate Limit:** 10 requests per minute per endpoint  
**Request:**
```json
{
  "official_asset": "official content",
  "ai_preferences": {
    "platform_name": ["content1", "content2"]
  }
}
```
**Response:**
```json
{
  "status": "success",
  "analysis_result": {},
  "content_hit_rate": 0.85,
  "optimization_suggestions": ["suggestion1", "suggestion2"]
}
```

### 10. Reporting Endpoints

#### GET /hub/summary
**Description:** Get hub summary data - brand GEO operations analysis summary  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Query Params:** `brand_name` (required), `days` (default: 7)  
**Response:**
```json
{
  "status": "success",
  "summary": {}
}
```

#### GET /reports/executive
**Description:** Get executive perspective report  
**Auth:** Optional  
**Rate Limit:** 5 requests per minute per endpoint  
**Query Params:** `brand_name` (required), `days` (default: 30)  
**Response:**
```json
{
  "status": "success",
  "report": {}
}
```

#### GET /reports/pdf
**Description:** Get PDF format report  
**Auth:** Optional  
**Rate Limit:** 3 requests per minute per endpoint  
**Query Params:** `brand_name` (required), `days` (default: 30)  
**Response:** PDF file attachment

### 11. Workflow Management Endpoints

#### POST /workflow/tasks
**Description:** Create workflow task - process negative evidence and distribute to specified webhook  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Request:**
```json
{
  "evidence_fragment": "evidence text",
  "associated_url": "https://example.com",
  "source_name": "source name",
  "risk_level": "High",
  "brand_name": "brand name",
  "intervention_script": "script content",
  "source_meta": {},
  "webhook_url": "https://webhook.url",
  "priority": "medium"
}
```
**Response:**
```json
{
  "status": "success",
  "task_id": "generated_task_id",
  "message": "Workflow task created and dispatched successfully",
  "webhook_url": "https://webhook.url"
}
```

#### GET /workflow/tasks/<task_id>
**Description:** Get workflow task status  
**Auth:** Optional  
**Rate Limit:** 20 requests per minute per endpoint  
**Response:**
```json
{
  "status": "success",
  "task_info": {}
}
```

## Error Handling

### Common Error Responses
```json
{
  "error": "Error message",
  "details": "Additional details (optional)"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request - Invalid input data
- `403`: Forbidden - Access denied
- `404`: Not Found - Resource not found
- `500`: Internal Server Error

## Security Features

1. **Input Validation & Sanitization:** All inputs are validated using `InputValidator` and sanitized using `InputSanitizer`
2. **SQL Injection Protection:** Using `sql_protector` for all database queries
3. **Rate Limiting:** Per IP and per endpoint rate limiting
4. **Authentication:** JWT-based authentication with optional/required enforcement
5. **Security Headers:** All responses include security headers (X-Content-Type-Options, X-Frame-Options, etc.)
6. **Signature Verification:** WeChat signature verification for webhook authenticity

## API Best Practices

1. Always include proper authentication headers when required
2. Respect rate limits to avoid being throttled
3. Validate all input data before sending requests
4. Handle errors gracefully on the client side
5. Use HTTPS in production environments
6. Store API keys securely and never expose them in client-side code