# 状态机快速参考卡

**版本**: 1.0.0  
**最后更新**: 2026-02-27

---

## 状态定义

```python
from wechat_backend.v2.state_machine import DiagnosisState

# 7 个状态
DiagnosisState.INITIALIZING      # 初始化中
DiagnosisState.AI_FETCHING       # AI 收集中
DiagnosisState.ANALYZING         # 分析中
DiagnosisState.COMPLETED         # 已完成
DiagnosisState.PARTIAL_SUCCESS   # 部分成功
DiagnosisState.FAILED            # 失败
DiagnosisState.TIMEOUT           # 超时
```

---

## 状态流转图

```
INITIALIZING ─┬─ succeed ─→ AI_FETCHING ─┬─ all_complete ──┐
              │                          │                 │
              └─ fail ─→ FAILED          │                 ↓
                                         ├─ partial_complete ─→ ANALYZING
                                         │                      │
                                         ├─ all_fail ─→ FAILED │
                                         │                      ├─ succeed ─→ COMPLETED
                                         └─ timeout ─→ TIMEOUT  │
                                                                ├─ partial_succeed ─→ PARTIAL_SUCCESS
                                                                │
                                                                └─ fail ─→ FAILED
```

---

## 基本使用

```python
from wechat_backend.v2.state_machine import DiagnosisStateMachine
from wechat_backend.v2.repositories import DiagnosisRepository

# 1. 创建状态机
repo = DiagnosisRepository()
sm = DiagnosisStateMachine(
    execution_id='exec-123',
    repository=repo,
)

# 2. 状态流转
sm.transition('succeed', progress=10)

# 3. 查询状态
state = sm.get_current_state()
progress = sm.get_progress()
should_stop = sm.should_stop_polling()
```

---

## 流转事件

| 事件 | 说明 | 典型场景 |
|------|------|---------|
| `succeed` | 成功 | 初始化完成、分析完成 |
| `fail` | 失败 | 初始化失败、分析失败 |
| `all_complete` | 全部完成 | 所有 AI 调用成功 |
| `partial_complete` | 部分完成 | 部分 AI 调用成功 |
| `all_fail` | 全部失败 | 所有 AI 调用失败 |
| `timeout` | 超时 | 执行超时 |
| `partial_succeed` | 部分成功 | 部分分析完成 |

---

## API 参考

### DiagnosisStateMachine

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | `execution_id: str`, `repository: Optional` | - | 初始化 |
| `transition` | `event: str`, `progress: Optional[int]`, `**kwargs` | `bool` | 状态流转 |
| `update_progress` | `progress: int` | `None` | 更新进度 |
| `persist_state` | - | `None` | 持久化 |
| `get_current_state` | - | `DiagnosisState` | 获取状态 |
| `get_progress` | - | `int` | 获取进度 |
| `should_stop_polling` | - | `bool` | 是否停止轮询 |
| `is_terminal_state` | - | `bool` | 是否终态 |
| `reset` | - | `None` | 重置状态 |
| `to_dict` | - | `dict` | 转为字典 |

### DiagnosisRepository

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `update_state` | `execution_id`, `status`, `stage`, `progress`, `is_completed`, `should_stop_polling`, `metadata` | `bool` | 更新状态 |
| `get_state` | `execution_id` | `Optional[dict]` | 获取状态 |
| `create_report` | `execution_id`, `user_id`, `brand_name`, `config` | `int` | 创建报告 |

---

## 特性开关

```python
from wechat_backend.v2.feature_flags import (
    enable_feature,
    disable_feature,
    is_feature_enabled,
    should_use_v2,
)

# 启用状态机
enable_feature('diagnosis_v2_state_machine')

# 禁用状态机
disable_feature('diagnosis_v2_state_machine')

# 检查是否启用
if is_feature_enabled('diagnosis_v2_state_machine'):
    # 使用 v2

# 判断用户是否使用 v2
if should_use_v2(user_id):
    # 使用 v2
```

---

## 异常处理

```python
from wechat_backend.v2.exceptions import (
    DiagnosisError,
    DiagnosisTimeoutError,
    DiagnosisValidationError,
    DiagnosisStateError,
    AIPlatformError,
    DataPersistenceError,
    DatabaseError,
)

try:
    sm.transition('succeed', progress=10)
except DiagnosisValidationError as e:
    # 参数验证失败
    logger.error(f"验证失败：{e.message}")
except DatabaseError as e:
    # 数据库错误
    logger.error(f"数据库错误：{e.message}")
except DiagnosisError as e:
    # 其他诊断错误
    logger.error(f"诊断错误：{e.message}")
```

---

## 日志格式

```python
# 状态流转日志
{
    'event': 'state_machine_transitioned',
    'execution_id': 'exec-123',
    'old_state': 'initializing',
    'new_state': 'ai_fetching',
    'event': 'succeed',
    'progress': 10,
    'is_terminal': False,
}

# 持久化日志
{
    'event': 'state_machine_persisted',
    'execution_id': 'exec-123',
    'status': 'ai_fetching',
    'progress': 10,
    'is_completed': False,
    'should_stop_polling': False,
}
```

---

## 测试示例

```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def state_machine():
    repo = Mock()
    repo.update_state = Mock(return_value=True)
    return DiagnosisStateMachine(
        execution_id='test-123',
        repository=repo,
    )

def test_transition(state_machine):
    result = state_machine.transition('succeed', progress=10)
    assert result is True
    assert state_machine.get_current_state() == DiagnosisState.AI_FETCHING
    assert state_machine.get_progress() == 10
```

---

## 常见问题

### Q: 如何回滚到旧版本？

A: 关闭特性开关即可：
```python
disable_feature('diagnosis_v2_state_machine')
```

### Q: 终态还能流转吗？

A: 不能。终态（COMPLETED, FAILED, TIMEOUT, PARTIAL_SUCCESS）不允许再流转。

### Q: 进度可以减少吗？

A: 技术上可以，但会记录警告日志。建议只增不减。

### Q: 没有 Repository 会怎样？

A: `persist_state()` 会记录警告日志，但不抛异常。

### Q: 如何添加新状态？

A: 
1. 在 `DiagnosisState` 枚举中添加
2. 在 `TRANSITIONS` 字典中添加流转规则
3. 更新相关测试

---

## 检查清单

提交前检查:
- [ ] 类型注解完整
- [ ] 异常处理正确
- [ ] 日志结构化
- [ ] 测试覆盖率 > 90%
- [ ] 特性开关已配置
- [ ] 文档已更新

---

**快速参考结束**

详细文档：
- 重构基线：`2026-02-27-重构基线.md`
- 实施路线：`2026-02-27-重构实施路线图.md`
- 开发规范：`2026-02-27-重构开发规范.md`
