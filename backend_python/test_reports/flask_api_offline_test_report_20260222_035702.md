# Flask API 离线集成测试报告

**测试执行时间**: 2026-02-22 03:57:02
**测试方式**: Flask 测试客户端（离线）
**测试套件数量**: 2
**测试用例总数**: 13
**通过数量**: 0
**通过率**: 0.0%

## 1. 服务层 API 离线测试
_使用 Flask 测试客户端测试 ReportDataService 功能_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 8 | 0 | 0 | 8 | 0 | 0.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 结果/错误 |
|----|------|------|-----------|-----------|
| SV-OFF-001 | ReportDataService 初始化 | 🔴 ERROR | 3313 | `无法初始化 ReportDataService...` |
| SV-OFF-002 | _get_base_data 有效 executionId | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| SV-OFF-003 | _get_base_data 数据完整性 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| SV-OFF-004 | _build_platform_scores 方法 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| SV-OFF-005 | _build_dimension_scores 方法 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| SV-OFF-006 | _get_or_generate_competitive_data 方法 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| SV-OFF-007 | _get_or_generate_negative_sources 方法 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| SV-OFF-008 | generate_full_report 方法 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |

## 2. 边界异常离线测试
_测试边界条件和异常情况处理_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 5 | 0 | 0 | 5 | 0 | 0.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 结果/错误 |
|----|------|------|-----------|-----------|
| BE-OFF-001 | 空 execution_id 处理 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| BE-OFF-002 | None execution_id 处理 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| BE-OFF-003 | 无效 execution_id 处理 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| BE-OFF-004 | 超长 execution_id 处理 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
| BE-OFF-005 | 特殊字符 execution_id 处理 | 🔴 ERROR | 0 | `无法初始化 ReportDataService...` |
