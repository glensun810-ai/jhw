# 品牌洞察报告功能全面测试报告

**测试执行时间**: 2026-02-22 03:44:40
**测试套件数量**: 5
**测试用例总数**: 39
**通过数量**: 22
**通过率**: 56.4%

## 1. 数据库验证测试
_验证数据库表结构、索引、数据完整性_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 10 | 10 | 0 | 0 | 0 | 100.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 错误信息 |
|----|------|------|-----------|----------|
| DB-001 | test_records 表存在性 | ✅ PASS | 0 | - |
| DB-002 | competitive_analysis 表存在性 | ✅ PASS | 0 | - |
| DB-003 | negative_sources 表存在性 | ✅ PASS | 0 | - |
| DB-004 | report_metadata 表存在性 | ✅ PASS | 0 | - |
| DB-005 | deep_intelligence_results 表存在性 | ✅ PASS | 0 | - |
| DB-006 | test_records 表结构验证 | ✅ PASS | 0 | - |
| DB-007 | test_records 索引验证 | ✅ PASS | 0 | - |
| DB-008 | test_records 数据存在性 | ✅ PASS | 0 | - |
| DB-009 | test_results 视图存在性 | ✅ PASS | 0 | - |
| DB-010 | results_summary 数据完整性 | ✅ PASS | 0 | - |

## 2. 数据访问层单元测试
_测试数据查询、解压、解析逻辑_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 8 | 8 | 0 | 0 | 0 | 100.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 错误信息 |
|----|------|------|-----------|----------|
| DA-001 | test_records 基础查询 | ✅ PASS | 0 | - |
| DA-002 | results_summary 解压测试 | ✅ PASS | 0 | - |
| DA-003 | detailed_results 解压测试 | ✅ PASS | 0 | - |
| DA-004 | execution_id 提取测试 | ✅ PASS | 0 | - |
| DA-005 | competitor_brands 提取测试 | ✅ PASS | 0 | - |
| DA-006 | 压缩标志处理测试 | ✅ PASS | 0 | - |
| DA-007 | JSON 解析错误处理 | ✅ PASS | 0 | - |
| DA-008 | gzip 解压错误处理 | ✅ PASS | 0 | - |

## 3. 服务层集成测试
_测试 ReportDataService 等服务的集成功能_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 8 | 0 | 0 | 1 | 7 | 0.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 错误信息 |
|----|------|------|-----------|----------|
| SV-001 | ReportDataService 初始化 | ⚠️  SKIP | 0 | - |
| SV-002 | _get_base_data 方法存在性 | 🔴 ERROR | 0 | `初始化异常：KeyError: 'wechat_backend'...` |
| SV-003 | _get_base_data 返回结构 | ⚠️  SKIP | 0 | - |
| SV-004 | _build_platform_scores 方法 | ⚠️  SKIP | 0 | - |
| SV-005 | _build_dimension_scores 方法 | ⚠️  SKIP | 0 | - |
| SV-006 | _get_or_generate_competitive_data 方法 | ⚠️  SKIP | 0 | - |
| SV-007 | _get_or_generate_negative_sources 方法 | ⚠️  SKIP | 0 | - |
| SV-008 | generate_full_report 方法 | ⚠️  SKIP | 0 | - |

## 4. API 端点测试
_测试报告相关的 API 端点_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 5 | 4 | 1 | 0 | 0 | 80.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 错误信息 |
|----|------|------|-----------|----------|
| API-001 | GET /api/export/report-data 端点存在性 | ✅ PASS | 0 | - |
| API-002 | GET /api/export/report-data 缺少 executionId | ✅ PASS | 0 | - |
| API-003 | GET /api/export/pdf 端点存在性 | ✅ PASS | 0 | - |
| API-004 | GET /api/export/html 端点存在性 | ✅ PASS | 0 | - |
| API-005 | 无效 executionId 处理 | ❌ FAIL | 0 | - |

## 5. 边界和异常测试
_测试边界条件和异常情况处理_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 8 | 0 | 3 | 0 | 5 | 0.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 错误信息 |
|----|------|------|-----------|----------|
| BE-001 | 空 execution_id 处理 | ❌ FAIL | 0 | `处理异常：KeyError: 'wechat_backend'...` |
| BE-002 | None execution_id 处理 | ❌ FAIL | 0 | `处理异常：KeyError: 'wechat_backend'...` |
| BE-003 | 超长 execution_id 处理 | ❌ FAIL | 0 | `处理异常：KeyError: 'wechat_backend'...` |
| BE-004 | 空数据库处理 | ⚠️  SKIP | 0 | - |
| BE-005 | 损坏的 gzip 数据处理 | ⚠️  SKIP | 0 | - |
| BE-006 | 损坏的 JSON 数据处理 | ⚠️  SKIP | 0 | - |
| BE-007 | 缺失字段处理 | ⚠️  SKIP | 0 | - |
| BE-008 | 并发访问处理 | ⚠️  SKIP | 0 | - |
