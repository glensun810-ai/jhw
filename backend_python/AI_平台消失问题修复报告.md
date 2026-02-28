# AI 平台消失问题修复报告

**日期**: 2026-02-28  
**问题级别**: P0  
**修复状态**: ✅ 已完成

## 问题描述

重启后，国内和海外 AI 平台（ChatGPT、Gemini、智谱 AI 等）在系统中"消失"，无法使用。

### 错误日志
```
2026-02-28 09:48:32 - wechat_backend - WARNING - app.py:46 - ⚠️  数据库读写分离启动失败：
No module named 'config.config_database'; 'config' is not a package
```

## 根本原因分析

### 1. 直接原因
`provider_factory.py` 只注册了 3 个国内平台 provider：
- ✅ doubao（豆包）
- ✅ deepseek（DeepSeek）
- ✅ qwen（通义千问）
- ❌ **缺少海外平台**：chatgpt, gemini, zhipu, wenxin

### 2. 架构问题
系统存在两层 AI 集成架构：
- **Adapter 层** (`wechat_backend.ai_adapters.factory`): 注册了 8 个平台 ✅
- **Provider 层** (`wechat_backend.ai_adapters.provider_factory`): 只注册了 3 个平台 ❌

Provider 层负责实际的 API 调用，缺失导致平台"消失"。

### 3. 配置问题
- `config.py` 文件与 `config/` 目录命名冲突，导致导入失败
- 海外平台 provider 实现缺失

## 修复方案

### 1. 修复配置导入冲突
**文件**: `backend_python/config.py` → `backend_python/legacy_config.py`

重命名 `config.py` 为 `legacy_config.py`，解决与 `config/` 包的命名冲突。

**影响文件**:
- `wechat_backend/app.py`
- `wechat_backend/views/*.py`
- `wechat_backend/nxm_*.py`
- `src/adapters/*.py`

### 2. 创建海外平台 Provider 实现
**新文件**: `wechat_backend/ai_adapters/overseas_providers.py`

实现以下海外平台 provider：
- `ChatGPTProvider` (OpenAI)
- `GeminiProvider` (Google)
- `ZhipuProvider` (智谱 AI)
- `WenxinProvider` (百度文心一言)

### 3. 修复 Provider 注册
**文件**: `wechat_backend/ai_adapters/provider_factory.py`

修改前：
```python
ProviderFactory.register('doubao', DoubaoProvider)
ProviderFactory.register('deepseek', DeepSeekProvider)
ProviderFactory.register('qwen', QwenProvider)
```

修改后：
```python
# 国内平台
cls._register_with_key_check('doubao', DoubaoProvider, '豆包/Doubao')
cls._register_with_key_check('deepseek', DeepSeekProvider, 'DeepSeek')
cls._register_with_key_check('qwen', QwenProvider, '通义千问/Qwen')

# 海外平台
cls._register_with_key_check('chatgpt', ChatGPTProvider, 'ChatGPT/OpenAI')
cls._register_with_key_check('gemini', GeminiProvider, 'Gemini/Google')
cls._register_with_key_check('zhipu', ZhipuProvider, '智谱 AI/Zhipu')
cls._register_with_key_check('wenxin', WenxinProvider, '文心一言/Wenxin')
```

### 4. 添加健康检查机制
**新文件**: `wechat_backend/ai_adapters/platform_health_monitor.py`

功能：
- 启动时自动检查所有平台注册状态
- 检测 adapter 和 provider 是否匹配
- 检查 API key 配置状态
- 生成详细诊断报告

**集成到**: `wechat_backend/app.py`

```python
# AI Platform Health Check - 防止平台消失问题复发
from wechat_backend.ai_adapters.platform_health_monitor import run_startup_health_check

health_results = run_startup_health_check()
if health_results['status'] == 'unhealthy':
    app_logger.error("⚠️  AI Platform health check FAILED!")
```

### 5. 创建验证脚本
**新文件**: `scripts/verify_ai_platforms.py`

使用方法：
```bash
cd backend_python
python scripts/verify_ai_platforms.py
```

## 修复验证

### 启动日志
```
✅ Provider registered for 'doubao' (豆包/Doubao)
✅ Provider registered for 'deepseek' (DeepSeek)
✅ Provider registered for 'qwen' (通义千问/Qwen)
✅ Provider registered for 'chatgpt' (ChatGPT/OpenAI)
✅ Provider registered for 'gemini' (Gemini/Google)
✅ Provider registered for 'zhipu' (智谱 AI/Zhipu)
⚠️  Provider NOT registered for 'wenxin' (文心一言/Wenxin): API key not configured

=== Provider Registration Complete ===
Registered: 6/7 providers
Registered providers: ['chatgpt', 'deepseek', 'doubao', 'gemini', 'qwen', 'zhipu']
```

### 健康检查结果
```
✅ doubao: OK
✅ deepseek: OK
✅ qwen: OK
✅ chatgpt: OK
✅ gemini: OK
✅ zhipu: OK
⚠️  wenxin: Provider not registered (adapter OK)

Status: degraded
Healthy: 6/7
Degraded: 1/7
Unhealthy: 0/7
```

## 防复发机制

### 1. 启动时健康检查
每次应用启动自动运行健康检查，发现问题立即告警。

### 2. 详细日志记录
记录每个平台的注册状态和失败原因。

### 3. 验证脚本
提供独立的验证脚本，可随时检查平台状态。

### 4. 配置验证
检查 API key 配置，未配置时明确提示。

## 文件清单

### 新增文件
- `wechat_backend/ai_adapters/overseas_providers.py` - 海外平台 provider 实现
- `wechat_backend/ai_adapters/platform_health_monitor.py` - 健康监控器
- `scripts/verify_ai_platforms.py` - 验证脚本

### 修改文件
- `backend_python/config.py` → `backend_python/legacy_config.py` (重命名)
- `wechat_backend/app.py` - 添加健康检查
- `wechat_backend/ai_adapters/provider_factory.py` - 修复注册逻辑
- `src/adapters/provider_factory.py` - 同步修复
- 14 个导入 `config` 的文件 - 更新为 `legacy_config`

## 后续建议

### 1. 配置 wenxin API key
如需使用文心一言，在 `.env` 文件中添加：
```env
WENXIN_API_KEY=your_api_key_here
```

### 2. 定期检查
运行验证脚本检查平台状态：
```bash
python backend_python/scripts/verify_ai_platforms.py
```

### 3. 监控告警
关注启动日志中的健康检查结果：
- `✅` 表示平台正常
- `⚠️` 表示降级运行（如缺少 API key）
- `❌` 表示平台不可用

## 总结

本次修复通过以下步骤彻底解决了 AI 平台消失问题：

1. **修复配置冲突** - 重命名 config.py
2. **补全 provider 实现** - 添加海外平台支持
3. **完善注册逻辑** - 自动检查 API key 后注册
4. **添加健康检查** - 启动时自动诊断
5. **创建验证工具** - 便于日常检查

现在系统支持 7 个 AI 平台（6 个已配置），并在启动时自动验证所有平台的健康状态，有效防止问题复发。
