# Circuit Breaker Fix: Global Termination Flag Reset Mechanism

**Date:** 2026-03-05  
**Priority:** P0 - Critical Fix  
**Status:** ✅ Completed

## Problem Summary

The global termination flag (`global.isTerminated`) was being set to `true` when a diagnosis task completed or failed, but there was **no mechanism to reset it**. This caused the following issues:

1. **Subsequent tasks blocked**: After one task terminated, all future diagnosis tasks were blocked
2. **Permanent circuit breaker state**: The flag remained `true` indefinitely
3. **User impact**: Users could not run new diagnoses after completing/failing one

## Root Cause Analysis

### Code Flow Before Fix

```javascript
// Task completion (3 locations in brandTestService.js)
global.isTerminated = true;  // ✅ Set on complete/failure

// Task start check
if (global.isTerminated) {
  return;  // ❌ Blocks all new tasks forever
}
```

### Missing Reset Mechanism

- No reset on new task start
- No manual reset function exposed
- Flag initialized implicitly, not explicitly

## Solution Implemented

### 1. Explicit Initialization

```javascript
// 【P0 关键修复 - 2026-03-05】全局终止标志，防止多个 onComplete 调用
global.isTerminated = false;
```

**Location:** Line 37 in `services/brandTestService.js`

### 2. Auto-Reset on Task Start

```javascript
const startDiagnosis = async (inputData, onProgress, onComplete, onError) => {
  // Check if diagnosis is already in progress
  if (isDiagnosing) {
    console.warn('[startDiagnosis] ⚠️ 诊断已在进行中，跳过重复启动');
    throw new Error('诊断任务已在执行中，请勿重复点击');
  }

  // ✅ NEW: Reset termination flag to allow new task
  global.isTerminated = false;

  isDiagnosing = true;
  // ... rest of task start logic
};
```

**Location:** Lines 200-209 in `services/brandTestService.js`

### 3. Manual Reset Function

```javascript
module.exports = {
  // ... existing exports
  resetTerminationFlag: () => {
    global.isTerminated = false;
    isDiagnosing = false;
    pollingInstance = null;
    console.log('[brandTestService] ✅ 全局终止标志已重置');
  }
};
```

**Location:** Lines 1060-1066 in `services/brandTestService.js`

## Changes Made

| File | Line(s) | Change Type | Description |
|------|---------|-------------|-------------|
| `services/brandTestService.js` | 37 | Addition | Explicit initialization of `global.isTerminated` |
| `services/brandTestService.js` | 207 | Addition | Auto-reset flag at task start |
| `services/brandTestService.js` | 1060-1066 | Addition | Exported manual reset function |

## Usage

### Automatic Reset (Recommended)

The flag is automatically reset when starting a new diagnosis:

```javascript
const { startDiagnosis } = require('../services/brandTestService');

// This will automatically reset the termination flag
await startDiagnosis(inputData, onProgress, onComplete, onError);
```

### Manual Reset (Emergency Use)

If needed, you can manually reset the flag:

```javascript
const { resetTerminationFlag } = require('../services/brandTestService');

// Reset all state (use with caution)
resetTerminationFlag();
```

## State Machine

### Before Fix

```
Task Start → Check isTerminated → (if true) BLOCK FOREVER ❌
                        ↓
                   (if false) Continue
                        ↓
Task Complete → Set isTerminated = true → END (permanent) ❌
```

### After Fix

```
Task Start → Reset isTerminated = false → Continue ✅
                                        ↓
Task Complete → Set isTerminated = true → END
                                        ↓
Next Task Start → Reset isTerminated = false → Continue ✅
```

## Testing Recommendations

1. **Normal Flow Test**
   - Run a diagnosis task to completion
   - Immediately start a new diagnosis task
   - Verify the second task starts successfully

2. **Failure Flow Test**
   - Run a diagnosis task that fails
   - Immediately start a new diagnosis task
   - Verify the second task starts successfully

3. **Manual Reset Test**
   - Run a diagnosis task to completion
   - Call `resetTerminationFlag()` manually
   - Verify the flag is reset in console logs

4. **Concurrent Protection Test**
   - Try to start two diagnosis tasks simultaneously
   - Verify the `isDiagnosing` flag prevents duplicate starts

## Related Fixes

This fix complements other P0 circuit breaker fixes:

- **Global Termination Check** (Line 352): Prevents multiple polling instances
- **Singleton Pattern** (Line 33): Ensures only one polling controller
- **Diagnosis In-Progress Flag** (Line 35): Prevents duplicate task starts
- **onComplete Circuit Breaker** (Lines 676, 721, 743): Sets termination flag

## Impact Assessment

| Metric | Before | After |
|--------|--------|-------|
| Tasks after completion | ❌ Blocked | ✅ Allowed |
| Tasks after failure | ❌ Blocked | ✅ Allowed |
| Manual reset capability | ❌ None | ✅ Available |
| State cleanup | ❌ Manual code edit | ✅ Automatic/Function |

## Conclusion

The circuit breaker reset mechanism ensures that:
1. ✅ Users can run multiple diagnosis tasks sequentially
2. ✅ The system recovers automatically from terminal states
3. ✅ Manual override is available for debugging/emergencies
4. ✅ Protection against concurrent tasks is maintained

**Status:** ✅ Fix completed and ready for testing
