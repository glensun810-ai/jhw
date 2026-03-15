# 历史诊断记录查看功能完善实施计划

**制定日期**: 2026-03-12  
**优先级**: P0 - 高优先级  
**状态**: 待实施  

---

## 一、现状分析

### 1.1 当前功能状态

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 历史列表展示 | ✅ 已实现 | `pages/history/history.js` 可正常显示历史列表 |
| 后端历史记录 API | ✅ 已实现 | `/api/diagnosis/history` 返回历史列表 |
| 后端报告详情 API | ✅ 已实现 | `/api/diagnosis/report/{execution_id}` 返回完整报告 |
| 历史详情页 | ⚠️ 部分实现 | `pages/history-detail/history-detail.js` 有基础逻辑 |
| 报告页 V2 加载历史 | ⚠️ 部分实现 | `report-v2.js` 有 `loadHistoryReport` 方法 |
| 诊断页加载历史 | ❌ 未实现 | `diagnosis.js` 的 `loadHistoryReport` 方法为空 |

### 1.2 数据库存储结构

```sql
-- 诊断报告主表
CREATE TABLE diagnosis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,      -- 执行 ID（前端查询关键字段）
    user_id TEXT NOT NULL,                   -- 用户 ID
    brand_name TEXT NOT NULL,                -- 品牌名称
    competitor_brands TEXT,                  -- 竞品列表（JSON）
    selected_models TEXT,                    -- AI 模型列表（JSON）
    status TEXT DEFAULT 'processing',        -- 状态：processing/completed/failed
    progress INTEGER DEFAULT 0,              -- 进度：0-100
    stage TEXT DEFAULT 'init',               -- 阶段
    is_completed BOOLEAN DEFAULT 0,          -- 是否完成
    created_at TEXT,                         -- 创建时间
    updated_at TEXT,                         -- 更新时间
    -- ... 其他字段
);

-- 诊断结果明细表
CREATE TABLE diagnosis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,              -- 关联 diagnosis_reports.id
    execution_id TEXT NOT NULL,              -- 执行 ID（便于查询）
    brand TEXT NOT NULL,                     -- 品牌名称
    question TEXT,                           -- 问题
    model TEXT,                              -- AI 模型
    response TEXT,                           -- AI 响应
    geo_data TEXT,                           -- GEO 分析数据（JSON）
    -- ... 其他字段
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
);
```

### 1.3 数据流分析

```
历史列表页 (history.js)
    ↓
    点击历史记录
    ↓
    跳转参数：{ reportId, executionId, brandName }
    ↓
历史详情页 (history-detail.js) 或 报告页 V2 (report-v2.js)
    ↓
    loadHistoryReport(reportId/executionId)
    ↓
    loadReportData(executionId)
    ↓
数据源优先级:
    1. globalData.pendingReport (通常为空，因为是历史数据)
    2. 云函数 getFullReport(executionId) → 后端 API
    3. Storage 本地缓存
```

---

## 二、问题识别

### 2.1 核心问题

**问题**: 用户从历史列表点击记录后，无法查看完整的历史诊断报告详情

**原因**:
1. `diagnosis.js` 的 `loadHistoryReport` 方法未实现（只有注释"这里应该调用获取历史报告的 API"）
2. `report-v2.js` 的 `loadHistoryReport` 方法依赖 `loadReportData`，但逻辑不够健壮
3. 历史数据加载没有统一的入口和错误处理机制
4. 本地缓存和服务器数据的优先级策略不清晰

### 2.2 具体问题清单

| 编号 | 问题描述 | 影响 | 优先级 |
|------|---------|------|--------|
| P1 | `diagnosis.js` `loadHistoryReport` 方法为空 | 从诊断页打开历史报告失败 | P0 |
| P2 | `report-v2.js` 历史数据加载逻辑不清晰 | 可能加载失败或显示空数据 | P0 |
| P3 | 后端 `/api/diagnosis/report/{id}` 可能返回空数据 | 前端看不到结果 | P0 |
| P4 | 本地缓存策略不完善 | 网络异常时无法查看历史 | P1 |
| P5 | 错误提示不友好 | 用户体验差 | P1 |

---

## 三、实施计划

### 3.1 总体目标

**目标**: 实现完整、可靠的历史诊断记录查看功能，用户可以随时查看任何历史诊断的完整报告。

### 3.2 实施阶段

| 阶段 | 任务 | 预计时间 | 负责人 | 状态 |
|------|------|----------|--------|------|
| **阶段一** | 后端 API 验证和修复 | 2 小时 | 后端组 | 待开始 |
| **阶段二** | 前端历史数据加载逻辑统一 | 3 小时 | 前端组 | 待开始 |
| **阶段三** | 本地缓存优化 | 2 小时 | 前端组 | 待开始 |
| **阶段四** | 错误处理和用户体验优化 | 2 小时 | 前端组 | 待开始 |
| **阶段五** | 集成测试和验收 | 2 小时 | QA 组 | 待开始 |

---

## 四、详细实施方案

### 阶段一：后端 API 验证和修复 (2 小时)

#### 任务 1.1: 验证 `/api/diagnosis/report/{execution_id}` API

**目标**: 确保后端 API 能正确返回历史报告数据

**验证步骤**:
```bash
# 1. 获取一个已完成的 execution_id
sqlite3 backend_python/database.db "SELECT execution_id FROM diagnosis_reports WHERE status='completed' LIMIT 1"

# 2. 调用 API
curl http://localhost:5001/api/diagnosis/report/<execution_id> | jq '.'

# 3. 检查返回数据结构
# 必须包含:
# - brandDistribution: { data: {...}, total_count: N }
# - sentimentDistribution: { data: {...}, total_count: N }
# - keywords: [...]
# - results: [...]
```

**预期结果**:
- ✅ API 返回 200 状态码
- ✅ 包含 `brandDistribution` 且有数据
- ✅ 包含 `sentimentDistribution` 且有数据
- ✅ 包含 `keywords` 且有数据
- ✅ 包含 `results` 且有数据

**修复点** (如果验证失败):
```python
# 文件：backend_python/wechat_backend/diagnosis_report_service.py
# 方法：get_full_report()

# 确保结果数据不为空时，正确计算各项指标
def get_full_report(self, execution_id: str):
    # ...
    results = self.result_repo.get_by_execution_id(execution_id)
    
    if not results or len(results) == 0:
        # 创建降级报告，但要包含元数据
        return self._create_fallback_report(...)
    
    # 计算品牌分布
    brand_distribution = self._calculate_brand_distribution(results)
    
    # ✅ 关键：确保 brand_distribution 包含 data 和 total_count
    if not brand_distribution.get('data') or brand_distribution.get('total_count', 0) == 0:
        api_logger.error(f"❌ 品牌分布为空：execution_id={execution_id}")
        # 记录详细错误，但不中断流程
    
    # 构建完整报告
    full_report = {
        'brandDistribution': brand_distribution,
        'sentimentDistribution': sentiment_distribution,
        'keywords': keywords,
        'results': results,
        # ...
    }
    
    return full_report
```

#### 任务 1.2: 添加历史报告专用 API

**目标**: 为历史报告查看优化 API 响应

**新增端点**:
```python
# 文件：backend_python/wechat_backend/views/diagnosis_api.py

@diagnosis_bp.route('/report/<execution_id>/history', methods=['GET'])
def get_history_report(execution_id):
    """
    获取历史报告（优化版）
    
    专为历史报告查看优化：
    1. 优先从数据库读取，不触发新的诊断
    2. 包含完整的元数据（品牌、时间、状态等）
    3. 即使部分数据缺失，也返回可用的最大数据集
    """
    try:
        service = get_report_service()
        
        # 获取历史报告（不重新计算）
        report = service.get_history_report(execution_id)
        
        if not report:
            return jsonify({
                'error': '报告不存在',
                'execution_id': execution_id,
                'fallback': True
            }), 404
        
        return jsonify(convert_response_to_camel(report)), 200
        
    except Exception as e:
        api_logger.error(f"获取历史报告失败：{e}")
        return jsonify({
            'error': '获取失败',
            'execution_id': execution_id,
            'message': str(e)
        }), 500
```

---

### 阶段二：前端历史数据加载逻辑统一 (3 小时)

#### 任务 2.1: 实现 `diagnosis.js` 的 `loadHistoryReport` 方法

**文件**: `miniprogram/pages/diagnosis/diagnosis.js`

**实现代码**:
```javascript
/**
 * 加载历史报告
 * @param {string} reportId - 报告 ID 或 executionId
 */
async loadHistoryReport(reportId) {
  console.log('[DiagnosisPage] 加载历史报告:', reportId);
  showLoading('加载中...');

  try {
    // 1. 优先从本地缓存加载
    const cachedData = wx.getStorageSync(`history_report_${reportId}`);
    if (cachedData && cachedData.executionId) {
      console.log('[DiagnosisPage] ✅ 从本地缓存加载历史报告');
      
      // 跳转到报告页，传递缓存数据
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.pendingReport = {
          executionId: cachedData.executionId,
          dashboardData: cachedData.dashboardData,
          rawResults: cachedData.rawResults,
          timestamp: cachedData.timestamp,
          isHistory: true  // 标记为历史数据
        };
      }
      
      hideLoading();
      wx.navigateTo({
        url: `/pages/report-v2/report-v2?executionId=${cachedData.executionId}`
      });
      return;
    }

    // 2. 从服务器加载
    console.log('[DiagnosisPage] 从服务器加载历史报告');
    const reportService = require('../../services/reportService').default;
    const report = await reportService.getFullReport(reportId);

    if (report && report.brandDistribution && report.brandDistribution.data) {
      console.log('[DiagnosisPage] ✅ 服务器加载成功');
      
      // 处理数据
      const { generateDashboardData } = require('../../../services/brandTestService');
      const rawResults = report.results || report.detailed_results || [];
      const dashboardData = generateDashboardData(rawResults, {
        brandName: report.brandName || '',
        competitorBrands: report.competitorBrands || []
      });

      // 保存到全局变量
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.pendingReport = {
          executionId: report.executionId || reportId,
          dashboardData: dashboardData,
          rawResults: rawResults,
          timestamp: Date.now(),
          isHistory: true
        };
      }

      // 缓存到本地
      wx.setStorageSync(`history_report_${reportId}`, {
        executionId: report.executionId || reportId,
        dashboardData: dashboardData,
        rawResults: rawResults,
        timestamp: Date.now()
      });

      hideLoading();
      wx.navigateTo({
        url: `/pages/report-v2/report-v2?executionId=${report.executionId || reportId}`
      });
    } else {
      throw new Error('报告数据不完整');
    }
  } catch (error) {
    console.error('[DiagnosisPage] 加载历史报告失败:', error);
    hideLoading();
    
    wx.showModal({
      title: '加载失败',
      content: error.message || '无法加载历史报告，请稍后重试',
      confirmText: '重试',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.loadHistoryReport(reportId);
        } else {
          wx.navigateBack();
        }
      }
    });
  }
}
```

#### 任务 2.2: 增强 `report-v2.js` 的 `loadHistoryReport` 方法

**文件**: `miniprogram/pages/report-v2/report-v2.js`

**修改内容**:
```javascript
/**
 * 加载历史报告
 * @param {string} reportId - 报告 ID 或 executionId
 */
async loadHistoryReport(reportId) {
  console.log('[ReportPageV2] 加载历史报告:', reportId);
  showLoading('加载中...');

  try {
    // 1. 检查全局变量（可能已从 diagnosis.js 传递）
    const app = getApp();
    if (app && app.globalData && app.globalData.pendingReport) {
      const pendingReport = app.globalData.pendingReport;
      if (pendingReport.executionId === reportId && pendingReport.isHistory) {
        console.log('[ReportPageV2] ✅ 从全局变量加载历史数据');
        this.setData({
          brandDistribution: pendingReport.dashboardData?.brandDistribution || {},
          sentimentDistribution: pendingReport.dashboardData?.sentimentDistribution || {},
          keywords: pendingReport.dashboardData?.keywords || [],
          brandScores: pendingReport.dashboardData?.brandScores || {},
          isHistoryData: true,
          hasError: false
        });
        hideLoading();
        return;
      }
    }

    // 2. 从云函数加载
    console.log('[ReportPageV2] 从云函数加载历史报告');
    const reportService = require('../../services/reportService').default;
    const report = await reportService.getFullReport(reportId);

    if (report && report.brandDistribution && report.brandDistribution.data) {
      console.log('[ReportPageV2] ✅ 云函数加载成功');
      this.setData({
        brandDistribution: report.brandDistribution || {},
        sentimentDistribution: report.sentimentDistribution || {},
        keywords: report.keywords || [],
        brandScores: report.brandScores || {},
        isHistoryData: true,
        hasError: false
      });

      // 缓存到 Storage
      wx.setStorageSync(`history_report_${reportId}`, {
        executionId: report.executionId || reportId,
        dashboardData: {
          brandDistribution: report.brandDistribution,
          sentimentDistribution: report.sentimentDistribution,
          keywords: report.keywords,
          brandScores: report.brandScores
        },
        rawResults: report.results || [],
        timestamp: Date.now()
      });

      hideLoading();
    } else {
      throw new Error('报告数据不完整');
    }
  } catch (error) {
    console.error('[ReportPageV2] 加载历史报告失败:', error);
    hideLoading();
    
    // 尝试从 Storage 加载备份
    const cachedData = wx.getStorageSync(`history_report_${reportId}`);
    if (cachedData && cachedData.dashboardData) {
      console.log('[ReportPageV2] ⚠️ 从 Storage 备份加载');
      this.setData({
        brandDistribution: cachedData.dashboardData.brandDistribution || {},
        sentimentDistribution: cachedData.dashboardData.sentimentDistribution || {},
        keywords: cachedData.dashboardData.keywords || [],
        brandScores: cachedData.dashboardData.brandScores || {},
        isHistoryData: true,
        fromBackup: true,
        hasError: false
      });
    } else {
      this.setData({
        hasError: true,
        errorType: 'load_history_failed',
        errorMessage: error.message || '加载失败'
      });
    }
  }
}
```

---

### 阶段三：本地缓存优化 (2 小时)

#### 任务 3.1: 实现智能缓存策略

**文件**: `miniprogram/utils/storage-manager.js`

**新增功能**:
```javascript
/**
 * 保存历史报告到缓存
 * @param {string} executionId - 执行 ID
 * @param {Object} reportData - 报告数据
 * @param {Object} options - 选项
 */
function saveHistoryReport(executionId, reportData, options = {}) {
  const {
    ttl = 7 * 24 * 60 * 60 * 1000,  // 默认 7 天
    compress = false  // 是否压缩
  } = options;

  const cacheKey = `history_report_${executionId}`;
  const cacheData = {
    executionId,
    reportData,
    timestamp: Date.now(),
    expiresAt: Date.now() + ttl
  };

  try {
    if (compress) {
      // 压缩存储（大数据量时）
      const compressed = LZString.compress(JSON.stringify(cacheData));
      wx.setStorageSync(cacheKey + '_compressed', compressed);
    } else {
      wx.setStorageSync(cacheKey, cacheData);
    }
    console.log(`[StorageManager] ✅ 历史报告已缓存：${executionId}`);
  } catch (error) {
    console.error(`[StorageManager] ❌ 缓存失败：${executionId}`, error);
  }
}

/**
 * 从缓存加载历史报告
 * @param {string} executionId - 执行 ID
 * @returns {Object|null} 报告数据，如果不存在或已过期则返回 null
 */
function loadHistoryReport(executionId) {
  const cacheKey = `history_report_${executionId}`;
  
  try {
    // 尝试加载压缩版本
    const compressed = wx.getStorageSync(cacheKey + '_compressed');
    if (compressed) {
      const cacheData = JSON.parse(LZString.decompress(compressed));
      if (cacheData.expiresAt > Date.now()) {
        return cacheData.reportData;
      } else {
        // 已过期，清理
        wx.removeStorageSync(cacheKey + '_compressed');
      }
    }

    // 尝试加载普通版本
    const cacheData = wx.getStorageSync(cacheKey);
    if (cacheData) {
      if (cacheData.expiresAt > Date.now()) {
        return cacheData.reportData;
      } else {
        // 已过期，清理
        wx.removeStorageSync(cacheKey);
      }
    }
  } catch (error) {
    console.error(`[StorageManager] ❌ 加载缓存失败：${executionId}`, error);
  }

  return null;
}

module.exports = {
  saveHistoryReport,
  loadHistoryReport,
  // ... 其他导出
};
```

---

### 阶段四：错误处理和用户体验优化 (2 小时)

#### 任务 4.1: 统一的错误处理

**文件**: `miniprogram/services/reportService.js`

**新增错误类型**:
```javascript
const HistoryErrorTypes = {
  NOT_FOUND: 'HISTORY_NOT_FOUND',
  INCOMPLETE: 'HISTORY_INCOMPLETE',
  EXPIRED: 'HISTORY_EXPIRED',
  LOAD_FAILED: 'HISTORY_LOAD_FAILED'
};

const HistoryErrorMessages = {
  [HistoryErrorTypes.NOT_FOUND]: '该历史报告不存在或已被删除',
  [HistoryErrorTypes.INCOMPLETE]: '该历史报告数据不完整',
  [HistoryErrorTypes.EXPIRED]: '该历史报告已过期，无法查看',
  [HistoryErrorTypes.LOAD_FAILED]: '加载历史报告失败，请检查网络'
};

/**
 * 创建历史报告错误
 */
function createHistoryError(type, details = {}) {
  const error = new Error(HistoryErrorMessages[type] || '未知错误');
  error.type = type;
  error.details = details;
  error.suggestion = getSuggestionForError(type);
  return error;
}

function getSuggestionForError(type) {
  const suggestions = {
    [HistoryErrorTypes.NOT_FOUND]: '建议重新进行诊断',
    [HistoryErrorTypes.INCOMPLETE]: '建议联系技术支持',
    [HistoryErrorTypes.EXPIRED]: '历史报告仅保留 7 天',
    [HistoryErrorTypes.LOAD_FAILED]: '请检查网络连接后重试'
  };
  return suggestions[type] || '请稍后重试';
}

module.exports = {
  HistoryErrorTypes,
  HistoryErrorMessages,
  createHistoryError,
  getSuggestionForError,
  // ... 其他导出
};
```

---

### 阶段五：集成测试和验收 (2 小时)

#### 测试用例

| 用例 ID | 测试场景 | 预期结果 | 状态 |
|---------|---------|----------|------|
| TC-H001 | 从历史列表点击已完成的报告 | 正常显示报告详情 | 待执行 |
| TC-H002 | 从历史列表点击失败的报告 | 显示失败状态和错误信息 | 待执行 |
| TC-H003 | 网络正常时加载历史报告 | 从服务器加载并缓存 | 待执行 |
| TC-H004 | 网络异常时加载历史报告 | 从本地缓存加载 | 待执行 |
| TC-H005 | 缓存过期时加载历史报告 | 提示报告已过期 | 待执行 |
| TC-H006 | 报告不存在时 | 显示友好的错误提示 | 待执行 |
| TC-H007 | 报告数据不完整时 | 显示可用数据并提示 | 待执行 |

---

## 五、验收标准

### 5.1 功能验收

- [ ] 从历史列表可以正常打开任何已完成的报告
- [ ] 报告数据显示完整（品牌分布、情感分析、关键词云）
- [ ] 网络异常时可以从本地缓存加载
- [ ] 报告不存在时显示友好的错误提示
- [ ] 加载过程有明确的 loading 状态
- [ ] 错误提示包含可操作的建议

### 5.2 性能验收

- [ ] 本地缓存加载时间 < 500ms
- [ ] 服务器加载时间 < 3s（网络正常）
- [ ] 缓存命中率 > 80%

### 5.3 用户体验验收

- [ ] 加载过程有进度提示
- [ ] 错误提示友好且可操作
- [ ] 支持重试机制
- [ ] 支持返回上一页

---

## 六、实施时间表

| 日期 | 阶段 | 任务 | 负责人 |
|------|------|------|--------|
| 2026-03-12 上午 | 阶段一 | 后端 API 验证和修复 | 后端组 |
| 2026-03-12 下午 | 阶段二 | 前端历史数据加载逻辑统一 | 前端组 |
| 2026-03-13 上午 | 阶段三 | 本地缓存优化 | 前端组 |
| 2026-03-13 下午 | 阶段四 | 错误处理和用户体验优化 | 前端组 |
| 2026-03-14 上午 | 阶段五 | 集成测试和验收 | QA 组 |

---

## 七、风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 后端 API 返回空数据 | 中 | 高 | 添加降级方案，返回元数据 |
| 本地缓存容量不足 | 低 | 中 | 实现压缩存储和自动清理 |
| 网络异常率高 | 中 | 中 | 强化本地缓存策略 |
| 历史数据量过大 | 低 | 低 | 分页加载和懒加载 |

---

**制定人**: 系统架构组  
**审核人**: ___________  
**批准人**: ___________  
**日期**: 2026-03-12
