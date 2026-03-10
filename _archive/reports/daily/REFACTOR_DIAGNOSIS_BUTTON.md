# AI 品牌战略诊断按钮逻辑状态机重构方案

## 问题诊断

**核心 Bug**: 诊断按钮启动后长时间卡在"诊断中"状态 (`isTesting: true`),无法根据后端任务进度切换状态。

**根因分析**:
1. `wx.request` 或 `uploadFile` 的 `complete` 回调中缺少明确的状态重置逻辑
2. 轮询控制器在异常情况下未能正确停止
3. 错误处理路径未覆盖所有分支，导致状态死锁

---

## 重构后的 index.js 核心函数

### 1. startBrandTest - 状态机入口

```javascript
/**
 * 【核心重构】启动品牌诊断 - 状态机模式
 * 确保诊断请求在 success、fail、complete 生命周期中都有明确的状态重置逻辑
 * 
 * 状态流转:
 * idle → checking → testing → completed/error → idle
 */
startBrandTest: function() {
  try {
    // ===== 状态 1: 输入验证 =====
    const brandName = this.data.brandName.trim();
    if (!brandName) {
      wx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
      return;
    }

    // 校验 AI 平台选择
    if (!this.validateModelSelection()) {
      return;
    }

    // 【P0 修复】确保数组数据存在
    const domesticAiModels = Array.isArray(this.data.domesticAiModels) ? this.data.domesticAiModels : [];
    const overseasAiModels = Array.isArray(this.data.overseasAiModels) ? this.data.overseasAiModels : [];
    const competitorBrands = Array.isArray(this.data.competitorBrands) ? this.data.competitorBrands : [];

    // 获取当前市场选中的模型
    let selectedModels = this.getCurrentMarketSelectedModels();
    let customQuestions = this.getValidQuestions();

    if (selectedModels.length === 0) {
      wx.showToast({ title: '请选择至少一个 AI 模型', icon: 'error' });
      return;
    }

    // 使用默认问题列表 (如果为空)
    if (customQuestions.length === 0) {
      customQuestions = [
        "{brandName}的核心竞争优势是什么？",
        "{brandName}在目标用户群体中的认知度如何？",
        "{brandName}与竞品的主要差异化体现在哪里？"
      ];
    }

    // ===== 状态 2: 进入诊断中状态 (原子操作) =====
    // 关键：在发起请求前，必须原子性地设置状态，防止死循环
    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      hasLastReport: false,  // 清除旧报告标记
      completedTime: null,
      currentStage: 'checking'  // 新阶段：验证中
    });

    // 保存用户 AI 平台偏好
    this.saveUserPlatformPreferences();

    // ===== 状态 3: 发起诊断请求 =====
    const brandList = [brandName, ...competitorBrands];
    this._executeDiagnosis(brandList, selectedModels, customQuestions);

  } catch (error) {
    // 【防御性异常拦截器】确保任何异常都能恢复按钮状态
    console.error('[startBrandTest] 异常捕获:', error);
    this._resetButtonState();
    this.handleException(error, '诊断启动');
  }
},
```

### 2. _executeDiagnosis - 完整生命周期管理

```javascript
/**
 * 【核心重构】执行诊断请求 - 完整的生命周期管理
 * 包含 success、fail、complete 三个生命周期的状态处理
 */
_executeDiagnosis: async function(brandList, selectedModels, customQuestions) {
  wx.showLoading({ title: '启动诊断...', mask: true });

  try {
    // ===== 生命周期 1: 启动诊断 =====
    const inputData = {
      brandName: brandList[0],
      competitorBrands: brandList.slice(1),
      selectedModels,
      customQuestions
    };

    const executionId = await startDiagnosis(inputData);
    console.log('[诊断启动] ✅ 任务创建成功，执行 ID:', executionId);

    // ===== 生命周期 2: 创建轮询控制器 (带完整回调) =====
    this.pollingController = createPollingController(
      executionId,
      // onProgress: 进度回调
      (parsedStatus) => {
        this.setData({
          testProgress: parsedStatus.progress || 0,
          progressText: parsedStatus.statusText || '诊断中...',
          currentStage: parsedStatus.stage || 'analyzing',
          debugJson: JSON.stringify(parsedStatus, null, 2)
        });
      },
      // onComplete: 完成回调 (最关键)
      (parsedStatus) => {
        wx.hideLoading();
        this._onDiagnosisComplete(parsedStatus, executionId);
      },
      // onError: 错误回调
      (error) => {
        wx.hideLoading();
        this._onDiagnosisError(error);
      }
    );

  } catch (err) {
    // ===== 生命周期 3: 启动失败处理 =====
    wx.hideLoading();
    this._onDiagnosisError(err);
  }
},
```

### 3. _onDiagnosisComplete - 状态闭环

```javascript
/**
 * 【核心重构】诊断完成处理 - 确保状态闭环
 * @param {Object} parsedStatus - 解析后的状态
 * @param {string} executionId - 执行 ID
 */
_onDiagnosisComplete: function(parsedStatus, executionId) {
  try {
    console.log('[诊断完成] ✅ 执行 ID:', executionId, '进度:', parsedStatus.progress);

    // 【P1 新增】部分完成警告提示
    if (parsedStatus.warning || parsedStatus.missing_count > 0) {
      const resultsCount = (parsedStatus.detailed_results || parsedStatus.results || []).length;
      const totalCount = resultsCount + (parsedStatus.missing_count || 0);
      wx.showModal({
        title: '诊断提示',
        content: `诊断部分完成：已获取 ${resultsCount}/${totalCount} 个结果\n${parsedStatus.warning || '部分 AI 调用失败，已展示可用结果'}`,
        showCancel: false,
        confirmText: '查看结果'
      });
    }

    // ===== 状态闭环：关键修复 =====
    // 1. 立即更新按钮状态 (原子操作)
    // 2. 设置 testCompleted: true 和 hasLastReport: true
    this.setData({
      isTesting: false,        // 停止加载状态
      testCompleted: true,     // 标记诊断完成
      hasLastReport: true,     // 标记有报告可查看
      completedTime: this.getCompletedTimeText(),
      currentStage: 'completed'
    });

    // ===== 数据持久化 =====
    const resultsToSave = parsedStatus.detailed_results || parsedStatus.results || [];
    const competitiveAnalysisToSave = parsedStatus.competitive_analysis || {};

    const saveSuccess = saveDiagnosisResult(executionId, {
      brandName: this.data.brandName,
      competitorBrands: this.data.competitorBrands || [],
      selectedModels: parsedStatus.selectedModels || [],
      customQuestions: parsedStatus.customQuestions || [],
      completedAt: new Date().toISOString(),
      results: resultsToSave || [],
      detailedResults: parsedStatus.detailed_results || [],
      competitiveAnalysis: competitiveAnalysisToSave,
      brandScores: competitiveAnalysisToSave.brandScores || {},
      rawResponse: parsedStatus
    });

    if (saveSuccess) {
      console.log('[数据持久化] ✅ Storage 保存成功:', executionId);
    }

    // ===== 跳转结果页 =====
    wx.navigateTo({
      url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}`
    });

    // ===== 异步数据处理 (不阻塞跳转) =====
    setTimeout(() => {
      try {
        const rawResults = parsedStatus.detailed_results || parsedStatus.results || [];
        const dashboardData = generateDashboardData(rawResults, {
          brandName: this.data.brandName,
          competitorBrands: this.data.competitorBrands
        });

        const processedReportData = processReportData({
          results: rawResults,
          detailed_results: rawResults,
          semantic_drift_data: parsedStatus.semantic_drift_data,
          recommendation_data: parsedStatus.recommendation_data,
          competitive_analysis: parsedStatus.competitive_analysis
        });

        this.setData({
          reportData: processedReportData,
          trendChartData: generateTrendChartData(processedReportData),
          predictionData: extractPredictionData(processedReportData),
          scoreData: extractScoreData(processedReportData),
          competitionData: extractCompetitionData(processedReportData),
          sourceListData: extractSourceListData(processedReportData),
          dashboardData: dashboardData
        });
        console.log('[异步数据处理] ✅ 完成');
      } catch (error) {
        console.error('[异步数据处理] 失败:', error);
      }
    }, 0);

  } catch (error) {
    // 【防御性处理】即使处理失败也要确保按钮状态正确
    console.error('[_onDiagnosisComplete] 处理失败:', error);
    this.setData({
      isTesting: false,
      testCompleted: true,
      completedTime: this.getCompletedTimeText()
    });
    wx.showToast({ title: '处理结果失败', icon: 'none' });
  }
},
```

### 4. _onDiagnosisError - 按钮恢复

```javascript
/**
 * 【核心重构】诊断错误处理 - 确保按钮可恢复
 * 即使后端崩溃，前端按钮也能恢复可点击状态
 * @param {Error} error - 错误对象
 */
_onDiagnosisError: function(error) {
  console.error('[诊断错误] ❌', error);

  // ===== 状态恢复：关键修复 =====
  // 确保按钮状态重置，避免死循环
  this._resetButtonState();

  // 使用统一异常拦截器处理
  const friendlyError = this.handleException(error, '诊断启动');

  // 显示友好错误提示
  wx.showModal({
    title: '诊断失败',
    content: friendlyError,
    showCancel: false,
    confirmText: '我知道了'
  });
},
```

### 5. _resetButtonState - 统一状态恢复

```javascript
/**
 * 【新增】重置按钮状态 - 统一状态恢复函数
 * 确保按钮在任何错误情况下都能恢复可点击状态
 */
_resetButtonState: function() {
  this.setData({
    isTesting: false,
    testProgress: 0,
    testCompleted: false,
    currentStage: 'error'
  });
},
```

---

## 重构后的 index.wxml 按钮区域代码

```xml
<!-- 主操作按钮区域 - 简化逻辑 -->
<view class="main-action-section">
  <!-- 统一按钮：根据 appState 切换文案和状态 -->
  <button 
    class="scan-button {{isTesting ? 'testing' : ''}} {{testCompleted ? 'completed' : ''}}"
    bindtap="startBrandTest"
    disabled="{{isTesting}}">
    
    <text class="button-content">
      <!-- 加载动画 -->
      <text class="loading-spinner" wx:if="{{isTesting}}"></text>
      
      <!-- 按钮文字：根据状态动态切换 -->
      <text class="button-text">
        <block wx:if="{{isTesting}}">
          诊断中... {{testProgress}}%
        </block>
        <block wx:elif="{{testCompleted}}">
          重新诊断
        </block>
        <block wx:else>
          AI 品牌战略诊断
        </block>
      </text>
    </text>
  </button>

  <!-- 诊断完成后的查看报告入口 (显著位置) -->
  <view class="view-report-entry {{testCompleted ? 'visible' : 'hidden'}}" 
        bindtap="viewReport">
    <text class="entry-icon">📊</text>
    <text class="entry-text">查看诊断报告</text>
    <text class="entry-time" wx:if="{{completedTime}}">{{completedTime}}</text>
  </view>
</view>

<!-- 分析卡片：显示当前任务状态 -->
<analysis-card
  title="AI 品牌认知诊断"
  subtitle="实时监控 AI 对品牌的认知状态"
  status="{{currentStage}}"
  progress="{{testProgress}}"
  data="{{reportData}}"
  loading="{{isTesting}}"
  wx:if="{{isTesting || reportData}}">
</analysis-card>
```

---

## 配套 WXSS 样式

```wxss
/* 主操作按钮区域 */
.main-action-section {
  margin: 40rpx 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
}

/* 诊断按钮 - 统一样式 */
.scan-button {
  width: 100%;
  height: 100rpx;
  border-radius: 50rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 32rpx;
  font-weight: 600;
  box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
  border: none;
  padding: 0;
}

.scan-button[disabled] {
  background: linear-gradient(135deg, #a0a8c0 0%, #8a7fb0 100%);
  opacity: 0.8;
}

.scan-button.testing {
  animation: pulse 1.5s infinite;
}

.scan-button.completed {
  background: linear-gradient(135deg, #51cf66 0%, #37b24d 100%);
}

.button-content {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

/* 加载动画 */
.loading-spinner {
  display: inline-block;
  width: 32rpx;
  height: 32rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}

/* 查看报告入口 */
.view-report-entry {
  width: 100%;
  height: 80rpx;
  border-radius: 40rpx;
  background: rgba(255, 255, 255, 0.95);
  border: 2rpx solid #667eea;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  box-shadow: 0 4rpx 16rpx rgba(102, 126, 234, 0.2);
  transition: all 0.3s ease;
  cursor: pointer;
}

.view-report-entry.visible {
  opacity: 1;
  transform: translateY(0);
}

.view-report-entry.hidden {
  opacity: 0;
  transform: translateY(-20rpx);
  pointer-events: none;
}

.entry-icon {
  font-size: 36rpx;
}

.entry-text {
  font-size: 30rpx;
  font-weight: 600;
  color: #667eea;
}

.entry-time {
  font-size: 24rpx;
  color: #999;
  margin-left: 8rpx;
}
```

---

## 关键修复点总结

| 问题 | 修复方案 | 代码位置 |
|------|----------|----------|
| 状态死循环 | 在 `complete` 回调中强制设置 `isTesting: false` | `_onDiagnosisComplete` |
| 错误恢复缺失 | 统一错误处理，确保按钮状态重置 | `_onDiagnosisError` + `_resetButtonState` |
| 轮询未停止 | 轮询控制器在回调中自动停止 | `brandTestService.createPollingController` |
| UI 状态不同步 | 使用 `currentStage` 统一状态枚举 | `setData` 原子操作 |
| 超时处理缺失 | 8 分钟无进度更新自动超时 | `brandTestService` 中的 `noProgressTimeout` |

---

## 状态流转图

```
┌─────────────┐
│    idle     │
│  (初始状态)  │
└──────┬──────┘
       │ startBrandTest()
       ▼
┌─────────────┐
│  checking   │
│  (验证输入)  │
└──────┬──────┘
       │ 验证通过
       ▼
┌─────────────┐
│   testing   │◄─────┐
│  (诊断中)    │      │ 轮询中
└──────┬──────┘      │
       │             │
       ├─ complete ──┘
       │
       ├─ success
       │     ▼
       │  ┌─────────────┐
       │  │  completed  │
       │  │  (可查看)    │
       │  └─────────────┘
       │
       └─ error
             ▼
          ┌─────────────┐
          │    error    │
          │  (可重试)    │
          └─────────────┘
```

---

## 使用说明

1. **替换 index.js 中的相关函数**:
   - `startBrandTest` → 使用新的状态机版本
   - `callBackendBrandTest` → 替换为 `_executeDiagnosis`
   - 添加 `_onDiagnosisComplete`、`_onDiagnosisError`、`_resetButtonState`

2. **替换 index.wxml 按钮区域**:
   - 删除冗余的 `completed-actions` 和 `scan-button` 互斥判断
   - 采用单一按钮根据状态切换文案的模式

3. **添加 WXSS 样式**:
   - 复制上述样式到 `index.wxss`

4. **测试场景**:
   - ✅ 正常诊断完成 → 按钮变为"重新诊断",显示"查看报告"入口
   - ✅ 后端报错 500 → 按钮恢复可点击，显示友好错误
   - ✅ 网络超时 → 8 分钟无进度自动超时，按钮恢复
   - ✅ 认证失败 → 熔断机制触发，按钮恢复
