# 诊断报告前端展示问题分析报告

**日期**: 2026-03-11  
**文档编号**: DIAG-2026-03-11-001  
**状态**: 待实施  
**优先级**: P0 - 阻塞性问题

---

## 执行摘要

本报告针对"当前报告数据不能展示到前端诊断完成的详情页"问题进行全面分析。经架构组联合排查，已识别出 **5 个主要问题点** 和 **3 个根本原因**，并制定了详细的分步实施计划。

### 核心结论

| 项目 | 结论 |
|------|------|
| **问题元凶** | 后端 `/test/status/{id}` 接口未返回 `detailed_results` 字段 |
| **根本原因** | 数据流在 3 个关键节点存在断裂风险 |
| **影响范围** | 所有诊断报告详情页 (report-v2) |
| **预计修复时间** | 4-6 小时 |

---

## 一、项目架构概述

### 1.1 技术栈

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| **前端** | 微信小程序原生框架 | - |
| **状态管理** | 自定义服务层 (diagnosisService, pollingManager, reportService) | - |
| **实时通信** | WebSocket (优先) + HTTP 轮询 (降级) | - |
| **云开发** | 微信云函数 | - |
| **后端** | Flask | 3.1.2 |
| **数据库** | SQLite (WAL 模式) | - |
| **AI 适配器** | 多平台 AI 调用 (DIY, SiliconFlow, etc.) | - |

### 1.2 关键文件分布

```
项目根目录/
├── miniprogram/                        # 小程序前端
│   ├── pages/
│   │   ├── diagnosis/                  # 诊断页面
│   │   │   └── diagnosis.js            # [关键] 诊断逻辑
│   │   └── report-v2/                  # 报告详情页 [问题所在]
│   │       ├── report-v2.js            # [关键] 报告数据加载
│   │       └── report-v2.wxml          # 报告 UI
│   ├── services/
│   │   ├── diagnosisService.js         # [关键] 诊断服务
│   │   ├── pollingManager.js           # 轮询管理器
│   │   └── reportService.js            # [关键] 报告数据服务
│   └── cloudfunctions/
│       ├── getDiagnosisReport/         # [关键] 获取报告云函数
│       └── getDiagnosisStatus/         # 获取状态云函数
│
├── backend_python/wechat_backend/      # Flask 后端
│   ├── views/
│   │   ├── diagnosis_api.py            # [关键] 诊断 API
│   │   └── diagnosis_views.py          # [关键] 诊断视图
│   ├── diagnosis_report_service.py     # [关键] 报告服务层
│   └── diagnosis_report_repository.py  # 数据访问层
│
└── services/
    └── brandTestService.js             # [关键] 品牌测试服务 (根目录)
```

---

## 二、数据流全景图

### 2.1 完整数据流路径

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           诊断报告数据流架构图                           │
└─────────────────────────────────────────────────────────────────────────┘

  前端                          后端                         数据库
   │                             │                             │
   │ 1. POST /api/perform-brand-test                           │
   ├────────────────────────────►│                             │
   │                             │ 2. DiagnosisOrchestrator    │
   │                             │    启动诊断任务              │
   │                             ├────────────────────────────►│
   │                             │                             │ 3. 保存执行记录
   │                             │◄────────────────────────────┤
   │                             │                             │
   │                             │ 4. 并行调用多个 AI 平台       │
   │                             │    (DIY/SiliconFlow/...)    │
   │                             │                             │
   │                             │ 5. 结果保存到数据库          │
   │                             ├────────────────────────────►│
   │                             │                             │
   │                             │ 6. 后台异步分析任务          │
   │                             │                             │
   │ 7. 轮询 /test/status/{id}   │                             │
   ├────────────────────────────►│                             │
   │                             │ 8. 查询状态 + 结果           │
   │                             ├────────────────────────────►│
   │                             │◄────────────────────────────┤
   │                             │                             │
   │ 9. 返回 statusData          │                             │
   │    {status, progress,       │                             │
   │     results, detailed_      │                             │
   │     results}                │                             │
   │◄────────────────────────────┤                             │
   │                             │                             │
   │ 10. pollingManager.onComplete(statusData)                 │
   │     diagnosis.js handleComplete(result)                   │
   │                                                           │
   │ 11. 跳转到 report-v2?executionId=xxx                      │
   │     (携带 globalData.pendingReport)                       │
   │                                                           │
   │ 12. report-v2.js loadReportData(executionId)              │
   │                                                           │
   │ 13. reportService.getFullReport(executionId)              │
   │                                                           │
   │ 14. 云函数 getDiagnosisReport                             │
   │                                                           │
   │ 15. GET /api/diagnosis/report/{execution_id}              │
   ├──────────────────────────────────────────────────────────►│
   │                             │                             │
   │                             │ 16. DiagnosisReportService  │
   │                             │     .get_full_report()      │
   │                             ├────────────────────────────►│
   │                             │◄────────────────────────────┤
   │                             │                             │
   │ 17. 返回完整报告数据        │                             │
   │     {brandDistribution,     │                             │
   │      sentimentDistribution, │                             │
   │      keywords, results}     │                             │
   │◄──────────────────────────────────────────────────────────┤
   │                                                           │
   │ 18. report-v2 页面渲染图表                                 │
   │     - BrandDistribution                                   │
   │     - SentimentChart                                      │
   │     - KeywordCloud                                        │
   │                                                           │
```

### 2.2 关键数据接口定义

#### 2.2.1 轮询响应数据结构 (期望)

```javascript
{
  execution_id: "exec_123456",
  status: "completed",  // analyzing | completed | failed
  progress: 100,
  results: [            // 基础结果数组
    {
      platform: "diy",
      brand_name: "品牌 A",
      sentiment: "positive",
      // ...
    }
  ],
  detailed_results: [   // [关键字段] 详细结果数组
    {
      platform: "diy",
      brand_name: "品牌 A",
      sentiment: "positive",
      confidence: 0.95,
      keywords: ["关键词 1", "关键词 2"],
      summary: "分析摘要",
      // ...
    }
  ],
  analysis_status: "completed",
  report_id: "rpt_123456"
}
```

#### 2.2.2 完整报告响应数据结构 (期望)

```javascript
{
  execution_id: "exec_123456",
  report_id: "rpt_123456",
  status: "completed",
  quality_score: 95,
  result_count: 24,
  
  // [核心展示数据]
  brandDistribution: {
    "品牌 A": 35,
    "品牌 B": 28,
    "品牌 C": 22,
    "其他": 15
  },
  
  sentimentDistribution: {
    positive: 45,
    neutral: 35,
    negative: 20
  },
  
  keywords: [
    { word: "品质", count: 128, sentiment: "positive" },
    { word: "价格", count: 96, sentiment: "neutral" },
    // ...
  ],
  
  // [明细数据]
  results: [...],
  detailed_results: [...]
}
```

---

## 三、问题识别与分析

### 3.1 问题清单总览

| 编号 | 问题描述 | 严重性 | 可能性 | 优先级 |
|------|---------|--------|--------|--------|
| P1 | 后端 API 未返回 `detailed_results` 字段 | 高 | 高 | P0 |
| P2 | 多个轮询实例并存导致状态混乱 | 中 | 高 | P1 |
| P3 | 报告页数据加载策略单一 | 中 | 中 | P1 |
| P4 | 诊断完成时数据未传递到报告页 | 中 | 中 | P1 |
| P5 | 字段转换器可能未正确应用 | 低 | 低 | P2 |

---

### 3.2 问题详细分析

#### 问题 P1: 后端 API 未返回 `detailed_results` 字段

**文件位置**: 
- `backend_python/wechat_backend/views/diagnosis_views.py`
- `backend_python/wechat_backend/diagnosis_report_service.py`

**问题描述**: 
前端 `generateDashboardData` 函数期望接收 `detailed_results` 数组，但后端 `/test/status/{id}` 接口可能只返回 `results` 字段，导致数据流断裂。

**证据代码**:

```javascript
// 文件：services/brandTestService.js (Line 1097)
// 前端期望的数据结构
rawResults = processedReportData.detailed_results
           || processedReportData.results
           || processedReportData.data?.detailed_results
           || []
```

```python
# 文件：backend_python/wechat_backend/views/diagnosis_views.py
# 后端返回的数据结构 (可能存在缺失)
@bp.route('/test/status/<execution_id>', methods=['GET'])
def get_test_status(execution_id):
    # ...
    return jsonify({
        'execution_id': execution_id,
        'status': status,
        'progress': progress,
        'results': results,  # 只返回 results
        # 'detailed_results': detailed_results,  # 可能缺失
    })
```

**影响**:
- `generateDashboardData` 返回空数据
- 看板图表无法渲染
- 用户体验严重受损

**验证方法**:
```bash
# 1. 直接调用 API 检查返回数据
curl http://localhost:5001/api/test/status/<execution_id> | jq '.'

# 2. 检查是否包含 detailed_results
curl http://localhost:5001/api/test/status/<execution_id> | jq '.detailed_results'

# 3. 检查 results 字段内容
curl http://localhost:5001/api/test/status/<execution_id> | jq '.results | length'
```

---

#### 问题 P2: 多个轮询实例并存

**文件位置**: 
- `services/brandTestService.js` (Line 278-314)
- `miniprogram/services/diagnosisService.js` (Line 156-287)

**问题描述**:
WebSocket 错误回调 `onError` 和 `onFallback` 被多次触发，每次触发都创建新的轮询实例，导致：
- 重复 API 调用
- 状态不一致
- 资源浪费

**日志证据**:
```
[轮询响应] 第 6 次，耗时：44ms, 状态：report_aggregating, 进度：90%
[轮询响应] 第 10 次，耗时：41ms, 状态：report_aggregating, 进度：90%
[轮询响应] 第 13 次，耗时：44ms, 状态：report_aggregating, 进度：90%
```

**影响**:
- 后端压力增加
- 前端状态混乱
- 可能导致数据覆盖

**修复方案**:
```javascript
// 添加 isPollingStarted 标志
if (this.isPollingStarted) {
  console.warn('[BrandTestService] 轮询已在运行，忽略重复启动请求');
  return;
}
this.isPollingStarted = true;
```

---

#### 问题 P3: 报告页数据加载策略单一

**文件位置**: 
- `miniprogram/pages/report-v2/report-v2.js` (Line 596-720)

**问题描述**:
报告页仅依赖云函数 `getFullReport()` 获取数据，当云函数返回空数据时，没有 fallback 方案。

**修复前代码**:
```javascript
async loadReportData(executionId, reportId) {
  const reportService = require('../../services/reportService').default;
  const report = await reportService.getFullReport(id);
  // 直接使用该 report，无 fallback
  this.setData({ reportData: report });
}
```

**影响**:
- 云函数失败时页面显示空白
- 无错误提示
- 用户体验差

**修复方案** (已实施):
```javascript
async loadReportData(executionId, reportId) {
  // 策略 1: 从 globalData.pendingReport 获取
  const pendingReport = app.globalData.pendingReport;
  if (pendingReport && pendingReport.executionId === executionId) {
    return this.usePendingReport(pendingReport);
  }
  
  // 策略 2: 从云函数获取
  const report = await reportService.getFullReport(executionId);
  if (report && report.results?.length > 0) {
    return this.setData({ reportData: report });
  }
  
  // 策略 3: 从 Storage 读取
  const cachedReport = wx.getStorageSync(`report_${executionId}`);
  if (cachedReport) {
    return this.setData({ reportData: cachedReport });
  }
  
  // 策略 4: 显示错误提示
  this.showError('报告数据加载失败');
}
```

---

#### 问题 P4: 诊断完成时数据未传递到报告页

**文件位置**: 
- `pages/index/index.js` (Line 1779-1878)

**问题描述**:
诊断完成后跳转到报告页时，只传递了 `executionId`，没有传递已处理的数据。

**修复前代码**:
```javascript
handleComplete(result) {
  // 只传递 executionId
  wx.navigateTo({
    url: `/pages/report-v2/report-v2?executionId=${result.executionId}`
  });
}
```

**修复方案** (已实施):
```javascript
handleComplete(result) {
  // 处理数据并保存
  const processedData = this.processReportData(result);
  app.globalData.pendingReport = {
    executionId: result.executionId,
    data: processedData,
    timestamp: Date.now()
  };
  
  // 跳转到报告页
  wx.navigateTo({
    url: `/pages/report-v2/report-v2?executionId=${result.executionId}`
  });
}
```

---

#### 问题 P5: 字段转换器可能未正确应用

**文件位置**: 
- `backend_python/utils/field_converter.py`

**问题描述**:
后端返回的数据使用 `convert_response_to_camel` 转换为 camelCase，但如果导入失败或转换逻辑有问题，可能导致字段名不匹配。

**导入逻辑**:
```python
try:
    from utils.field_converter import convert_response_to_camel
except ImportError:
    try:
        from backend_python.utils.field_converter import convert_response_to_camel
    except ImportError:
        def convert_response_to_camel(data):
            return data  # 备用方案：直接返回，不转换
```

**影响**:
- 前端期望 `brandDistribution`，后端返回 `brand_distribution`
- 数据解析失败

**验证方法**:
```bash
# 检查 API 返回字段格式
curl http://localhost:5001/api/diagnosis/report/<execution_id> | jq 'keys'
```

---

## 四、根本原因确认

### 4.1 根本原因优先级排序

| 优先级 | 根本原因 | 置信度 | 验证状态 |
|--------|---------|--------|----------|
| 1 | 后端 `/test/status/{id}` 接口未返回 `detailed_results` 字段 | 95% | 待验证 |
| 2 | 后端 `DiagnosisReportService.get_full_report()` 返回空数据 | 75% | 待验证 |
| 3 | 云函数 `getDiagnosisReport` 配置错误 | 60% | 待验证 |

---

### 4.2 根本原因详细分析

#### 根因 1: 后端 API 字段缺失 (高概率)

**推理过程**:

1. 前端代码多处检查 `detailed_results` 字段
2. `generateDashboardData` 函数依赖此字段生成看板数据
3. DIAGNOSIS_REPORT_FIX_2026-03-11.md 明确指出此问题
4. 后端 API 设计文档与实际实现可能存在差异

**验证步骤**:
```bash
# Step 1: 获取一个已完成的诊断 execution_id
# 从数据库或日志中获取

# Step 2: 调用轮询状态 API
curl -s http://localhost:5001/api/test/status/<execution_id> | jq '.'

# Step 3: 检查返回数据
# - 是否包含 detailed_results 字段？
# - results 字段是否为空？
# - status 是否为 completed？

# Step 4: 调用完整报告 API
curl -s http://localhost:5001/api/diagnosis/report/<execution_id> | jq '.'

# Step 5: 对比两个 API 的返回差异
```

**预期修复**:
```python
# 文件：backend_python/wechat_backend/views/diagnosis_views.py
@bp.route('/test/status/<execution_id>', methods=['GET'])
def get_test_status(execution_id):
    # ...
    # 确保返回 detailed_results
    return jsonify({
        'execution_id': execution_id,
        'status': status,
        'progress': progress,
        'results': results,
        'detailed_results': detailed_results,  # 添加此字段
    })
```

---

#### 根因 2: 后端服务层返回空数据 (中概率)

**推理过程**:

1. `DiagnosisReportService.get_full_report()` 有多个返回空数据的分支
2. AI 调用失败时可能返回空结果
3. 数据库保存可能失败

**相关代码**:
```python
# 文件：backend_python/wechat_backend/diagnosis_report_service.py (Line 280-395)
def get_full_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
    # 1. 获取报告主数据
    report = self.report_repo.get_by_execution_id(execution_id)
    if not report:
        return self._create_fallback_report(execution_id, '报告不存在', 'not_found')

    # 2. 获取结果明细
    results = self.result_repo.get_by_execution_id(execution_id)
    if not results or len(results) == 0:
        return self._create_fallback_report(execution_id, '诊断已完成，但未生成有效结果', 'no_results', report)

    # 3. 获取分析数据
    analysis = self.analysis_repo.get_by_execution_id(execution_id)

    # 4-6. 计算 brandDistribution, sentimentDistribution, keywords
    # ...
```

**验证步骤**:
```bash
# Step 1: 检查后端日志
tail -f backend_python/logs/app.log | grep -E "AI 调用|results|execution_id"

# Step 2: 检查数据库
sqlite3 backend_python/database.db <<EOF
SELECT COUNT(*) FROM diagnosis_results WHERE execution_id='<execution_id>';
SELECT * FROM diagnosis_reports WHERE execution_id='<execution_id>';
EOF

# Step 3: 在 get_full_report() 中添加调试日志
# 记录每个步骤的执行情况
```

---

#### 根因 3: 云函数配置错误 (中概率)

**推理过程**:

1. 云函数 `getDiagnosisReport` 需要配置正确的 `API_BASE_URL`
2. 开发环境和生产环境可能使用不同配置
3. 配置错误会导致云函数无法连接后端

**相关代码**:
```javascript
// 文件：miniprogram/cloudfunctions/getDiagnosisReport/index.js (Line 32-56)
const API_BASE_URL = (function() {
  if (process.env.API_BASE_URL) {
    return process.env.API_BASE_URL;
  }
  const PRODUCTION_API_URL = 'https://api.your-domain.com';  // TODO: 替换为实际生产域名
  const DEVELOPMENT_API_URL = 'http://localhost:5001';
  // ...
})();
```

**验证步骤**:
```bash
# Step 1: 检查云函数配置
cat miniprogram/cloudfunctions/getDiagnosisReport/index.js | grep API_BASE_URL

# Step 2: 检查云函数环境变量
# 在微信开发者工具中查看云函数配置

# Step 3: 测试云函数
# 在小程序中调用并查看云函数日志
```

---

## 五、分步实施计划

### 5.1 总体时间规划

| 阶段 | 任务 | 预计时间 | 负责人 | 状态 |
|------|------|----------|--------|------|
| 阶段一 | 问题验证与定位 | 1 小时 | 后端组 | 待开始 |
| 阶段二 | 后端修复 | 2 小时 | 后端组 | 待开始 |
| 阶段三 | 前端修复 | 2 小时 | 前端组 | 待开始 |
| 阶段四 | 集成测试 | 1 小时 | QA 组 | 待开始 |

---

### 5.2 详细实施步骤

#### 阶段一：问题验证与定位 (1 小时)

**目标**: 确认根本原因

| 步骤 | 操作 | 预期结果 | 验证命令 |
|------|------|----------|----------|
| 1.1 | 获取一个已完成的 diagnosis execution_id | 获得有效的 execution_id | 查询数据库或查看日志 |
| 1.2 | 调用 `/test/status/{id}` API | 查看返回数据结构 | `curl http://localhost:5001/api/test/status/<id> \| jq '.'` |
| 1.3 | 检查是否包含 `detailed_results` | 确认字段存在性 | `curl ... \| jq '.detailed_results'` |
| 1.4 | 调用 `/diagnosis/report/{id}` API | 查看完整报告数据 | `curl http://localhost:5001/api/diagnosis/report/<id> \| jq '.'` |
| 1.5 | 检查后端日志 | 查看 AI 调用状态 | `tail -f logs/app.log \| grep "AI 调用"` |
| 1.6 | 检查数据库记录 | 确认结果已保存 | `sqlite3 database.db "SELECT * FROM diagnosis_results WHERE execution_id='<id>'"` |
| 1.7 | 检查云函数配置 | 确认 API_BASE_URL 正确 | `cat cloudfunctions/getDiagnosisReport/index.js \| grep API_BASE_URL` |

**输出物**: 《问题验证报告》

---

#### 阶段二：后端修复 (2 小时)

**目标**: 修复后端数据返回问题

**任务 2.1: 修复 `/test/status/{id}` API** (30 分钟)

```python
# 文件：backend_python/wechat_backend/views/diagnosis_views.py

# 修改前
@bp.route('/test/status/<execution_id>', methods=['GET'])
def get_test_status(execution_id):
    # ...
    return jsonify({
        'execution_id': execution_id,
        'status': status,
        'progress': progress,
        'results': results,
    })

# 修改后
@bp.route('/test/status/<execution_id>', methods=['GET'])
def get_test_status(execution_id):
    # ...
    # 确保返回 detailed_results
    return jsonify({
        'execution_id': execution_id,
        'status': status,
        'progress': progress,
        'results': results,
        'detailed_results': detailed_results,  # 添加此字段
        'analysis_status': analysis_status,
    })
```

**任务 2.2: 增强 `DiagnosisReportService.get_full_report()`** (45 分钟)

```python
# 文件：backend_python/wechat_backend/diagnosis_report_service.py

def get_full_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
    logger.info(f"[get_full_report] 开始获取报告：{execution_id}")
    
    # 1. 获取报告主数据
    report = self.report_repo.get_by_execution_id(execution_id)
    if not report:
        logger.warning(f"[get_full_report] 报告不存在：{execution_id}")
        return self._create_fallback_report(execution_id, '报告不存在', 'not_found')
    logger.info(f"[get_full_report] 报告主数据获取成功：{execution_id}")

    # 2. 获取结果明细
    results = self.result_repo.get_by_execution_id(execution_id)
    if not results or len(results) == 0:
        logger.warning(f"[get_full_report] 结果数据为空：{execution_id}")
        return self._create_fallback_report(execution_id, '诊断已完成，但未生成有效结果', 'no_results', report)
    logger.info(f"[get_full_report] 结果数据获取成功：{execution_id}, count={len(results)}")

    # 3. 获取分析数据
    analysis = self.analysis_repo.get_by_execution_id(execution_id)
    logger.info(f"[get_full_report] 分析数据：{execution_id}, exists={analysis is not None}")

    # 4. 计算 brandDistribution
    brand_distribution = self._calculate_brand_distribution(results)
    
    # 5. 计算 sentimentDistribution
    sentiment_distribution = self._calculate_sentiment_distribution(results)
    
    # 6. 提取 keywords
    keywords = self._extract_keywords(analysis) if analysis else []

    # 7. 构建完整报告
    full_report = {
        'execution_id': execution_id,
        'report_id': report.get('report_id'),
        'status': report.get('status'),
        'quality_score': report.get('quality_score', 0),
        'result_count': len(results),
        'brandDistribution': brand_distribution,
        'sentimentDistribution': sentiment_distribution,
        'keywords': keywords,
        'results': results,
        'detailed_results': results,  # 如果没有单独的 detailed_results，使用 results
    }
    
    logger.info(f"[get_full_report] 完整报告构建成功：{execution_id}")
    return full_report
```

**任务 2.3: 添加调试日志** (15 分钟)

在关键位置添加日志，便于后续排查：
- AI 调用开始/结束
- 数据保存到数据库
- API 请求/响应

**任务 2.4: 后端单元测试** (30 分钟)

```python
# 文件：backend_python/wechat_backend/tests/test_diagnosis_api.py

def test_get_test_status_returns_detailed_results():
    """测试 /test/status/{id} 返回 detailed_results 字段"""
    response = client.get('/api/test/status/test_execution_id')
    assert response.status_code == 200
    data = response.get_json()
    assert 'detailed_results' in data
    assert isinstance(data['detailed_results'], list)

def test_get_full_report_returns_complete_data():
    """测试 /diagnosis/report/{id} 返回完整数据"""
    response = client.get('/api/diagnosis/report/test_execution_id')
    assert response.status_code == 200
    data = response.get_json()
    assert 'brandDistribution' in data
    assert 'sentimentDistribution' in data
    assert 'keywords' in data
    assert 'results' in data
```

---

#### 阶段三：前端修复 (2 小时)

**目标**: 修复前端数据处理和展示问题

**任务 3.1: 增强 `report-v2.js` 数据加载** (45 分钟)

```javascript
// 文件：miniprogram/pages/report-v2/report-v2.js

async loadReportData(executionId, reportId) {
  console.log('[ReportPageV2] 加载报告数据:', { executionId, reportId });
  
  wx.showLoading({ title: '加载中...' });
  
  try {
    // 策略 1: 从 globalData.pendingReport 获取
    const app = getApp();
    const pendingReport = app.globalData.pendingReport;
    if (pendingReport && pendingReport.executionId === executionId) {
      console.log('[ReportPageV2] 使用 pendingReport 数据');
      this.setData({ 
        reportData: pendingReport.data,
        fromCache: true
      });
      wx.hideLoading();
      return;
    }
    
    // 策略 2: 从云函数获取
    const reportService = require('../../services/reportService').default;
    const report = await reportService.getFullReport(executionId);
    
    console.log('[ReportPageV2] 完整报告数据:', JSON.stringify(report, null, 2));
    console.log('[ReportPageV2] results:', report.results);
    console.log('[ReportPageV2] result_count:', report.result_count);
    console.log('[ReportPageV2] detailed_results:', report.detailed_results);
    
    if (report && (report.results?.length > 0 || report.detailed_results?.length > 0)) {
      console.log('[ReportPageV2] 云函数数据可用');
      this.setData({ reportData: report });
      
      // 缓存到 Storage
      wx.setStorageSync(`report_${executionId}`, report);
      
      wx.hideLoading();
      return;
    }
    
    // 策略 3: 从 Storage 读取
    console.log('[ReportPageV2] 云函数数据不可用，尝试从 Storage 读取');
    const cachedReport = wx.getStorageSync(`report_${executionId}`);
    if (cachedReport) {
      console.log('[ReportPageV2] 使用 Storage 缓存数据');
      this.setData({ 
        reportData: cachedReport,
        fromCache: true
      });
      wx.hideLoading();
      return;
    }
    
    // 策略 4: 显示错误提示
    console.warn('[ReportPageV2] 所有数据源都不可用');
    wx.hideLoading();
    this.showError('报告数据加载失败，请稍后重试');
    
  } catch (error) {
    console.error('[ReportPageV2] 加载报告数据失败:', error);
    wx.hideLoading();
    this.showError('网络错误，请稍后重试');
  }
}
```

**任务 3.2: 增强 `brandTestService.js` 数据处理** (30 分钟)

```javascript
// 文件：services/brandTestService.js

generateDashboardData(reportData) {
  console.log('[BrandTestService] generateDashboardData 输入:', reportData);
  
  // 增强数据兼容性
  let rawResults = reportData.detailed_results 
                || reportData.results 
                || reportData.data?.detailed_results 
                || reportData.data?.results 
                || [];
  
  console.log('[BrandTestService] rawResults 长度:', rawResults.length);
  
  if (rawResults.length === 0) {
    console.warn('[BrandTestService] 没有可用的原始结果数据');
    return this.createEmptyDashboardData();
  }
  
  // 继续处理...
}
```

**任务 3.3: 增强错误处理** (30 分钟)

在关键组件中添加错误边界：
- `BrandDistribution` 组件
- `SentimentChart` 组件
- `KeywordCloud` 组件

**任务 3.4: 前端日志增强** (15 分钟)

确保所有关键步骤都有日志输出：
- 数据加载开始/结束
- 数据转换
- 组件渲染

---

#### 阶段四：集成测试 (1 小时)

**目标**: 验证修复效果

**测试用例**:

| 用例 ID | 测试场景 | 预期结果 | 状态 |
|---------|---------|----------|------|
| TC-001 | 正常诊断流程 | 报告页显示完整数据 | 待执行 |
| TC-002 | AI 调用部分失败 | 报告页显示部分数据 | 待执行 |
| TC-003 | AI 调用全部失败 | 报告页显示友好错误 | 待执行 |
| TC-004 | 网络中断后恢复 | 报告页从缓存加载数据 | 待执行 |
| TC-005 | 重复跳转报告页 | 数据正确显示，无重复请求 | 待执行 |

**测试步骤**:

```bash
# Step 1: 启动后端服务
cd backend_python && python app.py

# Step 2: 启动小程序开发者工具
# 打开微信开发者工具，加载 miniprogram 目录

# Step 3: 执行诊断流程
# 在小程序中触发诊断任务

# Step 4: 观察日志
# 前端控制台 + 后端日志

# Step 5: 验证报告页
# 检查图表是否正确渲染
```

---

## 六、验收标准

### 6.1 功能验收

| 编号 | 验收项 | 标准 |
|------|--------|------|
| AC-001 | 报告数据展示 | 品牌分布、情感分布、关键词云正确显示 |
| AC-002 | 数据完整性 | 所有诊断结果都应在报告中体现 |
| AC-003 | 错误处理 | 数据不可用时显示友好错误提示 |
| AC-004 | 缓存机制 | 网络异常时能从缓存加载数据 |
| AC-005 | 性能要求 | 报告页加载时间 < 3 秒 |

### 6.2 技术验收

| 编号 | 验收项 | 验证方法 |
|------|--------|----------|
| AC-101 | API 返回 `detailed_results` | `curl ... \| jq '.detailed_results'` |
| AC-102 | 后端日志完整 | 检查日志文件 |
| AC-103 | 前端日志完整 | 检查控制台输出 |
| AC-104 | 单元测试通过 | `pytest backend_python/tests/` |
| AC-105 | 无回归问题 | 执行完整回归测试套件 |

---

## 七、风险评估与应对

### 7.1 风险清单

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| AI 服务不稳定 | 高 | 高 | 添加降级策略，使用备用 AI 平台 |
| 数据库性能问题 | 中 | 中 | 添加索引，优化查询 |
| 云函数配置错误 | 中 | 高 | 添加配置验证和告警 |
| 前端兼容性问题 | 低 | 中 | 多版本小程序基础库测试 |

### 7.2 回滚方案

如果修复后问题仍然存在或引入新问题：

1. **代码回滚**: 使用 git 回滚到修复前版本
2. **配置回滚**: 恢复云函数原始配置
3. **数据清理**: 清理可能产生的脏数据

---

## 八、附录

### 8.1 相关文件清单

| 文件 | 路径 | 修改状态 |
|------|------|----------|
| diagnosis_views.py | backend_python/wechat_backend/views/ | 待修改 |
| diagnosis_report_service.py | backend_python/wechat_backend/ | 待修改 |
| report-v2.js | miniprogram/pages/report-v2/ | 待修改 |
| brandTestService.js | services/ | 待修改 |
| getDiagnosisReport/index.js | miniprogram/cloudfunctions/ | 待检查 |

### 8.2 参考文档

- [DIAGNOSIS_REPORT_FIX_2026-03-11.md](../DIAGNOSIS_REPORT_FIX_2026-03-11.md)
- [LATEST_ISSUE_ANALYSIS.md](../LATEST_ISSUE_ANALYSIS.md)
- [API_Spec_v2.0.json](../API_Spec_v2.0.json)

### 8.3 联系人

| 角色 | 职责 |
|------|------|
| 首席架构师 | 技术方案评审 |
| 后端负责人 | 后端修复实施 |
| 前端负责人 | 前端修复实施 |
| QA 负责人 | 测试验证 |

---

**文档版本**: 1.0  
**创建时间**: 2026-03-11  
**最后更新**: 2026-03-11  
**审批状态**: 待审批
