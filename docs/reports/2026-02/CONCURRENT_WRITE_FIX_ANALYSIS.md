# 并发写入冲突问题深度分析报告

**分析日期**: 2026-02-20  
**分析人**: AI Assistant (资深测试专家)  
**严重性**: P0 (数据丢失风险)

---

## 🐛 问题描述

### 用户反馈

> "启动监测后，是不是每请求获取到一个 API 的反馈，就会及时记录下来，能够确保多个 API 平台同时反馈时，写入结果不会冲突"

### 问题根因

**当前实现**:
```
启动诊断 → 轮询后端 → 等待完成 → 一次性写入所有结果
                                              ↓
                                      ❌ 中间结果丢失风险
                                      ❌ 并发冲突风险
```

**问题**:
1. **只在任务完成时写入** - 中间结果不保存
2. **一次性写入所有结果** - 可能覆盖冲突
3. **没有任务级锁机制** - 并发时可能冲突

---

## 🔍 代码分析

### 前端写入逻辑

**当前实现** (`pages/detail/index.js`):
```javascript
// 只在任务完成时写入
if (isCompleted) {
  const resultsData = statusData.detailed_results || statusData.results || [];
  
  // ❌ 问题：一次性写入所有结果
  wx.setStorageSync('latestTestResults_' + this.executionId, resultsData);
  
  wx.navigateTo({...});
}
```

**问题**:
- ❌ 9 个任务完成后才写入一次
- ❌ 如果第 10 个任务失败，前 9 个结果丢失
- ❌ 多 API 并发时可能覆盖

---

### 后端存储逻辑

**当前实现** (`backend_python/wechat_backend/models.py`):
```python
def save_deep_intelligence_result(task_id, deep_intelligence_result):
    # 只在任务完成时保存
    if existing_record:
        UPDATE ...
    else:
        INSERT ...
```

**问题**:
- ❌ 没有任务完成计数器
- ❌ 没有实时记录每个任务的完成状态
- ❌ 没有并发锁机制

---

## 🎯 解决方案

### 方案 1: 实时写入每个任务结果 (推荐)

#### 前端修改

```javascript
// 每次轮询时检查是否有新完成的任务
const performPoll = async () => {
  const statusData = await this.fetchTaskStatus();
  
  if (statusData) {
    // 新增：检查已完成任务列表
    if (statusData.completedTasks && Array.isArray(statusData.completedTasks)) {
      // 实时写入每个完成的任务
      for (const task of statusData.completedTasks) {
        await this.saveTaskResult(task);
      }
    }
  }
};

// 新增方法：保存单个任务结果
saveTaskResult: function(task) {
  const key = 'task_result_' + this.executionId + '_' + task.taskId;
  
  // 检查是否已保存 (避免重复写入)
  const existing = wx.getStorageSync(key);
  if (existing) {
    console.log('任务已保存:', task.taskId);
    return;
  }
  
  // 保存任务结果
  wx.setStorageSync(key, {
    taskId: task.taskId,
    question: task.question,
    model: task.model,
    response: task.response,
    geoData: task.geoData,
    completedAt: Date.now()
  });
  
  console.log('✅ 任务已保存:', task.taskId);
  
  // 更新进度管理器
  if (this.progressManager) {
    this.progressManager.incrementProgress();
  }
},
```

#### 后端修改

**1. 添加任务完成计数器**

```python
# models.py
def save_task_completion(task_id, task_data):
    """保存单个任务完成结果"""
    safe_query = SafeDatabaseQuery(DB_PATH)
    
    # 检查是否已保存
    existing = safe_query.execute_query(
        'SELECT task_id FROM task_results WHERE task_id = ? AND model = ?',
        (task_id, task_data['model'])
    )
    
    if existing:
        return False  # 已保存，避免重复
    
    # 插入任务结果
    safe_query.execute_query('''
        INSERT INTO task_results
        (task_id, model, question, response, geo_data, completed_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        task_id,
        task_data['model'],
        task_data['question'],
        json.dumps(task_data['response']),
        json.dumps(task_data['geo_data'])
    ))
    
    # 更新任务状态表的完成计数
    safe_query.execute_query('''
        UPDATE task_statuses
        SET completed_count = completed_count + 1
        WHERE task_id = ?
    ''', (task_id,))
    
    return True
```

**2. 返回已完成任务列表**

```python
# views.py - get_task_status_api
def get_task_status_api(task_id):
    task_status = get_task_status(task_id)
    
    # 新增：获取已完成的任务列表
    completed_tasks = get_completed_tasks(task_id)
    
    return jsonify({
        'progress': task_status.progress,
        'status': 'running',
        'completedTasks': completed_tasks,  # 新增
        'totalTasks': get_total_tasks(task_id)  # 新增
    })
```

---

### 方案 2: 写入队列 + 批量提交

```javascript
// 前端实现写入队列
this.resultQueue = [];
this.isWriting = false;

// 添加到队列
addToQueue: function(taskResult) {
  this.resultQueue.push(taskResult);
  
  // 触发批量写入
  if (!this.isWriting) {
    this.flushQueue();
  }
},

// 批量写入 (每 5 个或每 2 秒)
flushQueue: function() {
  if (this.resultQueue.length === 0) {
    this.isWriting = false;
    return;
  }
  
  this.isWriting = true;
  
  // 每 5 个写入一次
  const batchSize = Math.min(5, this.resultQueue.length);
  const batch = this.resultQueue.splice(0, batchSize);
  
  // 批量写入
  const allResults = this.getAllResults();
  allResults.push(...batch);
  
  wx.setStorageSync('latestTestResults_' + this.executionId, allResults);
  
  // 2 秒后再次尝试
  setTimeout(() => this.flushQueue(), 2000);
}
```

---

### 方案 3: 使用数据库事务 (最安全)

```javascript
// 使用事务确保写入原子性
saveTaskResult: function(task) {
  try {
    // 开始事务
    wx.startBatchLog();
    
    // 读取现有结果
    const existing = wx.getStorageSync('latestTestResults_' + this.executionId) || [];
    
    // 检查是否重复
    const exists = existing.some(r => 
      r.taskId === task.taskId && r.model === task.model
    );
    
    if (exists) {
      wx.abortBatchLog();
      return;
    }
    
    // 添加新结果
    existing.push(task);
    
    // 写入
    wx.setStorageSync('latestTestResults_' + this.executionId, existing);
    
    // 提交事务
    wx.commitBatchLog();
    
    console.log('✅ 任务已保存:', task.taskId);
  } catch (e) {
    wx.abortBatchLog();
    console.error('写入失败:', e);
  }
}
```

---

## 📊 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **方案 1** | 实时写入，数据不丢失 | 需要后端配合 | ⭐⭐⭐⭐⭐ |
| **方案 2** | 前端独立实现，减少写入次数 | 可能丢失队列中数据 | ⭐⭐⭐⭐ |
| **方案 3** | 最安全，原子性保证 | 微信小程序不支持事务 | ⭐⭐ |

---

## 🎯 推荐实施方案

### 阶段 1: 前端实时写入 (立即实施)

**无需后端配合**:
```javascript
// 在 detail/index.js 中添加
saveTaskResult: function(taskIndex, model, response) {
  const key = 'task_result_' + this.executionId + '_' + taskIndex + '_' + model;
  
  // 检查是否已保存
  const existing = wx.getStorageSync(key);
  if (existing) return;
  
  // 保存
  wx.setStorageSync(key, {
    taskIndex,
    model,
    response,
    timestamp: Date.now()
  });
  
  // 累加到总结果
  const allResults = this.getAllResults();
  allResults.push({
    taskIndex,
    model,
    response,
    geoData: response.geo_data
  });
  
  wx.setStorageSync('latestTestResults_' + this.executionId, allResults);
  
  console.log('✅ 任务已实时保存');
},

getAllResults: function() {
  return wx.getStorageSync('latestTestResults_' + this.executionId) || [];
},
```

### 阶段 2: 后端支持 (需要后端开发)

- 添加 `task_results` 表
- 实现 `save_task_completion` 方法
- 返回 `completedTasks` 列表

---

## 📋 实施清单

### 前端修改

- [ ] 添加 `saveTaskResult` 方法
- [ ] 添加 `getAllResults` 方法
- [ ] 修改轮询逻辑，实时写入
- [ ] 添加并发锁 (避免重复写入)

### 后端修改 (可选)

- [ ] 创建 `task_results` 表
- [ ] 实现 `save_task_completion` 方法
- [ ] 修改 `get_task_status_api` 返回 completedTasks

---

## 🧪 测试用例

### 用例 1: 并发写入测试

**步骤**:
1. 启动 3 问题×3 模型诊断
2. 观察 Console 日志
3. 检查存储数据

**预期**:
- ✅ 每个任务完成后立即写入
- ✅ 无重复写入
- ✅ 无写入冲突

---

**下一步**: 开始实施方案 1
