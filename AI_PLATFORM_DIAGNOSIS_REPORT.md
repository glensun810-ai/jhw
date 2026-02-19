# AI Platform API 问题诊断报告

## 执行摘要

对豆包 (Doubao)、通义千问 (Qwen) 和智谱 AI (Zhipu) 三个平台的 API 进行了详细测试和分析。

### 测试结果

| 平台 | 状态 | API Key | 问题描述 |
|------|------|---------|----------|
| **Qwen (通义千问)** | ✅ 正常 | `sk-5261a4...c653` | 工作正常，延迟 1.70s |
| **Zhipu (智谱 AI)** | ✅ 正常 | `504d64a0...HbiNh` | 工作正常，延迟 0.93s |
| **Doubao (豆包)** | ❌ 失败 | `2a376e32...c9f92` | **404 错误 - 模型/端点不存在** |

---

## 详细分析

### 1. Qwen API (阿里云通义千问) ✅

**配置信息:**
- **Endpoint:** `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation`
- **Model:** `qwen-max`
- **API Key 格式:** `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (35 字符)

**测试结果:**
```
响应状态：200
延迟：1.70s
响应内容：你好，我是 Qwen，由阿里云开发的超大规模语言模型...
```

**结论:** Qwen API 配置正确，工作正常。

---

### 2. Zhipu API (智谱 AI) ✅

**配置信息:**
- **Endpoint:** `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- **Model:** `glm-4`
- **API Key 格式:** `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxx` (49 字符，包含点号分隔)

**测试结果:**
```
响应状态：200
延迟：0.93s
响应内容：你好，我是一个由智谱 AI 训练的大语言模型...
```

**结论:** Zhipu API 配置正确，工作正常。

---

### 3. Doubao API (字节豆包) ❌

**配置信息:**
- **Endpoint:** `https://ark.cn-beijing.volces.com/api/v3/chat/completions`
- **当前 Model:** `Doubao-pro` / `doubao-lite` (❌ 错误)
- **API Key 格式:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (36 字符，UUID 格式)

**错误信息:**
```json
{
  "error": {
    "code": "InvalidEndpointOrModel.NotFound",
    "message": "The model or endpoint doubao-lite does not exist or you do not have access to it."
  }
}
```

**问题根因:**

豆包 API **不支持**直接使用通用模型名称（如 `doubao-lite`、`doubao-pro`），而是需要使用**部署点 ID (Endpoint ID)**。

**正确的模型名称格式:**
1. **部署点 ID 格式:** `ep-xxxxxxxxxxxxxxxx-xxxx` (例如：`ep-20260212000000-gd5tq`)
2. **完整模型版本格式:** `doubao-1-5-pro-32k-250115` (包含版本号和日期)

**已测试的无效模型名称:**
- ❌ `doubao-lite`
- ❌ `doubao-pro`
- ❌ `doubao-1-5-pro`
- ❌ `doubao-1-5-lite`
- ❌ `doubao-1-5`
- ❌ `doubao`
- ❌ `ep-default-model`

---

## 解决方案

### 方案一：获取正确的部署点 ID (推荐)

1. **登录火山引擎方舟控制台:**
   - 访问 https://console.volcengine.com/ark/

2. **创建推理接入点:**
   - 进入「模型广场」
   - 选择需要的模型（如 Doubao-pro-32k）
   - 点击「使用现在」
   - 创建推理接入点
   - 获取 **Endpoint ID** (格式：`ep-xxxxxxxxxxxxxxxx-xxxx`)

3. **更新环境变量:**
   ```bash
   DOUBAO_MODEL_ID=ep-20260212000000-gd5tq  # 替换为实际的 Endpoint ID
   ```

### 方案二：使用完整模型版本名称

如果不想创建部署点，可以使用完整的模型版本名称：

```bash
DOUBAO_MODEL_ID=doubao-1-5-pro-32k-250115
```

**注意:** 需要确保 API Key 有权限访问该模型版本。

---

## 代码修复建议

### 修改 `doubao_adapter.py`

当前代码问题：
```python
model_name = os.getenv('DOUBAO_MODEL_ID', 'Doubao-pro')  # ❌ 默认值无效
```

建议修改为：
```python
model_name = os.getenv('DOUBAO_MODEL_ID')
if not model_name:
    # 如果没有配置，使用一个常见的部署点 ID 格式
    # 用户必须在环境变量中配置正确的 Endpoint ID
    api_logger.warning("DOUBAO_MODEL_ID not configured. Please set it in .env file.")
    model_name = 'ep-20260212000000-gd5tq'  # 示例格式，实际需要替换
```

### 修改 `.env.secure` 文件

添加明确的配置说明：
```bash
# 豆包 API Key (UUID 格式)
DOUBAO_API_KEY=2a376e32-8877-4df8-9865-7eb3e99c9f92

# 豆包部署点 ID (必须配置，格式：ep-xxxxxxxxxxxxxxxx-xxxx)
# 获取方式：登录火山引擎方舟控制台 -> 模型广场 -> 创建推理接入点
DOUBAO_MODEL_ID=ep-20260212000000-gd5tq
```

---

## 验证步骤

1. **获取正确的 Endpoint ID 后，运行测试脚本:**
   ```bash
   cd /Users/sgl/PycharmProjects/PythonProject/backend_python
   python3 test_three_platforms.py
   ```

2. **预期输出:**
   ```
   Qwen: ✅ PASS
   Doubao: ✅ PASS
   Zhipu: ✅ PASS
   ```

---

## 其他注意事项

### API Key 有效性检查

当前代码中的检查逻辑有问题：
```python
# config.py 中的问题代码
return bool(api_key and api_key.strip() != '' and 
            not api_key.startswith('sk-') and  # ❌ 错误：Qwen 的 key 就是以 sk- 开头
            not api_key.endswith('[在此粘贴你的 Key]'))
```

**建议修复:**
```python
return bool(api_key and api_key.strip() != '' and 
            not api_key.endswith('[在此粘贴你的 Key]'))
```

### 电路断路器状态

检查是否因为之前的失败导致电路断路器处于开启状态：
```python
# 查看电路断路器状态
# 如果断路器开启，需要等待恢复或重启服务
```

---

## 总结

1. **Qwen 和 Zhipu API 工作正常**，无需修改
2. **Doubao API 失败原因:** 使用了无效的模型名称
3. **解决方案:** 在火山引擎方舟控制台创建推理接入点，获取正确的 Endpoint ID
4. **紧急程度:** 高 - 需要尽快配置正确的 Endpoint ID

---

**生成时间:** 2026-02-18  
**诊断工具:** `test_three_platforms.py`, `test_doubao_models.py`
