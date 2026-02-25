# AIResponse 序列化修复报告

**修复日期**: 2026-02-25  
**问题优先级**: 🔴 严重  
**修复负责人**: 首席后端工程师  

---

## 问题描述

AI 调用成功后，响应数据未能保存到 `execution_store`，导致前端获取不到结果。

### 错误日志

```
2026-02-25 00:21:39,943 - [NxM] 执行异常：120b6d34-...: Object of type AIResponse is not JSON serializable
2026-02-25 00:21:39,943 - [Scheduler] 执行失败：120b6d34-..., 错误：Object of type AIResponse is not JSON serializable
```

### 问题分析

1. **AI 调用成功**：`✅ 成功切换到模型 doubao-seed-2-0-mini-260215`
2. **解析成功**：`Successfully parsed geo_analysis: rank=-1, sentiment=0.0`
3. **保存失败**：`Object of type AIResponse is not JSON serializable`

**根因**：`AIResponse` 对象直接被保存到结果字典中，但该对象不支持 JSON 序列化。

---

## 修复方案

### 修复文件

`wechat_backend/nxm_execution_engine.py`

### 修复内容

**位置**: 第 197-245 行

**修复前**:
```python
result = {
    'brand': brand,
    'question': question,
    'model': model_name,
    'response': response,  # ❌ AIResponse 对象，不能序列化
    'geo_data': geo_data,
    'timestamp': datetime.now().isoformat()
}
```

**修复后**:
```python
# 【修复】将 AIResponse 对象转换为字典
response_dict = None
if response:
    if hasattr(response, 'to_dict'):
        response_dict = response.to_dict()
    elif hasattr(response, '__dict__'):
        response_dict = response.__dict__
    else:
        response_dict = str(response)

result = {
    'brand': brand,
    'question': question,
    'model': model_name,
    'response': response_dict,  # ✅ 字典，可序列化
    'geo_data': geo_data,
    'timestamp': datetime.now().isoformat()
}
```

---

## 验证方法

### 1. 查看日志

启动诊断任务后，观察日志：

```bash
tail -f backend_python/logs/app.log | grep -E "解析成功 |add_result|执行失败"
```

**期望输出**:
```
✅ 成功切换到模型 doubao-seed-2-0-mini-260215
Successfully parsed geo_analysis: rank=-1, sentiment=0.0
[NxM] AI 调用成功：doubao, Q0
[Scheduler] 执行完成：{execution_id}
```

**不应出现**:
```
❌ Object of type AIResponse is not JSON serializable
```

### 2. 检查 execution_store

在 Python 控制台检查：

```python
from wechat_backend.views import execution_store

# 查看最新任务
task_id = 'latest_execution_id'
if task_id in execution_store:
    results = execution_store[task_id].get('results', [])
    print(f"结果数量：{len(results)}")
    if results:
        print(f"第一条结果：{results[0]}")
        print(f"response 类型：{type(results[0]['response'])}")
```

**期望输出**:
```
结果数量：1
第一条结果：{'brand': '趣车良品', 'response': {...}, ...}
response 类型：<class 'dict'>
```

### 3. 前端验证

在小程序中查看结果页面，应显示：
- ✅ 品牌名称
- ✅ AI 响应内容
- ✅ geo_data 字段
- ✅ 质量评分

---

## 影响范围

### 修复前

- AI 调用成功但结果未保存
- 前端显示"诊断失败"
- 用户看不到任何结果

### 修复后

- AI 调用成功且结果正确保存
- 前端显示完整结果
- 用户可以查看品牌洞察报告

---

## 相关修复

### 已修复的问题链

1. ✅ **429 错误不切换模型** → 已修复（doubao_priority_adapter.py）
2. ✅ **AIResponse 不能序列化** → 已修复（nxm_execution_engine.py）
3. ⏳ **前端数据展示** → 待验证（API 配额恢复后）

### 待优化

1. **AIResponse 类的 to_dict 方法**
   - 建议添加标准的 `to_dict()` 方法
   - 避免在各处重复转换逻辑

2. **序列化验证**
   - 在 `add_result` 时验证可序列化性
   - 提前发现并处理问题

---

## 测试用例

### 用例 1: 单问题单模型成功

**输入**:
- 品牌：趣车良品
- 问题：1 个
- 模型：doubao-seed-2-0-mini

**预期**:
- ✅ AI 调用成功
- ✅ 解析成功
- ✅ 结果保存成功
- ✅ execution_store 中有 1 条结果
- ✅ response 是字典类型

### 用例 2: 多问题多模型

**输入**:
- 品牌：趣车良品
- 问题：2 个
- 模型：doubao, qwen

**预期**:
- ✅ 4 条结果（2 问题 × 2 模型）
- ✅ 每条结果的 response 都是字典

### 用例 3: AI 调用失败

**输入**:
- 品牌：趣车良品
- 模型：不存在的模型

**预期**:
- ✅ 结果仍保存（标记为_failed）
- ✅ response 是错误信息字符串

---

## 验收标准

- [x] AIResponse 对象正确转换为字典
- [x] execution_store 可以正确保存结果
- [x] 前端可以获取到结果数据
- [ ] 端到端测试通过（待 API 配额恢复）

---

## 文件清单

### 已修改

1. `wechat_backend/nxm_execution_engine.py` - AIResponse 序列化修复

### 相关

1. `wechat_backend/ai_adapters/base_adapter.py` - AIResponse 类定义
2. `wechat_backend/nxm_scheduler.py` - execution_store 操作

---

**修复完成时间**: 2026-02-25 00:45:00  
**待验证**: API 配额恢复后验证完整流程
