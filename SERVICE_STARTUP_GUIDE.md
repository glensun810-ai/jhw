# 微信小程序后端服务启动指南

## 服务状态

✅ **当前状态**: 服务正在运行
✅ **访问地址**: http://127.0.0.1:5001
✅ **进程ID**: （动态）

## 启动服务

要启动后端服务，请运行以下命令：

```bash
cd /Users/sgl/PycharmProjects/PythonProject
./start_server.sh
```

## 服务管理脚本

### 1. 启动服务
```bash
./start_server.sh
```

### 2. 检查服务状态
```bash
./status_server.sh
```

### 3. 停止服务
```bash
./stop_server.sh
```

## 服务特性

### 安全功能
- ✅ API密钥安全存储和管理
- ✅ 输入验证和净化
- ✅ SSL证书验证
- ✅ 速率限制和防滥用保护
- ✅ 断路器和容错机制

### 性能功能
- ✅ 连接池管理
- ✅ 智能重试机制
- ✅ 响应时间优化
- ✅ 资源高效利用

### 监控功能
- ✅ API性能指标收集
- ✅ 错误率监控
- ✅ 安全事件记录
- ✅ 结构化日志记录

## 微信小程序配置

在微信小程序前端中，配置后端服务地址：

```javascript
// app.js 或相应的配置文件
const BACKEND_BASE_URL = 'http://127.0.0.1:5001';

// 示例API调用
wx.request({
  url: `${BACKEND_BASE_URL}/api/perform-brand-test`,
  method: 'POST',
  data: {
    // 你的请求数据
  },
  success: (res) => {
    console.log('请求成功', res.data);
  },
  fail: (err) => {
    console.error('请求失败', err);
  }
});
```

## 常见问题

### 1. 端口被占用
如果遇到端口被占用问题，运行：
```bash
./stop_server.sh
./start_server.sh
```

### 2. 服务无法启动
检查日志文件 `app.log` 了解详细错误信息：
```bash
tail -f app.log
```

### 3. 微信小程序连接失败
- 确认后端服务正在运行：`./status_server.sh`
- 检查防火墙设置
- 确认端口5000未被阻止

## 开发说明

### 项目结构
```
wechat_backend/          # 后端主目录
├── app.py              # Flask应用入口
├── views.py            # API路由
├── security/           # 安全模块
├── network/            # 网络通信模块
├── monitoring/         # 监控模块
├── ai_adapters/        # AI平台适配器
└── ...
```

### 安全改进
1. **API密钥管理**: 使用加密存储和环境变量
2. **输入验证**: 全面的输入验证和净化
3. **网络通信**: 安全的HTTP请求和SSL验证
4. **错误处理**: 适当的错误处理和日志记录
5. **监控告警**: 完整的监控和告警系统

## 部署到生产环境

在生产环境中部署时，请注意：

1. 使用生产级Web服务器（如Gunicorn + Nginx）
2. 配置HTTPS证书
3. 使用安全的密钥管理系统
4. 设置适当的监控和告警
5. 配置日志轮转

## 技术栈

- **后端框架**: Flask
- **数据库**: SQLite
- **安全库**: PyJWT, cryptography, bleach
- **监控**: 自定义指标收集和告警系统
- **网络**: requests, urllib3

## 支持

如果遇到问题，请检查：
1. 服务是否正在运行：`./status_server.sh`
2. 日志文件：`app.log`
3. 端口是否可用：`lsof -i :5000`

---
*微信小程序后端服务已准备就绪，可为前端提供安全、可靠的API服务。*