# ReportId Passing Fix Report

## Issue Description

The frontend `diagnosisService.js` was expecting `report_id` from the backend response, but the backend only returned `execution_id`. This caused `reportId` to be `undefined` in the frontend.

## Root Cause

The diagnosis flow creates the report record in **Phase 3** (results saving) of the `DiagnosisOrchestrator`, but the API response is returned immediately after starting the async thread (before Phase 3 completes).

```
Timeline:
1. API receives request
2. Generate execution_id
3. Start async thread ← API returns here (no report_id yet)
4. Async Phase 1: Init
5. Async Phase 2: AI fetching
6. Async Phase 3: Results saving ← report_id created here (too late)
```

## Solution

Create the initial report record **before** starting the async thread, so `report_id` is available in the API response.

### Backend Changes

#### 1. diagnosis_views.py

**Location**: Line ~396 (before async thread start)

```python
# 【P0 修复 - 2026-03-04】提前创建报告记录，获取 report_id
report_id = None
try:
    from wechat_backend.diagnosis_report_service import get_report_service
    
    service = get_report_service()
    config = {
        'brand_name': brand_list[0],
        'competitor_brands': brand_list[1:] if len(brand_list) > 1 else [],
        'selected_models': selected_models,
        'custom_questions': custom_questions
    }
    
    # 创建初始报告记录
    report_id = service.create_report(
        execution_id=execution_id,
        user_id=user_id or 'anonymous',
        config=config
    )
    
    # 更新初始状态
    service.report_repo.update_status(
        execution_id=execution_id,
        status='initializing',
        progress=0,
        stage='init',
        is_completed=False
    )
    
except Exception as e:
    api_logger.error(f"[Orchestrator] ⚠️ 创建初始报告记录失败：{e}")
    # 报告记录创建失败不影响主流程，继续执行
```

**Location**: Line ~649 (API response)

```python
# P0 修复：转换为 camelCase 并返回 report_id
response_data = {
    'status': 'success',
    'execution_id': execution_id,
    'report_id': report_id,
    'message': 'Test started successfully'
}
return jsonify(convert_response_to_camel(response_data))
```

#### 2. diagnosis_views_v2.py

Already had report creation logic, just updated the response:

```python
# P0 修复：转换为 camelCase 并返回 report_id
response_data = {
    'status': 'success',
    'execution_id': execution_id,
    'report_id': report_id,
    'message': 'Test started successfully'
}
return jsonify(convert_response_to_camel(response_data))
```

#### 3. diagnosis_orchestrator.py

Skip creating report if it already exists (avoid duplication):

```python
# 【P0 修复 - 2026-03-04】检查 report_id 是否已存在（提前创建的情况）
if hasattr(self, '_report_id') and self._report_id is not None:
    # report_id 已存在，直接使用
    api_logger.info(
        f"[Orchestrator] 使用已存在的 report_id: {self.execution_id}, "
        f"report_id={self._report_id}"
    )
    report_id = self._report_id
else:
    # 创建报告记录（事务操作）
    report_id = tx.create_report(
        user_id=params['user_id'] or 'anonymous',
        config=config
    )
    # 存储 report_id 供后续阶段使用
    self._report_id = report_id
```

### Frontend Changes

#### 1. diagnosisService.js

**Location**: Line ~69

```javascript
// 记录当前任务
this.currentTask = {
  executionId: taskInfo.executionId || taskInfo.execution_id,
  reportId: taskInfo.reportId || taskInfo.report_id || null,
  startTime: Date.now(),
  config: config
};
```

**Changes**:
- Support both camelCase (`reportId`) and snake_case (`report_id`) for backward compatibility
- Default to `null` if not available (graceful degradation)

#### 2. startDiagnosis/index.js (Cloud Function)

**Location**: Line ~212

```javascript
// 5. 返回结果给前端
const result = {
  success: true,
  execution_id: response.data.executionId || response.data.execution_id,
  report_id: response.data.reportId || response.data.report_id,
  message: response.data.message || '诊断任务已启动',
  elapsedTime: elapsed
};
```

**Changes**:
- Support both camelCase and snake_case field names
- Properly pass through `report_id` from backend

## New Flow

```
Timeline (Fixed):
1. API receives request
2. Generate execution_id
3. Create initial report record ← report_id available here
4. Start async thread ← API returns here (with report_id)
5. Async Phase 1: Init
6. Async Phase 2: AI fetching
7. Async Phase 3: Results saving ← Skip report creation (already exists)
```

## Benefits

1. **Frontend has report_id immediately** - Can use it for logging, tracking, or direct report queries
2. **No duplication** - Orchestrator skips report creation if already exists
3. **Backward compatible** - Supports both old and new field naming conventions
4. **Graceful degradation** - Works even if report creation fails (report_id will be null)

## API Response Format

### Before Fix
```json
{
  "status": "success",
  "executionId": "uuid-here",
  "message": "Test started successfully"
}
```

### After Fix
```json
{
  "status": "success",
  "executionId": "uuid-here",
  "reportId": 123,
  "message": "Test started successfully"
}
```

## Testing Checklist

- [ ] Backend creates initial report record successfully
- [ ] API response includes `reportId` (camelCase)
- [ ] Frontend receives and stores `reportId`
- [ ] Orchestrator skips duplicate report creation
- [ ] Diagnosis flow completes successfully
- [ ] Report can be queried using `reportId`
- [ ] Error handling works (report_id is null if creation fails)

## Files Modified

### Backend (3 files)
1. `backend_python/wechat_backend/views/diagnosis_views.py`
2. `backend_python/wechat_backend/views/diagnosis_views_v2.py`
3. `backend_python/wechat_backend/services/diagnosis_orchestrator.py`

### Frontend (2 files)
1. `miniprogram/services/diagnosisService.js`
2. `miniprogram/cloudfunctions/startDiagnosis/index.js`

## Notes

- Report creation failure is non-blocking (diagnosis continues even if it fails)
- The initial report record is minimal (just basic info, no results)
- Full report data is populated during Phase 3 (results saving)
- `execution_id` remains the primary identifier for polling
- `report_id` is useful for direct report queries and database lookups

---

**Fix Date**: 2026-03-04
**Status**: ✅ COMPLETE
**Verified**: Pending integration test
