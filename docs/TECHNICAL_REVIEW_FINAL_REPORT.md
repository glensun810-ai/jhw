# 诊断报告空数据问题 - 技术审查最终报告

**审查会议日期**: 2026-03-11  
**审查主持人**: 系统首席架构师  
**参会团队**: 前端团队、后端团队、测试团队、架构组

---

## 一、问题回顾

### 1.1 问题现象
诊断任务完成后，报告详情页（report-v2）显示空数据：
- ✅ 诊断任务成功完成（`status: completed, progress: 100%`）
- ✅ 后端返回了 `brandScores` 数据
- ❌ 报告页图表组件收到空数据：`BrandDistribution: {}`, `SentimentChart: {}`, `KeywordCloud: count: 0`

### 1.2 影响范围
- **影响模块**: 品牌诊断报告生成与展示
- **影响用户**: 所有使用品牌诊断功能的用户
- **影响程度**: P0 级（核心功能不可用）

---

## 二、根本原因分析（RCA）

### 2.1 数据流断裂（P0 - 最关键）

**问题位置**: 后端 API `/test/status/<task_id>`

**发现**:
```python
# 原始代码（有缺陷）
if task_id in execution_store:
    response_data = {
        'task_id': task_id,
        'progress': task_status.get('progress', 0),
        'stage': task_status.get('stage', 'init'),
        'status': task_status.get('status', 'init'),
        'results': task_status.get('results', []),
        # ❌ 缺少 detailed_results, brand_scores 等关键字段
    }
```

**影响**: 前端无法获取 `detailed_results` 数组，导致 `generateDashboardData` 返回空数据

---

### 2.2 多轮询实例并存（P1）

**问题位置**: `services/brandTestService.js` + `miniprogram/services/diagnosisService.js`

**发现**: WebSocket 错误回调被多次触发，每次都创建新的轮询实例

**日志证据**:
```
[轮询响应] 第 6 次，耗时：44ms
[轮询响应] 第 10 次，耗时：41ms
[轮询响应] 第 13 次，耗时：44ms
```

---

### 2.3 报告页数据源单一（P1）

**问题位置**: `miniprogram/pages/report-v2/report-v2.js`

**发现**: 仅依赖云函数获取数据，没有 fallback 机制

---

## 三、修复方案审查

### 3.1 后端 API 修复 ✅

**文件**: `backend_python/wechat_backend/views.py`

**修复内容**:
```python
if task_id in execution_store:
    task_status = execution_store[task_id]
    
    # 【P0 关键修复】提取所有详细结果字段
    results_data = task_status.get('results', [])
    detailed_results = task_status.get('detailed_results', [])
    brand_scores = task_status.get('brand_scores', {})
    competitive_analysis = task_status.get('competitive_analysis', {})
    semantic_drift_data = task_status.get('semantic_drift_data', {})
    recommendation_data = task_status.get('recommendation_data', {})
    negative_sources = task_status.get('negative_sources', [])
    overall_score = task_status.get('overall_score', 0)
    
    # 添加 fallback 逻辑
    if not detailed_results and results_data:
        if isinstance(results_data, list):
            detailed_results = results_data
        elif isinstance(results_data, dict):
            detailed_results = results_data.get('detailed_results', [])
            # ... 提取其他字段
    
    response_data = {
        'task_id': task_id,
        'progress': task_status.get('progress', 0),
        'stage': task_status.get('stage', 'init'),
        'status': task_status.get('status', 'init'),
        'results': results_data,
        'detailed_results': detailed_results,  # ✅ 新增
        'brand_scores': brand_scores,  # ✅ 新增
        'competitive_analysis': competitive_analysis,  # ✅ 新增
        'semantic_drift_data': semantic_drift_data,  # ✅ 新增
        'recommendation_data': recommendation_data,  # ✅ 新增
        'negative_sources': negative_sources,  # ✅ 新增
        'overall_score': overall_score,  # ✅ 新增
        'is_completed': task_status.get('status') == 'completed',
        'created_at': task_status.get('start_time', None)
    }
```

**审查结论**: ✅ 通过 - 确保后端返回完整数据

---

### 3.2 防止轮询重复启动 ✅

**文件**: `services/brandTestService.js`, `miniprogram/services/diagnosisService.js`

**修复内容**:
```javascript
// brandTestService.js
onError: (error) => {
  if (pollingInstance && pollingInstance.isActive) {
    console.warn('[onError] ⚠️ 轮询已在运行中，跳过重复启动');
    return;
  }
  // ...
}

// diagnosisService.js
_connectWebSocket(executionId, callbacks) {
  this.isPollingStarted = false;  // 初始化标志
  
  onError: (error) => {
    if (this.isPollingStarted) {
      console.warn('[onError] ⚠️ 轮询已启动，跳过重复降级');
      return;
    }
  }
}

_startPolling(executionId, callbacks) {
  this.isPollingStarted = true;  // 设置标志
  // ...
}
```

**审查结论**: ✅ 通过 - 有效防止多实例并存

---

### 3.3 报告页多数据源加载 ✅

**文件**: `miniprogram/pages/report-v2/report-v2.js`

**修复内容**:
```javascript
async loadReportData(executionId, reportId) {
  // Step 1: 检查全局变量（诊断完成时传递）
  const app = getApp();
  if (app && app.globalData && app.globalData.pendingReport) {
    if (pendingReport.executionId === id) {
      report = { /* 从全局变量获取 */ };
      dataSource = 'globalData';
    }
  }

  // Step 2: 从云函数获取
  if (!report || !report.brandDistribution) {
    const cloudReport = await reportService.getFullReport(id);
    if (cloudReport.brandDistribution) {
      report = { /* 从云函数获取 */ };
      dataSource = 'cloudFunction';
    }
  }

  // Step 3: 从 Storage 读取备份
  if (!report || !report.brandDistribution) {
    const storageData = wx.getStorageSync('last_diagnostic_results');
    if (storageData) {
      report = { /* 从 Storage 获取 */ };
      dataSource = 'storage';
    }
  }
}
```

**审查结论**: ✅ 通过 - 三层 fallback 机制确保数据可用性

---

### 3.4 诊断完成时传递数据 ✅

**文件**: `pages/index/index.js`

**修复内容**:
```javascript
handleDiagnosisComplete(parsedStatus, executionId) {
  // 先处理数据，再跳转
  let dashboardData = null;
  let processedReportData = null;

  try {
    const rawResults = parsedStatus.detailed_results || parsedStatus.results || [];
    
    if (rawResults && rawResults.length > 0) {
      dashboardData = generateDashboardData(rawResults, {...});
      processedReportData = processReportData({...});
      
      // 保存到全局变量，供报告页使用
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.pendingReport = {
          executionId: executionId,
          dashboardData: dashboardData,
          processedReportData: processedReportData,
          rawResults: rawResults,
          timestamp: Date.now()
        };
      }
    }
  } catch (error) {
    console.error('数据处理失败:', error);
  }

  // 跳转到报告页
  setTimeout(() => {
    wx.navigateTo({ url: `/pages/report-v2/report-v2?executionId=${executionId}` });
  }, 500);
}
```

**审查结论**: ✅ 通过 - 确保数据在跳转前已准备就绪

---

### 3.5 增强调试日志 ✅

**文件**: `services/brandTestService.js`

**修复内容**: 在 `generateDashboardData` 函数中添加详细日志
- 输入参数验证
- 数据提取过程
- 输出结果验证

**审查结论**: ✅ 通过 - 便于问题排查

---

## 四、审查发现的额外问题

### 4.1 组件空数据处理（P2）

**发现**: 组件已正确处理空数据，但错误提示可以更友好

**建议**: 添加更详细的空数据原因说明

---

### 4.2 网络错误重试机制（P2）

**发现**: 报告页加载失败后，用户需要手动刷新

**建议**: 添加自动重试机制（最多 3 次）

---

### 4.3 数据版本兼容性（P2）

**发现**: Storage 数据格式可能有多个版本

**建议**: 添加数据版本迁移逻辑

---

## 五、测试验证计划

### 5.1 单元测试

| 测试用例 | 测试内容 | 预期结果 |
|---------|---------|---------|
| `test_backend_api_returns_detailed_results` | 后端 API 返回 detailed_results | ✅ 包含所有字段 |
| `test_prevent_duplicate_polling` | 防止轮询重复启动 | ✅ 只有一个实例 |
| `test_report_page_load_from_global_data` | 报告页从全局变量加载 | ✅ 数据正确显示 |
| `test_report_page_fallback_to_storage` | 报告页 Storage fallback | ✅ 降级成功 |

### 5.2 集成测试

| 测试场景 | 测试步骤 | 预期结果 |
|---------|---------|---------|
| 完整诊断流程 | 启动诊断 → 等待完成 → 查看报告 | ✅ 报告显示完整数据 |
| WebSocket 失败降级 | 禁用 WebSocket → 启动诊断 → 查看报告 | ✅ 轮询正常工作 |
| 网络中断恢复 | 诊断中断网 → 恢复 → 查看报告 | ✅ 数据不丢失 |

### 5.3 性能测试

| 测试项目 | 指标 | 目标值 |
|---------|------|-------|
| 报告加载时间 | 从跳转到显示 | < 2 秒 |
| 数据聚合耗时 | generateDashboardData | < 500ms |
| 轮询请求频率 | 请求间隔 | ≥ 1.5 秒 |

---

## 六、上线检查清单

### 6.1 代码审查
- [x] 后端 API 修复已审查
- [x] 前端轮询修复已审查
- [x] 报告页数据加载修复已审查
- [x] 调试日志已添加

### 6.2 测试验证
- [ ] 单元测试通过率 100%
- [ ] 集成测试通过
- [ ] 性能测试达标
- [ ] 回归测试通过

### 6.3 部署准备
- [ ] 后端代码已打包
- [ ] 前端代码已编译
- [ ] 数据库迁移脚本（如有）
- [ ] 回滚方案已准备

### 6.4 监控告警
- [ ] API 错误率监控
- [ ] 报告加载失败率监控
- [ ] 轮询异常监控
- [ ] 告警阈值已设置

---

## 七、风险评估

| 风险项 | 可能性 | 影响 | 缓解措施 |
|-------|-------|------|---------|
| 后端修复引入新 bug | 低 | 高 | 灰度发布 + 快速回滚 |
| 前端缓存数据格式不兼容 | 中 | 中 | 添加数据版本检查 |
| 轮询逻辑修复不彻底 | 低 | 高 | 加强日志监控 |
| 性能下降 | 低 | 中 | 性能测试验证 |

---

## 八、最终结论

### 8.1 审查结论
**✅ 修复方案通过审查**

所有关键问题已得到妥善解决：
1. ✅ 后端 API 现在返回完整的 `detailed_results` 和其他必要字段
2. ✅ 轮询重复启动问题已修复
3. ✅ 报告页实现了三层数据源 fallback 机制
4. ✅ 诊断完成时数据正确传递到报告页
5. ✅ 调试日志增强便于问题排查

### 8.2 上线建议
1. **分阶段发布**:
   - 第一阶段：后端 API 修复（灰度 10%）
   - 第二阶段：前端修复（灰度 20%）
   - 第三阶段：全量发布

2. **监控重点**:
   - 后端 API 响应时间和错误率
   - 报告页加载成功率
   - 轮询实例数量

3. **回滚方案**:
   - 准备旧版本代码包
   - 配置快速回滚脚本
   - 指定责任人

### 8.3 后续优化
1. 添加数据版本迁移机制
2. 实现报告页自动重试
3. 优化组件空数据提示
4. 考虑引入 IndexedDB 替代 Storage

---

## 九、签字确认

| 角色 | 姓名 | 日期 | 签字 |
|------|------|------|------|
| 首席架构师 | | 2026-03-11 | |
| 前端负责人 | | 2026-03-11 | |
| 后端负责人 | | 2026-03-11 | |
| 测试负责人 | | 2026-03-11 | |
| 产品经理 | | 2026-03-11 | |

---

**审查会议结束时间**: 2026-03-11  
**下次审查日期**: 2026-03-18（上线后一周回顾）
