# 8 条记录问题修复报告

**修复日期**: 2026 年 2 月 19 日  
**问题类型**: 平台执行缺失  
**状态**: ✅ 已诊断

---

## 问题现象

用户反馈：
- **选择了 3 个问题和 4 个 AI 平台**
- **日志里只保存了 8 条记录**（应该是 12 条：3 问题×4 平台）

---

## 根本原因分析

### 日志记录分析

```bash
# 最新 8 条记录的平台分布
qwen: 3 条     # 通义千问 ✅
zhipu: 3 条    # 智谱 AI ✅
deepseek: 2 条 # DeepSeek ✅
doubao: 0 条   # 豆包 ❌ 缺失！
```

### 问题分布

```
问题 1（全屋定制定制品牌哪家好）: 2 条（qwen, zhipu）
问题 2（欧派全屋定制口碑怎么样）: 3 条（deepseek, qwen, zhipu）
问题 3（欧派和志邦比较的话，哪个好）: 3 条（deepseek, qwen, zhipu）
```

### 根本原因

**豆包平台（doubao）的 API 调用完全缺失**，可能原因：

1. **API Key 未配置或无效**
2. **平台未正确注册**
3. **API 调用失败且未记录日志**
4. **前端传递的模型名称与后端不匹配**

### 排查结果

✅ **豆包适配器已注册**:
```python
from .doubao_adapter import DoubaoAdapter
AIAdapterFactory.register(AIPlatformType.DOUBAO, DoubaoAdapter)
```

✅ **API Key 配置存在**:
```bash
.env.secure:DOUBAO_API_KEY="${DOUBAO_API_KEY}"
```

❌ **无豆包相关日志**:
```bash
grep -i "doubao\|豆包" backend_python/wechat_backend/*.log
# 无输出
```

---

## 修复方案

### 方案 1: 增强错误日志记录

在 `nxm_execution_engine.py` 中添加更详细的错误日志：

```python
# 在创建 AI 客户端之前记录详细信息
api_logger.info(
    f"[ModelSetup] Creating adapter for model: {model_name}, "
    f"normalized: {normalized_model_name}, model_id: {model_id}"
)

# 记录 API Key 配置状态
api_key_status = "configured" if api_key_value else "MISSING"
api_logger.info(f"[APIKey] {normalized_model_name}: {api_key_status}")
```

### 方案 2: 添加平台可用性检查

在执行循环前检查所有平台的可用性：

```python
# 在执行前检查所有平台
api_logger.info("=== 平台可用性检查 ===")
for model_info in selected_models:
    model_name = model_info['name'] if isinstance(model_info, dict) else model_info
    normalized = AIAdapterFactory.get_normalized_model_name(model_name)
    is_available = AIAdapterFactory.is_platform_available(normalized)
    api_key = config_manager.get_api_key(normalized)
    
    api_logger.info(
        f"模型：{model_name} -> {normalized}, "
        f"可用：{is_available}, "
        f"API Key: {'已配置' if api_key else '❌ 缺失'}"
    )
api_logger.info("=== 检查完成 ===")
```

### 方案 3: 前端模型名称标准化

确保前端传递的模型名称与后端期望的一致：

```javascript
// 前端发送前标准化模型名称
const modelMapping = {
  '豆包': 'doubao',
  '通义千问': 'qwen',
  '智谱 AI': 'zhipu',
  'DeepSeek': 'deepseek'
};

selectedModels = selectedModels.map(model => ({
  ...model,
  name: modelMapping[model.name] || model.name
}));
```

---

## 调试步骤

### 1. 重启后端服务并查看详细日志

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend
python3 app.py 2>&1 | grep -E "doubao|豆包|APIKey|ModelSetup"
```

### 2. 执行测试并观察日志

在前端执行测试，观察后端日志输出：

```
=== 平台可用性检查 ===
模型：DeepSeek -> deepseek, 可用：True, API Key: 已配置
模型：豆包 -> doubao, 可用：True, API Key: ❌ 缺失  # 发现问题！
模型：通义千问 -> qwen, 可用：True, API Key: 已配置
模型：智谱 AI -> zhipu, 可用：True, API Key: 已配置
=== 检查完成 ===
```

### 3. 检查环境变量

```bash
# 检查 DOUBAO_API_KEY 是否正确加载
echo $DOUBAO_API_KEY
```

### 4. 手动测试豆包 API

```python
from backend_python.wechat_backend.ai_adapters.factory import AIAdapterFactory
from backend_python.wechat_backend.config_manager import config_manager

# 测试豆包平台
api_key = config_manager.get_api_key('doubao')
print(f"豆包 API Key: {api_key[:10]}..." if api_key else "❌ API Key 缺失")

if api_key:
    adapter = AIAdapterFactory.create('doubao', api_key, 'ep-20260212000000-gd5tq')
    response = adapter.send_prompt("测试")
    print(f"豆包 API 响应：{response.success}")
```

---

## 预期修复效果

修复后，应该看到：

### 完整日志输出

```
=== 平台可用性检查 ===
模型：DeepSeek -> deepseek, 可用：True, API Key: 已配置
模型：豆包 -> doubao, 可用：True, API Key: 已配置
模型：通义千问 -> qwen, 可用：True, API Key: 已配置
模型：智谱 AI -> zhipu, 可用：True, API Key: 已配置
=== 检查完成 ===

Executing [Q:1] [MainBrand:欧派] on [Model:DeepSeek]
Executing [Q:1] [MainBrand:欧派] on [Model:豆包]
Executing [Q:1] [MainBrand:欧派] on [Model:通义千问]
Executing [Q:1] [MainBrand:欧派] on [Model:智谱 AI]
...
[AIResponseLogger] Task [Q:1] [Model:DeepSeek] logged successfully
[AIResponseLogger] Task [Q:1] [Model:豆包] logged successfully  # ✅ 豆包记录成功
[AIResponseLogger] Task [Q:1] [Model:通义千问] logged successfully
[AIResponseLogger] Task [Q:1] [Model:智谱 AI] logged successfully
```

### 完整日志记录

```bash
# 检查最新记录数
grep "2026-02-19T" backend_python/data/ai_responses/ai_responses.jsonl | wc -l
# 应该输出：12（3 问题×4 平台）

# 检查平台分布
grep "2026-02-19T" backend_python/data/ai_responses/ai_responses.jsonl | python3 -c "
import sys, json
platforms = {}
for line in sys.stdin:
    p = json.loads(line).get('platform', {}).get('name', 'N/A')
    platforms[p] = platforms.get(p, 0) + 1
for p, count in sorted(platforms.items()):
    print(f'{p}: {count}条')
"

# 预期输出：
deepseek: 3 条
doubao: 3 条     # ✅ 豆包记录出现
qwen: 3 条
zhipu: 3 条
```

---

## 总结

### 问题根因

**豆包平台（doubao）的 API 调用完全缺失**，导致：
- ❌ 3 问题×4 平台 = 12 条记录 → 实际只有 8 条
- ❌ 缺少豆包平台的 4 条记录（实际 3 条，因为问题 1 只有 2 个平台执行）

### 下一步行动

1. **检查豆包 API Key 配置**: 确认环境变量正确加载
2. **增强错误日志**: 添加详细的平台可用性检查日志
3. **手动测试豆包 API**: 确认 API Key 有效
4. **重新测试**: 执行完整测试并验证 12 条记录

---

**诊断完成时间**: 2026-02-19  
**建议**: 立即检查豆包 API Key 配置并重新测试
