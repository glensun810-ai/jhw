#!/bin/bash
"""
后台启动后端服务脚本
用于启动微信小程序后端服务
"""

# 设置项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 检查Python解释器
PYTHON_PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Python解释器未找到: $PYTHON_PATH"
    # 尝试使用系统Python
    PYTHON_PATH=$(which python3)
    if [ -z "$PYTHON_PATH" ]; then
        echo "❌ 未找到Python 3解释器"
        exit 1
    fi
fi

# 检查端口是否被占用并终止占用进程
PORT=5002
PID=$(lsof -ti:$PORT)
if [ ! -z "$PID" ]; then
    echo "⚠️  端口 $PORT 被占用，终止进程: $PID"
    kill -9 $PID
fi

# 启动后端服务
echo "🚀 启动微信小程序后端服务..."
echo "   Python路径: $PYTHON_PATH"
echo "   项目路径: $PROJECT_DIR"
echo "   监听端口: $PORT"

# 启动服务并将其放到后台
nohup $PYTHON_PATH main.py > app.log 2>&1 &

# 获取后台进程ID
SERVER_PID=$!

if [ $? -eq 0 ]; then
    echo "✅ 服务已启动，进程ID: $SERVER_PID"
    echo "✅ 服务监听地址: http://127.0.0.1:$PORT"
    echo "✅ 日志文件: $PROJECT_DIR/app.log"
    
    # 等待几秒钟让服务启动
    sleep 3
    
    # 验证服务是否正常运行
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo "✅ 服务进程正在运行"
        
        # 尝试访问服务
        if curl -s --connect-timeout 5 http://127.0.0.1:$PORT/ > /dev/null 2>&1; then
            echo "✅ 服务响应正常"
            echo "🎉 微信小程序后端服务启动成功！"
            echo "   前端可访问地址: http://127.0.0.1:$PORT"
        else
            echo "⚠️  服务进程运行但无法访问，请检查日志文件 app.log"
        fi
    else
        echo "❌ 服务未能正常启动，请检查日志文件 app.log"
        exit 1
    fi
else
    echo "❌ 服务启动失败"
    exit 1
fi