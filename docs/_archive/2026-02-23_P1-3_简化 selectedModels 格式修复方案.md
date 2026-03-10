# P1-3: 简化 selectedModels 格式 - 修复方案

**问题**: 前后端 selectedModels 格式转换重复，增加复杂度
**影响**: 代码维护困难，可能出错
**修复**: 前端直接发送字符串数组，后端简化处理

---

## 修复内容

### 1. 前端修复

**文件**: `services/brandTestService.js` ✅ 已修复

**修复前**:
```javascript
// ❌ 复杂：转换为对象数组
const processedSelectedModels = (selectedModels || []).map(item => {
  if (typeof item === 'object' && item !== null) {
    const modelName = (item.id || item.name || item.value || '').toLowerCase();
    return {
      name: modelName,
      checked: item.checked !== undefined ? item.checked : true
    };
  }
  // ...
});

return {
  brand_list,
  selectedModels: processedSelectedModels,  // [{name, checked}, ...]
  custom_question
};
```

**修复后**:
```javascript
// ✅ 简化：直接发送字符串数组
const modelNames = (selectedModels || [])
  .map(item => {
    let modelName;
    if (typeof item === 'object' && item !== null) {
      modelName = (item.id || item.name || item.value || item.label || '').toLowerCase();
    } else if (typeof item === 'string') {
      modelName = item.toLowerCase();
    } else {
      return null;
    }
    return modelName;
  })
  .filter(name => SUPPORTED_MODELS.includes(name));

return {
  brand_list,
  selectedModels: modelNames,  // ['deepseek', 'qwen', ...]
  custom_question
};
```

### 2. 后端修复

**文件**: `wechat_backend/views.py` (需手动应用补丁)

**修复前**:
```python
# ❌ 复杂：处理对象数组
parsed_selected_models = []
for model in selected_models:
    if isinstance(model, dict):
        model_name = model.get('name') or model.get('id')
        if model_name:
            parsed_selected_models.append({
                'name': model_name,
                'checked': model.get('checked', True)
            })
    elif isinstance(model, str):
        parsed_selected_models.append({'name': model, 'checked': True})

selected_models = parsed_selected_models  # [{name, checked}, ...]
```

**修复后**:
```python
# ✅ 简化：处理字符串数组（向后兼容对象）
parsed_selected_models = []
for model in selected_models:
    if isinstance(model, str):
        # P1-3 修复：直接使用字符串
        model_name = model.lower().strip()
        if model_name:
            parsed_selected_models.append(model_name)
    elif isinstance(model, dict):
        # 兼容旧格式
        model_name = model.get('name') or model.get('id')
        if model_name:
            parsed_selected_models.append(str(model_name).lower().strip())

selected_models = parsed_selected_models  # ['deepseek', 'qwen', ...]
```

---

## 数据格式对比

| 阶段 | 格式 | 示例 |
|-----|------|------|
| **修复前** | 对象数组 | `[{name: 'deepseek', checked: true}, ...]` |
| **修复后** | 字符串数组 | `['deepseek', 'qwen', 'doubao']` |

---

## 优势

1. ✅ **简化前端逻辑** - 减少对象转换
2. ✅ **简化后端逻辑** - 直接处理字符串
3. ✅ **减少数据量** - 去除冗余的 `checked` 字段
4. ✅ **向后兼容** - 后端仍支持对象格式

---

## 集成步骤

### 步骤 1: 前端已修复 ✅

`services/brandTestService.js` 已更新，无需额外操作。

### 步骤 2: 后端手动应用补丁

在 `wechat_backend/views.py` 中找到第 242-274 行，替换为：

```python
# P1-3 修复：简化 selectedModels 处理，前端已发送字符串数组
selected_models = data['selectedModels']
if not selected_models:
    return jsonify({"status": "error", "error": 'At least one AI model must be selected', "code": 400}), 400

# 验证并规范化模型名称（支持字符串和对象两种格式，向后兼容）
parsed_selected_models = []
for model in selected_models:
    if isinstance(model, str):
        # P1-3 修复：直接使用字符串
        model_name = model.lower().strip()
        if model_name:
            parsed_selected_models.append(model_name)
    elif isinstance(model, dict):
        # 兼容旧格式：从对象提取名称
        model_name = model.get('name') or model.get('id') or model.get('value') or model.get('label')
        if model_name:
            parsed_selected_models.append(str(model_name).lower().strip())
    else:
        api_logger.warning(f"Unsupported model format: {model}, type: {type(model)}")

# 更新 selected_models 为解析后的字符串列表
selected_models = parsed_selected_models

# 审计要求：在后端打印关键调试日志
api_logger.info(f"[Sprint 1] 模型列表：{selected_models} (原始：{data['selectedModels']})")

if not selected_models:
    return jsonify({"status": "error", "error": 'No valid AI models found after parsing', "code": 400}), 400
```

---

## 验证方法

### 1. 前端验证
```javascript
// 在浏览器控制台测试
const payload = buildPayload({
  brandName: '测试品牌',
  selectedModels: [
    {id: 'deepseek', name: 'DeepSeek'},
    {name: 'Qwen', id: 'qwen'},
    'doubao'
  ],
  customQuestions: ['问题 1']
});

console.log('selectedModels 格式:', payload.selectedModels);
// 应该输出：['deepseek', 'qwen', 'doubao']
```

### 2. 后端验证
```bash
# 发送测试请求
curl -X POST http://127.0.0.1:5000/api/perform-brand-test \
  -H "Content-Type: application/json" \
  -d '{
    "brand_list": ["测试品牌"],
    "selectedModels": ["deepseek", "qwen"],
    "custom_question": "问题"
  }'

# 检查日志
grep "模型列表" backend_python/logs/app.log
# 应该输出：[Sprint 1] 模型列表：['deepseek', 'qwen']
```

---

**状态**: ✅ 前端已完成，⏳ 后端需手动应用补丁
**兼容性**: ✅ 向后兼容旧格式
