#!/bin/bash
"""
检查服务状态脚本
用于检查微信小程序后端服务状态
"""

# 设置项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT=5002

echo "🔍 检查微信小程序后端服务状态..."

# 检查端口是否被占用
PID=$(lsof -ti:$PORT)
if [ ! -z "$PID" ]; then
    echo "✅ 服务正在运行"
    echo "   进程ID: $PID"
    echo "   监听端口: $PORT"
    
    # 检查进程详情
    PROCESS_INFO=$(ps -p $PID -o pid,ppid,cmd,etime,pcpu,pmem 2>/dev/null)
    if [ ! -z "$PROCESS_INFO" ]; then
        echo "   进程详情:"
        echo "$PROCESS_INFO"
    fi
    
    # 尝试访问服务
    if curl -s --connect-timeout 5 http://127.0.0.1:$PORT/ > /dev/null 2>&1; then
        echo "✅ 服务响应正常"
        echo "   访问地址: http://127.0.0.1:$PORT"
    else
        echo "❌ 服务进程运行但无法访问"
    fi
else
    echo "❌ 服务未运行"
    echo "   端口 $PORT 未被占用"
    echo "   请运行 start_server.sh 启动服务"
fi

# 显示日志文件信息
if [ -f "app.log" ]; then
    LOG_SIZE=$(du -h app.log | cut -f1)
    LATEST_LOG=$(tail -n 5 app.log 2>/dev/null)
    echo ""
    echo "📄 最近的日志 (app.log, 大小: $LOG_SIZE):"
    echo "$LATEST_LOG"
else
    echo ""
    echo "📄 日志文件 app.log 不存在"
fi