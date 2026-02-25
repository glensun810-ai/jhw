#!/bin/bash
# 清理微信开发者工具缓存

echo "============================================================"
echo "清理微信开发者工具缓存"
echo "============================================================"

# 微信开发者工具缓存目录
WECHAT_CACHE_DIR="$HOME/Library/Application Support/微信开发者工具/Cache"
WECHAT_USER_DATA="$HOME/Library/Application Support/微信开发者工具/User Data"
WECHAT_TEMP="$HOME/Library/Caches/微信开发者工具"

echo ""
echo "正在清理缓存..."

# 清理 Cache
if [ -d "$WECHAT_CACHE_DIR" ]; then
    rm -rf "$WECHAT_CACHE_DIR"/*
    echo "✅ 已清理 Cache 目录"
else
    echo "ℹ️  Cache 目录不存在"
fi

# 清理 User Data
if [ -d "$WECHAT_USER_DATA" ]; then
    rm -rf "$WECHAT_USER_DATA"/Default/Cache/*
    echo "✅ 已清理 User Data Cache"
else
    echo "ℹ️  User Data 目录不存在"
fi

# 清理 Temp
if [ -d "$WECHAT_TEMP" ]; then
    rm -rf "$WECHAT_TEMP"/*
    echo "✅ 已清理 Temp 目录"
else
    echo "ℹ️  Temp 目录不存在"
fi

# 清理项目临时文件
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "正在清理项目临时文件..."

# 清理 .wechat 目录
if [ -d "$PROJECT_ROOT/.wechat" ]; then
    rm -rf "$PROJECT_ROOT/.wechat"
    echo "✅ 已清理 .wechat 目录"
fi

# 清理 miniprogram_simulator
if [ -d "$PROJECT_ROOT/.miniprogram_simulator" ]; then
    rm -rf "$PROJECT_ROOT/.miniprogram_simulator"
    echo "✅ 已清理 .miniprogram_simulator 目录"
fi

echo ""
echo "============================================================"
echo "缓存清理完成！"
echo "============================================================"
echo ""
echo "请重启微信开发者工具，然后："
echo "1. 点击 '工具' → '清除缓存' → '清除全部缓存'"
echo "2. 点击 '编译' 重新编译项目"
echo ""
