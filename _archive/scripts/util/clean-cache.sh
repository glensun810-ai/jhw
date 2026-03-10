#!/bin/bash
# 微信开发者工具缓存清理脚本
# 严格按照第四步执行

set -e

echo "============================================================"
echo "微信开发者工具缓存清理脚本"
echo "============================================================"
echo ""

# 颜色定义
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠️  重要提示：${NC}"
echo "1. 请先完全关闭微信开发者工具（包括后台进程）"
echo "2. 运行此脚本"
echo "3. 重新打开微信开发者工具"
echo ""

read -p "是否已关闭微信开发者工具？(y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo -e "${RED}请先关闭微信开发者工具${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}开始清理缓存...${NC}"
echo ""

# 1. 清理项目根目录的缓存
echo "1. 清理项目缓存目录..."
rm -rf .wechat 2>/dev/null || true
rm -rf .miniprogram-cache 2>/dev/null || true
rm -rf logs/wechat 2>/dev/null || true
rm -rf .idea/workspace.xml 2>/dev/null || true
echo -e "   ${GREEN}✅ 项目缓存清理完成${NC}"

# 2. 清理 Python 缓存
echo "2. 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "   ${GREEN}✅ Python 缓存清理完成${NC}"

# 3. 清理备份文件
echo "3. 清理备份文件 (.bak)..."
BAK_COUNT=$(find pages -name "*.bak" -type f 2>/dev/null | wc -l)
if [ "$BAK_COUNT" -gt 0 ]; then
    find pages -name "*.bak" -type f -delete
    echo -e "   ${GREEN}✅ 已删除 $BAK_COUNT 个备份文件${NC}"
else
    echo -e "   ${GREEN}✅ 无需清理备份文件${NC}"
fi

# 4. 验证修复
echo ""
echo "4. 验证修复..."
echo ""

# 运行页面检查
python3 check-pages.py

echo ""
echo "============================================================"
echo -e "${GREEN}缓存清理完成！${NC}"
echo "============================================================"
echo ""
echo -e "${YELLOW}下一步操作 (必须手动执行):${NC}"
echo ""
echo "1. 打开微信开发者工具"
echo ""
echo "2. 重新导入项目 (关键步骤!)"
echo "   - 文件 → 导入项目"
echo "   - 选择目录：/Users/sgl/PycharmProjects/PythonProject"
echo "   - 不要直接打开现有项目!"
echo ""
echo "3. 清除缓存"
echo "   - 控制台 → 清除缓存 → 全部清除"
echo "   - 或按快捷键 Shift + Cmd + Delete"
echo ""
echo "4. 重新编译"
echo "   - 按 Ctrl/Cmd + B"
echo ""
echo "5. 验证修复"
echo "   - 检查控制台是否还有错误"
echo "   - 检查日志中 ID 是否显示为 unknown"
echo "   - 测试所有导航按钮"
echo ""
echo "============================================================"
