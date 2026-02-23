#!/bin/bash
# 生产环境部署脚本
# 使用方法：./deploy_production.sh

set -e

echo "============================================================"
echo "品牌诊断系统 - 生产环境部署脚本"
echo "============================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/Users/sgl/PycharmProjects/PythonProject"
BACKEND_ROOT="$PROJECT_ROOT/backend_python"
LOG_DIR="$BACKEND_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 步骤 1: 环境检查
echo "============================================================"
echo "步骤 1: 环境检查"
echo "============================================================"

log_info "检查 Python 版本..."
python3 --version || { log_error "Python3 未安装"; exit 1; }

log_info "检查 Node.js 版本..."
node --version || { log_warn "Node.js 未安装（可选）"; }

log_info "检查 Git 状态..."
cd "$PROJECT_ROOT"
git status --short || { log_warn "Git 仓库不可用"; }

echo ""

# 步骤 2: 备份现有环境
echo "============================================================"
echo "步骤 2: 备份现有环境"
echo "============================================================"

log_info "备份数据库..."
if [ -f "$BACKEND_ROOT/database.db" ]; then
    cp "$BACKEND_ROOT/database.db" "$BACKEND_ROOT/database.db.backup.$TIMESTAMP"
    log_info "数据库已备份：database.db.backup.$TIMESTAMP"
else
    log_warn "数据库文件不存在"
fi

log_info "备份日志文件..."
if [ -d "$LOG_DIR" ]; then
    tar -czf "$LOG_DIR/logs.backup.$TIMESTAMP.tar.gz" -C "$LOG_DIR" . 2>/dev/null || log_warn "日志备份失败"
fi

echo ""

# 步骤 3: 更新代码
echo "============================================================"
echo "步骤 3: 更新代码"
echo "============================================================"

log_info "检查代码更新..."
cd "$PROJECT_ROOT"
git fetch origin || log_warn "无法连接远程仓库"

# 如果有更新，询问是否拉取
if ! git diff --quiet HEAD origin/main 2>/dev/null; then
    log_warn "检测到代码更新"
    read -p "是否拉取最新代码？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git pull origin main
        log_info "代码已更新"
    fi
else
    log_info "代码已是最新"
fi

echo ""

# 步骤 4: 安装依赖
echo "============================================================"
echo "步骤 4: 安装依赖"
echo "============================================================"

log_info "检查 Python 依赖..."
cd "$BACKEND_ROOT"

# 检查 requirements.txt
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    log_info "Python 依赖已安装"
else
    log_warn "requirements.txt 不存在"
fi

echo ""

# 步骤 5: 配置环境变量
echo "============================================================"
echo "步骤 5: 配置环境变量"
echo "============================================================"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_warn ".env 文件不存在，从示例文件复制..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    log_info "请编辑 .env 文件配置以下变量:"
    echo "  - ARK_API_KEY"
    echo "  - DEEPSEEK_API_KEY"
    echo "  - QWEN_API_KEY"
    echo "  - DATA_ENCRYPTION_KEY"
    echo ""
    read -p "配置完成后按回车继续..."
fi

# 检查关键环境变量
if ! grep -q "ARK_API_KEY=" "$PROJECT_ROOT/.env" || \
   ! grep -q "DATA_ENCRYPTION_KEY=" "$PROJECT_ROOT/.env"; then
    log_warn "关键环境变量可能未配置，请检查 .env 文件"
fi

echo ""

# 步骤 6: 启动服务
echo "============================================================"
echo "步骤 6: 启动服务"
echo "============================================================"

log_info "停止旧服务..."
pkill -f "python.*run.py" || log_warn "未找到运行中的服务"

sleep 2

log_info "启动新服务..."
cd "$BACKEND_ROOT"
nohup python3 run.py > "$LOG_DIR/flask.$TIMESTAMP.log" 2>&1 &
FLASK_PID=$!

sleep 5

# 验证服务启动
if ps -p $FLASK_PID > /dev/null; then
    log_info "服务已启动 (PID: $FLASK_PID)"
else
    log_error "服务启动失败，请查看日志：$LOG_DIR/flask.$TIMESTAMP.log"
    exit 1
fi

echo ""

# 步骤 7: 健康检查
echo "============================================================"
echo "步骤 7: 健康检查"
echo "============================================================"

log_info "检查 API 端点..."

# 等待服务完全启动
sleep 3

# 健康检查
if curl -s http://127.0.0.1:5000/api/test | grep -q "success"; then
    log_info "✅ /api/test 端点正常"
else
    log_error "❌ /api/test 端点异常"
    exit 1
fi

if curl -s http://127.0.0.1:5000/health | grep -q "healthy"; then
    log_info "✅ /health 端点正常"
else
    log_error "❌ /health 端点异常"
    exit 1
fi

echo ""

# 步骤 8: 运行验证
echo "============================================================"
echo "步骤 8: 运行验证脚本"
echo "============================================================"

log_info "运行综合验证..."
cd "$PROJECT_ROOT"
python3 final_verification.py

echo ""

# 步骤 9: 配置定时任务
echo "============================================================"
echo "步骤 9: 配置定时任务"
echo "============================================================"

log_info "配置数据清理定时任务..."

# 检查是否已配置
if crontab -l 2>/dev/null | grep -q "data_retention"; then
    log_info "定时任务已配置"
else
    log_warn "定时任务未配置，请手动添加:"
    echo "  0 3 * * * cd $BACKEND_ROOT && python3 -c \"from wechat_backend.database.data_retention import cleanup_expired_data; cleanup_expired_data()\""
fi

echo ""

# 部署完成
echo "============================================================"
echo "部署完成！"
echo "============================================================"
echo ""
log_info "服务 PID: $FLASK_PID"
log_info "日志文件：$LOG_DIR/flask.$TIMESTAMP.log"
log_info "备份文件：$BACKEND_ROOT/database.db.backup.$TIMESTAMP"
echo ""
log_info "后续操作:"
echo "  1. 查看实时日志：tail -f $LOG_DIR/flask.$TIMESTAMP.log"
echo "  2. 停止服务：pkill -f 'python.*run.py'"
echo "  3. 重启服务：cd $BACKEND_ROOT && nohup python3 run.py > /tmp/flask.log 2>&1 &"
echo ""
log_info "部署成功！✅"
