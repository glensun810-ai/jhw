# 修复品牌诊断任务启动失败问题

## 问题概述

您遇到的"启动任务失败，创建任务失败"错误并不是由用户权限限制导致的，而是由API密钥配置缺失引起的。后端服务在接收请求时会验证所选AI模型是否已正确配置API密钥，如果未配置，会返回400错误。

## 详细分析

通过代码分析，发现问题出现在以下几个地方：

### 1. 后端验证逻辑（views.py:289-300）
```python
# 检查平台是否可用（已注册且API密钥已配置）
if not AIAdapterFactory.is_platform_available(normalized_model_name):
    # 打印出当前所有已注册的 Keys 并在报错中返回给前端
    registered_keys = [pt.value for pt in AIAdapterFactory._adapters.keys()]
    api_logger.error(f"Model {model_name} (normalized to {normalized_model_name}) not registered or not configured. Available models: {registered_keys}")
    return jsonify({
        "status": "error",
        "error": f'Model {model_name} not registered or not configured in AIAdapterFactory',
        "code": 400,
        "available_models": registered_keys,
        "received_model": model_name,
        "normalized_to": normalized_model_name
    }), 400
```

### 2. 配置管理器验证（config.py:79-103）
```python
@classmethod
def is_api_key_configured(cls, platform: str) -> bool:
    # 检查API密钥是否存在且非空
    api_key = cls.get_api_key(normalized_platform)
    return bool(api_key and api_key.strip() != '' and not api_key.startswith('sk-') and not api_key.endswith('[在此粘贴你的Key]'))
```

## 修复步骤

### 步骤1: 检查并配置环境变量

1. 检查项目根目录是否有 `.env` 文件
2. 如果没有，请创建 `.env` 文件并添加所需API密钥：

```bash
DEEPSEEK_API_KEY="your-actual-deepseek-api-key"
DOUBAO_API_KEY="your-actual-doubao-api-key"
QWEN_API_KEY="your-actual-qwen-api-key"
# 根据需要配置其他平台
```

### 步骤2: 确保后端服务重启

修改环境变量后，必须重启后端服务：
```bash
cd backend_python
# 如果有运行中的进程，先终止它
pkill -f "python run.py"  # 或者 Ctrl+C 停止当前运行的服务
# 重新启动服务
python run.py
```

### 步骤3: 验证修复

1. 确认后端服务已启动并在端口5000上运行
2. 检查前端是否能正常连接到后端
3. 尝试启动品牌诊断任务

## 权限相关说明

系统确实有权限控制机制，但目前的错误并非由权限问题引起。认证机制主要用于：

1. 用户识别和跟踪
2. 请求频率限制
3. 操作审计

即使在未认证的情况下，系统也会允许请求通过（使用 `require_auth_optional` 装饰器），但会以 "anonymous" 用户身份记录。

## 临时解决方案

如果您暂时无法获取API密钥，可以考虑以下临时方案：

1. 修改后端代码，移除API密钥检查（不推荐，仅用于测试）
2. 使用模拟数据模式进行测试

## 总结

这不是权限问题，而是API密钥配置问题。只要配置好相应的API密钥并重启后端服务，问题就能解决。这是正常的商业AI平台使用流程，需要有效的API密钥才能调用相应服务。