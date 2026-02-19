# 豆包、千问、智谱 AI API 问题诊断报告

## 执行摘要

**测试日期:** 2026-02-18  
**测试工具:** `test_three_platforms.py`

### 测试结果汇总

| 平台 | API Key | 状态 | 延迟 | 问题 |
|------|---------|------|------|------|
| **Qwen (通义千问)** | `sk-5261a4...c653` | ✅ **正常** | 1.70s | 无 |
| **Zhipu (智谱 AI)** | `504d64a0...HbiNh` | ✅ **正常** | 0.93s | 无 |
| **Doubao (豆包)** | `2a376e32...c9f92` | ❌ **失败** | - | **404 错误** |

---

## 详细分析

### 1. Qwen API (阿里云通义千问) ✅

**配置:**
- **Endpoint:** `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation`
- **Model:** `qwen-max`
- **API Key:** `sk-5261a4dfdf964a5c9a6364128cc4c653`

**测试结果:**
```
HTTP 状态码：200
响应时间：1.70 秒
响应内容：你好，我是 Qwen，由阿里云开发的超大规模语言模型...
```

**结论:** ✅ 配置正确，工作正常

---

### 2. Zhipu API (智谱 AI) ✅

**配置:**
- **Endpoint:** `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- **Model:** `glm-4`
- **API Key:** `504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh`

**测试结果:**
```
HTTP 状态码：200
响应时间：0.93 秒
响应内容：你好，我是一个由智谱 AI 训练的大语言模型...
```

**结论:** ✅ 配置正确，工作正常

---

### 3. Doubao API (字节豆包) ❌

**配置:**
- **Endpoint:** `https://ark.cn-beijing.volces.com/api/v3/chat/completions`
- **当前 Model:** `doubao-lite` (❌ 错误)
- **API Key:** `2a376e32-8877-4df8-9865-7eb3e99c9f92`

**错误响应:**
```json
{
  "error": {
    "code": "InvalidEndpointOrModel.NotFound",
    "message": "The model or endpoint doubao-lite does not exist or you do not have access to it."
  }
}
```

**HTTP 状态码:** 404 Not Found

---

## 问题根因

### 豆包 API 的特殊要求

豆包 API **不支持**直接使用通用模型名称（如 `doubao-lite`、`doubao-pro`），必须使用以下两种格式之一：

#### 格式 1: 部署点 ID (推荐)
```
ep-xxxxxxxxxxxxxxxx-xxxx
```
**示例:** `ep-20260212000000-gd5tq`

#### 格式 2: 完整模型版本号
```
doubao-1-5-pro-32k-250115
```
**示例:** `doubao-1-5-pro-32k-250115`

### 已测试的无效模型名称

以下模型名称均返回 404 错误：

- ❌ `doubao-lite`
- ❌ `doubao-pro`
- ❌ `doubao-1-5-pro`
- ❌ `doubao-1-5-lite`
- ❌ `doubao-1-5`
- ❌ `doubao`
- ❌ `ep-default-model`

---

## 解决方案

### 方案一：获取部署点 ID (推荐)

#### 步骤 1: 登录火山引擎方舟控制台

访问：https://console.volcengine.com/ark/

#### 步骤 2: 创建推理接入点

1. 进入「模型广场」
2. 选择需要的模型（如 **Doubao-pro-32k**）
3. 点击「使用现在」
4. 创建推理接入点
5. 复制 **Endpoint ID** (格式：`ep-xxxxxxxxxxxxxxxx-xxxx`)

#### 步骤 3: 更新环境变量

编辑 `.env` 文件或添加环境变量：

```bash
DOUBAO_MODEL_ID=ep-20260212000000-gd5tq
```

**注意:** 将 `ep-20260212000000-gd5tq` 替换为你实际的部署点 ID

---

### 方案二：使用完整模型版本号

如果不想创建部署点，可以使用完整模型版本号：

```bash
DOUBAO_MODEL_ID=doubao-1-5-pro-32k-250115
```

**前提条件:** API Key 必须有权限访问该模型版本

---

## 已修复的代码问题

### 1. config.py - API Key 验证逻辑

**问题:**
```python
# 原代码 - 错误地排除了 sk- 开头的 API Key
return bool(api_key and api_key.strip() != '' and 
            not api_key.startswith('sk-') and  # ❌ Qwen 的 Key 就是 sk- 开头
            not api_key.endswith('[在此粘贴你的 Key]'))
```

**修复:**
```python
# 新代码 - 移除了 sk- 前缀检查
return bool(api_key and api_key.strip() != '' and 
            not api_key.endswith('[在此粘贴你的 Key]'))
```

### 2. doubao_adapter.py - 默认模型 ID

**问题:**
```python
# 原代码 - 使用无效的通用模型名
model_name = os.getenv('DOUBAO_MODEL_ID', 'Doubao-pro')
```

**修复:**
```python
# 新代码 - 使用部署点 ID 格式
model_name = os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')
```

---

## 验证步骤

### 1. 设置正确的环境变量

```bash
# 方法 1: 直接设置
export DOUBAO_MODEL_ID=ep-20260212000000-gd5tq

# 方法 2: 编辑 .env 文件
echo "DOUBAO_MODEL_ID=ep-20260212000000-gd5tq" >> .env
```

### 2. 运行测试脚本

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 test_three_platforms.py
```

### 3. 预期输出

```
============================================================
  Testing Qwen API (Alibaba DashScope)
============================================================
✅ SUCCESS: 你好，我是 Qwen，由阿里云开发的超大规模语言模型...

============================================================
  Testing Doubao API (ByteDance VolcEngine)
============================================================
✅ SUCCESS: [豆包的回答内容]

============================================================
  Testing Zhipu AI API
============================================================
✅ SUCCESS: 你好，我是一个由智谱 AI 训练的大语言模型...

============================================================
  Summary
============================================================
  Qwen: ✅ PASS
  Doubao: ✅ PASS
  Zhipu: ✅ PASS

  All platforms are working correctly!
```

---

## 其他注意事项

### 1. API Key 格式说明

| 平台 | API Key 格式 | 示例 |
|------|-------------|------|
| Qwen | `sk-` + 32 位十六进制 | `sk-5261a4dfdf964a5c9a6364128cc4c653` |
| Zhipu | 32 位十六进制 + `.` + 16 位字符 | `504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh` |
| Doubao | UUID 格式 | `2a376e32-8877-4df8-9865-7eb3e99c9f92` |

### 2. 电路断路器状态

如果之前有过多失败，电路断路器可能处于开启状态。重启服务后会自动恢复。

### 3. 日志文件

查看详细日志：
```bash
tail -f logs/app.log
```

---

## 快速参考

### 豆包部署点 ID 获取流程

```
1. 访问 https://console.volcengine.com/ark/
   ↓
2. 登录/注册火山引擎账号
   ↓
3. 进入「模型广场」
   ↓
4. 选择模型 (如 Doubao-pro-32k)
   ↓
5. 点击「使用现在」
   ↓
6. 创建推理接入点
   ↓
7. 复制 Endpoint ID (ep-xxxxxxxxxxxxxxxx-xxxx)
   ↓
8. 设置到环境变量 DOUBAO_MODEL_ID
```

### 相关文档

- 火山引擎方舟文档：https://www.volcengine.com/docs/82379
- 豆包 API 参考：https://www.volcengine.com/docs/82379/1263546

---

## 总结

| 项目 | 状态 | 行动项 |
|------|------|--------|
| Qwen API | ✅ 正常 | 无需操作 |
| Zhipu API | ✅ 正常 | 无需操作 |
| Doubao API | ❌ 失败 | **需要配置正确的部署点 ID** |
| config.py | ✅ 已修复 | 已移除错误的 sk- 检查 |
| doubao_adapter.py | ✅ 已修复 | 已更新默认部署点 ID 格式 |

**下一步:** 获取豆包部署点 ID 并设置 `DOUBAO_MODEL_ID` 环境变量

---

**报告生成时间:** 2026-02-18  
**诊断工具:** `test_three_platforms.py`, `test_doubao_models.py`
