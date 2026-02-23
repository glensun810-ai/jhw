#!/bin/bash
# 项目清理脚本
# 用途：清理临时文件、编译文件、备份文件等

set -e

echo "========================================"
echo "项目清理脚本"
echo "========================================"
echo ""

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 项目根目录：$PWD"
echo ""

# 1. 清理临时文件
echo "🗑️  清理临时文件..."
find . -type f \( -name "*.bak" -o -name "*.bak2" -o -name "*.old" -o -name "*.fixed" -o -name "*.temp" -o -name "*.tmp" \) \
  -not -path "./.git/*" \
  -not -path "./backup/*" \
  -delete 2>/dev/null || true
echo "✅ 临时文件清理完成"
echo ""

# 2. 清理编译文件
echo "🗑️  清理编译文件..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" -not -path "./.git/*" | wc -l)
PYC_COUNT=$(find . -type f -name "*.pyc" -not -path "./.git/*" | wc -l)

find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true

echo "✅ 已清理 $PYCACHE_COUNT 个 __pycache__ 目录和 $PYC_COUNT 个 .pyc 文件"
echo ""

# 3. 清理 IDE 文件
echo "🗑️  清理 IDE 文件..."
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
find . -type f -name "*.swp" -delete 2>/dev/null || true
echo "✅ IDE 文件清理完成"
echo ""

# 4. 清理日志文件（保留最近 7 天）
echo "🗑️  清理旧日志文件..."
if [ -d "logs" ]; then
  find logs -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
  echo "✅ 已清理 7 天前的日志文件"
fi
echo ""

# 5. 统计清理结果
echo "========================================"
echo "清理完成统计"
echo "========================================"
REMAINING_BAK=$(find . -type f \( -name "*.bak" -o -name "*.bak2" -o -name "*.old" -o -name "*.fixed" \) -not -path "./.git/*" -not -path "./backup/*" | wc -l)
REMAINING_PYCACHE=$(find . -type d -name "__pycache__" -not -path "./.git/*" | wc -l)
REMAINING_PYC=$(find . -type f -name "*.pyc" -not -path "./.git/*" | wc -l)

echo "剩余备份文件：$REMAINING_BAK"
echo "剩余 __pycache__: $REMAINING_PYCACHE"
echo "剩余 .pyc 文件：$REMAINING_PYC"
echo ""

if [ $REMAINING_BAK -eq 0 ] && [ $REMAINING_PYCACHE -eq 0 ] && [ $REMAINING_PYC -eq 0 ]; then
  echo "✅ 清理成功！"
else
  echo "⚠️  仍有部分文件未清理，请手动检查"
fi
echo ""

echo "========================================"
echo "清理脚本执行完成"
echo "========================================"
