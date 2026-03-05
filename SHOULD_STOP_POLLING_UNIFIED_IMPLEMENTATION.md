# should_stop_polling 统一实现方案

## 一、现状分析

### ✅ 已实现的部分

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 数据库迁移 | `migrations/003_add_should_stop_polling.py` | ✅ 已完成 | 添加 `should_stop_polling` 字段 |
| 后端状态管理 | `state_manager.py` | ✅ 已完成 | `complete_execution()` 设置 `should_stop_polling=True` |
| 后端 API | `diagnosis_views.py` | ✅ 已完成 | `/api/test-progress` 返回 `should_stop_polling` |
| 前端解析 | `services/taskStatusService.js` | ✅ 已完成 | `parseTaskStatus()` 解析字段 |
| 前端轮询 | `services/brandTestService.js` | ✅ 已完成 | 轮询检查 `should_stop_polling` |

### ⚠️ 需要统一的部分

**问题**: 前端 `index.js` 中虽然轮询停止了，但按钮状态 (`isTesting`) 没有及时重置

**根本原因**: 
1. `onComplete` 回调中设置了 `isTesting: false`
2. 但 `index.js` 的 `_onDiagnosisComplete` 函数有冗余代码和异常处理分支
3. 某些错误路径可能跳过状态重置

---

## 二、统一实现方案

### 后端部分（已完整，无需修改）

```python
# backend_python/wechat_backend/state_manager.py
def complete_execution(self, execution_id, user_id=None, ...):
    """完成执行时必须设置 should_stop_polling=True"""
    
    success = self.update_state(
        execution_id=execution_id,
        status='completed',
        stage='completed',
        progress=100,
        is_completed=True,
        should_stop_polling=True,  # ✅ 关键：通知前端停止轮询
        write_to_db=True,
        ...
    )
```

```python
# backend_python/wechat_backend/views/diagnosis_views.py
@wechat_bp.route('/api/test-progress', methods=['GET'])
def get_test_progress():
    """返回进度时必须包含 should_stop_polling"""
    
    # 内存路径
    if execution_id in execution_store:
        progress_data = execution_store[execution_id]
        
        # ✅ 关键：完成后强制设置
        if progress_data.get('status') in ['completed', 'failed']:
            progress_data['should_stop_polling'] = True
        
        return jsonify(progress_data)
    
    # 数据库恢复路径
    if report:
        db_data = {
            'status': report.get('status', 'processing'),
            'should_stop_polling': report.get('status') in ['completed', 'failed'],
        }
        
        # ✅ 关键：数据库显示完成后强制停止
        if report.get('is_completed') == 1 or report.get('status') in ['completed', 'failed']:
            db_data['should_stop_polling'] = True
        
        return jsonify(db_data)
```

---

### 前端部分（需要统一）

#### 1. services/taskStatusService.js - 解析逻辑 ✅

```javascript
const parseTaskStatus = (statusData, startTime = Date.now()) => {
  const parsed = {
    status: statusData?.status || 'unknown',
    progress: statusData?.progress || 0,
    stage: statusData?.stage || 'init',
    
    // ✅ 关键：优先读取后端的 should_stop_polling
    should_stop_polling: (statusData && typeof statusData.should_stop_polling === 'boolean')
      ? statusData.should_stop_polling
      : false,
    
    // ✅ 关键：is_completed 也重要
    is_completed: (statusData && typeof statusData.is_completed === 'boolean')
      ? statusData.is_completed
      : false,
    
    results: statusData?.results || [],
    detailed_results: statusData?.detailed_results || [],
    error: statusData?.error || null
  };
  
  // ✅ 关键：如果 should_stop_polling=true，强制覆盖为完成状态
  if (parsed.should_stop_polling) {
    console.log('[parseTaskStatus] ✅ 后端标记 should_stop_polling=true');
    
    // 如果后端返回了明确的状态，直接使用
    if (statusData?.status === 'completed' || statusData?.status === 'failed') {
      parsed.stage = statusData.status;
      parsed.is_completed = (statusData.status === 'completed');
      parsed.progress = 100;
    } else if (parsed.stage !== 'completed' && parsed.stage !== 'failed') {
      // 异常情况：should_stop_polling=true 但 stage 不是终态
      console.warn('[parseTaskStatus] ⚠️ 异常：强制设置为 completed');
      parsed.stage = 'completed';
      parsed.is_completed = true;
      parsed.progress = 100;
    }
  }
  
  return parsed;
};

module.exports = { parseTaskStatus };
```

#### 2. services/brandTestService.js - 轮询终止逻辑 ✅

```javascript
const startLegacyPolling = (executionId, onProgress, onComplete, onError) => {
  let pollInterval = null;
  let isStopped = false;
  
  const poll = async () => {
    try {
      const res = await getTaskStatusApi(executionId);
      const parsedStatus = parseTaskStatus(res);
      
      if (onProgress) {
        onProgress(parsedStatus);
      }
      
      // ✅ 关键：优先检查 should_stop_polling（最高优先级）
      if (parsedStatus.should_stop_polling === true) {
        controller.stop();
        console.log('[轮询终止] 后端标记 should_stop_polling=true，停止轮询');
        
        // 判断是成功还是失败
        if (parsedStatus.stage === 'completed' || parsedStatus.is_completed === true) {
          if (onComplete) onComplete(parsedStatus);
        } else if (parsedStatus.stage === 'failed') {
          // 失败但有结果
          const hasResults = parsedStatus.detailed_results?.length > 0;
          if (hasResults) {
            if (onComplete) onComplete(parsedStatus);
          } else if (onError) {
            onError(new Error(parsedStatus.error || '诊断失败'));
          }
        } else {
          // 其他情况视为完成
          if (onComplete) onComplete(parsedStatus);
        }
        return;
      }
      
      // 兼容旧逻辑：检查状态枚举
      if (isTerminalStatus(parsedStatus.stage)) {
        controller.stop();
        if (onComplete) onComplete(parsedStatus);
        return;
      }
      
    } catch (err) {
      if (onError) onError(err);
    }
  };
  
  poll();
  
  return {
    stop: () => {
      if (pollInterval) clearInterval(pollInterval);
      isStopped = true;
    }
  };
};
```

#### 3. pages/index/index.js - 状态重置逻辑 ⚠️ **需要统一**

**当前问题**: `onComplete` 回调中设置了 `isTesting: false`，但某些异常路径可能跳过

**统一后的实现**:

```javascript
// pages/index/index.js

/**
 * 【核心重构】执行诊断请求 - 完整的生命周期管理
 */
_executeDiagnosis: async function(brandList, selectedModels, customQuestions) {
  wx.showLoading({ title: '启动诊断...', mask: true });

  try {
    const inputData = {
      brandName: brandList[0],
      competitorBrands: brandList.slice(1),
      selectedModels,
      customQuestions
    };

    const executionId = await startDiagnosis(inputData);
    console.log('[诊断启动] ✅ 任务创建成功，执行 ID:', executionId);

    // ✅ 关键：创建轮询控制器（带完整回调）
    this.pollingController = createPollingController(
      executionId,
      
      // onProgress: 进度回调
      (parsedStatus) => {
        // ✅ 只更新进度显示，不改变 isTesting
        this.setData({
          testProgress: parsedStatus.progress || 0,
          progressText: parsedStatus.statusText || '诊断中...',
          currentStage: parsedStatus.stage || 'analyzing'
        });
      },
      
      // onComplete: 完成回调（最关键）
      (parsedStatus) => {
        wx.hideLoading();
        
        // ✅ 关键修复：立即更新按钮状态（原子操作）
        this.setData({
          isTesting: false,        // 停止加载
          testCompleted: true,     // 标记完成
          hasLastReport: true,     // 标记有报告
          currentStage: 'completed'
        });
        
        console.log('[诊断完成] ✅ 执行 ID:', executionId);
        this._onDiagnosisComplete(parsedStatus, executionId);
      },
      
      // onError: 错误回调
      (error) => {
        wx.hideLoading();
        
        // ✅ 关键修复：确保按钮恢复
        this.setData({
          isTesting: false,
          testProgress: 0,
          testCompleted: false,
          currentStage: 'error'
        });
        
        console.error('[诊断错误] ❌', error);
        this._onDiagnosisError(error);
      }
    );

  } catch (err) {
    // ✅ 启动失败也要恢复按钮
    wx.hideLoading();
    this.setData({ isTesting: false, testCompleted: false });
    this._onDiagnosisError(err);
  }
},

/**
 * 【核心重构】诊断完成处理
 */
_onDiagnosisComplete: function(parsedStatus, executionId) {
  try {
    // ✅ 状态已经在 _executeDiagnosis 的 onComplete 中设置
    // 这里只处理数据持久化和跳转
    
    console.log('[诊断完成] 执行 ID:', executionId);

    // 部分完成警告
    if (parsedStatus.warning || parsedStatus.missing_count > 0) {
      wx.showModal({
        title: '诊断提示',
        content: `诊断部分完成：已获取 ${parsedStatus.detailed_results?.length || 0} 个结果`,
        showCancel: false,
        confirmText: '查看结果'
      });
    }

    // 数据持久化
    const saveSuccess = saveDiagnosisResult(executionId, {
      brandName: this.data.brandName,
      results: parsedStatus.detailed_results || [],
      rawResponse: parsedStatus
    });

    // 跳转结果页
    wx.navigateTo({
      url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}`
    });

  } catch (error) {
    console.error('[_onDiagnosisComplete] 处理失败:', error);
    // ✅ 即使处理失败，按钮状态已经正确，不影响用户体验
  }
},

/**
 * 【核心重构】诊断错误处理
 */
_onDiagnosisError: function(error) {
  // ✅ 状态已经在 _executeDiagnosis 的 onError 中设置
  // 这里只显示错误提示
  
  const friendlyError = this.handleException(error, '诊断启动');
  
  wx.showModal({
    title: '诊断失败',
    content: friendlyError,
    showCancel: false,
    confirmText: '我知道了'
  });
},

/**
 * 【新增】重置按钮状态 - 统一状态恢复函数
 */
_resetButtonState: function() {
  this.setData({
    isTesting: false,
    testProgress: 0,
    testCompleted: false,
    currentStage: 'error'
  });
}
```

---

## 三、数据流验证

### 完整流程图

```
用户点击"诊断"
    ↓
index.js: startBrandTest()
    ↓
setData({ isTesting: true, testProgress: 0 })
    ↓
_executeDiagnosis()
    ↓
wx.showLoading()
    ↓
startDiagnosis() → POST /api/test
    ↓
后端创建任务，返回 executionId
    ↓
createPollingController(executionId, onProgress, onComplete, onError)
    ↓
═══════════════════════════
轮询阶段（每 800ms）
═══════════════════════════
    ↓
getTaskStatusApi(executionId) → GET /api/test-progress/{id}
    ↓
后端返回：
{
  status: 'processing',
  progress: 30,
  should_stop_polling: false  ← 继续轮询
}
    ↓
parseTaskStatus() 解析
    ↓
onProgress(parsedStatus)
    ↓
index.js: setData({ testProgress: 30 })
    ↓
[循环...直到后端返回 should_stop_polling=true]
    ↓
═══════════════════════════
完成阶段
═══════════════════════════
    ↓
后端返回：
{
  status: 'completed',
  progress: 100,
  should_stop_polling: true  ← 停止轮询
}
    ↓
parseTaskStatus() 解析
  → should_stop_polling = true
  → stage = 'completed'
  → is_completed = true
    ↓
轮询检查：if (should_stop_polling === true)
    ↓
controller.stop()  ← 停止轮询
    ↓
onComplete(parsedStatus)  ← 触发完成回调
    ↓
wx.hideLoading()
    ↓
index.js: setData({     ← ✅ 关键：立即重置按钮状态
  isTesting: false,
  testCompleted: true,
  hasLastReport: true
})
    ↓
_onDiagnosisComplete()  ← 处理数据和跳转
    ↓
saveDiagnosisResult()  ← 保存到 Storage
    ↓
wx.navigateTo()  ← 跳转到结果页
```

---

## 四、验证清单

### 后端验证

```bash
# 1. 检查数据库字段
sqlite3 diagnosis.db "PRAGMA table_info(diagnosis_reports);" | grep should_stop_polling

# 2. 检查 API 返回
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/test-progress/<executionId>" | jq '.should_stop_polling'

# 3. 检查日志
tail -100 logs/app.log | grep "should_stop_polling"
```

**期望输出**:
```
# 1. 数据库字段
19|should_stop_polling|BOOLEAN|0|0|0

# 2. API 返回
true  # 完成后

# 3. 日志
[StateManager] ✅ 执行完成：<id>, should_stop_polling=True
[进度查询] 数据库显示已完成，强制停止轮询：<id>
```

### 前端验证

```javascript
// 在开发者工具 Console 中运行

// 1. 检查 parseTaskStatus 解析
const testResponse = {
  status: 'completed',
  progress: 100,
  should_stop_polling: true
};
const parsed = parseTaskStatus(testResponse);
console.log('should_stop_polling:', parsed.should_stop_polling);
// 期望：true

// 2. 检查轮询终止
// 观察日志：[轮询终止] 后端标记 should_stop_polling=true，停止轮询

// 3. 检查按钮状态
// 在诊断完成后运行
const page = getCurrentPages()[getCurrentPages().length - 1];
console.log('isTesting:', page.data.isTesting);
console.log('testCompleted:', page.data.testCompleted);
// 期望：isTesting=false, testCompleted=true
```

---

## 五、测试用例

### 用例 1: 正常诊断完成

```javascript
// 后端返回
{
  status: 'completed',
  progress: 100,
  should_stop_polling: true,
  detailed_results: [...]
}

// 前端行为
✅ 轮询停止
✅ isTesting → false
✅ testCompleted → true
✅ 按钮文字 → "重新诊断"
✅ 显示"查看报告"入口
```

### 用例 2: 诊断失败

```javascript
// 后端返回
{
  status: 'failed',
  progress: 45,
  should_stop_polling: true,
  error: 'AI 调用失败'
}

// 前端行为
✅ 轮询停止
✅ isTesting → false
✅ testCompleted → false
✅ 按钮文字 → "AI 品牌战略诊断"（可点击）
✅ 显示错误提示
```

### 用例 3: 部分完成（有警告）

```javascript
// 后端返回
{
  status: 'completed',
  progress: 100,
  should_stop_polling: true,
  warning: '3/5 个 AI 调用成功',
  missing_count: 2
}

// 前端行为
✅ 轮询停止
✅ isTesting → false
✅ testCompleted → true
✅ 显示警告弹窗
✅ 按钮文字 → "重新诊断"
```

### 用例 4: 网络超时

```javascript
// 前端行为（8 分钟无进度更新）
✅ 轮询自动停止
✅ isTesting → false
✅ testCompleted → false
✅ 显示超时错误
✅ 按钮恢复可点击
```

---

## 六、关键修复点总结

| 位置 | 修复内容 | 优先级 |
|------|----------|--------|
| `state_manager.py` | `complete_execution()` 设置 `should_stop_polling=True` | ✅ 已完成 |
| `diagnosis_views.py` | `/api/test-progress` 返回 `should_stop_polling` | ✅ 已完成 |
| `taskStatusService.js` | `parseTaskStatus()` 优先读取 `should_stop_polling` | ✅ 已完成 |
| `brandTestService.js` | 轮询检查 `should_stop_polling === true` | ✅ 已完成 |
| `index.js` | `onComplete` 中立即 `setData({ isTesting: false })` | ⚠️ **需要统一** |
| `index.js` | `onError` 中立即 `setData({ isTesting: false })` | ⚠️ **需要统一** |

---

## 七、执行建议

1. **立即验证后端**: 确认 `/api/test-progress` 返回 `should_stop_polling`
2. **统一前端代码**: 将 `index.js` 的 `_executeDiagnosis` 和 `onComplete`/`onError` 重构为上述版本
3. **添加监控日志**: 在关键节点添加 `console.log` 便于调试
4. **端到端测试**: 运行完整诊断流程，验证按钮状态切换
