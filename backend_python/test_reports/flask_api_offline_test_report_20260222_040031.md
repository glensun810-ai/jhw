# Flask API 离线集成测试报告

**测试执行时间**: 2026-02-22 04:00:31
**测试方式**: Flask 测试客户端（离线）
**测试套件数量**: 2
**测试用例总数**: 13
**通过数量**: 12
**通过率**: 92.3%

## 1. 服务层 API 离线测试
_使用 Flask 测试客户端测试 ReportDataService 功能_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 8 | 7 | 1 | 0 | 0 | 87.5% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 结果/错误 |
|----|------|------|-----------|-----------|
| SV-OFF-001 | ReportDataService 初始化 | ✅ PASS | 63 | 服务实例创建成功 |
| SV-OFF-002 | _get_base_data 有效 executionId | ✅ PASS | 7 | 品牌：华为, 分数：0 |
| SV-OFF-003 | _get_base_data 数据完整性 | ✅ PASS | 0 | 包含所有必需字段：['brand_name', 'overall_score', 'platform_scores', 'dimension_scores'] |
| SV-OFF-004 | _build_platform_scores 方法 | ✅ PASS | 0 | 平台评分数量：6 |
| SV-OFF-005 | _build_dimension_scores 方法 | ✅ PASS | 0 | 包含所有维度：['authority', 'visibility', 'purity', 'consistency'] |
| SV-OFF-006 | _get_or_generate_competitive_data 方法 | ✅ PASS | 2 | 竞品数量：3 |
| SV-OFF-007 | _get_or_generate_negative_sources 方法 | ✅ PASS | 0 | 负面信源数量：3 |
| SV-OFF-008 | generate_full_report 方法 | ❌ FAIL | 6 | `no such column: created_at...` |

## 2. 边界异常离线测试
_测试边界条件和异常情况处理_

| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 5 | 5 | 0 | 0 | 0 | 100.0% |

### 测试用例详情

| ID | 名称 | 状态 | 耗时 (ms) | 结果/错误 |
|----|------|------|-----------|-----------|
| BE-OFF-001 | 空 execution_id 处理 | ✅ PASS | 0 | 返回类型：dict |
| BE-OFF-002 | None execution_id 处理 | ✅ PASS | 0 | 返回类型：dict |
| BE-OFF-003 | 无效 execution_id 处理 | ✅ PASS | 0 | 返回类型：dict |
| BE-OFF-004 | 超长 execution_id 处理 | ✅ PASS | 0 | 返回类型：dict |
| BE-OFF-005 | 特殊字符 execution_id 处理 | ✅ PASS | 0 | 返回类型：dict |
