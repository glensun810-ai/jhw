# 最新问题分析报告 - 诊断完成但 results 为空

**分析日期**: 2026-03-11  
**问题级别**: 🔴 P0 关键问题  
**状态**: 分析完成

---

## 一、问题现象

### 截图信息

从微信开发者工具截图可以看到：

**控制台日志**:
```javascript
❌ [handleDiagnosisComplete] results.length == 0, 跳转到报告页展示详情
(env: macOS,mp,2.01.2510280; lib: 3.14.2)
```

**模拟器状态**:
- 右侧手机模拟器显示 "加载中..."
- 页面卡在加载状态

**任务状态**:
```javascript
[parseTaskStatus] 解析结果：
{
  stage: "completed",
  progress: 100,
  is_completed: true,
  should_stop_polling: false,  // ⚠️ 注意：这个值为 false
  status: "completed"
}
```

---

## 二、问题分析

### 2.1 日志流程分析

**正常的流程**:
1. ✅ 轮询响应正常（第 28 次，耗时 43ms）
2. ✅ 状态解析正常（completed, 100%）
3. ✅ 智能轮询正常
4. ✅ 轮询终止（任务完成）
5. ❌ **results.length == 0**
6. ✅ 存储记录已保存
7. ✅ 报告详情页已加载

### 2.2 核心问题

**问题**: `results.length == 0`

**可能原因**:

| 可能性 | 原因 | 验证方法 |
|--------|------|---------|
| 高 | 后端 AI 调用返回空结果 | 检查后端日志 |
| 中 | 后端完成时未返回 results 字段 | 检查后端响应 |
| 中 | 前端解析错误导致 results 丢失 | 检查前端代码 |
| 低 | 网络问题导致数据丢失 | 检查网络请求 |

### 2.3 关键发现

**发现 1**: 后端代码分析

查看 `diagnosis_views.py` Line 3162-3168:

```python
# 【P0 关键修复 - 2026-03-07】完成时总是返回结果数据
if is_completed:
    from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository
    result_repo = DiagnosisResultRepository()
    
    results = result_repo.get_by_execution_id(task_id)
    response_data['results'] = results or []
    response_data['result_count'] = len(results) if results else 0
```

**结论**: 后端确实返回了 `results` 字段。

**发现 2**: 前端轮询管理器分析

查看 `pollingManager.js` Line 262-264:

```javascript
if (statusData.status === 'completed' ||
    statusData.status === 'partial_success') {
  // 成功完成
  if (task.callbacks.onComplete) {
    task.callbacks.onComplete(statusData);  // 传递 statusData
  }
}
```

**结论**: `onComplete` 回调接收的是 `statusData`，应该包含 `results`。

**发现 3**: 前端诊断页面分析

查看 `diagnosis.js` Line 298-312:

```javascript
handleComplete(result) {
  console.log('[DiagnosisPage] Task completed:', result);
  this.stopPolling();

  showToast({
    title: '诊断完成',
    icon: 'success',
    duration: 2000
  });

  // 【修复】跳转到报告页面 v2
  setTimeout(() => {
    wx.navigateTo({
      url: `/pages/report-v2/report-v2?executionId=${this.data.executionId}`
    });
  }, 1500);
}
```

**结论**: 诊断页面跳转到 report-v2 页面，只传递了 `executionId`。

**发现 4**: report-v2 页面分析

查看 `report-v2.js` Line 532-549:

```javascript
handleComplete(result) {
  console.log('[ReportPageV2] 诊断完成:', result);
  this.stopListening();

  this.setData({ connectionState: ConnectionState.COMPLETED });

  showToast({
    title: '诊断完成',
    icon: 'success',
    duration: 2000
  });

  // 刷新当前页面数据
  setTimeout(() => {
    this.loadReportData(this.data.executionId);
  }, 1500);
}
```

**结论**: report-v2 页面调用 `loadReportData` 重新获取数据。

**发现 5**: loadReportData 分析

查看 `report-v2.js` Line 596-620:

```javascript
async loadReportData(executionId, reportId) {
  const reportService = require('../../services/reportService').default;
  const id = executionId || this.data.executionId;

  // 获取完整报告
  const report = await reportService.getFullReport(id);

  console.log('[ReportPageV2] 报告数据:', report);

  // 检查是否有错误
  if (report.error) {
    // 处理错误
  }

  // 更新页面数据
  this.setData({
    brandDistribution: report.brandDistribution || {},
    sentimentDistribution: report.sentimentDistribution || {},
    keywords: report.keywords || [],
    // ...
  });
}
```

**结论**: 页面使用 `reportService.getFullReport()` 获取数据，而不是使用 `handleComplete` 的 `result` 参数。

---

## 三、根因定位

### 核心问题

**问题不在前端，而在后端**！

从日志可以看到：
```javascript
❌ [handleDiagnosisComplete] results.length == 0
```

这说明 `handleComplete` 接收到的 `result` 参数中 `results` 数组为空。

### 可能的后端原因

1. **AI 调用返回空结果**
   - 所有 AI 模型调用都失败
   - AI 调用超时
   - API Key 无效或配额用尽

2. **数据库保存失败**
   - 结果未成功保存到数据库
   - 保存后查询失败

3. **后端响应构建问题**
   - `results` 字段未正确添加到响应中
   - 字段名不匹配（snake_case vs camelCase）

---

## 四、验证步骤

### 4.1 检查后端日志

```bash
# 查看 AI 调用日志
tail -f backend_python/logs/app.log | grep -E "AI 调用|results|execution_id"

# 查看数据库保存日志
tail -f backend_python/logs/app.log | grep -E "保存|INSERT|diagnosis_results"
```

### 4.2 检查 API 响应

```bash
# 直接调用后端 API 检查返回数据
curl http://localhost:5001/api/test/status/<execution_id> | jq .

# 检查 results 字段
curl http://localhost:5001/api/test/status/<execution_id> | jq '.results'
```

### 4.3 检查数据库

```bash
# 检查 diagnosis_results 表是否有数据
sqlite3 backend_python/database.db "SELECT * FROM diagnosis_results WHERE execution_id='<execution_id>' LIMIT 10;"
```

---

## 五、解决方案

### 方案 1: 检查 AI 调用状态（推荐）

**步骤**:
1. 查看后端日志确认 AI 调用是否成功
2. 检查 API Key 配置是否正确
3. 验证 AI 平台是否可用

**预期结果**:
- AI 调用成功，有结果返回
- `results.length > 0`

### 方案 2: 添加详细日志

**前端代码** (`report-v2.js`):

```javascript
async loadReportData(executionId, reportId) {
  console.log('[ReportPageV2] 加载报告数据:', { executionId, reportId });

  try {
    const reportService = require('../../services/reportService').default;
    const id = executionId || this.data.executionId;

    if (!id) {
      throw new Error('缺少执行 ID');
    }

    showLoading('加载报告中...');

    // 获取完整报告
    const report = await reportService.getFullReport(id);

    // 🔍 添加详细日志
    console.log('[ReportPageV2] 完整报告数据:', JSON.stringify(report, null, 2));
    console.log('[ReportPageV2] results:', report.results);
    console.log('[ReportPageV2] result_count:', report.result_count);

    // ...
  } catch (error) {
    console.error('[ReportPageV2] 加载报告数据失败:', error);
    // ...
  }
}
```

### 方案 3: 后端添加调试日志

**后端代码** (`diagnosis_views.py`):

```python
# 【P0 关键修复 - 2026-03-07】完成时总是返回结果数据
if is_completed:
    from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository
    result_repo = DiagnosisResultRepository()

    results = result_repo.get_by_execution_id(task_id)

    # 🔍 添加调试日志
    api_logger.info(
        f"[TaskStatus] 完成时返回结果：{task_id}, "
        f"results_count={len(results) if results else 0}, "
        f"results={results[:2] if results else '[]'}"  # 只记录前 2 条
    )

    response_data['results'] = results or []
    response_data['result_count'] = len(results) if results else 0
```

---

## 六、临时解决方案

### 从历史记录查看

从日志可以看到：
```
[Storage] ✅ 诊断记录已添加到列表：062c49d8-71c6-44d6-ab6c-e034a927ec02
[报告详情页] ✅ 本地缓存命中，直接加载
```

**说明**: 诊断记录已保存到本地存储。

**临时方案**:
1. 返回首页
2. 进入"历史记录"
3. 点击对应的诊断记录查看详情

---

## 七、总结

### 问题级别

🔴 **P0 关键问题** - 诊断完成但无结果数据

### 影响范围

- 用户体验：诊断完成后无法查看报告
- 数据完整性：AI 调用结果可能丢失

### 优先级

**立即处理** - 需要尽快确定是 AI 调用失败还是数据传输问题

### 下一步行动

1. **立即**: 检查后端日志确认 AI 调用状态
2. **1 小时内**: 验证 API Key 配置
3. **今天**: 修复问题并重新测试

---

**分析人**: 首席全栈工程师  
**日期**: 2026-03-11  
**状态**: 等待后端日志确认
