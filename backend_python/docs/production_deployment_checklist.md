# 生产环境部署清单

## 部署前检查

### 1. 代码审查
- [x] 所有敏感信息已从代码库中移除
- [x] 加密配置管理模块已实现
- [x] 安全网络通信已配置
- [x] 弹性功能（断路器、重试）已实现
- [x] 监控和日志系统已部署
- [x] 速率限制器已配置

### 2. 测试验证
- [x] 单元测试全部通过
- [x] 集成测试全部通过
- [x] 安全扫描无敏感信息泄露
- [x] 性能基准测试完成

### 3. 依赖项检查
- [x] `cryptography` 库已添加到 requirements.txt
- [x] `certifi` 库已添加以支持证书验证
- [x] 所有依赖版本兼容性验证

## 部署步骤

### 步骤 1: 环境准备
```bash
# 1. 克隆代码仓库
git clone <repository-url>
cd <project-directory>

# 2. 创建虚拟环境
python -m venv production-env
source production-env/bin/activate  # Linux/Mac
# 或
production-env\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

### 步骤 2: 安全配置
```bash
# 1. 配置安全的API密钥管理
# 使用环境变量或安全的密钥管理系统
export DEEPSEEK_API_KEY=<your-secure-key>
export QWEN_API_KEY=<your-secure-key>
export CHATGPT_API_KEY=<your-secure-key>
# ... 其他API密钥

# 2. 设置加密密钥
export SECURE_CONFIG_PASSWORD=<strong-encryption-password>
```

### 步骤 3: 启动应用
```bash
# 1. 运行应用
python main.py

# 2. 或使用生产级WSGI服务器
gunicorn --bind 0.0.0.0:5000 app:app
```

## 生产环境配置

### 1. 环境变量设置
```
# API密钥（使用安全的密钥管理系统）
DEEPSEEK_API_KEY=your_encrypted_key
QWEN_API_KEY=your_encrypted_key
CHATGPT_API_KEY=your_encrypted_key
GEMINI_API_KEY=your_encrypted_key
ZHIPU_API_KEY=your_encrypted_key
DOUBAO_API_KEY=your_encrypted_key

# 安全配置
SECURE_CONFIG_PASSWORD=your_strong_encryption_password
FLASK_ENV=production
FLASK_DEBUG=False

# 微信配置
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_TOKEN=your_token

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/app.log
```

### 2. 监控配置
```
# 告警阈值
API_ERROR_RATE_THRESHOLD=0.05  # 5%错误率触发告警
RESPONSE_TIME_THRESHOLD=5.0    # 响应时间超过5秒触发告警
RATE_LIMIT_THRESHOLD=100       # 每分钟超过100次请求触发告警
```

## 运维操作指南

### 1. 日常监控
- 监控API调用成功率
- 检查断路器状态
- 观察错误率和响应时间
- 检查安全事件日志

### 2. 告警处理
- 高错误率：检查上游API服务状态
- 高响应时间：检查网络连接和服务负载
- 安全事件：立即调查并采取相应措施
- 断路器打开：等待恢复或手动重置

### 3. 安全维护
- 定期轮换API密钥（建议每月一次）
- 定期更新依赖库
- 审查访问日志
- 检查权限配置

## 回滚计划

如果部署出现问题，执行以下回滚步骤：

1. 停止当前应用
```bash
# 如果使用gunicorn
pkill gunicorn

# 或停止其他进程
```

2. 恢复到上一个稳定版本
```bash
git fetch
git checkout <stable-branch-or-tag>
```

3. 重启应用
```bash
python main.py
```

## 验证步骤

部署完成后，执行以下验证：

1. **功能测试**
   - API调用是否正常
   - 所有AI平台连接是否正常
   - 响应时间是否在可接受范围内

2. **安全测试**
   - 敏感信息是否未泄露
   - HTTPS连接是否正常
   - 认证授权是否正常

3. **性能测试**
   - 并发请求处理能力
   - 断路器是否正常工作
   - 速率限制是否生效

## 注意事项

1. **安全第一**
   - 绝不在代码中硬编码API密钥
   - 使用安全的密钥管理系统
   - 定期轮换所有密钥

2. **监控不可少**
   - 设置适当的告警阈值
   - 定期审查日志
   - 监控系统性能指标

3. **备份策略**
   - 定期备份配置
   - 保留部署前的快照
   - 确保回滚计划可行

## 联系信息

如遇问题，请联系：
- 开发团队: [联系方式]
- 运维团队: [联系方式]
- 安全团队: [联系方式]