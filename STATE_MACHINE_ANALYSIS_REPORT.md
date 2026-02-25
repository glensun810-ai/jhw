# 🏗️ 品牌诊断系统状态机深度分析报告

**报告日期**: 2026-02-26 01:30  
**分析团队**: 首席架构师、前端工程师、后台工程师、数据专家  
**分析范围**: 端到端业务逻辑状态流转

---

## 一、状态机架构总览

### 1.1 核心状态实体

| 表名 | 状态字段 | 用途 |
|------|----------|------|
| `diagnosis_reports` | `status`, `stage`, `progress`, `is_completed` | 诊断报告主表 |
| `task_statuses` | `stage`, `progress`, `status_text` | 任务状态跟踪 |
| `dimension_results` | `status` (success/failed) | 维度结果 |
| `test_records` | 无状态字段（汇总表） | 测试汇总记录 |
| `execution_store` | 内存状态 | 实时进度缓存 |

### 1.2 标准状态流转

```
┌─────────────────────────────────────────────────────────────────┐
│                    诊断任务状态流转图                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户提交诊断                                                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐                                                │
│  │ initializing │ status='initializing'                         │
│  │ progress=0   │ stage='init'                                  │
│  └──────┬──────┘                                                │
│         │ 创建 execution_id                                      │
│         ▼                                                         │
│  ┌─────────────┐                                                │
│  │ ai_fetching  │ status='ai_fetching'                          │
│  │ progress=0→  │ stage='ai_fetching'                           │
│  └──────┬──────┘ 每完成一个任务更新进度                           │
│         │                                                         │
│         ▼                                                         │
│  ┌─────────────┐                                                │
│  │ analyzing    │ status='analyzing' (跳过)                      │
│  │ progress=80  │ stage='analyzing' (跳过)                       │
│  └──────┬──────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌─────────────┐                                                │
│  │  completed   │ status='completed'                             │
│  │ progress=100 │ stage='completed'                              │
│  └─────────────┘ 保存 test_records                               │
│                                                                 │
│  异常流转：                                                      │
│  - 超时：fail_execution("执行超时")                              │
│  - 全失败：fail_execution("未获取任何有效结果")                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、状态机详细分析

### 2.1 后端状态管理

**初始化阶段**:
```python
# nxm_execution_engine.py:88
scheduler.initialize_execution(total_tasks)

# 实际调用
def initialize_execution(self, total_tasks):
    self.execution_store[self.execution_id] = {
        'progress': 0,
        'completed': 0,
        'total': total_tasks,
        'status': 'initializing',
        'stage': 'init',
        'results': [],
        'start_time': datetime.now().isoformat()
    }
    
    # 同时保存到 diagnosis_reports 表
    save_diagnosis_report(
        execution_id=execution_id,
        status='initializing',
        progress=0,
        stage='init',
        is_completed=False
    )
```

**执行阶段**:
```python
# nxm_execution_engine.py:127
scheduler.update_progress(completed, total_tasks, 'ai_fetching')

# 实际调用
def update_progress(self, completed, total, stage):
    progress = int((completed / total) * 100) if total > 0 else 0
    
    # 更新内存
    self.execution_store[self.execution_id].update({
        'progress': progress,
        'stage': stage,
        'completed': completed
    })
    
    # 持久化到 task_statuses 表
    save_task_status(
        task_id=self.execution_id,
        stage=stage,
        progress=progress,
        ...
    )
```

**完成阶段**:
```python
# nxm_execution_engine.py:326 (新增修复)
# 保存测试汇总记录到 test_records 表
save_test_record(
    user_openid=user_id or 'anonymous',
    brand_name=main_brand,
    ai_models_used=','.join(selected_models),
    questions_used=';'.join(raw_questions),
    overall_score=overall_score,
    total_tasks=len(deduplicated),
    results_summary=压缩的摘要数据,
    detailed_results=压缩的详细结果,
    execution_id=execution_id
)
```

### 2.2 前端轮询状态判断

**文件**: `services/brandTestService.js`

```javascript
// 轮询终止条件
if (['completed', 'finished', 'done', 'partial_completed'].includes(stage)) {
  if (this.callbacks.onComplete) {
    this.callbacks.onComplete(data);
  }
  return;
}

if (stage === 'failed') {
  // 检查是否有结果（部分完成）
  const hasResults = parsedStatus.results && parsedStatus.results.length > 0;
  if (hasResults) {
    // 有结果，视为部分完成
    if (onComplete) onComplete(parsedStatus);
  } else {
    // 完全失败
    if (onError) onError(new Error(parsedStatus.error));
  }
  return;
}
```

---

## 三、发现的问题及根因

### 🔴 问题 1: 状态不一致风险

**现象**:
```python
# diagnosis_reports 表
status='completed', stage='ai_fetching'  # 不一致！
```

**根因**:
- `status` 和 `stage` 字段在多处更新
- 没有统一的同步机制
- 部分代码只更新 `status` 不更新 `stage`

**影响**:
- 前端轮询可能误判状态
- 历史记录显示异常

**修复建议**:
```python
# 统一状态更新函数
def update_task_status(execution_id, status, stage, progress):
    """确保 status 和 stage 同步更新"""
    # 状态映射
    status_stage_map = {
        'initializing': 'init',
        'ai_fetching': 'ai_fetching',
        'analyzing': 'analyzing',
        'completed': 'completed',
        'failed': 'failed'
    }
    
    # 如果只传入 status，自动推导 stage
    if stage is None:
        stage = status_stage_map.get(status, status)
    
    # 同时更新两个字段
    cursor.execute('''
        UPDATE diagnosis_reports 
        SET status = ?, stage = ?, progress = ?, updated_at = ?
        WHERE execution_id = ?
    ''', (status, stage, progress, datetime.now(), execution_id))
```

---

### 🟡 问题 2: 进度更新频率过高

**现象**:
```python
# 每完成一个 AI 调用就更新一次进度
completed += 1
scheduler.update_progress(completed, total_tasks, 'ai_fetching')
```

**根因**:
- 36 次 AI 调用 = 36 次数据库写入
- 每次写入都有 I/O 开销

**影响**:
- 数据库负载高
- 执行时间增加

**修复建议**:
```python
# 批量更新进度（每 5 次更新一次）
PROGRESS_UPDATE_INTERVAL = 5

if completed % PROGRESS_UPDATE_INTERVAL == 0:
    scheduler.update_progress(completed, total_tasks, 'ai_fetching')
```

---

### 🟡 问题 3: test_records 保存时机

**现象**:
- 诊断完成后才保存 test_records
- 如果中途失败，test_records 为空

**根因**:
- test_records 是汇总表，依赖完整结果

**影响**:
- 用户看到 7 次诊断，但 test_records 都是 0 条
- 历史记录显示空记录

**当前修复**:
```python
# nxm_execution_engine.py:326
# 在诊断完成后保存 test_records
save_test_record(...)
```

**建议增强**:
```python
# 增加失败时的清理逻辑
if not success:
    # 删除空的诊断报告
    cursor.execute('''
        DELETE FROM diagnosis_reports 
        WHERE execution_id = ? AND status = 'failed'
    ''', (execution_id,))
```

---

### 🟢 问题 4: 前端状态判断复杂

**现象**:
```javascript
// 前端需要判断多个状态
if (['completed', 'finished', 'done', 'partial_completed'].includes(stage)) {
  // 完成
}
if (stage === 'failed' && hasResults) {
  // 部分完成
}
```

**根因**:
- 后端状态定义不清晰
- `partial_completed` 状态未正式定义

**建议**:
```python
# 后端明确定义状态
TASK_STATUS = {
    'INITIALIZING': 'initializing',
    'AI_FETCHING': 'ai_fetching',
    'ANALYZING': 'analyzing',
    'COMPLETED': 'completed',      # 100% 完成
    'PARTIAL_COMPLETED': 'partial_completed',  # 部分完成
    'FAILED': 'failed'             # 完全失败
}
```

---

### 🟢 问题 5: execution_store 与数据库不同步

**现象**:
```python
# execution_store 中有数据
execution_store[execution_id] = {'progress': 100, ...}

# 但数据库中没有
SELECT * FROM diagnosis_reports WHERE execution_id = ?  # 空
```

**根因**:
- execution_store 是内存缓存
- 数据库持久化可能失败
- 没有同步检查机制

**影响**:
- 前端轮询拿到内存数据
- 刷新后数据丢失

**建议**:
```python
# 增加同步检查
def get_execution_status(execution_id):
    # 优先从数据库读取
    report = get_diagnosis_report(execution_id)
    if report and report.status == 'completed':
        return report
    
    # 数据库没有，检查内存
    return execution_store.get(execution_id)
```

---

## 四、状态机完整性检查

### 4.1 状态覆盖度

| 状态 | 定义 | 使用位置 | 完整性 |
|------|------|----------|--------|
| `initializing` | ✅ 明确 | 初始化 | ✅ |
| `ai_fetching` | ✅ 明确 | AI 调用中 | ✅ |
| `analyzing` | ⚠️ 跳过 | 结果聚合 | ⚠️ 未使用 |
| `completed` | ✅ 明确 | 完成 | ✅ |
| `failed` | ✅ 明确 | 失败 | ✅ |
| `partial_completed` | ⚠️ 模糊 | 前端判断 | ⚠️ 未正式定义 |

### 4.2 状态转换合法性

```
合法转换：
initializing → ai_fetching ✅
ai_fetching → analyzing ⚠️ (跳过)
ai_fetching → completed ✅
ai_fetching → failed ✅
analyzing → completed ✅
analyzing → failed ✅

非法转换：
initializing → completed ❌ (未经历 ai_fetching)
completed → ai_fetching ❌ (不可逆)
```

---

## 五、修复建议汇总

### P0 级别（关键）

| 问题 | 修复方案 | 优先级 |
|------|----------|--------|
| 状态不一致 | 统一状态更新函数 | 🔴 |
| test_records 空记录 | 失败时清理空报告 | 🔴 |

### P1 级别（重要）

| 问题 | 修复方案 | 优先级 |
|------|----------|--------|
| 进度更新频率高 | 批量更新（每 5 次） | 🟡 |
| execution_store 不同步 | 增加同步检查 | 🟡 |

### P2 级别（优化）

| 问题 | 修复方案 | 优先级 |
|------|----------|--------|
| 前端状态判断复杂 | 明确定义状态枚举 | 🟢 |
| analyzing 状态跳过 | 恢复或移除该状态 | 🟢 |

---

## 六、总结

### 状态机健康度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 状态定义 | 8/10 | 大部分明确，部分模糊 |
| 状态转换 | 9/10 | 转换逻辑清晰 |
| 数据一致性 | 7/10 | 存在不一致风险 |
| 性能优化 | 7/10 | 进度更新频率可优化 |
| 错误处理 | 8/10 | 有超时和失败处理 |

**综合评分**: **7.8/10**

### 核心结论

1. **状态机整体设计合理** - 覆盖了诊断任务的主要状态
2. **存在数据一致性风险** - status 和 stage 可能不同步
3. **性能有优化空间** - 进度更新频率可降低
4. **test_records 问题已修复** - 诊断完成后保存汇总记录

### 建议行动

**立即执行**:
1. 统一状态更新函数
2. 失败时清理空报告

**短期优化**:
1. 批量更新进度
2. 增加同步检查

**长期改进**:
1. 明确定义状态枚举
2. 简化前端状态判断

---

**报告完成时间**: 2026-02-26 01:30  
**分析团队**: 首席架构师、前端工程师、后台工程师、数据专家  
**状态**: ✅ **分析完成，修复建议已提出**
