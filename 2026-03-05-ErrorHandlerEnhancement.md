# Error Handling Enhancement: Display Backend Error Suggestions

**Date:** 2026-03-05  
**Priority:** P3 - Enhancement  
**Status:** ✅ Completed

## Overview

Enhanced error handling to display backend error messages and suggestions to end users, providing a better user experience with actionable guidance when errors occur.

## Problem Statement

### Before Enhancement

1. **Generic Error Messages**: Users saw generic errors like "诊断执行失败" without specific guidance
2. **No Backend Context**: Backend error details and suggestions were not forwarded to frontend
3. **Poor User Experience**: Users had no idea how to resolve issues
4. **Repeated Support Tickets**: Same issues generated multiple support requests

### Example (Before)

```
Error: 诊断执行失败

建议：
1. 查看历史记录
2. 重新发起诊断
```

### After Enhancement

1. **Specific Error Messages**: Backend returns detailed error messages
2. **Actionable Suggestions**: Context-aware suggestions based on error type
3. **Error Details**: Technical details for debugging (optional)
4. **Better UX**: Users can self-resolve common issues

### Example (After)

```
Error: AI 平台响应超时

建议：
• 请稍后重试
• 尝试使用其他 AI 模型
• 检查网络连接

详情：Connection timeout after 90s
```

## Solution Architecture

### 1. Backend Error Handler Module

**File:** `backend_python/wechat_backend/error_handler.py`

#### Features

- **Pre-defined Error Codes**: Standardized error codes with messages and suggestions
- **Structured Responses**: Consistent error response format
- **Context-Aware Suggestions**: Different suggestions for different error types
- **Helper Functions**: Specialized handlers for common error scenarios
- **Decorators**: `@handle_api_exceptions` for automatic error handling

#### Error Registry

```python
ERROR_REGISTRY = {
    'AI_TIMEOUT': {
        'message': 'AI 平台响应超时',
        'suggestion': ['请稍后重试', '尝试使用其他 AI 模型', '检查网络连接'],
        'http_status': 504
    },
    'AI_RATE_LIMIT_EXCEEDED': {
        'message': 'AI 平台请求过于频繁',
        'suggestion': ['请等待 1 分钟后重试', '减少并发请求数量'],
        'http_status': 429
    },
    # ... more error codes
}
```

#### Response Format

```json
{
  "error": "AI 平台响应超时",
  "error_code": "AI_TIMEOUT",
  "suggestion": ["请稍后重试", "尝试使用其他 AI 模型", "检查网络连接"],
  "details": {
    "error": "Connection timeout after 90s"
  }
}
```

#### Available Functions

```python
# Create error response
create_error_response(error_code, message, suggestion, details)

# Handle AI platform errors
handle_ai_platform_error(error, platform_name)

# Handle validation errors
handle_validation_error(field_name, message)

# Handle database errors
handle_database_error(error, operation)

# Create success response
create_success_response(data, message, code)

# Decorators
@handle_api_exceptions  # Auto error handling for API endpoints
@handle_errors         # Generic error handling decorator
```

### 2. Frontend Error Processing

**File:** `services/brandTestService.js`

#### Enhanced `createUserFriendlyError` Function

The function now:

1. **Extracts Backend Errors**: Parses backend error responses
2. **Prioritizes Backend Messages**: Uses backend messages when more informative
3. **Merges Suggestions**: Combines frontend and backend suggestions
4. **Displays Details**: Shows technical details for debugging

#### Error Extraction Logic

```javascript
// Extract backend error from response
if (errorInfo.backendError) {
  const backendError = errorInfo.backendError;
  
  // Use backend message if available
  if (backendError.message || backendError.error) {
    message = backendError.message || backendError.error;
  }
  
  // Use backend suggestion if available
  if (backendError.suggestion || backendError.recommendation) {
    suggestion = '\n\n建议：\n' + backendError.suggestion;
  }
  
  // Show details if available
  if (backendError.details) {
    suggestion += '\n\n详情：' + backendError.details;
  }
}
```

### 3. Backend Integration

**File:** `backend_python/wechat_backend/views.py`

#### Updated Error Handling in `mvp_brand_test`

```python
except Exception as e:
    from wechat_backend.error_handler import create_error_response
    
    error_msg = str(e).lower()
    
    # Type-specific error responses
    if 'timeout' in error_msg:
        return create_error_response(
            error_code='AI_TIMEOUT',
            message='AI 平台响应超时',
            suggestion=['请稍后重试', '尝试使用其他 AI 模型'],
            details={'error': str(e)}
        )[0], 504
    elif 'api key' in error_msg:
        return create_error_response(
            error_code='AI_API_KEY_INVALID',
            message='AI API 密钥无效',
            suggestion=['请联系管理员更新 API 密钥'],
            details={'error': str(e)}
        )[0], 401
    # ... more error types
```

## Implementation Details

### Backend Changes

| File | Change | Description |
|------|--------|-------------|
| `wechat_backend/error_handler.py` | Created | New error handling module |
| `wechat_backend/views.py` | Updated | Integration with error handler |

### Frontend Changes

| File | Change | Description |
|------|--------|-------------|
| `services/brandTestService.js` | Enhanced | Backend error extraction and display |

## Error Code Reference

### Authentication Errors

| Code | Message | HTTP Status | Suggestions |
|------|---------|-------------|-------------|
| `AUTH_REQUIRED` | 认证信息已过期 | 401 | 请重新登录，清除缓存后重试 |
| `AUTH_INVALID` | 认证信息无效 | 401 | 请检查 Token 是否正确 |
| `AUTH_FORBIDDEN` | 无权访问此资源 | 403 | 请联系管理员获取权限 |

### Validation Errors

| Code | Message | HTTP Status | Suggestions |
|------|---------|-------------|-------------|
| `VALIDATION_ERROR` | 输入数据格式错误 | 400 | 检查品牌名称、确认 AI 模型 |
| `MISSING_PARAMETER` | 缺少必需参数 | 400 | 请检查请求参数是否完整 |
| `INVALID_PARAMETER` | 参数值无效 | 400 | 检查参数格式和取值范围 |

### AI Platform Errors

| Code | Message | HTTP Status | Suggestions |
|------|---------|-------------|-------------|
| `AI_PLATFORM_UNAVAILABLE` | AI 平台暂时不可用 | 503 | 稍后重试、更换 AI 模型 |
| `AI_API_KEY_MISSING` | AI API 密钥未配置 | 500 | 联系管理员配置 API 密钥 |
| `AI_API_KEY_INVALID` | AI API 密钥无效 | 401 | 联系管理员更新 API 密钥 |
| `AI_RATE_LIMIT_EXCEEDED` | AI 平台请求过于频繁 | 429 | 等待 1 分钟后重试 |
| `AI_TIMEOUT` | AI 平台响应超时 | 504 | 稍后重试、检查网络 |
| `AI_RESPONSE_PARSE_ERROR` | AI 响应解析失败 | 500 | 重试、检查返回格式 |

### Task Execution Errors

| Code | Message | HTTP Status | Suggestions |
|------|---------|-------------|-------------|
| `TASK_EXECUTION_FAILED` | 任务执行失败 | 500 | 查看历史记录、重新诊断 |
| `TASK_TIMEOUT` | 任务执行超时 | 408 | 重试、减少问题数量 |
| `TASK_NOT_FOUND` | 任务不存在 | 404 | 检查执行 ID、重新发起 |

### Database Errors

| Code | Message | HTTP Status | Suggestions |
|------|---------|-------------|-------------|
| `DATABASE_ERROR` | 数据库操作失败 | 500 | 联系技术支持 |
| `DATABASE_CONNECTION_ERROR` | 数据库连接失败 | 503 | 稍后重试、联系支持 |

## Usage Examples

### Backend: Creating Error Responses

#### Simple Error

```python
from wechat_backend.error_handler import create_error_response

return create_error_response(
    error_code='VALIDATION_ERROR',
    message='品牌名称不能为空',
    suggestion=['请输入有效的品牌名称']
)[0], 400
```

#### Error with Details

```python
return create_error_response(
    error_code='AI_TIMEOUT',
    message='豆包 API 响应超时',
    suggestion=['请稍后重试', '尝试使用其他 AI 模型'],
    details={'timeout_seconds': 90, 'platform': 'doubao'}
)[0], 504
```

#### Using Helper Functions

```python
from wechat_backend.error_handler import handle_ai_platform_error

try:
    response = adapter.send_prompt(prompt)
except Exception as e:
    return handle_ai_platform_error(e, '豆包 API')[0], 503
```

### Frontend: Error Display

The error is automatically formatted and displayed to users:

```javascript
try {
    await startDiagnosis(data, onProgress, onComplete, onError);
} catch (error) {
    // Error message includes backend suggestions
    wx.showModal({
        title: '诊断失败',
        content: error.message,  // Includes backend message + suggestions
        showCancel: false
    });
}
```

## Error Flow

### 1. Error Occurs

```
Backend: AI API timeout exception
```

### 2. Backend Processing

```python
# Detect error type
if 'timeout' in error_msg:
    # Return structured error with suggestions
    return create_error_response(
        error_code='AI_TIMEOUT',
        message='AI 平台响应超时',
        suggestion=['请稍后重试', '尝试使用其他 AI 模型'],
        details={'error': str(e)}
    )
```

### 3. Frontend Processing

```javascript
// Extract backend error
if (errorInfo.backendError) {
    message = backendError.message;
    suggestion = backendError.suggestion;
}

// Display to user
return new Error(message + suggestion);
```

### 4. User Sees

```
AI 平台响应超时

建议：
• 请稍后重试
• 尝试使用其他 AI 模型

详情：Connection timeout after 90s
```

## Benefits

### For Users

1. ✅ **Clear Guidance**: Know exactly what to do when errors occur
2. ✅ **Self-Service**: Can resolve common issues without support
3. ✅ **Better UX**: Feels more professional and trustworthy
4. ✅ **Reduced Frustration**: Understands what went wrong

### For Developers

1. ✅ **Standardized Errors**: Consistent error handling across codebase
2. ✅ **Easy Debugging**: Error details available for troubleshooting
3. ✅ **Maintainable**: Centralized error definitions
4. ✅ **Extensible**: Easy to add new error types

### For Support

1. ✅ **Fewer Tickets**: Users self-resolve common issues
2. ✅ **Better Context**: Error codes help diagnose issues faster
3. ✅ **Pattern Recognition**: Error codes reveal systemic issues

## Testing Recommendations

### 1. Test AI Timeout

```bash
# Simulate timeout (backend will return AI_TIMEOUT error)
# User should see timeout-specific suggestions
```

### 2. Test Rate Limiting

```bash
# Make rapid requests to trigger rate limiting
# User should see rate limit suggestions
```

### 3. Test Validation Errors

```bash
# Send invalid data (missing brand_list or questions)
# User should see validation error with specific guidance
```

### 4. Test AI API Key Errors

```bash
# Use invalid API key
# User should see API key error with admin contact suggestion
```

## Future Enhancements

1. **Error Analytics**: Track error codes to identify common issues
2. **Localized Messages**: Support multiple languages
3. **Dynamic Suggestions**: Adjust suggestions based on user behavior
4. **Error Recovery**: Auto-retry with suggested fixes
5. **User Feedback**: Allow users to rate suggestion helpfulness

## Related Documentation

- [Circuit Breaker Reset Fix](./2026-03-05-CircuitBreakerResetFix.md)
- [Backend Error Handler API](./backend_python/wechat_backend/error_handler.py)
- [Frontend Error Display](./services/brandTestService.js)

## Conclusion

The enhanced error handling system provides users with clear, actionable guidance when errors occur, reducing support burden and improving user experience. The standardized error format makes it easy to add new error types and maintain consistency across the application.

**Status:** ✅ Implementation complete and ready for testing
