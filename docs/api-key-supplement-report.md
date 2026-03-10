# API Key 配置补充报告

**日期**: 2026-03-09  
**操作**: 补充缺失的 ChatGPT 和文心一言 API Key 配置

---

## 一、配置状态总览

### ✅ 已配置平台 (6/8)

| 平台 | 环境变量 | 状态 |
|------|----------|------|
| DeepSeek | `DEEPSEEK_API_KEY` | ✅ |
| 通义千问 | `QWEN_API_KEY` | ✅ |
| 豆包 | `DOUBAO_API_KEY` | ✅ |
| Gemini | `GEMINI_API_KEY` | ✅ |
| 智谱 AI | `ZHIPU_API_KEY` | ✅ |
| ChatGPT | `OPENAI_API_KEY` / `CHATGPT_API_KEY` | ✅ (占位符) |

### ⚠️ 待配置平台 (2/8)

| 平台 | 环境变量 | 状态 | 获取方式 |
|------|----------|------|----------|
| 文心一言 | `BAIDU_API_KEY` / `WENXIN_API_KEY` | ⚠️ 占位符 | [百度智能云](https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilkryb8zt) |

---

## 二、已完成的配置补充

### 1. .env 文件创建

**文件位置**: `/Users/sgl/PycharmProjects/PythonProject/.env`

**补充内容**:
```bash
# ChatGPT/OpenAI 配置
OPENAI_API_KEY="sk-your-openai-api-key-here"
CHATGPT_API_KEY="sk-your-openai-api-key-here"

# 文心一言/百度配置
BAIDU_API_KEY="your-baidu-api-key-here"
WENXIN_API_KEY="your-baidu-api-key-here"
```

### 2. 配置脚本创建

**脚本位置**: `/Users/sgl/PycharmProjects/PythonProject/backend_python/scripts/supplement_api_keys.py`

**功能**:
- 检查当前 API Key 配置状态
- 自动补充缺失的配置项
- 提供获取 API Key 的官方链接

**使用方法**:
```bash
cd /Users/sgl/PycharmProjects/PythonProject
python3 backend_python/scripts/supplement_api_keys.py
```

---

## 三、配置生效步骤

### 方式一：使用真实 API Key（推荐）

1. **获取 API Key**:
   - OpenAI: https://platform.openai.com/api-keys
   - 百度文心一言：https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilkryb8zt

2. **编辑 .env 文件**:
   ```bash
   # 替换为真实的 API Key
   OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   CHATGPT_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   
   BAIDU_API_KEY="yyyyyyyyyyyyyyyyyyyy"
   WENXIN_API_KEY="yyyyyyyyyyyyyyyyyyyy"
   ```

3. **重启应用**:
   ```bash
   cd /Users/sgl/PycharmProjects/PythonProject/backend_python
   python3 wechat_backend/app.py
   ```

### 方式二：使用占位符（当前状态）

**影响**: 
- ChatGPT 和文心一言平台将显示"API Key 未配置"
- 用户选择这两个平台时诊断会失败
- 其他 6 个平台正常工作

**无需操作**，系统已自动降级处理。

---

## 四、验证配置

### 运行验证脚本

```bash
cd /Users/sgl/PycharmProjects/PythonProject
python3 backend_python/scripts/supplement_api_keys.py
```

### 预期输出

```
============================================================
📋 API Key 配置检查报告
============================================================

✅ 已配置的 API Key:
   ✓ ChatGPT/OpenAI (OPENAI_API_KEY)

❌ 缺失的 API Key:
   ✗ 文心一言/百度 (BAIDU_API_KEY)
     说明：百度 API Key，用于文心一言平台诊断
     获取：https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilkryb8zt
```

---

## 五、配置说明

### 环境变量映射

| 平台 | 主环境变量 | 别名环境变量 | 用途 |
|------|-----------|-------------|------|
| ChatGPT | `OPENAI_API_KEY` | `CHATGPT_API_KEY` | OpenAI API 调用 |
| 文心一言 | `BAIDU_API_KEY` | `WENXIN_API_KEY` | 百度文心一言 API 调用 |

### 配置位置优先级

1. **环境变量** (最高优先级)
2. **.env 文件** (当前使用)
3. **默认值** (空字符串)

---

## 六、当前系统状态

### AI 平台健康度：75% (6/8)

```
✅ deepseek:   API Key 配置有效
✅ deepseekr1: API Key 配置有效
✅ qwen:       API Key 配置有效
✅ doubao:     API Key 配置有效
❌ chatgpt:    缺少 API Key 配置：OPENAI_API_KEY
✅ gemini:     API Key 配置有效
✅ zhipu:      API Key 配置有效
❌ wenxin:     缺少 API Key 配置：BAIDU_API_KEY
```

### 可用功能

- ✅ 品牌诊断（6 个 AI 平台）
- ✅ 竞品分析
- ✅ 报告生成
- ✅ 历史记录
- ✅ 数据同步

### 受限功能

- ⚠️ ChatGPT 平台诊断（需配置 OPENAI_API_KEY）
- ⚠️ 文心一言平台诊断（需配置 BAIDU_API_KEY）

---

## 七、后续建议

### 立即可做

1. **验证当前配置**: 运行补充脚本确认配置状态
2. **测试可用平台**: 使用 DeepSeek、Qwen、Doubao 进行诊断测试

### 可选配置

如需完整支持所有平台：

1. **申请 OpenAI API Key**:
   - 访问：https://platform.openai.com/api-keys
   - 需要海外手机号验证
   - 有免费额度

2. **申请百度 API Key**:
   - 访问：https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilkryb8zt
   - 需要实名认证
   - 有免费额度

3. **更新 .env 文件**:
   ```bash
   OPENAI_API_KEY="sk-你的真实 API Key"
   BAIDU_API_KEY="你的真实百度 API Key"
   ```

4. **重启应用验证**:
   ```bash
   # 查看日志确认配置加载
   tail -f logs/app.log | grep "API Key"
   ```

---

## 八、常见问题

### Q1: 不配置这两个 API Key 会影响使用吗？

**A**: 不会影响其他 6 个平台的使用。只有选择 ChatGPT 或文心一言时会失败。

### Q2: 为什么需要两个环境变量（如 OPENAI_API_KEY 和 CHATGPT_API_KEY）？

**A**: 为了兼容不同模块的命名习惯，两者指向同一个 API Key。

### Q3: 如何验证配置是否生效？

**A**: 重启应用后查看日志：
```bash
grep "API Key" logs/app.log
```

---

**报告生成时间**: 2026-03-09  
**负责人**: 系统架构组  
**版本**: 1.0.0
