# 后端服务启动指南

## 问题诊断

如果您在前端看到类似以下错误：
```
GET http://127.0.0.1:5001/api/test net::ERR_CONNECTION_REFUSED
```

这意味着前端无法连接到后端服务。这通常是因为后端服务没有启动。

## 启动步骤

### 1. 环境准备

在启动后端服务之前，请确保：

1. **安装Python 3.9+**
2. **安装依赖包**：
   ```bash
   cd backend_python
   pip install -r requirements.txt
   ```

3. **配置API密钥**：
   - 复制 `.env.example` 文件为 `.env`
   - 填入相应的API密钥

### 2. 启动后端服务

有两种方式启动后端服务：

#### 方式一：直接运行（推荐用于开发）

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 run.py
```

或

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 main.py
```

#### 方式二：使用启动脚本

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
chmod +x start_server.sh
./start_server.sh
```

### 3. 验证服务启动

服务启动后，您应该看到类似输出：
```
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
 * Running on http://127.0.0.1:5001
```

验证服务是否正常运行：
```bash
curl http://127.0.0.1:5001/
```

预期响应：
```json
{
  "message": "WeChat Mini Program Backend Server",
  "status": "running",
  "app_id": "your-app-id"
}
```

## 常见问题解决

### 1. 端口被占用

如果看到 "Address already in use" 或 "Port 5000 is in use by another program" 错误：

```bash
# 查找占用端口5000的进程
lsof -ti:5000

# 终止占用端口5000的进程
kill -9 $(lsof -ti:5000)
```

### 2. macOS AirPlay冲突

如果在macOS上看到关于AirPlay Receiver的提示，请在系统设置中禁用AirPlay接收器，或使用不同端口启动服务。

### 2. API密钥缺失

如果看到认证错误，请确保 `.env` 文件中有相应的API密钥。

### 3. 模块导入错误

如果遇到 `ModuleNotFoundError`，请确保在 `backend_python` 目录下运行服务。

## 与前端集成

一旦后端服务成功启动，前端应该能够：

1. 连接到 `http://127.0.0.1:5001`
2. 执行品牌诊断测试
3. 正确轮询任务状态

## 服务配置

- **默认端口**：5000
- **主机地址**：127.0.0.1 (localhost)
- **API基础路径**：/
- **健康检查端点**：`/health`

## 故障排除

如果仍有连接问题，请检查：

1. 防火墙设置
2. 端口5000是否被其他程序占用
3. 后端服务是否正常启动（查看控制台输出）
4. 前端配置的端口是否与后端一致（都应为5000）