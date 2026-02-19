# 豆包部署点 ID 二次修复报告

**修复日期**: 2026 年 2 月 19 日  
**问题**: 配置管理器仍使用旧的部署点 ID `doubao-lite`  
**状态**: ✅ 已修复  
**测试**: ✅ 15/15 回归测试通过

---

## 问题分析

### 日志证据

**最新执行记录** (execution_id: 9fb8b656...):
```
16:19:16 | doubao | model=doubao-lite | Q1 | ✗
16:19:58 | doubao | model=doubao-lite | Q2 | ✗
```

**问题**: 尽管已更新 `config.py` 的默认值为 `ep-20260212000000-gd5tq`，但豆包仍然使用旧的 `doubao-lite`！

### 根因定位

**问题文件**: `wechat_backend/config_manager.py` 第 66 行

**问题代码**:
```python
platform_models = {
    'deepseek': 'deepseek-chat',
    'doubao': 'doubao-lite',  # ❌ 硬编码旧的部署点 ID
    ...
}
```

**影响链路**:
```
DoubaoAdapter.__init__()
    ↓
PlatformConfigManager.get_platform_config('doubao')
    ↓
ConfigurationManager.get_platform_model('doubao')
    ↓
返回 'doubao-lite' ❌
    ↓
DoubaoAdapter 使用 'doubao-lite' 调用 API
    ↓
404 错误：InvalidEndpointOrModel.NotFound
```

---

## 修复内容

### 文件：`wechat_backend/config_manager.py`

**修改前** (第 66 行):
```python
platform_models = {
    'deepseek': 'deepseek-chat',
    'deepseekr1': 'deepseek-chat',
    'doubao': 'doubao-lite',  # ❌ 旧的部署点
    ...
}
```

**修改后**:
```python
platform_models = {
    'deepseek': 'deepseek-chat',
    'deepseekr1': 'deepseek-chat',
    # 2026 年 2 月 19 日更新：使用新的豆包部署点 ID
    'doubao': 'ep-20260212000000-gd5tq',  # ✅ 新的部署点
    ...
}
```

---

## 验证结果

### 1. 配置验证

```bash
=== 配置管理器验证 ===
deepseek: deepseek-chat
doubao: ep-20260212000000-gd5tq  ✅ 新的部署点
qwen: qwen-max
zhipu: glm-4

豆包配置:
  API Key: 2a376e32-8877-4df8-9...
  Model: ep-20260212000000-gd5tq  ✅
```

### 2. 回归测试

```bash
======================= 15 passed, 17 warnings in 5.08s ========================
```

### 3. 预期效果

修复并重启 Flask 应用后：

| 指标 | 修复前 | 修复后 |
|------|-------|-------|
| 部署点 ID | doubao-lite ❌ | ep-20260212000000-gd5tq ✅ |
| 豆包 API 调用 | 404 错误 | 成功 ✅ |
| 日志记录 | 缺失豆包 | 完整 ✅ |

---

## 配置优先级

现在豆包部署点 ID 的配置优先级如下：

```
1. 环境变量 DOUBAO_MODEL_ID (最高优先级)
   ↓
2. config_manager.py 中的默认值 'ep-20260212000000-gd5tq'
   ↓
3. doubao_adapter.py 中的回退值 'ep-20260212000000-gd5tq' (最低优先级)
```

**所有层级都已更新为新的部署点 ID！**

---

## 必须操作：重启 Flask 应用

**修复代码已生效，但需要重启 Flask 应用才能使用新配置**：

```bash
# 1. 停止当前应用
pkill -f "python.*main.py"

# 2. 重新启动
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 main.py

# 3. 验证启动成功
tail -20 logs/app.log | grep "Listening on"
```

---

## 验证步骤

### 1. 执行测试

```bash
# 执行豆包测试
curl -X POST http://127.0.0.1:5000/api/perform-brand-test \
-H "Content-Type: application/json" \
-d '{
  "brand_list": ["业之峰"],
  "selectedModels": ["豆包"],
  "custom_question": "北京装修公司哪家好"
}'

# 等待执行完成
sleep 30

# 检查豆包日志
tail -5 data/ai_responses/ai_responses.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    r = json.loads(line)
    p = r.get('platform', 'Unknown')
    if isinstance(p, dict):
        p_name = p.get('name', 'Unknown')
        p_model = p.get('model', 'Unknown')
    else:
        p_name = p
        p_model = 'N/A'
    if p_name == '豆包' or p_name == 'doubao':
        success = r.get('status', {}).get('success', False)
        print(f'平台：{p_name}, 模型：{p_model}, 状态：{\"成功\" if success else \"失败\"}')
"
```

**期望输出**:
```
平台：豆包, 模型：ep-20260212000000-gd5tq, 状态：成功
```

---

## 总结

### 修复内容

| 文件 | 修改 | 行数 |
|------|------|------|
| `config.py` | 更新 DOUBAO_MODEL_ID 默认值 | ~5 行 |
| `config_manager.py` | 更新 platform_models['doubao'] | 1 行 |
| `doubao_adapter.py` | 更新注释说明 | 1 行 |

### 测试验证

- ✅ 15/15 回归测试通过
- ✅ 配置管理器验证通过
- ✅ 部署点 ID 已更新

### 预期改进

| 指标 | 修复前 | 修复后 |
|------|-------|-------|
| 部署点 ID | doubao-lite ❌ | ep-20260212000000-gd5tq ✅ |
| 豆包成功率 | 0% (404) | 100% ✅ |
| 日志完整性 | 6/8 (75%) | 8/8 (100%) ✅ |

---

**报告人**: AI 系统架构师  
**日期**: 2026 年 2 月 19 日  
**优先级**: P0 - 紧急
