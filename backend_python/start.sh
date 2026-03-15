#!/bin/bash
# 启动后端服务脚本（Flask + WebSocket）

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PYTHON_PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"

echo "============================================================"
echo "微信小程序后端服务"
echo "============================================================"

# 停止旧进程
echo "🛑 停止旧服务..."
pkill -f "python.*app.py" 2>/dev/null
pkill -f "python.*websocket_server.py" 2>/dev/null
sleep 1

# 启动 Flask 服务
echo "🚀 启动 Flask 服务..."
nohup $PYTHON_PATH app.py > app.log 2>&1 &
FLASK_PID=$!
echo "   Flask PID: $FLASK_PID"

# 启动 WebSocket 服务
echo "🚀 启动 WebSocket 服务..."
nohup $PYTHON_PATH websocket_server.py > websocket.log 2>&1 &
WS_PID=$!
echo "   WebSocket PID: $WS_PID"

# 等待启动
sleep 5

# 检查服务状态
echo ""
echo "============================================================"
echo "服务状态检查"
echo "============================================================"

# 检查 Flask
if kill -0 $FLASK_PID 2>/dev/null; then
    if lsof -i :5000 | grep -q LISTEN; then
        echo "✅ Flask 服务：运行正常 (端口 5000)"
    else
        echo "⚠️  Flask 服务：运行但端口 5000 未监听"
    fi
else
    echo "❌ Flask 服务：未运行"
fi

# 检查 WebSocket
if kill -0 $WS_PID 2>/dev/null; then
    if lsof -i :8765 | grep -q LISTEN; then
        echo "✅ WebSocket 服务：运行正常 (端口 8765)"
    else
        echo "⚠️  WebSocket 服务：运行但端口 8765 未监听"
    fi
else
    echo "❌ WebSocket 服务：未运行"
fi

echo ""
echo "============================================================"
echo "服务地址"
echo "============================================================"
echo "Flask API:      http://127.0.0.1:5000"
echo "WebSocket:      ws://127.0.0.1:8765"
echo ""
echo "日志文件:"
echo "Flask:          $PROJECT_DIR/app.log"
echo "WebSocket:      $PROJECT_DIR/websocket.log"
echo "============================================================"
