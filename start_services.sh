#!/bin/bash

# 服务启动脚本 for macOS ARM64
# 自动诊断环境并启动前后端服务

set -e  # 遇到错误时退出

echo "🚀 开始启动服务..."
echo "========================================"

# 检查工作目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "📋 工作目录: $PROJECT_DIR"

# 检查Python环境
echo "🔍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到python3，请先安装Python"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ Python版本: $PYTHON_VERSION"

# 检查架构
ARCH=$(uname -m)
echo "✅ 系统架构: $ARCH"

# 运行系统诊断
echo "🔧 运行系统诊断..."
python3 system_diagnostics_and_fix.py

# 启动后端服务
echo "🔧 启动后端服务..."
cd backend_python

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "✅ 激活虚拟环境..."
    source venv/bin/activate
else
    echo "⚠️  未找到虚拟环境，使用系统Python..."
fi

# 安装依赖
echo "📦 安装依赖包..."
pip3 install -r requirements.txt

# 启动后端服务
echo "🚀 启动Flask后端服务..."
echo "服务将在 http://127.0.0.1:5001 运行"
echo "按 Ctrl+C 停止服务"
echo "========================================"

python3 run.py

# 脚本结束
echo "🛑 服务已停止"