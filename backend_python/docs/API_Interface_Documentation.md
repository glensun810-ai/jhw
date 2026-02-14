# WeChat Mini Program Backend - API Interface Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [API Endpoints](#api-endpoints)
4. [AI Platform Integration](#ai-platform-integration)
5. [Security & Authentication](#security--authentication)
6. [Database Interfaces](#database-interfaces)
7. [Monitoring & Logging](#monitoring--logging)
8. [Configuration](#configuration)

## Overview

This document provides a comprehensive overview of the API interfaces for the WeChat Mini Program Backend. The system is designed for brand cognition testing across multiple AI platforms, with robust security, monitoring, and scalability features.

### Technology Stack
- **Framework**: Flask (Python)
- **Database**: SQLite
- **Authentication**: JWT + WeChat Session
- **Security**: Rate limiting, Input validation, SQL injection protection
- **Monitoring**: Custom metrics collection and alerting

## System Architecture

The system follows a modular architecture with the following layers:

```
┌─────────────────────────────────────┐
│           Frontend Layer            │
├─────────────────────────────────────┤
│         API Gateway Layer           │
├─────────────────────────────────────┤
│         Business Logic Layer        │
│  ┌─────────────┬─────────────────┐  │
│  │ Brand Test  │ AI Integration  │  │
│  │ Engine      │ Engine          │  │
│  └─────────────┴─────────────────┘  │
├─────────────────────────────────────┤
│         Data Access Layer           │
├─────────────────────────────────────┤
│         Security Layer              │
├─────────────────────────────────────┤
│         Monitoring Layer            │
└─────────────────────────────────────┘
```

## API Endpoints

### 1. WeChat Integration Endpoints

#### `GET/POST /wechat/verify`
**Description**: Handles WeChat server verification during webhook setup.

**Parameters**:
- `signature` (query): WeChat signature for verification
- `timestamp` (query): Timestamp
- `nonce` (query): Random number
- `echostr` (query): Echo string (for GET requests)

**Response**:
- Success: Returns `echostr` for GET requests
- Failure: Returns 403 status code

#### `POST /api/login`
**Description**: Handles login with WeChat Mini Program code.

**Headers**:
- `Content-Type`: application/json

**Request Body**:
```json
{
  "code": "string"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "openid": "string",
    "session_key": "string",
    "unionid": "string",
    "login_time": "ISO8601 timestamp"
  },
  "token": "JWT token"
}
```

**Rate Limit**: 10 requests per minute per IP

### 2. Brand Testing Endpoints

#### `GET /api/test`
**Description**: Basic API test endpoint to verify backend connectivity.

**Response**:
```json
{
  "message": "Backend is working correctly!",
  "status": "success"
}
```

#### `POST /api/perform-brand-test`
**Description**: Performs brand cognition test across multiple AI platforms asynchronously.

**Headers**:
- `Authorization`: Bearer {token} (optional)
- `Content-Type`: application/json

**Request Body**:
```json
{
  "brand_list": ["string"],
  "selectedModels": [
    {
      "name": "string",
      "checked": boolean
    }
  ],
  "customQuestions": ["string"],
  "userOpenid": "string",
  "userLevel": "string",
  "judgePlatform": "string",
  "judgeModel": "string",
  "judgeApiKey": "string"
}
```

**Response**:
```json
{
  "status": "success",
  "executionId": "UUID string",
  "message": "Test started successfully"
}
```

**Rate Limit**: 5 requests per minute per endpoint

#### `GET /api/test-progress`
**Description**: Gets the progress of a brand test by execution ID.

**Parameters**:
- `executionId` (query): UUID of the test execution

**Response**:
```json
{
  "progress": number,
  "completed": number,
  "total": number,
  "status": "string",
  "results": [],
  "start_time": "ISO8601 timestamp",
  "should_stop_polling": boolean (when completed/failed)
}
```

### 3. User History Endpoints

#### `GET /api/test-history`
**Description**: Retrieves user's test history.

**Parameters**:
- `userOpenid` (query): User's OpenID
- `limit` (query): Number of records to return (default: 20)
- `offset` (query): Offset for pagination (default: 0)

**Response**:
```json
{
  "status": "success",
  "history": [
    {
      "id": number,
      "brand_name": "string",
      "test_date": "ISO8601 timestamp",
      "ai_models_used": [],
      "overall_score": number,
      "total_tests": number
    }
  ],
  "count": number
}
```

#### `GET /api/test-record/{record_id}`
**Description**: Retrieves a specific test record by ID.

**Parameters**:
- `record_id` (path): Numeric ID of the test record

**Response**:
```json
{
  "status": "success",
  "record": {
    "id": number,
    "brand_name": "string",
    "test_date": "ISO8601 timestamp",
    "ai_models_used": [],
    "overall_score": number,
    "total_tests": number,
    "detailed_results": []
  }
}
```

### 4. Platform & Configuration Endpoints

#### `GET /api/config`
**Description**: Returns basic configuration information.

**Headers**:
- `Authorization`: Bearer {token} (optional)

**Response**:
```json
{
  "app_id": "string",
  "server_time": "ISO8601 timestamp",
  "status": "active",
  "user_id": "string"
}
```

#### `GET /api/platform-status`
**Description**: Gets status information for all AI platforms.

**Headers**:
- `Authorization`: Bearer {token} (optional)

**Response**:
```json
{
  "status": "success",
  "platforms": {
    "platform_name": {
      "status": "string",
      "has_api_key": boolean,
      "quota": {
        "daily_limit": number,
        "used_today": number,
        "remaining": number
      },
      "cost_per_request": number,
      "rate_limit": number
    }
  }
}
```

#### `GET /api/ai-platforms`
**Description**: Gets available AI platforms with their default selection status.

**Response**:
```json
{
  "domestic": [
    {
      "name": "string",
      "checked": boolean
    }
  ],
  "overseas": [
    {
      "name": "string",
      "checked": boolean
    }
  ]
}
```

### 5. Utility Endpoints

#### `GET /api/source-intelligence`
**Description**: Gets source intelligence map for a brand.

**Parameters**:
- `brandName` (query): Name of the brand (default: '默认品牌')

**Response**:
```json
{
  "status": "success",
  "data": {
    "nodes": [],
    "links": []
  }
}
```

#### `POST /api/send_message`
**Description**: Sends template message (placeholder implementation).

**Response**:
```json
{
  "status": "success"
}
```

#### `GET /api/access_token`
**Description**: Gets access token (placeholder implementation).

**Response**:
```json
{
  "access_token": "mock_token",
  "status": "success"
}
```

#### `POST /api/user_info`
**Description**: Decrypts user information (placeholder implementation).

**Response**:
```json
{
  "status": "success",
  "user_info": {}
}
```

### 6. System Endpoints

#### `GET /`
**Description**: Main index endpoint.

**Response**:
```json
{
  "message": "WeChat Mini Program Backend Server",
  "status": "running",
  "app_id": "string"
}
```

#### `GET /health`
**Description**: Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "ISO8601 timestamp"
}
```

## AI Platform Integration

### Supported Platforms

The system supports multiple AI platforms through a unified interface:

| Platform | Identifier | Notes |
|----------|------------|-------|
| DeepSeek | `deepseek` | Chinese LLM |
| ChatGPT | `chatgpt` | OpenAI GPT models |
| Claude | `claude` | Anthropic models |
| Gemini | `gemini` | Google models |
| Qwen | `qwen` | Alibaba Tongyi Qianwen |
| Wenxin Yiyan | `wenxin` | Baidu ERNIE Bot |
| Doubao | `doubao` | ByteDance Doubao |
| Kimi | `kimi` | Moonshot Kimi |
| Yuanbao | `yuanbao` | Tencent Yuanbao |
| Spark | `spark` | iFlytek Spark |
| Zhipu | `zhipu` | Zhipu AI |

### Base Interface

#### `AIClient` Abstract Class
All AI adapters inherit from this base class:

```python
class AIClient(ABC):
    def __init__(self, platform_type: AIPlatformType, model_name: str, api_key: str):
        pass

    @abstractmethod
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        pass
```

#### `AIResponse` Data Structure
Standardized response format across all AI platforms:

```python
@dataclass
class AIResponse:
    success: bool
    content: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[AIErrorType] = None
    model: Optional[str] = None
    platform: Optional[str] = None
    tokens_used: int = 0
    latency: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
```

#### `AIAdapterFactory`
Factory class for creating AI adapter instances:

```python
# Create an adapter instance
adapter = AIAdapterFactory.create('qwen', 'api_key_here', 'qwen-max')
```

## Security & Authentication

### Authentication Methods

The system supports multiple authentication methods:

1. **JWT Authentication**:
   - Header: `Authorization: Bearer {token}`
   - Validated using HS256 algorithm
   - Default expiration: 24 hours

2. **WeChat Session Authentication**:
   - Headers: `X-WX-OpenID`, `X-OpenID`, or `X-Wechat-OpenID`
   - Extracts user identity from WeChat session

3. **Frontend-Passed Identity**:
   - Extracts `userOpenid` from request body
   - Used when frontend manages user identity

### Security Decorators

#### `@require_auth`
Requires valid authentication:

```python
@require_auth
def protected_endpoint():
    pass
```

#### `@require_auth_optional`
Provides optional authentication:

```python
@require_auth_optional
def semi_protected_endpoint():
    user_id = get_current_user_id()  # May be None
    pass
```

#### `@rate_limit`
Applies rate limiting to endpoints:

```python
@rate_limit(limit=10, window=60, per='ip')  # 10 requests per minute per IP
def rate_limited_endpoint():
    pass
```

### Input Validation & Sanitization

#### `InputValidator`
Validates various input types:

```python
# Validate email
InputValidator.validate_email('user@example.com')

# Validate URL
InputValidator.validate_url('https://example.com')

# Validate alphanumeric
InputValidator.validate_alphanumeric('abc123', min_length=3, max_length=10)

# Validate safe text (prevents XSS)
InputValidator.validate_safe_text('<script>alert("xss")</script>')  # Returns False
```

#### `InputSanitizer`
Sanitizes user inputs:

```python
# Sanitize HTML
InputSanitizer.sanitize_html('<p>Hello <script>alert("xss")</script></p>')

# Sanitize string
InputSanitizer.sanitize_string('<script>alert("xss")</script>')

# Sanitize entire data structure
InputSanitizer.sanitize_user_input({
    'name': '<script>alert("xss")</script>',
    'nested': {'value': 'safe'}
})
```

### SQL Injection Protection

#### `SQLInjectionProtector`
Detects and prevents SQL injection attempts:

```python
protector = SQLInjectionProtector()
is_safe = protector.validate_input("user'; DROP TABLE users; --")
```

#### `SafeDatabaseQuery`
Executes parameterized queries safely:

```python
safe_query = SafeDatabaseQuery('database.db')
results = safe_query.execute_query('SELECT * FROM users WHERE id = ?', (user_id,))
```

## Database Interfaces

### Schema

The system uses SQLite with the following tables:

#### `users`
Stores user information from WeChat authentication:
- `id`: Primary key, auto-increment
- `openid`: Unique WeChat OpenID
- `nickname`: User nickname
- `avatar_url`: Avatar URL
- `created_at`: Creation timestamp
- `updated_at`: Update timestamp

#### `brands`
Stores brand information associated with users:
- `id`: Primary key, auto-increment
- `user_id`: Foreign key to users
- `name`: Brand name
- `description`: Brand description
- `created_at`: Creation timestamp

#### `test_records`
Stores test results and history:
- `id`: Primary key, auto-increment
- `user_id`: Foreign key to users
- `brand_name`: Tested brand name
- `test_date`: Test timestamp
- `ai_models_used`: JSON string of used models
- `questions_used`: JSON string of used questions
- `overall_score`: Overall test score
- `total_tests`: Number of individual tests
- `results_summary`: JSON string of summary
- `detailed_results`: JSON string of detailed results

#### `user_preferences`
Stores user preferences:
- `id`: Primary key, auto-increment
- `user_id`: Foreign key to users
- `preference_key`: Preference key
- `preference_value`: Preference value (JSON string)
- `created_at`: Creation timestamp
- `updated_at`: Update timestamp

### Database Functions

#### `init_db()`
Initializes the database with required tables.

#### `save_test_record()`
Saves a test record to the database:
```python
record_id = save_test_record(
    user_openid="openid123",
    brand_name="Test Brand",
    ai_models_used=["qwen", "chatgpt"],
    questions_used=["What is your brand?"],
    overall_score=85.5,
    total_tests=10,
    results_summary={"accuracy": 0.9},
    detailed_results=[{"model": "qwen", "response": "..."}]
)
```

#### `get_user_test_history()`
Retrieves user's test history:
```python
history = get_user_test_history(
    user_openid="openid123",
    limit=20,
    offset=0
)
```

#### `get_test_record_by_id()`
Retrieves a specific test record:
```python
record = get_test_record_by_id(record_id=123)
```

#### `save_user_preference()`
Saves a user preference:
```python
save_user_preference(
    user_openid="openid123",
    preference_key="theme",
    preference_value="dark"
)
```

#### `get_user_preference()`
Gets a user preference:
```python
theme = get_user_preference(
    user_openid="openid123",
    preference_key="theme",
    default_value="light"
)
```

## Monitoring & Logging

### Loggers

The system uses multiple specialized loggers:

- `app_logger`: General application logging
- `api_logger`: API request/response logging
- `wechat_logger`: WeChat integration logging
- `db_logger`: Database operation logging

### Monitoring Decorator

#### `@monitored_endpoint`
Automatically monitors API endpoints:

```python
@monitored_endpoint(
    endpoint_name='/api/test',
    require_auth=False,
    validate_inputs=False
)
def test_api():
    return jsonify({'message': 'Backend is working correctly!'})
```

Features:
- Records API requests and responses
- Tracks response times
- Logs security events
- Collects metrics

### Metrics Collection

The system collects various metrics:

- API call counts and success rates
- Response time distributions
- Error rates by type
- Security event counts
- Resource utilization

### Alert System

Configurable alerts for:
- High error rates (>10% in 5 minutes)
- Slow response times (>5 seconds average)
- Security events (>5 events in 10 minutes)

## Configuration

### Environment Variables

The system uses environment variables for configuration:

#### WeChat Configuration
- `WECHAT_APP_ID`: WeChat Mini Program App ID
- `WECHAT_APP_SECRET`: WeChat Mini Program Secret
- `WECHAT_TOKEN`: WeChat verification token

#### Server Configuration
- `DEBUG`: Enable/disable debug mode
- `SECRET_KEY`: Secret key for JWT signing

#### Logging Configuration
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE`: Log file path
- `LOG_MAX_BYTES`: Maximum log file size (bytes)
- `LOG_BACKUP_COUNT`: Number of log backups to keep

#### AI Platform Configuration
Each platform can have specific configuration:
- `{PLATFORM}_API_KEY`: API key for the platform
- `{PLATFORM}_BASE_URL`: Base URL for API calls
- `{PLATFORM}_TEMPERATURE`: Temperature setting
- `{PLATFORM}_MAX_TOKENS`: Maximum tokens to generate
- `{PLATFORM}_TIMEOUT`: Request timeout (seconds)
- `{PLATFORM}_RETRY_TIMES`: Number of retries
- `{PLATFORM}_MODEL_ID`: Default model ID

Example: `QWEN_API_KEY`, `CHATGPT_BASE_URL`, `DOUBAO_MODEL_ID`

### Configuration Manager

The `Config` class in `config_manager.py` manages platform configurations:

```python
from config_manager import Config as PlatformConfigManager

config_manager = PlatformConfigManager()
platform_config = config_manager.get_platform_config('qwen')

if platform_config and platform_config.api_key:
    print(f"Qwen API key is configured: {bool(platform_config.api_key)}")
```

## Error Handling

### Standard Error Responses

The system returns consistent error responses:

```json
{
  "error": "Error message",
  "message": "Human-readable description"
}
```

### HTTP Status Codes

- `200`: Success
- `400`: Bad request (validation error)
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not found
- `429`: Rate limit exceeded
- `500`: Internal server error

### Rate Limit Response

When rate limits are exceeded:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later."
}
```

Rate limit headers are also included:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time when counter resets

## Best Practices

### Client Implementation

1. **Authentication**: Always include JWT token when available
2. **Error Handling**: Handle all HTTP status codes appropriately
3. **Rate Limits**: Respect rate limit headers and implement exponential backoff
4. **Timeouts**: Set appropriate request timeouts (recommended: 30+ seconds for brand tests)
5. **Polling**: Use `/api/test-progress` endpoint to poll for test results

### Security Considerations

1. **Input Validation**: Always validate and sanitize inputs on the client side
2. **API Keys**: Never expose API keys in client-side code
3. **Authentication**: Implement proper token refresh mechanisms
4. **HTTPS**: Always use HTTPS in production
5. **Privacy**: Follow privacy regulations for user data

### Performance Optimization

1. **Batch Requests**: Batch multiple operations when possible
2. **Caching**: Cache static resources and configuration
3. **Connection Pooling**: Reuse connections for multiple requests
4. **Asynchronous Processing**: Use asynchronous endpoints for long-running operations