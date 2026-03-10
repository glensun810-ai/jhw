#!/bin/bash
# Step 2.2: v2 回滚脚本
# 用于在 v2 出现严重问题时快速回滚到 v1

set -e

echo "=========================================="
echo "🚨 品牌诊断系统 - v2 回滚脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FEATURE_FLAGS_FILE="$PROJECT_ROOT/backend_python/wechat_backend/v2/feature_flags.py"
BACKUP_DIR="$PROJECT_ROOT/backup/v2_rollback"
HEALTH_CHECK_URL="http://localhost:5000/api/health"
SERVICE_NAME="wechat_backend"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 步骤 1: 关闭特性开关
echo -e "${YELLOW}[1/5] 关闭 v2 特性开关...${NC}"
if [ -f "$FEATURE_FLAGS_FILE" ]; then
    # 备份原文件
    cp "$FEATURE_FLAGS_FILE" "$BACKUP_DIR/feature_flags.py.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 关闭总开关
    sed -i '' "s/'diagnosis_v2_enabled': True/'diagnosis_v2_enabled': False/g" "$FEATURE_FLAGS_FILE"
    
    # 设置灰度比例为 0
    sed -i '' "s/'diagnosis_v2_gray_percentage': [0-9]*/'diagnosis_v2_gray_percentage': 0/g" "$FEATURE_FLAGS_FILE"
    
    echo -e "${GREEN}✅ v2 特性开关已关闭${NC}"
else
    echo -e "${RED}❌ 特性开关文件不存在：$FEATURE_FLAGS_FILE${NC}"
    exit 1
fi

# 步骤 2: 停止服务
echo -e "${YELLOW}[2/5] 停止服务...${NC}"
if command -v systemctl &> /dev/null; then
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || echo "⚠️  systemctl 停止服务失败，尝试其他方式"
else
    # 尝试使用 pkill
    pkill -f "python.*wechat_backend" 2>/dev/null || echo "⚠️  未找到运行中的服务"
fi
echo -e "${GREEN}✅ 服务已停止${NC}"

# 步骤 3: 清理缓存
echo -e "${YELLOW}[3/5] 清理缓存...${NC}"
# 清理 Python 缓存
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true

# 清理 Redis 缓存（如果存在）
if command -v redis-cli &> /dev/null; then
    redis-cli KEYS "diagnosis_v2:*" | xargs redis-cli DEL 2>/dev/null || true
fi

echo -e "${GREEN}✅ 缓存已清理${NC}"

# 步骤 4: 启动服务
echo -e "${YELLOW}[4/5] 启动服务...${NC}"
if command -v systemctl &> /dev/null; then
    sudo systemctl start "$SERVICE_NAME"
    sleep 3
else
    # 开发环境启动
    cd "$PROJECT_ROOT/backend_python"
    nohup python -m wechat_backend > /tmp/wechat_backend.log 2>&1 &
    sleep 3
fi
echo -e "${GREEN}✅ 服务已启动${NC}"

# 步骤 5: 健康检查
echo -e "${YELLOW}[5/5] 健康检查...${NC}"
sleep 2

MAX_RETRIES=5
RETRY_COUNT=0
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" | grep -q "200"; then
        HEALTH_OK=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⚠️  健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✅ 健康检查通过${NC}"
else
    echo -e "${RED}❌ 健康检查失败，请手动检查服务状态${NC}"
    exit 1
fi

# 输出回滚总结
echo ""
echo "=========================================="
echo -e "${GREEN}✅ 回滚完成！${NC}"
echo "=========================================="
echo ""
echo "📋 回滚总结:"
echo "  - v2 总开关：已关闭"
echo "  - 灰度比例：0%"
echo "  - 服务状态：运行中"
echo "  - 备份位置：$BACKUP_DIR"
echo ""
echo "📝 后续步骤:"
echo "  1. 检查错误日志：tail -f /var/log/wechat_backend/error.log"
echo "  2. 监控用户反馈"
echo "  3. 分析 v2 问题原因"
echo ""
echo "🔄 如需重新启用 v2，请运行:"
echo "   $PROJECT_ROOT/scripts/gray_release.sh 10"
echo ""

# 记录回滚日志
ROLLBACK_LOG="$BACKUP_DIR/rollback_history.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - v2 回滚执行成功" >> "$ROLLBACK_LOG"

exit 0
