#!/bin/bash

echo "=== 开始同步远程代码并推送 ==="

# 1. 拉取远程最新代码，合并到本地
echo "1. 拉取远程 main 分支..."
git pull origin main

# 2. 检查是否有未提交的更改
if git status --porcelain | grep -q "^U"; then
  echo "⚠️  检测到合并冲突，请手动解决冲突后，再次运行此脚本。"
  exit 1
fi

# 3. 推送代码到远程
echo "2. 推送代码到远程 main 分支..."
git push origin main

if [ $? -eq 0 ]; then
  echo "✅ 推送成功！"
else
  echo "❌ 推送失败，请检查错误信息。"
fi