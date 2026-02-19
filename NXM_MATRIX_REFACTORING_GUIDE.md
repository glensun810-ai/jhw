# NxM Matrix Refactoring Implementation Guide

## Overview
This document describes the changes made to implement the NxM matrix execution strategy for the brand testing backend.

## Summary: All Changes Completed ✅

All phases of the refactoring have been successfully completed:

1. ✅ **base_adapter.py** - GEO Prompt Template and Parser added
2. ✅ **nxm_execution_engine.py** - New execution engine module created
3. ✅ **views.py** - Integrated with NxM execution engine
4. ✅ **Syntax verification** - All Python files compile successfully

## Changes Completed

### 1. base_adapter.py - GEO Prompt Template and Parser ✅

**File**: `backend_python/wechat_backend/ai_adapters/base_adapter.py`

**Added**:
- `GEO_PROMPT_TEMPLATE`: A prompt template that forces AI to output self-audit JSON data
- `parse_geo_json()`: A function to extract the GEO analysis JSON from AI responses

The template requires AI to output:
```json
{
  "geo_analysis": {
    "brand_mentioned": boolean,
    "rank": number,
    "sentiment": number,
    "cited_sources": [
      {"url": "string", "site_name": "string", "attitude": "positive/negative/neutral"}
    ],
    "interception": "string"
  }
}
```

### 2. nxm_execution_engine.py - New Execution Engine ✅

**File**: `backend_python/wechat_backend/nxm_execution_engine.py`

**New module** with two main functions:

1. **`execute_nxm_test()`**: Implements the NxM loop:
   - Outer loop: iterates through questions
   - Middle loop: iterates through brands
   - Inner loop: iterates through models
   
2. **`verify_nxm_execution()`**: Validates the execution results

**Key features**:
- Each execution uses the GEO prompt template
- Results include `geo_data` field with parsed analysis
- Real-time progress updates to execution_store
- Automatic database saving

### 3. views.py - Integration ✅

**File**: `backend_python/wechat_backend/views.py`

**Added imports** (line 22-25):
```python
from .ai_adapters.base_adapter import AIPlatformType, AIClient, AIResponse, GEO_PROMPT_TEMPLATE, parse_geo_json
from .ai_adapters.factory import AIAdapterFactory
from .nxm_execution_engine import execute_nxm_test, verify_nxm_execution
```

**Modified function** (line 354-420):
The `run_async_test()` function now uses the new `execute_nxm_test` function from the NxM execution engine.

The old TestExecutor-based approach has been replaced with:
```python
def run_async_test():
    """
    重构后的 NxM 执行逻辑
    外层循环遍历问题，内层循环遍历模型
    使用 execute_nxm_test 函数执行实际测试
    """
    try:
        # ... question validation ...
        
        # 使用 NxM 执行引擎执行测试
        api_logger.info(f"Starting NxM execution engine for '{execution_id}'")
        
        # 调用 NxM 执行函数
        result = execute_nxm_test(
            execution_id=execution_id,
            brand_list=brand_list,
            selected_models=selected_models,
            raw_questions=raw_questions,
            user_id=user_id or "anonymous",
            user_level=user_level.value,
            execution_store=execution_store
        )
        # ... result handling ...
```

## Verification Checklist

### 1. Logic Verification (逻辑确认)
Check backend logs for multiple API calls:
- Expected: 3 questions × 4 models × 1 brand = 12 requests
- If only 4 requests, the NxM loop is NOT working

**How to check**:
```bash
# In logs, look for patterns like:
Executing [Q:1] [Brand:XXX] on [Model:YYY]
Executing [Q:2] [Brand:XXX] on [Model:YYY]
...
```

### 2. Data Verification (数据确认)
Check database or logs for results with `geo_data` field:

**Expected structure**:
```json
{
  "question_id": 0,
  "question_text": "...",
  "brand": "Brand Name",
  "model": "Model Name",
  "content": "AI response text...",
  "geo_data": {
    "brand_mentioned": true,
    "rank": 3,
    "sentiment": 0.7,
    "cited_sources": [...],
    "interception": ""
  },
  "status": "success"
}
```

### 3. Prompt Verification (Prompt 确认)
Check AI output for JSON block at the end:

**Expected pattern**:
```
[AI response text...]

{"geo_analysis": {"brand_mentioned": true, "rank": 3, ...}}
```

## Testing

### Run a Test
```python
# In Python shell or via API
import requests

response = requests.post('http://localhost:5000/api/perform-brand-test', json={
    'brand_list': ['Tesla'],
    'selectedModels': ['doubao', 'qwen', 'deepseek'],
    'custom_question': '介绍一下{brandName}'
})

execution_id = response.json()['execution_id']

# Poll for results
progress_response = requests.get(f'http://localhost:5000/api/execution-progress/{execution_id}')
```

### Verify Results
```python
from backend_python.wechat_backend.nxm_execution_engine import verify_nxm_execution
from backend_python.wechat_backend.views import execution_store

verification = verify_nxm_execution(
    execution_store=execution_store,
    execution_id=execution_id,
    expected_questions=1,
    expected_models=3,
    expected_brands=1
)

print(verification)
# Expected output:
# {
#   'valid': True,
#   'total_executions': 3,
#   'geo_data_percentage': 100.0,
#   ...
# }
```

## File Structure

```
backend_python/wechat_backend/
├── ai_adapters/
│   ├── base_adapter.py          # ✅ Modified: Added GEO_PROMPT_TEMPLATE, parse_geo_json
│   ├── factory.py
│   └── ...
├── nxm_execution_engine.py       # ✅ New: NxM execution logic
├── views.py                      # ✅ Modified: Integrated with NxM execution engine
└── ...
```

## Next Steps

1. **Test the implementation** using the verification checklist below
2. **Monitor logs** to confirm NxM pattern is working
3. **Check database** for results with `geo_data` field

## Troubleshooting

### Issue: Only M requests instead of N×M
**Solution**: Check that `run_async_test` is calling `execute_nxm_test` not the old TestExecutor

### Issue: No geo_data in results
**Solution**: 
1. Check that AI is receiving the GEO_PROMPT_TEMPLATE
2. Verify `parse_geo_json` is being called
3. Check AI response format matches expected JSON structure

### Issue: parse_geo_json returns default values
**Solution**: 
1. Check AI is outputting JSON at the end of response
2. Verify JSON is not wrapped in markdown code blocks
3. Adjust regex in `parse_geo_json` if needed

## Summary

The refactoring implements a clear NxM matrix execution pattern where:
- Each question is tested against each model
- Each execution includes GEO analysis requirements
- Results are structured with `geo_data` for automated ranking and source analysis
- Progress is tracked in real-time
- Results are saved to database immediately

This provides the foundation for automated brand ranking, sentiment analysis, and source intelligence gathering.
