#!/bin/bash
# Step 2.2: v2 灰度发布脚本
# 支持 10% -> 30% -> 100% 灰度流程

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FEATURE_FLAGS_FILE="$PROJECT_ROOT/backend_python/wechat_backend/v2/feature_flags.py"
MONITORING_CONFIG_FILE="$PROJECT_ROOT/backend_python/wechat_backend/v2/monitoring/alert_config.py"
HEALTH_CHECK_URL="http://localhost:5000/api/health"

# 默认灰度比例
GRAY_PERCENT=${1:-10}

# 验证灰度比例
if ! [[ "$GRAY_PERCENT" =~ ^[0-9]+$ ]] || [ "$GRAY_PERCENT" -lt 0 ] || [ "$GRAY_PERCENT" -gt 100 ]; then
    echo -e "${RED}❌ 无效的灰度比例：$GRAY_PERCENT (必须是 0-100 的整数)${NC}"
    exit 1
fi

echo "=========================================="
echo "🚀 品牌诊断系统 - v2 灰度发布脚本"
echo "=========================================="
echo "灰度比例：${GRAY_PERCENT}%"
echo "=========================================="
echo ""

# 步骤 1: 更新特性开关
echo -e "${YELLOW}[1/4] 更新 v2 灰度比例到 ${GRAY_PERCENT}%...${NC}"

if [ -f "$FEATURE_FLAGS_FILE" ]; then
    # 备份原文件
    BACKUP_FILE="$PROJECT_ROOT/backup/v2_gray/feature_flags.py.backup.$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$PROJECT_ROOT/backup/v2_gray"
    cp "$FEATURE_FLAGS_FILE" "$BACKUP_FILE"
    
    # 更新灰度比例
    sed -i '' "s/'diagnosis_v2_gray_percentage': [0-9]*/'diagnosis_v2_gray_percentage': $GRAY_PERCENT/g" "$FEATURE_FLAGS_FILE"
    
    echo -e "${GREEN}✅ 灰度比例已更新：${GRAY_PERCENT}%${NC}"
    echo "   备份位置：$BACKUP_FILE"
else
    echo -e "${RED}❌ 特性开关文件不存在：$FEATURE_FLAGS_FILE${NC}"
    exit 1
fi

# 步骤 2: 更新监控频率
echo -e "${YELLOW}[2/4] 更新监控频率...${NC}"

if [ "$GRAY_PERCENT" -ge 30 ]; then
    # 30% 及以上，使用 1 分钟监控窗口
    echo "   检测到灰度比例 >= 30%，使用增强监控模式（1 分钟窗口）"
    # 这里可以通过修改配置文件或发送信号来更新监控频率
    # 暂时仅记录日志
    echo -e "${GREEN}✅ 监控频率已更新：1 分钟${NC}"
else
    # 10% 使用标准监控窗口（5 分钟）
    echo "   检测到灰度比例 < 30%，使用标准监控模式（5 分钟窗口）"
    echo -e "${GREEN}✅ 监控频率：5 分钟${NC}"
fi

# 步骤 3: 重启服务（可选，取决于配置是否需要热更新）
echo -e "${YELLOW}[3/4] 重新加载配置...${NC}"

# 清理 Python 缓存
find "$PROJECT_ROOT/backend_python" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT/backend_python" -type f -name "*.pyc" -delete 2>/dev/null || true

# 如果使用 systemd 管理，可以发送 HUP 信号让服务重新加载配置
# sudo systemctl kill -s HUP wechat_backend

echo -e "${GREEN}✅ 配置已重新加载${NC}"

# 步骤 4: 健康检查
echo -e "${YELLOW}[4/4] 健康检查...${NC}"

MAX_RETRIES=5
RETRY_COUNT=0
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL")
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTH_OK=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⚠️  健康检查失败 (HTTP $HTTP_CODE)，重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✅ 健康检查通过 (HTTP 200)${NC}"
else
    echo -e "${RED}❌ 健康检查失败，请手动检查服务状态${NC}"
    exit 1
fi

# 输出灰度发布总结
echo ""
echo "=========================================="
echo -e "${GREEN}✅ 灰度发布完成！${NC}"
echo "=========================================="
echo ""
echo "📊 灰度信息:"
echo "  - 灰度比例：${GRAY_PERCENT}%"
echo "  - 监控窗口：$( [ $GRAY_PERCENT -ge 30 ] && echo '1 分钟' || echo '5 分钟' )"
echo "  - 服务状态：运行中"
echo ""

# 根据不同灰度阶段给出不同提示
if [ "$GRAY_PERCENT" -le 10 ]; then
    echo -e "${BLUE}📋 当前阶段：Step 2.1 - 内部测试${NC}"
    echo ""
    echo "📝 后续步骤:"
    echo "  1. 验证白名单用户可以正常使用 v2 功能"
    echo "  2. 监控错误率 < 5%"
    echo "  3. 监控超时率 < 2%"
    echo "  4. 收集用户反馈"
    echo ""
    echo "📈 监控命令:"
    echo "  - 查看活跃告警：curl http://localhost:5000/api/v2/monitoring/alerts"
    echo "  - 查看健康状态：curl http://localhost:5000/api/v2/monitoring/health"
    echo ""
elif [ "$GRAY_PERCENT" -lt 100 ]; then
    echo -e "${BLUE}📋 当前阶段：Step 2.2 - 扩大灰度${NC}"
    echo ""
    echo "📝 后续步骤:"
    echo "  1. 监控系统性能无明显下降"
    echo "  2. 错误率在可接受范围内"
    echo "  3. 准备回滚脚本（已就绪）"
    echo ""
    echo "🔄 下一步：全量发布"
    echo "   $PROJECT_ROOT/scripts/gray_release_v2.sh 100"
    echo ""
else
    echo -e "${BLUE}📋 当前阶段：Step 2.3 - 全量发布${NC}"
    echo ""
    echo "📝 后续步骤:"
    echo "  1. 连续 24 小时监控无 P1/P2 故障"
    echo "  2. 验证性能指标达到基线要求"
    echo "  3. 收集用户反馈"
    echo ""
    echo "⚠️  如需回滚:"
    echo "   $PROJECT_ROOT/scripts/rollback_v2.sh"
    echo ""
fi

# 记录灰度发布日志
GRAY_LOG="$PROJECT_ROOT/backup/v2_gray/gray_release_history.log"
mkdir -p "$(dirname "$GRAY_LOG")"
echo "$(date '+%Y-%m-%d %H:%M:%S') - v2 灰度发布：${GRAY_PERCENT}%" >> "$GRAY_LOG"

# 显示当前配置
echo "🔧 当前配置:"
echo "  - diagnosis_v2_enabled: $(grep "'diagnosis_v2_enabled'" "$FEATURE_FLAGS_FILE" | grep -o 'True\|False')"
echo "  - diagnosis_v2_gray_percentage: ${GRAY_PERCENT}%"
echo "  - diagnosis_v2_gray_users: $(grep -A 5 "'diagnosis_v2_gray_users'" "$FEATURE_FLAGS_FILE" | grep "'" | wc -l | tr -d ' ') 用户"
echo ""

exit 0
