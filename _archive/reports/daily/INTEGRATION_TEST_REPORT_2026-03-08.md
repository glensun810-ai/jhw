# Integration Test Report

**Test Execution Date:** 2026-03-08  
**Python Version:** 3.14.3  
**pytest Version:** 9.0.2  
**Platform:** darwin

---

## Executive Summary

| Test Suite | Passed | Failed | Errors | Skipped | Total | Pass Rate |
|------------|--------|--------|--------|---------|-------|-----------|
| Integration Tests | 55 | 85 | 15 | 0 | 155 | 35.5% |
| E2E Tests | 4 | 1 | 5 | 0 | 10 | 40.0% |
| Backend Tests | Partial (timeout) | - | - | - | 326+ | - |

**Overall Status:** ⚠️ **PARTIAL FAILURE** - Multiple critical issues detected

---

## 1. Integration Tests (`tests/integration/`)

### 1.1 Summary

- **Total:** 155 tests
- **Passed:** 55 (35.5%)
- **Failed:** 85 (54.8%)
- **Errors:** 15 (9.7%)

### 1.2 Test File Breakdown

| Test File | Status | Issues |
|-----------|--------|--------|
| `test_ai_adapters_integration.py` | ❌ 22 failed | Database index name validation errors, LogRecord KeyError |
| `test_concurrent_scenarios.py` | ❌ 3 failed, 1 error | DiagnosisService API changes, async fixture issues |
| `test_data_consistency.py` | ❌ 1 failed, 5 errors | DiagnosisService API changes, async fixture issues |
| `test_data_persistence_integration.py` | ❌ 5 failed, 2 errors | DiagnosisService API changes, database index errors |
| `test_dead_letter_api.py` | ❌ 6 failed, 6 errors | Flask `as_tuple` parameter removed in Werkzeug 3.0 |
| `test_dead_letter_integration.py` | ❌ 6 failed, 1 passed | DeadLetterQueue API signature changes |
| `test_diagnosis_flow.py` | ❌ 9 failed, 1 error | DiagnosisService API changes |
| `test_error_scenarios.py` | ❌ 6 failed | DiagnosisService API changes |
| `test_polling_integration.py` | ❌ 5 failed | DiagnosisService API changes |
| `test_region_consistency_integration.py` | ✅ 28 passed | All tests passing |
| `test_report_stub_flow.py` | ✅ 18 passed | All tests passing |
| `test_report_stub_integration.py` | ❌ 5 failed, 1 error | DiagnosisService API changes |
| `test_retry_integration.py` | ❌ 6 failed | RetryPolicy API changes |
| `test_state_machine_integration.py` | ❌ 8 failed | DiagnosisStateMachine API changes |
| `test_timeout_integration.py` | ❌ 2 failed, 4 passed | RetryPolicy API changes |

### 1.3 Root Cause Analysis

#### Issue 1: Database Index Name Validation Error
**Error Message:** `ValueError: 不允许的索引名称：idx_api_logs_execution`

**Affected Components:**
- `APICallLogRepository`
- `DiagnosisResultRepository`

**Root Cause:** The database repository initialization is validating index names with Chinese characters in the error message, but the validation logic is rejecting valid index names.

**Files to Fix:**
- `backend_python/wechat_backend/v2/repositories/api_call_log_repository.py` (line 211)
- `backend_python/wechat_backend/v2/repositories/diagnosis_result_repository.py` (line 202)

---

#### Issue 2: DiagnosisService API Signature Changes
**Error Message:** `TypeError: DiagnosisService.__init__() got an unexpected keyword argument 'db_path'`

**Affected Tests:** 40+ tests across multiple test files

**Root Cause:** The `DiagnosisService` class constructor signature has changed and no longer accepts `db_path` as a keyword argument.

**Files to Fix:**
- Test files need to be updated to use the new API
- OR `DiagnosisService` needs to restore backward compatibility

---

#### Issue 3: Flask/Werkzeug Compatibility Issue
**Error Message:** `TypeError: EnvironBuilder.__init__() got an unexpected keyword argument 'as_tuple'`

**Affected Components:**
- `test_dead_letter_api.py` - Flask test client usage

**Root Cause:** The `as_tuple` parameter was removed in Werkzeug 3.0. The Flask test client code needs to be updated.

---

#### Issue 4: DeadLetterQueue API Changes
**Error Messages:**
- `TypeError: DeadLetterQueue.list_dead_letters() got an unexpected keyword argument 'execution_id'`
- `AttributeError: 'DeadLetterQueue' object has no attribute 'mark_for_retry'`

**Root Cause:** API signature changes in the `DeadLetterQueue` class.

---

#### Issue 5: RetryPolicy API Changes
**Error Message:** `TypeError: RetryPolicy.__init__() got an unexpected keyword argument 'use_jitter'`

**Root Cause:** The `RetryPolicy` constructor no longer accepts `use_jitter` or `timeout` parameters.

---

#### Issue 6: Logging KeyError
**Error Message:** `KeyError: "Attempt to overwrite 'module' in LogRecord"`

**Affected Components:**
- `AIAdapterFactory`

**Root Cause:** The logging code is trying to set `module` as an extra field, but this conflicts with the standard LogRecord attributes in Python 3.14.

---

## 2. E2E Tests (`tests/e2e/`)

### 2.1 Summary

- **Total:** 10 tests
- **Passed:** 4 (40.0%)
- **Failed:** 1 (10.0%)
- **Errors:** 5 (50.0%)

### 2.2 Test Results

| Test Name | Status | Issue |
|-----------|--------|-------|
| `test_01_start_diagnosis` | ❌ Failed | API expects `selectedModels` but test sends `selected_models` |
| `test_02_wait_completion` | ❌ Error | Depends on failed setup |
| `test_03_verify_database` | ❌ Error | Depends on failed setup |
| `test_04_verify_report_api` | ❌ Error | Depends on failed setup |
| `test_05_verify_field_validation` | ❌ Error | Depends on failed setup |
| `test_full_flow` | ❌ Error | Depends on failed setup |
| `test_validate_valid_result` | ✅ Passed | - |
| `test_validate_missing_brand` | ✅ Passed | - |
| `test_validate_empty_brand` | ✅ Passed | - |
| `test_validate_batch` | ✅ Passed | - |

### 2.3 Root Cause Analysis

**Issue:** API Contract Mismatch
- **Error:** `Missing selectedModels in request data`
- **Root Cause:** The E2E test is using snake_case (`selected_models`) but the API expects camelCase (`selectedModels`)

---

## 3. Backend Tests (`backend_python/tests/`)

### 3.1 Collection Errors

2 test files failed to import:
- `tests/test_diagnosis_orchestrator.py` - Cannot import `DiagnosisErrorCode`
- `tests/unit/test_phase_result.py` - Cannot import `DiagnosisErrorCode`

### 3.2 Partial Results (before timeout)

Notable failures:
- `TestReportSnapshotRepository::test_save_and_get_snapshot` - Failed
- `TestPerformance::test_concurrent_execution` - Failed
- `TestConfigManager::test_load_config` - Failed
- Multiple config-related tests failing

---

## 4. Test Files with Collection Errors

The following test files could not be collected due to import errors:

1. `tests/integration/test_cleaning_pipeline_integration.py`
   - **Error:** `TypeError: non-default argument 'brand' follows default argument 'result_id'`
   - **Location:** `backend_python/wechat_backend/v2/cleaning/models/cleaned_data.py:47`

2. `tests/integration/test_error_handling.py`
   - **Error:** `ImportError: cannot import name 'ErrorCodeDefinition'`

---

## 5. Passing Test Suites ✅

The following test suites are fully passing:

1. **Region Consistency Integration** (`test_region_consistency_integration.py`) - 28/28 passed
2. **Report Stub Flow** (`test_report_stub_flow.py`) - 18/18 passed
3. **Validator Unit Tests** (in E2E) - 4/4 passed
4. **API Contract Tests** (partial) - 21/26 passed
5. **Brand Diagnosis System** (partial) - 20/22 passed
6. **Config Center** (partial) - 14/18 passed
7. **Data Aggregation** - 5/5 passed
8. **E2E Connectivity** - 6/6 passed

---

## 6. Critical Issues Summary

| Priority | Issue | Impact | Tests Affected |
|----------|-------|--------|----------------|
| P0 | Database index validation error | Blocks adapter initialization | 20+ |
| P0 | DiagnosisService API changes | Blocks most integration tests | 40+ |
| P1 | Flask/Werkzeug compatibility | Blocks dead letter API tests | 12 |
| P1 | DeadLetterQueue API changes | Blocks dead letter integration | 7 |
| P1 | RetryPolicy API changes | Blocks retry integration tests | 6 |
| P2 | Logging KeyError | Blocks AI adapter factory tests | 6 |
| P2 | E2E API contract mismatch | Blocks full E2E flow | 6 |
| P3 | Dataclass field ordering | Blocks cleaning pipeline tests | 2 |

---

## 7. Recommendations

### Immediate Actions (P0)

1. **Fix Database Index Validation**
   - Review and fix the index name validation logic in repository classes
   - Ensure valid index names are not rejected

2. **Fix DiagnosisService API**
   - Either restore `db_path` parameter backward compatibility
   - Or update all affected tests to use the new API

### Short-term Actions (P1)

3. **Update Flask Test Client**
   - Remove `as_tuple` parameter from Flask test client calls
   - Update to Werkzeug 3.0 compatible API

4. **Fix DeadLetterQueue API**
   - Update tests to match current API signatures
   - Add `mark_for_retry` method if needed

5. **Fix RetryPolicy API**
   - Update tests to use current parameter names
   - Add `use_jitter` and `timeout` parameters if needed

### Medium-term Actions (P2)

6. **Fix Logging Code**
   - Don't use reserved LogRecord attribute names as extras
   - Use alternative field names like `test_module` instead of `module`

7. **Fix E2E Test API Contract**
   - Update test to use camelCase (`selectedModels`)
   - Or add snake_case support to the API

### Long-term Actions (P3)

8. **Fix Dataclass Field Ordering**
   - Move fields with defaults after fields without defaults
   - Consider using `kw_only=True` for Python 3.10+

---

## 8. Test Output Files

The following log files were generated:

- `integration_test_output.log` - Full integration test output
- `e2e_test_output.log` - Full E2E test output
- `backend_integration_test_output.log` - Backend tests output

---

**Report Generated:** 2026-03-08  
**Next Steps:** Address P0 issues first, then proceed with P1 and P2 fixes.
