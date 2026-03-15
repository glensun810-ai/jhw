# 诊断报告页问题 debugging 计划

**文档编号**: DBG-2026-03-11-001  
**创建日期**: 2026-03-11  
**问题优先级**: P0  
**状态**: ⏳ 待调试  

---

## 一、问题现状

### 1.1 问题截图分析

从截图可见两个明显问题：

**问题 1: 配色不符** 🔵
- 当前：浅蓝色背景 (`#e6f7ff` 类似色)
- 期望：深色科技主题 (`#121826`)

**问题 2: 数据为空** ❌
- 报告摘要：总样本数 0、关键词 0、涉及品牌 0
- 品牌分布：暂无数据
- 情感分布：暂无数据

### 1.2 问题影响

| 维度 | 影响 |
|-----|------|
| **用户体验** | 视觉风格不统一，数据展示空白 |
| **功能可用性** | 诊断结果不可见，核心功能失效 |
| **品牌形象** | 影响产品专业度和可信度 |

---

## 二、问题根因初步分析

### 2.1 配色问题根因

**可能原因**:
1. `report-v2.wxss` 未正确导入全局样式
2. 页面容器未使用 `.report-page` 类
3. 内联样式覆盖了 CSS 变量
4. 组件内部使用了浅色背景

**验证方法**:
```css
/* 检查 report-v2.wxss */
.report-page {
  background-color: #121826;  /* 是否生效？ */
}
```

### 2.2 数据为空根因

**数据流分析**:
```
诊断完成 → 保存到 storage → report-v2 加载 → 解析数据 → 渲染展示
                                              ↓
                                        当前环节：❌
```

**可能原因**:
1. 数据未保存到 storage
2. storage key 不匹配
3. 数据解析逻辑错误
4. 数据结构不匹配
5. 异步加载时序问题

---

## 三、调试计划总览

### 3.1 调试顺序原则

**优先级排序**:
1. ✅ **先修复配色问题** (5 分钟，立竿见影)
2. ✅ **再调试数据问题** (按数据流顺序)

**数据流调试顺序**:
```
后端返回 → 前端接收 → storage 保存 → 页面加载 → 数据解析 → 渲染展示
   ↓          ↓          ↓          ↓          ↓          ↓
  步骤 6      步骤 5      步骤 4      步骤 3      步骤 2      步骤 1
```

### 3.2 预计时间

| 阶段 | 内容 | 预计时间 |
|-----|------|---------|
| **阶段 1** | 配色问题修复 | 10 分钟 |
| **阶段 2** | 数据流调试 (6 步) | 90 分钟 |
| **阶段 3** | 问题修复验证 | 30 分钟 |
| **合计** | - | 130 分钟 |

---

## 四、详细调试步骤

### 阶段 1: 配色问题修复 (10 分钟)

#### 步骤 1.1: 检查样式导入 (2 分钟)

**检查文件**: `miniprogram/pages/report-v2/report-v2.wxss`

**检查内容**:
```css
/* 第 1 行：是否导入全局样式？ */
@import "../../../app.wxss";

/* 第 18-25 行：.report-page 样式是否正确？ */
.report-page {
  min-height: 100vh;
  background-color: #121826;
  padding-bottom: 140rpx;
  color: #e8e8e8;
}
```

**预期结果**: ✅ 样式定义正确

#### 步骤 1.2: 检查 WXML 模板 (3 分钟)

**检查文件**: `miniprogram/pages/report-v2/report-v2.wxml`

**检查内容**:
```xml
<!-- 第 11 行：根元素是否使用了正确的类？ -->
<view class="report-page">
  <!-- 内容 -->
</view>
```

**修复方案** (如果根元素类名错误):
```xml
<!-- ❌ 错误示例 -->
<view class="container">

<!-- ✅ 正确示例 -->
<view class="report-page">
```

#### 步骤 1.3: 检查组件样式 (5 分钟)

**检查文件**: `miniprogram/components/` 下的组件

**检查内容**:
```css
/* 检查是否有组件使用了浅色背景 */
background: #fff;
background: #f5f6fa;
background: #e6f7ff;
```

**修复方案**:
```css
/* ❌ 浅色背景 */
background: #fff;

/* ✅ 深色背景 */
background: rgba(26, 32, 44, 0.6);
background: rgba(18, 24, 38, 0.8);
```

---

### 阶段 2: 数据流调试 (90 分钟)

#### 步骤 2.1: 检查页面渲染逻辑 (15 分钟)

**目标**: 确认数据是否正确传递到模板

**操作**:

1. **添加调试日志** - 修改 `report-v2.js` 的 `setData` 调用:
```javascript
// 在 handleStatusUpdate 或 handleComplete 中
console.log('[ReportPageV2] 准备渲染数据:', {
  brandDistribution: this.data.brandDistribution,
  sentimentDistribution: this.data.sentimentDistribution,
  keywords: this.data.keywords,
  hasData: !!this.data.brandDistribution?.total_count
});
```

2. **检查 WXML 数据绑定**:
```xml
<!-- 检查数据绑定是否正确 -->
<text>{{brandDistribution && brandDistribution.total_count ? brandDistribution.total_count : 0}}</text>
```

3. **查看控制台输出**:
```
期望看到:
[ReportPageV2] 准备渲染数据：{
  brandDistribution: {total_count: 10, ...},
  sentimentDistribution: {...},
  keywords: [...]
}
```

**判断标准**:
- ✅ 有数据 → 进入步骤 2.2
- ❌ 无数据 → 进入步骤 2.3

#### 步骤 2.2: 检查数据解析逻辑 (15 分钟)

**目标**: 确认后端返回数据是否正确解析

**操作**:

1. **定位数据处理函数**:
```javascript
// report-v2.js ~ 第 450-550 行
handleStatusUpdate(statusData) {
  console.log('[ReportPageV2] 收到状态更新:', statusData);
  
  // 检查数据解析逻辑
  const parsedData = this._parseReportData(statusData);
  console.log('[ReportPageV2] 解析后的数据:', parsedData);
}
```

2. **添加数据解析日志**:
```javascript
_parseReportData: function(rawData) {
  console.log('[数据解析] 原始数据:', rawData);
  
  const parsed = {
    brandDistribution: rawData.brandDistribution || {},
    sentimentDistribution: rawData.sentimentDistribution || {},
    keywords: rawData.keywords || []
  };
  
  console.log('[数据解析] 解析结果:', parsed);
  return parsed;
}
```

**判断标准**:
- ✅ 解析正确 → 进入步骤 2.3
- ❌ 解析失败 → 修复解析逻辑

#### 步骤 2.3: 检查 storage 保存 (20 分钟)

**目标**: 确认诊断完成后数据是否正确保存到 storage

**操作**:

1. **检查 storage 保存代码** - `pages/index/index.js`:
```javascript
// handleDiagnosisComplete 函数中
const saveSuccess = saveDiagnosisResult(executionId, {
  brandName: this.data.brandName,
  // ... 其他数据
  rawResponse: parsedStatus  // 确保保存了完整数据
});

console.log('[Storage] 保存结果:', {
  success: saveSuccess,
  executionId: executionId,
  hasData: !!parsedStatus.brandDistribution
});
```

2. **手动检查 storage**:
```javascript
// 在微信开发者工具控制台中执行
const key = 'diagnosis_result_xxx'; // 替换为实际 executionId
const data = wx.getStorageSync(key);
console.log('Storage 数据:', data);
console.log('Storage 数据 - brandDistribution:', data?.data?.brandDistribution);
```

3. **检查 storage-manager**:
```javascript
// utils/storage-manager.js - saveDiagnosisResult 函数
console.log('[Storage] 保存诊断结果:', {
  executionId: executionId,
  hasBrandDistribution: !!data.brandDistribution,
  dataKeys: Object.keys(data)
});
```

**判断标准**:
- ✅ storage 有数据 → 进入步骤 2.4
- ❌ storage 无数据 → 修复保存逻辑

#### 步骤 2.4: 检查 storage 加载 (15 分钟)

**目标**: 确认 report-v2 页面是否正确加载 storage 数据

**操作**:

1. **检查加载逻辑** - `report-v2.js`:
```javascript
// initPage 或 loadHistoryReport 函数
async initPage(options) {
  console.log('[ReportPageV2] initPage, options:', options);
  
  if (options.executionId) {
    // 检查是否从 storage 加载
    const storageData = this._loadFromStorage(options.executionId);
    console.log('[ReportPageV2] storage 加载结果:', storageData);
  }
}
```

2. **添加 storage 加载日志**:
```javascript
_loadFromStorage: function(executionId) {
  const key = 'diagnosis_result_' + executionId;
  const data = wx.getStorageSync(key);
  
  console.log('[Storage 加载] key:', key);
  console.log('[Storage 加载] 数据:', data);
  console.log('[Storage 加载] dashboard:', data?.dashboard);
  
  return data;
}
```

**判断标准**:
- ✅ 加载成功 → 进入步骤 2.5
- ❌ 加载失败 → 修复加载逻辑

#### 步骤 2.5: 检查后端数据返回 (15 分钟)

**目标**: 确认后端是否正确返回诊断数据

**操作**:

1. **检查后端日志**:
```bash
# 查看后端诊断相关日志
tail -f backend_python/logs/app.log | grep "diagnosis"
```

2. **检查 API 响应**:
```javascript
// 在 report-v2.js 的网络请求中添加日志
wx.request({
  url: `${serverUrl}/api/test-history`,
  success: (res) => {
    console.log('[API 响应] 完整响应:', res);
    console.log('[API 响应] data:', res.data);
    console.log('[API 响应] records:', res.data?.records);
  }
});
```

3. **手动测试 API**:
```bash
curl -X GET "http://localhost:5000/api/test-history?executionId=xxx"
```

**判断标准**:
- ✅ 后端有数据 → 进入步骤 2.6
- ❌ 后端无数据 → 检查后端诊断逻辑

#### 步骤 2.6: 检查诊断执行流程 (10 分钟)

**目标**: 确认诊断执行过程中数据是否正确生成

**操作**:

1. **检查诊断编排器** - `diagnosis_orchestrator.py`:
```python
# 检查数据生成和返回逻辑
def execute_diagnosis(self, execution_id: str, config: DiagnosisConfig):
    # ... 诊断逻辑
    
    # 检查是否生成 brandDistribution
    brand_distribution = self._generate_brand_distribution(results)
    print(f'[诊断编排器] 品牌分布：{brand_distribution}')
    
    # 检查是否保存到响应
    response = {
        'execution_id': execution_id,
        'brand_distribution': brand_distribution,
        # ...
    }
    
    return response
```

2. **添加后端调试日志**:
```python
# 在关键位置添加日志
api_logger.info(f'[诊断完成] execution_id={execution_id}')
api_logger.info(f'[诊断完成] brand_distribution={brand_distribution}')
```

---

### 阶段 3: 问题修复验证 (30 分钟)

#### 步骤 3.1: 配色问题验证 (5 分钟)

**验证清单**:
- [ ] 页面背景变为深色 (`#121826`)
- [ ] 卡片背景为半透明深色
- [ ] 文字颜色为浅色 (`#e8e8e8`)
- [ ] 与首页风格一致

**验证方法**:
```
微信开发者工具 → 编译 → 查看报告页
```

#### 步骤 3.2: 数据展示验证 (15 分钟)

**验证清单**:
- [ ] 报告摘要显示正确数字
- [ ] 品牌分布图表显示
- [ ] 情感分布图表显示
- [ ] 关键词列表显示

**验证方法**:
```
1. 执行完整诊断流程
2. 等待诊断完成
3. 查看报告详情页
4. 检查数据展示
```

#### 步骤 3.3: 回归测试 (10 分钟)

**测试场景**:
- [ ] 诊断成功 → 报告展示正常
- [ ] 诊断失败 → 展示失败信息
- [ ] 历史记录 → 加载正常
- [ ] 断网测试 → 使用本地缓存

---

## 五、常见问题速查

### 5.1 配色问题

**Q1: 样式修改后不生效？**
```bash
# 清除缓存
微信开发者工具 → 清除缓存 → 全部清除

# 重新编译
点击"编译"按钮
```

**Q2: 部分组件背景仍是浅色？**
```css
/* 检查组件 wxss 文件 */
/* 强制使用深色背景 */
.component-class {
  background: rgba(18, 24, 38, 0.8) !important;
}
```

### 5.2 数据问题

**Q1: storage 中无数据？**
```javascript
// 检查 key 是否正确
const keys = wx.getStorageInfoSync().keys;
console.log('所有 storage keys:', keys);
console.log('diagnosis_result_ 开头的 keys:', 
  keys.filter(k => k.startsWith('diagnosis_result_')));
```

**Q2: 数据结构不匹配？**
```javascript
// 检查期望的数据结构
console.log('期望的数据结构:', {
  brandDistribution: {
    total_count: Number,
    data: Object
  },
  sentimentDistribution: Object,
  keywords: Array
});

// 检查实际的数据结构
console.log('实际的数据结构:', actualData);
```

**Q3: 后端无数据返回？**
```python
# 检查后端诊断流程
# 1. 诊断是否成功执行
# 2. 数据是否正确聚合
# 3. 响应是否正确构造
```

---

## 六、调试工具使用

### 6.1 微信开发者工具

**调试器**:
```
1. 打开"调试器"面板
2. 查看 Console 日志
3. 查看 Network 请求
4. 查看 Storage 数据
```

**Wxml 面板**:
```
1. 检查 DOM 结构
2. 查看数据绑定
3. 检查样式应用
```

### 6.2 后端调试

**日志查看**:
```bash
# 实时查看后端日志
tail -f backend_python/logs/app.log

# 查看诊断相关日志
tail -f backend_python/logs/app.log | grep "diagnosis"

# 查看 API 请求日志
tail -f backend_python/logs/app.log | grep "GET /api"
```

**数据库检查**:
```bash
# 进入 SQLite
cd backend_python
sqlite3 database.db

# 查询诊断记录
SELECT * FROM diagnosis_reports ORDER BY created_at DESC LIMIT 10;

# 查询诊断结果
SELECT * FROM diagnosis_results WHERE execution_id = 'xxx';
```

---

## 七、修复记录

### 7.1 配色问题修复 ✅

| 时间 | 操作 | 结果 | 文件 |
|-----|------|------|------|
| 22:30 | 检查样式导入 | ✅ 样式正确 | report-v2.wxss |
| 22:31 | 检查 WXML 模板 | ✅ 模板正确 | report-v2.wxml |
| 22:32 | 修复页面容器背景 | ✅ 添加 `!important` | report-v2.wxss:22 |
| 22:33 | 修复组件包装器背景 | ✅ 深色渐变 | report-v2.wxss:543 |
| 22:34 | 强制组件透明背景 | ✅ 覆盖白色背景 | report-v2.wxss:552-571 |

**修复内容**:
```css
/* 1. 页面容器强制深色背景 */
.report-page {
  background-color: #121826 !important;
}

/* 2. 组件包装器深色渐变 */
.component-wrapper {
  background: linear-gradient(135deg, rgba(26, 32, 44, 0.6) 0%, rgba(15, 52, 96, 0.6) 100%);
}

/* 3. 组件内部强制透明 */
brand-distribution view,
sentiment-chart view,
keyword-cloud view {
  background-color: transparent !important;
}
```

**验证方法**:
```
微信开发者工具 → 清除缓存 → 编译 → 查看报告页
期望：深色科技主题背景，与首页风格一致
```

### 7.2 数据问题修复 ⏳

| 步骤 | 检查点 | 结果 | 修复方案 |
|-----|--------|------|---------|
| 2.1 | 页面渲染逻辑 | ⏳ 待执行 | - |
| 2.2 | 数据解析逻辑 | ⏳ 待执行 | - |
| 2.3 | storage 保存 | ⏳ 待执行 | - |
| 2.4 | storage 加载 | ⏳ 待执行 | - |
| 2.5 | 后端 API 返回 | ⏳ 待执行 | - |
| 2.6 | 诊断执行流程 | ⏳ 待执行 | - |

---

## 八、下一步行动

### 8.1 立即执行

- [ ] **步骤 1**: 修复配色问题 (10 分钟)
- [ ] **步骤 2.1**: 检查页面渲染逻辑 (15 分钟)
- [ ] **步骤 2.2**: 检查数据解析逻辑 (15 分钟)

### 8.2 后续执行

- [ ] **步骤 2.3**: 检查 storage 保存 (20 分钟)
- [ ] **步骤 2.4**: 检查 storage 加载 (15 分钟)
- [ ] **步骤 2.5**: 检查后端 API 返回 (15 分钟)
- [ ] **步骤 2.6**: 检查诊断执行流程 (10 分钟)

### 8.3 验证收尾

- [ ] **步骤 3.1**: 配色问题验证 (5 分钟)
- [ ] **步骤 3.2**: 数据展示验证 (15 分钟)
- [ ] **步骤 3.3**: 回归测试 (10 分钟)

---

## 九、总结

### 9.1 调试原则

1. **先易后难**: 先修复配色问题，建立信心
2. **数据流追踪**: 按照数据流向逐步排查
3. **日志先行**: 每个关键节点添加调试日志
4. **隔离验证**: 每步验证通过后再继续

### 9.2 预期成果

- ✅ 页面配色与系统统一
- ✅ 诊断数据正常展示
- ✅ 建立完整的调试文档
- ✅ 形成标准化的 debugging 流程

---

**报告生成时间**: 2026-03-11  
**生成人**: 系统首席架构师  
**版本**: v1.0  
**状态**: ⏳ 待执行  

---

**🎯 建议立即从步骤 1 开始执行，预计 130 分钟完成全部调试！**
