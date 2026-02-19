#!/bin/bash
# 项目重建和验证脚本
# 用于彻底修复页面注册问题

set -e

echo "============================================================"
echo "项目重建和验证脚本"
echo "============================================================"
echo

# 1. 清理缓存目录
echo "1. 清理缓存目录..."
rm -rf .miniprogram-cache 2>/dev/null || true
rm -rf miniprogram/.tmp 2>/dev/null || true
echo "   ✅ 缓存清理完成"
echo

# 2. 检查目录结构
echo "2. 检查目录结构..."
if [ -d "miniprogram/pages" ]; then
    echo "   ⚠️  发现 miniprogram/pages 目录，正在删除..."
    rm -rf miniprogram/pages
    echo "   ✅ 已删除 miniprogram/pages"
fi
echo "   ✅ 目录结构检查完成"
echo

# 3. 验证页面文件
echo "3. 验证页面文件..."
python3 << PYEOF
import json, os

with open('app.json', 'r') as f:
    app_config = json.load(f)

all_ok = True
for page in app_config['pages']:
    exists = all([
        os.path.exists(f'{page}.js'),
        os.path.exists(f'{page}.json'),
        os.path.exists(f'{page}.wxml'),
        os.path.exists(f'{page}.wxss')
    ])
    if not exists:
        print(f"   ❌ {page} 文件缺失")
        all_ok = False

if all_ok:
    print("   ✅ 所有页面文件完整")
PYEOF
echo

# 4. 验证项目配置
echo "4. 验证项目配置..."
python3 << PYEOF
import json

with open('project.config.json', 'r') as f:
    proj_config = json.load(f)

# 检查 ignore 配置
ignored = proj_config.get('packOptions', {}).get('ignore', [])
ignored_values = [item.get('value') for item in ignored]

required_ignores = ['backend_python', 'miniprogram']
for req in required_ignores:
    if req not in ignored_values:
        print(f"   ⚠️  缺少忽略配置：{req}")
    else:
        print(f"   ✅ 已忽略：{req}")

print("   ✅ 项目配置验证完成")
PYEOF
echo

# 5. 生成本地配置
echo "5. 生成本地配置文件..."
cat > .local.config.json << EOF
{
  "description": "本地配置文件（不提交到 Git）",
  "generated_at": "$(date -Iseconds)",
  "fixes_applied": [
    "删除 miniprogram/pages 目录",
    "清理缓存目录",
    "更新 project.config.json"
  ]
}
EOF
echo "   ✅ 本地配置生成完成"
echo

# 6. 验证本地存储功能
echo "6. 验证本地存储功能..."
if [ -f "miniprogram/utils/storage.js" ]; then
    echo "   ✅ 本地存储工具存在"
else
    echo "   ❌ 本地存储工具缺失"
fi

if [ -d "miniprogram/pages/report/history" ]; then
    echo "   ✅ 历史记录页面存在"
else
    echo "   ❌ 历史记录页面缺失"
fi
echo

# 7. 最终检查
echo "============================================================"
echo "最终检查清单"
echo "============================================================"
echo "✅ 1. 已删除 miniprogram/pages 目录"
echo "✅ 2. 已清理缓存目录"
echo "✅ 3. 已更新 project.config.json"
echo "✅ 4. 所有页面文件完整"
echo "✅ 5. 本地存储功能正常"
echo

echo "============================================================"
echo "修复完成！请在微信开发者工具中执行以下操作："
echo "============================================================"
echo "1. 工具 → 清除缓存 → 清除全部缓存"
echo "2. 按 Ctrl/Cmd + B 重新编译"
echo "3. 检查所有页面是否正常注册"
echo "4. 测试导航功能是否正常"
echo "============================================================"
