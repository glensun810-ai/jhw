#!/bin/bash
"""
停止后端服务脚本
用于停止微信小程序后端服务
"""

# 设置项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT=5001

# 查找并终止服务进程
PID=$(lsof -ti:$PORT)
if [ ! -z "$PID" ]; then
    echo "🛑 停止端口 $PORT 上的服务进程: $PID"
    kill -TERM $PID
    
    # 等待进程终止
    sleep 2
    
    # 检查进程是否仍然存在
    if kill -0 $PID 2>/dev/null; then
        echo "⚠️  进程未正常终止，强制杀死: $PID"
        kill -9 $PID
    fi
    
    echo "✅ 服务已停止"
else
    echo "ℹ️  端口 $PORT 上没有运行的服务"
fi

# 清理可能的僵尸进程
pkill -f "main.py" 2>/dev/null || true
pkill -f "python.*5001" 2>/dev/null || true

echo "✅ 清理完成"