# AI 平台市场切换逻辑优化 - 完成报告

## 📋 需求说明

### 原始需求
希望在切换国内 AI 平台和海外 AI 平台时，用户已选择的 AI 平台**不要被清空**，而是：
- 选择国内 AI 平台时，只有在国内 AI 平台下被选择的 AI 平台才会生效
- 海外 AI 平台下即使有选择的，也不生效
- 反之亦然，选择海外 AI 平台时，只有在海外 AI 平台下被选择的 AI 平台才会生效
- 国内 AI 平台下即使有选择的，也不生效

### 核心设计
**保留选中状态，控制生效范围**

---

## ✅ 实现方案

### 1. 数据结构设计

```javascript
data: {
  selectedMarketTab: 'domestic',  // 当前激活的市场 Tab
  domesticAiModels: [...],        // 国内平台列表（包含 checked 状态）
  overseasAiModels: [...],        // 海外平台列表（包含 checked 状态）
  selectedModelCount: 0,          // 当前 Tab 的选中数量
  totalSelectedCount: 0           // 两个市场的总选中数（用于提示）
}
```

### 2. 核心方法

#### switchMarketTab - 切换市场 Tab
```javascript
switchMarketTab: function(e) {
  const newMarket = e.currentTarget.dataset.market;
  
  // 只切换 Tab，不清空选中状态
  this.setData({ selectedMarketTab: newMarket });
  
  // 更新选中数量显示（只计算当前 Tab 的选中项）
  this.updateSelectedModelCount();
}
```

**关键变更**:
- ❌ 旧逻辑：切换时清空原市场的所有选中状态
- ✅ 新逻辑：切换时保留所有选中状态

#### updateSelectedModelCount - 更新选中数量
```javascript
updateSelectedModelCount: function() {
  const currentMarket = this.data.selectedMarketTab;
  
  // 只计算当前 Tab 的选中数用于显示
  const displayCount = currentMarket === 'domestic' 
    ? selectedDomesticCount 
    : selectedOverseasCount;
  
  this.setData({ 
    selectedModelCount: displayCount,
    totalSelectedCount: selectedDomesticCount + selectedOverseasCount
  });
}
```

**关键变更**:
- 显示当前 Tab 的选中数
- 保存总选中数用于提示

#### getCurrentMarketSelectedModels - 获取当前市场选中模型
```javascript
getCurrentMarketSelectedModels: function() {
  const currentMarket = this.data.selectedMarketTab;
  const key = currentMarket === 'domestic' ? 'domesticAiModels' : 'overseasAiModels';
  
  // 只返回当前 Tab 下选中的模型 ID
  return models
    .filter(model => model.checked && !model.disabled)
    .map(model => model.id);
}
```

**关键逻辑**:
- 提交时只包含当前 Tab 的选中模型
- 另一个市场的选中模型不会被提交

---

## 🎨 用户界面

### 已选平台提示条

```xml
<view class="selected-models-hint" wx:if="{{selectedModelCount > 0}}">
  <text class="hint-icon">✓</text>
  <view class="hint-content">
    <text class="hint-text">
      当前市场已选择 <text class="highlight">{{selectedModelCount}}</text> 个 AI 平台
    </text>
    <text class="hint-sub" wx:if="{{totalSelectedCount > selectedModelCount}}">
      （另一个市场还选择了 {{totalSelectedCount - selectedModelCount}} 个，切换后可见）
    </text>
  </view>
</view>
```

### 显示效果

**场景 1: 国内 Tab 激活**
```
✓ 当前市场已选择 3 个 AI 平台
  （另一个市场还选择了 2 个，切换后可见）
```

**场景 2: 海外 Tab 激活**
```
✓ 当前市场已选择 2 个 AI 平台
```

---

## 🔄 交互流程示例

### 用户操作流程

1. **初始状态**
   - 默认在"国内 AI 平台"Tab
   - 选中：DeepSeek、豆包、通义千问（3 个）
   - 提示："当前市场已选择 3 个 AI 平台"

2. **切换到海外 Tab**
   - 点击"海外 AI 平台"Tab
   - 国内的选中状态被保留（不显示）
   - 提示："已切换到海外 AI 平台"

3. **在海外 Tab 选择平台**
   - 选中：ChatGPT、Claude（2 个）
   - 提示："当前市场已选择 2 个 AI 平台"
   - （此时国内还有 3 个选中，但不显示）

4. **切换回国内 Tab**
   - 点击"国内 AI 平台"Tab
   - 显示之前选中的 DeepSeek、豆包、通义千问
   - 提示："当前市场已选择 3 个 AI 平台"
   - 提示："（另一个市场还选择了 2 个，切换后可见）"

5. **提交诊断**
   - 当前在国内 Tab
   - 提交：DeepSeek、豆包、通义千问（3 个）
   - ChatGPT、Claude 不会被提交

---

## 📊 前后端交互逻辑

### 前端提交逻辑

```javascript
startBrandTest: function() {
  // ... 其他校验 ...
  
  // 【关键】只获取当前市场的选中模型
  let selectedModels = this.getCurrentMarketSelectedModels();
  
  // 提交给后端
  this.callBackendBrandTest(brand_list, selectedModels, customQuestions);
}
```

### 后端接收数据

后端接收到的 `selectedModels` 只包含当前激活市场的选中模型 ID：

**场景 1: 国内 Tab 激活时提交**
```json
{
  "selectedModels": ["deepseek", "doubao", "qwen"]
}
```

**场景 2: 海外 Tab 激活时提交**
```json
{
  "selectedModels": ["chatgpt", "claude"]
}
```

---

## ✅ 测试验证清单

### 基础功能测试
- [x] 默认显示"国内 AI 平台"Tab
- [x] 国内 Tab 下可以选择多个平台
- [x] 海外 Tab 下可以选择多个平台
- [x] 切换 Tab 时显示 Toast 提示

### 选中状态保留测试
- [x] 在国内 Tab 选中 3 个平台
- [x] 切换到海外 Tab，国内选中状态保留
- [x] 在海外 Tab 选中 2 个平台
- [x] 切换回国内 Tab，显示之前选中的 3 个平台
- [x] 提示条显示"另一个市场还选择了 2 个"

### 提交逻辑测试
- [x] 在国内 Tab 提交，只包含国内选中的模型
- [x] 在海外 Tab 提交，只包含海外选中的模型
- [x] 未选择任何平台时提交，显示错误提示

---

## 📝 代码变更总结

### 修改的文件
1. **pages/index/index.js**
   - `switchMarketTab`: 移除清空逻辑
   - `updateSelectedModelCount`: 只显示当前 Tab 选中数
   - `getCurrentMarketSelectedModels`: 添加详细注释

2. **pages/index/index.wxml**
   - 更新已选平台提示条，显示详细信息

3. **pages/index/index.wxss**
   - 添加 `.hint-content`、`.hint-text .highlight`、`.hint-sub` 样式

### 新增的字段
- `totalSelectedCount`: 保存两个市场的总选中数

---

## 🎯 用户体验提升

### 优化前
- ❌ 切换 Tab 时清空所有选中
- ❌ 用户需要重新选择平台
- ❌ 无法预先配置两个市场

### 优化后
- ✅ 切换 Tab 时保留所有选中
- ✅ 用户可以预先配置两个市场
- ✅ 清晰的提示告知另一个市场的选择状态
- ✅ 减少重复操作，提升效率

---

## 🚀 部署状态

- ✅ 代码已提交
- ✅ 已推送到 GitHub
- ✅ 分支：`feature/phase1-state-machine-timeout-retry`
- ✅ 提交 ID: `ed51ff2`

---

## 📌 注意事项

1. **向后兼容**: 后端接收逻辑无需修改，仍然接收 `selectedModels` 数组
2. **数据持久化**: 保存配置时会保存两个市场的选中状态
3. **用户引导**: 通过提示条清晰告知用户当前状态

---

**实现完成时间**: 2026-02-28  
**实现者**: AI Assistant  
**状态**: ✅ 已完成并推送
