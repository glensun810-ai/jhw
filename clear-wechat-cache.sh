#!/bin/bash
# 清除微信小程序缓存脚本
# 用于解决 "webviewId is not found" 等缓存相关错误

echo "🧹 正在清除微信小程序缓存..."

# 微信开发者工具缓存目录
CACHE_DIR="$HOME/Library/Application Support/微信开发者工具"
WECHAT_CACHE_DIR="$HOME/Library/Caches/微信开发者工具"

# 清除缓存
if [ -d "$CACHE_DIR" ]; then
    echo "📁 清除开发者工具缓存：$CACHE_DIR"
    rm -rf "$CACHE_DIR"/Default/Cache/*
    rm -rf "$CACHE_DIR"/Default/Code\ Cache/*
    rm -rf "$CACHE_DIR"/Default/Session\ Storage/*
    rm -rf "$CACHE_DIR"/Default/Local\ Storage/*
fi

if [ -d "$WECHAT_CACHE_DIR" ]; then
    echo "📁 清除系统缓存：$WECHAT_CACHE_DIR"
    rm -rf "$WECHAT_CACHE_DIR"/*
fi

# 清除项目临时文件
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📁 清除项目临时文件：$PROJECT_DIR"
rm -rf "$PROJECT_DIR"/.wechat-dev-cache
rm -rf "$PROJECT_DIR"/miniprogram_dist

echo "✅ 缓存清除完成！"
echo ""
echo "📌 请按以下步骤操作："
echo "1. 关闭微信开发者工具"
echo "2. 重新打开微信开发者工具"
echo "3. 点击「清除缓存」→ 「清除全部缓存」"
echo "4. 重新编译项目"
