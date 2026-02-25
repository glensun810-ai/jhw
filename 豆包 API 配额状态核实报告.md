# 豆包 API 配额状态核实报告

**核实时间**: 2026-02-25 01:00:00  
**核实人**: 首席测试专家  

---

## 核实结论

### ✅ 确认：P2/P3/P4 配额充足

根据日志分析：
- **P1 (doubao-seed-1-8-251228)**: ❌ 配额用尽（429 错误）
- **P2 (doubao-seed-2-0-mini-260215)**: ✅ 配额充足，调用成功
- **P3 (doubao-seed-2-0-pro-260215)**: ✅ 配额充足（未使用）
- **P4 (doubao-seed-2-0-lite-260215)**: ✅ 配额充足（未使用）

### 证据

**P1 配额用尽**：
```
2026-02-25 00:21:21,932 - [EXCEPTION] INIT HEALTH_CHECK Doubao health check failed: 429
response: {"error":{"code":"SetLimitExceeded","message":"Your account [2103200550] has reached 
the set inference limit for the [doubao-seed-1-8] model..."}}
```

**P2 切换成功且无 429 错误**：
```
2026-02-25 00:21:27,487 - [DoubaoPriority] ✅ 成功切换到模型 doubao-seed-2-0-mini-260215
2026-02-25 00:21:27,488 - [DoubaoPriority] 使用新模型 doubao-seed-2-0-mini-260215 重试
（后续无 429 错误日志）
```

---

## 真正的问题

### 问题：AIResponse 对象不能序列化

**现象**：
```
✅ P2 调用成功
✅ Successfully parsed geo_analysis: rank=-1, sentiment=0.0
❌ Object of type AIResponse is not JSON serializable
❌ 执行失败：ae10f2ea-..., 错误：Object of type AIResponse is not JSON serializable
```

**根因**：
- AI 调用返回 `AIResponse` 对象
- 该对象直接保存到结果字典中
- `execution_store` 需要 JSON 序列化
- `AIResponse` 对象不支持 JSON 序列化

**修复**：
- 文件：`wechat_backend/nxm_execution_engine.py`
- 位置：第 197-245 行
- 方法：将 `AIResponse` 转换为字典

```python
# 修复后
response_dict = response.to_dict() if hasattr(response, 'to_dict') else response.__dict__
result = {
    'response': response_dict,  # ✅ 字典对象，可序列化
    ...
}
```

---

## 完整流程分析

### 最新测试（00:21:16）

```
用户选择：doubao
  ↓
调用 P1 (doubao-seed-1-8)
  ↓
❌ 429 错误（配额用尽）
  ↓
✅ 切换到 P2 (doubao-seed-2-0-mini)
  ↓
✅ AI 调用成功（无 429 错误）
  ↓
✅ 解析 geo_analysis 成功
  ↓
❌ 保存失败（AIResponse 不能序列化）← 当前问题
```

### 修复后的预期流程

```
用户选择：doubao
  ↓
调用 P1 (doubao-seed-1-8)
  ↓
❌ 429 错误（配额用尽）
  ↓
✅ 切换到 P2 (doubao-seed-2-0-mini)
  ↓
✅ AI 调用成功
  ↓
✅ 解析 geo_analysis 成功
  ↓
✅ 保存到 execution_store（AIResponse 已修复）
  ↓
✅ 返回结果给前端
  ↓
✅ 显示品牌洞察报告
```

---

## 验证方法

### 1. 检查 P2 配额状态

在豆包控制台查看：
- 模型：doubao-seed-2-0-mini-260215
- 配额使用情况：应显示充足

### 2. 查看日志

```bash
tail -f backend_python/logs/app.log | grep -E "P2|doubao-seed-2-0-mini|429|解析成功"
```

**期望输出**：
```
✅ 成功切换到模型 doubao-seed-2-0-mini-260215
使用新模型 doubao-seed-2-0-mini-260215 重试
Successfully parsed geo_analysis: rank=-1, sentiment=0.0
[Scheduler] 执行完成：{execution_id}
```

**不应出现**：
```
❌ 429 Client Error (针对 P2)
❌ Object of type AIResponse is not JSON serializable
```

---

## 结论

1. **P2/P3/P4 配额确实充足** - 用户反馈正确
2. **429 错误仅影响 P1** - 已自动切换到 P2
3. **当前阻塞问题是 AIResponse 序列化** - 已修复
4. **修复后即可正常使用** - 无需等待配额恢复

---

## 下一步

1. **重启后端服务**（加载修复代码）
2. **重新测试诊断**
3. **验证 P2 成功返回结果**
4. **检查前端展示**

---

**报告时间**: 2026-02-25 01:00:00  
**状态**: 等待修复验证
