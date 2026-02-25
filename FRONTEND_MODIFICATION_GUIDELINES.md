# 📋 前端代码修改规范要求

**版本**: 1.0  
**生效日期**: 2026-02-26  
**适用范围**: 所有前端代码修改

---

## 一、核心原则

### 1. 数据完整性第一原则

**规范**: 任何修改不得破坏现有数据结构的完整性

**具体要求**:
- ✅ 必须保留所有默认数据定义
- ✅ 不得删除或注释掉关键数据字段
- ✅ 修改数据初始化逻辑时，必须保留完整的默认值

**反面案例**:
```javascript
// ❌ 错误：依赖 pageContext.data 中的值，可能导致数据丢失
let domesticAiModels = pageContext.data?.domesticAiModels;
if (!Array.isArray(domesticAiModels)) {
  domesticAiModels = getDefaultModels();  // 如果 data 存在但为空，则使用空数组
}
```

**正面案例**:
```javascript
// ✅ 正确：始终使用完整的默认列表
let domesticAiModels = [
  { name: 'DeepSeek', id: 'deepseek', checked: false, ... },
  { name: '豆包', id: 'doubao', checked: false, ... },
  // ... 完整的默认列表
];
// 然后根据用户偏好更新选中状态
```

---

### 2. 防御性编程原则

**规范**: 始终假设数据可能不存在或格式不正确

**具体要求**:
- ✅ 访问嵌套属性前必须检查父对象存在
- ✅ 使用 `Array.isArray()` 验证数组
- ✅ 提供默认值避免 `undefined`

**反面案例**:
```javascript
// ❌ 错误：假设数据总是存在
const models = config.domesticAiModels;
models.forEach(m => console.log(m.name));  // 如果 models 是 undefined 会报错
```

**正面案例**:
```javascript
// ✅ 正确：防御性检查
const modelsConfig = Array.isArray(config.domesticAiModels) ? config.domesticAiModels : [];
const models = modelsConfig.length > 0 ? modelsConfig : getDefaultModels();
```

---

### 3. 数据源单一原则

**规范**: 每个数据字段只能有一个权威数据源

**具体要求**:
- ✅ 明确定义默认数据的定义位置
- ✅ 避免多处定义相同的默认数据
- ✅ 如需修改默认值，只在一处修改

**反面案例**:
```javascript
// ❌ 错误：多处定义相同的默认数据
// initService.js 中定义了一次
const defaultModels = [...];

// index.js 中又定义了一次
const defaultModels = [...];

// 如果两处不一致，会导致数据混乱
```

**正面案例**:
```javascript
// ✅ 正确：单一数据源
// initService.js 中唯一定义默认数据
const DEFAULT_MODELS = [...];

// 其他文件导入使用
import { DEFAULT_MODELS } from './initService';
```

---

### 4. 修改影响范围评估原则

**规范**: 修改前必须评估影响范围

**具体要求**:
- ✅ 修改前搜索所有引用该代码的位置
- ✅ 评估修改对上下游的影响
- ✅ 修改后验证相关功能是否正常

**检查清单**:
```
[ ] 是否搜索了所有引用点？
[ ] 是否评估了对其他模块的影响？
[ ] 是否测试了相关功能？
[ ] 是否更新了相关文档？
```

---

## 二、具体场景规范

### 场景 1: 修改数据初始化逻辑

**规范要求**:
1. 保留完整的默认数据定义
2. 不依赖可能为空的中间状态
3. 添加日志确认数据已正确设置

**示例**:
```javascript
// ✅ 正确的修改方式
const loadUserPlatformPreferences = (pageContext) => {
  // 1. 获取用户偏好
  const userPrefs = wx.getStorageSync(STORAGE_KEY_PLATFORM_PREFS);
  
  // 2. 始终使用完整的默认列表（不依赖 pageContext.data）
  let domesticAiModels = [
    { name: 'DeepSeek', id: 'deepseek', checked: false, ... },
    // ... 完整的 8 个国内平台
  ];
  
  // 3. 根据用户偏好更新选中状态
  const selectedDomestic = userPrefs?.domestic || ['DeepSeek', '豆包'];
  const updatedDomestic = domesticAiModels.map(model => ({
    ...model,
    checked: selectedDomestic.includes(model.name)
  }));
  
  // 4. 设置数据并确认
  pageContext.setData({ domesticAiModels: updatedDomestic });
  console.log('✅ AI 平台矩阵已设置，数量:', updatedDomestic.length);
};
```

---

### 场景 2: 修改 setData 调用

**规范要求**:
1. 不得覆盖未提及的字段
2. 使用展开运算符保留其他字段
3. 验证 setData 后数据是否正确

**反面案例**:
```javascript
// ❌ 错误：覆盖了整个 data 对象
this.setData({
  config: newConfig  // 这会丢失 config 以外的所有字段
});
```

**正面案例**:
```javascript
// ✅ 正确：只更新特定字段
this.setData({
  config: newConfig,
  // 保留其他字段不变
});
```

---

### 场景 3: 添加新功能

**规范要求**:
1. 不得破坏现有功能
2. 新功能代码与现有代码隔离
3. 添加功能开关便于回滚

**检查清单**:
```
[ ] 是否测试了现有功能？
[ ] 新功能是否可独立关闭？
[ ] 是否有回滚方案？
[ ] 是否更新了文档？
```

---

## 三、代码审查要求

### 提交前自查

**必须检查的项目**:
- [ ] 默认数据是否完整保留
- [ ] 防御性检查是否充分
- [ ] 日志是否确认关键操作成功
- [ ] 是否测试了相关功能

### 审查重点

**审查者必须验证**:
- [ ] 数据完整性是否被破坏
- [ ] 是否有潜在的 undefined/null 引用
- [ ] 日志是否充分
- [ ] 是否有回滚方案

---

## 四、违规处罚

### 一级违规（数据丢失）

**定义**: 修改导致默认数据丢失

**处罚**:
1. 立即回滚修改
2. 提交事故报告
3. 重新学习本规范

### 二级违规（功能破坏）

**定义**: 修改导致现有功能失效

**处罚**:
1. 立即修复
2. 补充测试用例
3. 团队内通报

### 三级违规（规范违反）

**定义**: 未遵守本规范但未造成实质影响

**处罚**:
1. 代码审查时指出
2. 修改后重新提交

---

## 五、附录

### A. 关键数据字段清单

**不得删除或修改的字段**:
- `domesticAiModels` - 国内 AI 平台列表
- `overseasAiModels` - 海外 AI 平台列表
- `customQuestions` - 自定义问题列表
- `competitorBrands` - 竞品品牌列表

### B. 默认值定义位置

| 数据字段 | 默认值定义位置 | 文件路径 |
|----------|----------------|----------|
| domesticAiModels | loadUserPlatformPreferences | services/initService.js |
| overseasAiModels | loadUserPlatformPreferences | services/initService.js |
| customQuestions | initializeDefaults | pages/index/index.js |

### C. 日志确认点

**必须添加日志确认的关键操作**:
```javascript
// 数据设置后
console.log('✅ AI 平台矩阵已设置，数量:', domesticAiModels.length);

// 配置加载后
console.log('✅ 配置已加载:', config);

// 草稿恢复后
console.log('✅ 草稿已恢复:', draft);
```

---

## 六、修订历史

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|----------|--------|
| 1.0 | 2026-02-26 | 初始版本 | 首席架构师 |

---

**本规范自发布之日起生效，所有前端代码修改必须遵守。**

**违反本规范导致的事故，将按照事故等级进行处罚。**
