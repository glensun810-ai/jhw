# 生产环境配置指南

**版本：** 1.0  
**更新日期：** 2026 年 2 月 26 日

---

## 📋 配置步骤

### 步骤 1: 复制环境变量文件

```bash
cd /path/to/PythonProject
cp .env.example .env
```

### 步骤 2: 配置 AI 平台 API Key

编辑 `.env` 文件，填入真实的 API 密钥：

```bash
# 必填 - 根据实际使用的 AI 平台配置
DEEPSEEK_API_KEY="sk-your-deepseek-key"
QWEN_API_KEY="sk-your-qwen-key"
DOUBAO_API_KEY="your-doubao-key"
CHATGPT_API_KEY="sk-your-chatgpt-key"
```

### 步骤 3: 配置微信小程序

```bash
# 必填 - 微信小程序后台获取
WECHAT_APP_ID="wx1234567890abcdef"
WECHAT_APP_SECRET="your-app-secret"
WECHAT_TOKEN="your-token"
```

### 步骤 4: 配置告警通知（P2-021）

#### 4.1 钉钉机器人配置

1. 打开钉钉群聊
2. 点击右上角设置 → 智能群助手 → 添加机器人
3. 选择"自定义"机器人
4. 复制 Webhook 地址
5. 填入 `.env`：

```bash
ALERT_ENABLED=true
ALERT_DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=your-token"
```

#### 4.2 邮件告警配置

1. 配置 SMTP 服务器（以企业邮箱为例）：

```bash
ALERT_EMAIL_RECIPIENTS="admin@yourcompany.com,ops@yourcompany.com"
SMTP_SERVER="smtp.qiye.aliyun.com"
SMTP_PORT=587
SMTP_USER="noreply@yourcompany.com"
SMTP_PASSWORD="your-smtp-password"
SENDER_EMAIL="noreply@yourcompany.com"
```

2. 常用 SMTP 配置参考：

| 服务商 | SMTP Server | 端口 |
|--------|-------------|------|
| 阿里云企业邮箱 | smtp.qiye.aliyun.com | 587 |
| 腾讯企业邮箱 | smtp.exmail.qq.com | 587 |
| 网易企业邮箱 | smtp.qi.163.com | 587 |
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp.office365.com | 587 |

### 步骤 5: 配置监控（P2-020）

```bash
# 监控数据保留天数（默认 30 天）
METRICS_RETENTION_DAYS=30

# 告警阈值
PERSISTENCE_ERROR_THRESHOLD=10  # 连续失败 10 次触发告警
PERSISTENCE_ERROR_WINDOW=300    # 5 分钟时间窗口
```

### 步骤 6: 生产环境配置

```bash
# 生产环境使用 INFO 级别日志
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

---

## 🔒 安全注意事项

### 1. 保护 .env 文件

```bash
# 确保 .env 在 .gitignore 中
echo ".env" >> .gitignore

# 设置文件权限（仅所有者可读写）
chmod 600 .env
```

### 2. 密钥管理

- 定期轮换 API Key 和密钥
- 使用密钥管理服务（如阿里云 KMS）
- 不要在代码中硬编码密钥

### 3. 访问控制

- 限制监控 API 的访问 IP
- 为管理接口添加身份验证
- 使用 HTTPS 加密传输

---

## 🧪 验证配置

### 验证环境变量加载

```bash
cd backend_python
python -c "from config import Config; print('配置加载成功')"
```

### 验证告警通知

#### 测试钉钉告警

```bash
cd backend_python
python -c "
from wechat_backend.alert_system import send_dingtalk_alert, AlertSeverity
send_dingtalk_alert('测试告警', '这是一条测试告警消息', AlertSeverity.MEDIUM)
"
```

#### 测试邮件告警

```bash
cd backend_python
python -c "
from wechat_backend.alert_system import send_email_alert, AlertSeverity
send_email_alert('测试告警', '这是一条测试告警消息', AlertSeverity.MEDIUM)
"
```

### 验证监控 API

启动服务后访问：

```bash
# 获取今日监控数据
curl http://localhost:5001/api/monitoring/dashboard?period=today

# 获取最近诊断列表
curl http://localhost:5001/api/monitoring/recent?limit=10
```

---

## 📊 监控大盘访问

### API 端点

| 端点 | 说明 | 参数 |
|------|------|------|
| `/api/monitoring/dashboard` | 监控大盘数据 | `period=today\|week\|month` |
| `/api/monitoring/recent` | 最近诊断列表 | `limit=1-100` |

### 响应示例

```json
{
  "success": true,
  "data": {
    "period": "today",
    "total_diagnosis": 150,
    "successful_diagnosis": 142,
    "failed_diagnosis": 8,
    "success_rate": 94.67,
    "completion": {
      "avg_completion_rate": 92.5,
      "full_completion_count": 135,
      "partial_completion_count": 15,
      "full_completion_rate": 90.0
    },
    "performance": {
      "avg_duration_seconds": 45.2,
      "max_duration_seconds": 120.5,
      "p95_duration_seconds": 85.3
    },
    "quota": {
      "quota_exhausted_count": 5,
      "quota_exhausted_rate": 3.33,
      "exhausted_models": ["doubao-v2", "qwen-plus"]
    },
    "errors": {
      "error_distribution": {
        "quota_exhausted": 3,
        "timeout": 2
      },
      "total_errors": 5
    }
  }
}
```

---

## 🔧 故障排查

### 问题 1: 告警不发送

**检查清单：**
1. `ALERT_ENABLED=true` 是否设置
2. Webhook URL 是否正确
3. 网络连接是否正常
4. 查看日志：`tail -f logs/app.log | grep "P2-021"`

### 问题 2: 监控数据为空

**检查清单：**
1. 诊断执行是否正常记录指标
2. 查看日志：`tail -f logs/app.log | grep "P2-020"`
3. 检查 `diagnosis_monitor_service.py` 是否导入成功

### 问题 3: 邮件发送失败

**检查清单：**
1. SMTP 服务器地址和端口是否正确
2. 用户名密码是否正确
3. 是否需要开启 SMTP 授权码
4. 查看日志错误信息

---

## 📈 监控指标说明

### 核心指标

| 指标 | 说明 | 警戒线 |
|------|------|--------|
| 诊断报告产出率 | 成功返回结果的诊断数/总诊断数 | < 99% |
| 完全完成率 | 100% 完成的诊断数/总诊断数 | < 90% |
| 部分完成率 | 有部分结果的诊断数/总诊断数 | < 99% |
| 配额用尽发生率 | 配额用尽的诊断数/总诊断数 | > 20% |
| 平均诊断耗时 | 诊断平均执行时长 | > 120 秒 |
| P95 耗时 | 95% 诊断的耗时上限 | > 180 秒 |

### 告警级别

| 级别 | 触发条件 | 通知方式 |
|------|---------|---------|
| LOW | 单平台配额用尽 | 仅日志 |
| MEDIUM | 错误率>10% | 钉钉 |
| HIGH | 错误率>20% 或 数据库持续化失败 | 钉钉 + 邮件 |
| CRITICAL | 服务不可用 | 钉钉 + 邮件 + 电话 |

---

## 🚀 部署检查清单

部署前请确认：

- [ ] `.env` 文件已创建并配置所有必填项
- [ ] `.env` 文件权限设置为 600
- [ ] `.env` 已添加到 `.gitignore`
- [ ] 告警通知测试通过
- [ ] 监控 API 访问正常
- [ ] 日志目录权限正确
- [ ] 所有 AI 平台 API Key 有效
- [ ] 微信小程序配置正确
- [ ] 数据库连接正常
- [ ] 备份策略已配置

---

**文档维护：** 运维团队  
**最后更新：** 2026-02-26
