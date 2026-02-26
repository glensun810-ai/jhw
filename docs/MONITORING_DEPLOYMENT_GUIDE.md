# 监控大盘部署指南

**版本：** 1.0  
**更新日期：** 2026 年 2 月 26 日

---

## 📋 部署步骤

### 步骤 1: 配置环境变量

编辑 `.env` 文件，配置告警和监控相关环境变量：

```bash
# 告警配置
ALERT_ENABLED=true
ALERT_DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=xxx"
ALERT_EMAIL_RECIPIENTS="admin@example.com"
SMTP_SERVER="smtp.example.com"
SMTP_PORT=587
SMTP_USER="user@example.com"
SMTP_PASSWORD="password"
SENDER_EMAIL="noreply@example.com"

# 监控配置
CHECK_INTERVAL=300  # 检查间隔（秒）
SUCCESS_RATE_MIN=95.0  # 最低成功率
COMPLETION_RATE_MIN=90.0  # 最低完成率
QUOTA_EXHAUSTED_MAX=20.0  # 最高配额用尽率
AVG_DURATION_MAX=120.0  # 最大平均耗时（秒）
ERROR_RATE_MAX=10.0  # 最高错误率
ALERT_COOLDOWN=1800  # 告警冷却时间（秒）
```

### 步骤 2: 访问监控大盘

启动 Flask 服务后，访问监控大盘：

```
http://localhost:5001/admin/monitoring
```

**功能：**
- 核心指标卡片（诊断总数、成功率、完成率、耗时等）
- 诊断趋势图（按小时分布）
- 完成率分布饼图
- 耗时分布柱状图
- 错误类型分布饼图
- 最近诊断记录表格

**自动刷新：** 每 30 秒自动刷新数据

### 步骤 3: 部署持续监控脚本

#### 方法 A: 直接运行

```bash
cd /path/to/PythonProject
python3 monitoring_daemon.py
```

#### 方法 B: 后台运行（推荐）

```bash
cd /path/to/PythonProject
nohup python3 monitoring_daemon.py > logs/monitoring.log 2>&1 &

# 查看进程
ps aux | grep monitoring_daemon

# 查看日志
tail -f logs/monitoring.log
```

#### 方法 C: 作为 systemd 服务运行（生产环境推荐）

1. 编辑服务文件：

```bash
sudo vim /etc/systemd/system/diagnosis-monitoring.service
```

修改配置：
- `WorkingDirectory` - 项目路径
- `EnvironmentFile` - .env 文件路径
- `ExecStart` - Python 路径和脚本路径
- `StandardOutput/StandardError` - 日志路径

2. 启用并启动服务：

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable diagnosis-monitoring

# 启动服务
sudo systemctl start diagnosis-monitoring

# 查看状态
sudo systemctl status diagnosis-monitoring

# 查看日志
sudo journalctl -u diagnosis-monitoring -f
```

3. 管理命令：

```bash
# 停止服务
sudo systemctl stop diagnosis-monitoring

# 重启服务
sudo systemctl restart diagnosis-monitoring

# 禁用服务
sudo systemctl disable diagnosis-monitoring
```

### 步骤 4: 验证监控

#### 验证 API

```bash
# 获取今日监控数据
curl http://localhost:5001/api/monitoring/dashboard?period=today

# 获取最近诊断列表
curl http://localhost:5001/api/monitoring/recent?limit=10
```

#### 验证告警

手动触发测试告警：

```bash
cd backend_python
python -c "
from wechat_backend.alert_system import send_dingtalk_alert, AlertSeverity
send_dingtalk_alert('测试告警', '这是一条测试消息', AlertSeverity.MEDIUM)
"
```

#### 验证监控脚本

```bash
# 手动运行一次检查
python3 monitoring_daemon.py

# 查看日志
tail -f logs/monitoring.log
```

---

## 📊 监控指标说明

### 核心指标

| 指标 | 说明 | 警戒线 | 告警级别 |
|------|------|--------|---------|
| 诊断成功率 | 成功返回结果的诊断数/总诊断数 | < 95% | HIGH |
| 平均完成率 | 所有诊断的平均完成率 | < 90% | MEDIUM |
| 完全完成率 | 100% 完成的诊断数/总诊断数 | - | - |
| 配额用尽率 | 配额用尽的诊断数/总诊断数 | > 20% | MEDIUM |
| 平均耗时 | 诊断平均执行时长 | > 120 秒 | MEDIUM |
| P95 耗时 | 95% 诊断的耗时上限 | - | - |
| 错误率 | 错误诊断数/总诊断数 | > 10% | HIGH |

### 告警级别

| 级别 | 触发条件 | 通知方式 |
|------|---------|---------|
| LOW | 日报 | 钉钉 |
| MEDIUM | 单指标超阈值 | 钉钉 |
| HIGH | 关键指标超阈值 | 钉钉 + 邮件 |
| CRITICAL | 服务不可用 | 钉钉 + 邮件 + 电话 |

---

## 🔧 配置调优

### 调整告警阈值

编辑 `.env` 文件：

```bash
# 更严格的成功率要求
SUCCESS_RATE_MIN=99.0

# 更短的超时时间
AVG_DURATION_MAX=60.0

# 更灵敏的告警
ALERT_COOLDOWN=900  # 15 分钟冷却
```

### 调整检查频率

```bash
# 更频繁的检查（生产环境建议 300 秒）
CHECK_INTERVAL=60  # 1 分钟检查一次

# 降低频率（节省资源）
CHECK_INTERVAL=600  # 10 分钟检查一次
```

### 自定义告警接收人

```bash
# 多个邮箱接收者（逗号分隔）
ALERT_EMAIL_RECIPIENTS="admin@example.com,ops@example.com,dev@example.com"
```

---

## 📈 监控报告

### 日报

每天凌晨 0:00-0:10 自动发送日报，包含：
- 核心指标汇总
- 错误类型分布
- 配额用尽模型列表

### 实时告警

当指标超过阈值时立即发送告警，包含：
- 告警名称和严重程度
- 当前值和阈值
- 详细指标数据
- 建议操作

---

## 🐛 故障排查

### 问题 1: 监控大盘无法访问

**检查：**
1. Flask 服务是否运行
2. 路由是否正确配置
3. 防火墙是否开放端口

```bash
# 检查服务
ps aux | grep flask

# 检查端口
netstat -tlnp | grep 5001

# 测试 API
curl http://localhost:5001/api/monitoring/dashboard
```

### 问题 2: 监控脚本不运行

**检查：**
1. Python 路径是否正确
2. 依赖是否安装
3. 日志文件权限

```bash
# 检查 Python
which python3

# 安装依赖
pip install requests

# 检查日志权限
ls -la logs/
chmod 644 logs/monitoring.log
```

### 问题 3: 告警不发送

**检查：**
1. 环境变量是否配置
2. 网络连接是否正常
3. 冷却时间是否已过

```bash
# 检查环境变量
cat .env | grep ALERT

# 测试网络
curl https://oapi.dingtalk.com/robot/send

# 清除告警状态
rm /tmp/diagnosis_monitor_state.json
```

---

## 📝 最佳实践

### 1. 监控告警分级

- **开发环境**: 仅 LOW 和 MEDIUM 级别告警
- **测试环境**: MEDIUM 和 HIGH 级别告警
- **生产环境**: 所有级别告警

### 2. 告警冷却设置

- **核心指标**（成功率）：冷却 15 分钟
- **次要指标**（耗时）：冷却 30 分钟
- **日报**：每天一次

### 3. 日志轮转

配置 logrotate 防止日志过大：

```bash
sudo vim /etc/logrotate.d/diagnosis-monitoring
```

内容：
```
/path/to/PythonProject/logs/monitoring.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
}
```

### 4. 监控自检

添加监控脚本的健康检查：

```bash
# crontab -e
*/5 * * * * pgrep -f monitoring_daemon.py || (cd /path/to/PythonProject && python3 monitoring_daemon.py &)
```

---

## 📞 支持

**文档维护：** 运维团队  
**问题反馈：** 提交 Issue 或联系技术支持  
**最后更新：** 2026-02-26
