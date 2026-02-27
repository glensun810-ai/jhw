# 阶段一集成测试套件

> 系统重构 - 阶段一（基础能力加固）- P1-T9

## 概述

本测试套件用于验证阶段一所有功能的正确集成和协作，确保重构后的系统可以平稳上线。

## 测试覆盖

### 核心业务流程
- ✅ 完整诊断流程（成功/部分成功/失败）
- ✅ 状态机与各组件的集成
- ✅ 超时、重试、死信队列的协作
- ✅ 数据持久化与一致性验证

### 异常处理流程
- ✅ AI 平台不可用
- ✅ 部分 AI 平台失败
- ✅ 轮询过程网络中断
- ✅ 数据库错误处理
- ✅ 超时与重试失败

### 并发场景
- ✅ 并发诊断任务（10+ 并行）
- ✅ 并发状态轮询
- ✅ 数据库并发写入
- ✅ 资源竞争处理

### 数据一致性
- ✅ 前端 - 后端 - 数据库一致性
- ✅ 报告与原始结果一致性
- ✅ 存根报告数据一致性
- ✅ 跨服务数据一致性

## 文件结构

```
tests/integration/
├── __init__.py
├── conftest.py                          # 测试夹具和配置
├── test_diagnosis_flow.py               # 核心诊断流程测试
├── test_state_machine_integration.py    # 状态机集成测试
├── test_timeout_integration.py          # 超时机制集成测试
├── test_retry_integration.py            # 重试机制集成测试
├── test_dead_letter_integration.py      # 死信队列集成测试
├── test_data_persistence_integration.py # 数据持久化集成测试
├── test_report_stub_integration.py      # 报告存根集成测试
├── test_polling_integration.py          # 轮询机制集成测试
├── test_concurrent_scenarios.py         # 并发场景测试
├── test_error_scenarios.py              # 异常场景测试
├── test_data_consistency.py             # 数据一致性测试
└── fixtures/
    ├── __init__.py
    ├── diagnosis_fixtures.py            # 诊断测试数据
    ├── ai_response_fixtures.py          # AI 响应模拟数据
    └── db_fixtures.py                   # 数据库测试数据

scripts/
├── run_integration_tests.sh             # 运行集成测试脚本
└── cleanup_test_data.py                 # 清理测试数据脚本
```

## 快速开始

### 运行所有集成测试

```bash
# 进入项目根目录
cd /Users/sgl/PycharmProjects/PythonProject

# 运行所有集成测试（生成覆盖率报告和 HTML 报告）
./scripts/run_integration_tests.sh

# 或者使用 pytest 直接运行
pytest tests/integration/ -v --cov=wechat_backend.v2 --cov-report=html
```

### 运行单个测试文件

```bash
# 运行核心诊断流程测试
pytest tests/integration/test_diagnosis_flow.py -v

# 运行状态机集成测试
pytest tests/integration/test_state_machine_integration.py -v

# 运行超时机制集成测试
pytest tests/integration/test_timeout_integration.py -v
```

### 运行特定测试用例

```bash
# 运行成功场景测试
pytest tests/integration/test_diagnosis_flow.py::TestDiagnosisFlow::test_full_diagnosis_flow_success -v

# 运行并发场景测试
pytest tests/integration/test_concurrent_scenarios.py::TestConcurrentScenarios::test_concurrent_diagnosis_tasks -v
```

### 清理测试数据

```bash
# 预览将清理的内容
python scripts/cleanup_test_data.py --dry-run

# 清理测试数据
python scripts/cleanup_test_data.py

# 完全清理（包括主数据库中的测试数据）
python scripts/cleanup_test_data.py --all
```

## 测试报告

测试运行后，会生成以下报告：

### HTML 测试报告
```
test_reports/integration/report.html
```
包含所有测试用例的执行结果、错误详情、日志等。

### 覆盖率报告
```
test_reports/integration/coverage_all/index.html
```
包含代码覆盖率统计，按模块和文件分类。

### 覆盖率 XML
```
test_reports/integration/coverage.xml
```
用于 CI/CD 集成的覆盖率数据。

## 测试用例清单

### 核心诊断流程测试 (test_diagnosis_flow.py)
- ✅ test_full_diagnosis_flow_success - 完整诊断流程（成功）
- ✅ test_diagnosis_flow_with_partial_success - 部分成功场景
- ✅ test_diagnosis_flow_with_retry - 重试机制集成
- ✅ test_diagnosis_flow_with_all_failures - 全部失败场景
- ✅ test_diagnosis_flow_state_transitions - 状态流转测试
- ✅ test_diagnosis_flow_with_custom_questions - 自定义问题测试
- ✅ test_diagnosis_flow_with_multiple_brands - 多品牌测试
- ✅ test_diagnosis_flow_report_data_integrity - 报告数据完整性
- ✅ test_diagnosis_flow_api_call_logging - API 调用日志
- ✅ test_diagnosis_flow_timeout_handling - 超时处理

### 状态机集成测试 (test_state_machine_integration.py)
- ✅ test_state_transitions_with_timeout - 超时状态流转
- ✅ test_state_persistence_across_service_boundaries - 状态持久化
- ✅ test_state_machine_with_dead_letter_integration - 死信队列集成
- ✅ test_state_machine_illegal_transition - 非法状态流转
- ✅ test_state_machine_valid_transitions - 合法状态流转
- ✅ test_state_machine_partial_success - 部分成功状态
- ✅ test_state_machine_progress_update - 进度更新
- ✅ test_state_machine_metadata_persistence - 元数据持久化

### 超时机制集成测试 (test_timeout_integration.py)
- ✅ test_timeout_triggers_state_change - 超时触发状态变更
- ✅ test_multiple_concurrent_timeouts - 多并发超时
- ✅ test_timeout_cancelled_on_completion - 完成时取消超时
- ✅ test_timeout_with_retry_integration - 超时与重试集成
- ✅ test_timeout_configuration - 超时配置
- ✅ test_timeout_error_handling - 超时错误处理

### 重试机制集成测试 (test_retry_integration.py)
- ✅ test_exponential_backoff_retry - 指数退避重试
- ✅ test_max_retry_limit - 最大重试次数限制
- ✅ test_retryable_vs_non_retryable_errors - 可重试与不可重试错误
- ✅ test_retry_with_dead_letter_queue - 重试与死信队列集成
- ✅ test_retry_success_after_failures - 重试后成功

### 死信队列集成测试 (test_dead_letter_integration.py)
- ✅ test_failed_task_added_to_dead_letter - 失败任务入队
- ✅ test_dead_letter_processing - 死信队列处理
- ✅ test_retry_recovery - 重试后恢复
- ✅ test_priority_handling - 优先级处理
- ✅ test_dead_letter_cleanup - 死信队列清理

### 数据持久化集成测试 (test_data_persistence_integration.py)
- ✅ test_api_call_log_persistence - API 调用日志持久化
- ✅ test_raw_data_persistence - 原始数据持久化
- ✅ test_report_snapshot_persistence - 报告快照持久化
- ✅ test_data_recovery - 数据恢复
- ✅ test_data_versioning - 数据版本控制
- ✅ test_data_integrity_check - 数据完整性检查
- ✅ test_data_cleanup - 数据清理

### 报告存根集成测试 (test_report_stub_integration.py)
- ✅ test_stub_report_on_failure - 失败时返回存根报告
- ✅ test_stub_report_partial_success - 部分成功时返回部分数据
- ✅ test_stub_report_data_integrity - 存根报告数据完整性
- ✅ test_stub_report_availability - 存根报告可用性
- ✅ test_stub_report_error_message - 存根报告错误信息
- ✅ test_stub_report_metadata - 存根报告元数据

### 轮询机制集成测试 (test_polling_integration.py)
- ✅ test_polling_stops_on_completion - 完成时停止轮询
- ✅ test_polling_termination_conditions - 轮询终止条件
- ✅ test_polling_timeout_handling - 轮询超时处理
- ✅ test_polling_recovery_mechanism - 轮询恢复机制
- ✅ test_polling_with_network_interruption - 网络中断轮询

### 并发场景测试 (test_concurrent_scenarios.py)
- ✅ test_concurrent_diagnosis_tasks - 并发诊断任务
- ✅ test_concurrent_status_polling - 并发状态轮询
- ✅ test_database_concurrent_writes - 数据库并发写入
- ✅ test_resource_contention_handling - 资源竞争处理
- ✅ test_concurrent_timeout_management - 并发超时管理
- ✅ test_concurrent_dead_letter_handling - 并发死信处理

### 异常场景测试 (test_error_scenarios.py)
- ✅ test_ai_platform_unavailable - AI 平台不可用
- ✅ test_partial_ai_platform_failure - 部分 AI 平台失败
- ✅ test_network_interruption_during_polling - 轮询过程网络中断
- ✅ test_database_error_handling - 数据库错误处理
- ✅ test_timeout_and_retry_failure - 超时与重试失败
- ✅ test_cascading_failures - 级联失败

### 数据一致性测试 (test_data_consistency.py)
- ✅ test_frontend_backend_database_consistency - 前端 - 后端 - 数据库一致性
- ✅ test_report_results_consistency - 报告与原始结果一致性
- ✅ test_stub_report_data_consistency - 存根报告数据一致性
- ✅ test_cross_service_data_consistency - 跨服务数据一致性
- ✅ test_data_synchronization - 数据同步

## 覆盖率要求

| 模块 | 集成测试覆盖率要求 |
|------|------------------|
| 核心诊断流程 | > 90% |
| 状态机集成 | > 85% |
| 超时机制 | > 85% |
| 重试机制 | > 85% |
| 死信队列 | > 80% |
| 数据持久化 | > 85% |
| 报告存根 | > 85% |
| 轮询机制 | > 80% |
| 并发场景 | > 75% |
| 异常场景 | > 80% |

**总体要求：关键路径覆盖率 > 80%**

## 测试通过标准

- ✅ 所有测试用例通过
- ✅ 无 P0/P1 级别的缺陷
- ✅ 性能测试在可接受范围内
- ✅ 数据一致性验证通过
- ✅ 关键路径覆盖率 > 80%
- ✅ 测试数据可自动清理
- ✅ 测试可重复运行

## 夹具（Fixtures）使用

### 诊断配置夹具

```python
def test_with_standard_config(standard_diagnosis_config):
    """使用标准诊断配置"""
    assert len(standard_diagnosis_config['brand_list']) == 2
    assert len(standard_diagnosis_config['selectedModels']) == 3

def test_with_custom_config(custom_question_config):
    """使用自定义问题配置"""
    assert '自定义' in custom_question_config['custom_question']
```

### AI 适配器夹具

```python
async def test_with_mock_ai(mock_ai_adapter):
    """使用模拟 AI 适配器（总是成功）"""
    response = await mock_ai_adapter.send_prompt('品牌', '问题', 'deepseek')
    assert 'content' in response

async def test_with_failing_ai(failing_ai_adapter):
    """使用总是失败的 AI 适配器"""
    with pytest.raises(Exception):
        await failing_ai_adapter.send_prompt('品牌', '问题', 'deepseek')

async def test_with_flaky_ai(flaky_ai_adapter):
    """使用偶尔失败的 AI 适配器"""
    # 30% 失败率
    pass
```

### 数据库夹具

```python
def test_with_completed_db(populated_db_completed):
    """使用已完成诊断的数据库"""
    exec_id = populated_db_completed['execution_id']
    report_id = populated_db_completed['report_id']

def test_with_failed_db(populated_db_failed):
    """使用失败诊断的数据库"""
    pass

def test_with_partial_db(populated_db_partial):
    """使用部分成功诊断的数据库"""
    success_count = populated_db_partial['success_count']
```

## 最佳实践

### 1. 测试独立性

每个测试用例必须独立，不依赖其他测试的结果：

```python
@pytest.fixture(autouse=True)
def clean_db(db_connection):
    """每个测试后清理数据"""
    yield
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM diagnosis_reports")
    # ... 清理其他表
    db_connection.commit()
```

### 2. 异步测试

正确使用 pytest-asyncio 处理异步代码：

```python
@pytest.mark.asyncio
async def test_async_function():
    """异步测试"""
    await asyncio.sleep(1)
    # ...
```

### 3. 模拟外部依赖

集成测试应尽量使用真实组件，只模拟外部依赖（如 AI 平台）：

```python
class MockAIAdapter:
    """模拟 AI 适配器"""
    async def send_prompt(self, brand, question, model):
        # 模拟成功响应
        return {'content': '模拟响应', 'model': model}
```

### 4. 数据清理

每个测试后必须清理数据，避免影响其他测试：

```bash
# 测试后运行清理
python scripts/cleanup_test_data.py
```

### 5. 错误信息

断言失败时提供清晰的错误信息：

```python
assert status['status'] == 'completed', \
    f"期望状态为 completed，实际为 {status['status']}"
```

## 故障排查

### 测试失败

1. 查看 HTML 测试报告：
   ```bash
   open test_reports/integration/report.html
   ```

2. 查看详细错误信息：
   ```bash
   pytest tests/integration/test_file.py -v --tb=long
   ```

### 覆盖率不足

1. 查看覆盖率报告：
   ```bash
   open test_reports/integration/coverage_all/index.html
   ```

2. 识别未覆盖的代码路径
3. 添加针对性的测试用例

### 测试耗时过长

1. 使用 `-x` 参数在首次失败时停止：
   ```bash
   pytest tests/integration/ -x
   ```

2. 使用 `-k` 参数运行特定测试：
   ```bash
   pytest tests/integration/ -k "test_timeout"
   ```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-html
      
      - name: Run integration tests
        run: |
          ./scripts/run_integration_tests.sh
      
      - name: Upload test report
        uses: actions/upload-artifact@v2
        with:
          name: test-report
          path: test_reports/integration/
```

## 相关文档

- [重构基线](../../../2026-02-27-重构基线.md) - 第 4.2 节 - 性能与可靠性测试
- [实施路线图](../../../2026-02-27-重构实施路线图.md) - P1-T9 详细设计
- [开发规范](../../../2026-02-27-重构开发规范.md) - 第 4 章 - 测试规范

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2026-02-27 | 初始版本，包含所有阶段一集成测试 |

## 联系

如有问题，请联系系统架构组。
