# DeepSeek API Incorrect Call Fix Report

## Problem Statement
The system was incorrectly calling the DeepSeek API even when users did not select DeepSeek as an AI evaluation model in the frontend. This resulted in:
- Multiple 401 Authentication Fail errors
- Unnecessary API calls to DeepSeek
- Poor resource utilization
- Confusing error logs

## Root Cause Analysis
The issue was caused by:

1. **Hardcoded Defaults in AIJudgeClient**: The `AIJudgeClient` class had hardcoded defaults for `judge_platform="deepseek"` and `judge_model="deepseek-chat"`
2. **No Dynamic Parameter Support**: The system didn't accept judge model parameters from the frontend
3. **Always-On AI Evaluation**: The system always attempted to create an AI judge regardless of frontend selections

## Solution Implemented

### 1. Enhanced AIJudgeClient Constructor
Modified the `AIJudgeClient` class to accept dynamic parameters:
```python
def __init__(self, judge_platform=None, judge_model=None, api_key=None):
```

### 2. Updated Processing Function
Modified `process_and_aggregate_results_with_ai_judge` to accept judge parameters:
```python
def process_and_aggregate_results_with_ai_judge(raw_results, all_brands, main_brand, judge_platform=None, judge_model=None, judge_api_key=None):
```

### 3. Frontend Parameter Extraction
Added extraction of judge parameters from the request data:
```python
judge_platform = data.get('judgePlatform')
judge_model = data.get('judgeModel')
judge_api_key = data.get('judgeApiKey')
```

### 4. Conditional AI Evaluation
Implemented logic to only create and use AI judge when parameters are provided:
```python
if judge_platform and judge_model and judge_api_key:
    ai_judge = AIJudgeClient(judge_platform=judge_platform, judge_model=judge_model, api_key=judge_api_key)
else:
    # Skip AI evaluation
```

### 5. Graceful Degradation
Added fallback behavior when no judge parameters are provided, maintaining compatibility with existing systems.

## Files Modified
- `ai_judge_module.py` - Enhanced AIJudgeClient constructor
- `wechat_backend/views.py` - Updated process_and_aggregate_results_with_ai_judge function and parameter extraction

## Verification
- All tests pass confirming the fix works correctly
- AIJudgeClient now accepts dynamic parameters
- Processing function accepts judge parameters
- System respects frontend model selection
- No more hardcoded DeepSeek calls when not selected

## Impact
- Eliminated unwanted DeepSeek API calls when not selected
- Improved system efficiency
- Reduced unnecessary error logs
- Enhanced flexibility for different AI model selections
- Maintained backward compatibility

## Usage
Frontend applications can now specify which model to use for AI judging by passing:
- `judgePlatform` - The platform to use for judging (e.g., "qwen", "doubao", etc.)
- `judgeModel` - The specific model to use for judging
- `judgeApiKey` - The API key for the judging model

If these parameters are not provided, the system will skip the AI evaluation phase entirely.