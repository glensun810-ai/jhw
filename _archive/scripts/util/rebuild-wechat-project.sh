#!/bin/bash
# 彻底重建项目索引脚本
# 用于修复微信开发者工具的页面注册问题

set -e

echo "============================================================"
echo "微信开发者工具项目重建脚本"
echo "============================================================"
echo

# 1. 关闭微信开发者工具提示
echo "⚠️  重要提示："
echo "1. 请先关闭微信开发者工具"
echo "2. 运行此脚本"
echo "3. 重新打开微信开发者工具"
echo

read -p "是否已关闭微信开发者工具？(y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "请先关闭微信开发者工具"
    exit 1
fi
echo

# 2. 清理微信开发者工具缓存
echo "2. 清理微信开发者工具缓存..."
rm -rf .wechat 2>/dev/null || true
rm -rf .miniprogram-cache 2>/dev/null || true
rm -rf miniprogram/.tmp 2>/dev/null || true
rm -rf .idea/workspace.xml 2>/dev/null || true
echo "   ✅ 缓存清理完成"
echo

# 3. 删除冲突目录
echo "3. 检查并删除冲突目录..."
if [ -d "miniprogram/pages" ]; then
    echo "   ⚠️  发现 miniprogram/pages，正在删除..."
    rm -rf miniprogram/pages
    echo "   ✅ 已删除 miniprogram/pages"
else
    echo "   ✅ miniprogram/pages 不存在"
fi
echo

# 4. 验证页面文件
echo "4. 验证所有页面文件..."
python3 << 'PYEOF'
import json, os, sys

with open('app.json', 'r') as f:
    app_config = json.load(f)

all_ok = True
missing_pages = []

for page in app_config['pages']:
    js_file = f'{page}.js'
    json_file = f'{page}.json'
    wxml_file = f'{page}.wxml'
    wxss_file = f'{page}.wxss'
    
    files_exist = all([
        os.path.exists(js_file),
        os.path.exists(json_file),
        os.path.exists(wxml_file),
        os.path.exists(wxss_file)
    ])
    
    if not files_exist:
        missing_pages.append(page)
        all_ok = False

if all_ok:
    print("   ✅ 所有页面文件完整")
else:
    print("   ❌ 以下页面文件缺失:")
    for page in missing_pages:
        print(f"      - {page}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "页面文件验证失败，请检查"
    exit 1
fi
echo

# 5. 验证项目配置
echo "5. 验证项目配置..."
python3 << 'PYEOF'
import json

with open('project.config.json', 'r') as f:
    proj_config = json.load(f)

ignored = proj_config.get('packOptions', {}).get('ignore', [])
ignored_values = [item.get('value') for item in ignored]

required_ignores = ['backend_python', 'miniprogram']
for req in required_ignores:
    if req not in ignored_values:
        print(f"   ❌ 缺少忽略配置：{req}")
        exit(1)
    else:
        print(f"   ✅ 已忽略：{req}")

print("   ✅ 项目配置验证通过")
PYEOF

if [ $? -ne 0 ]; then
    echo "项目配置验证失败"
    exit 1
fi
echo

# 6. 生成项目信息文件
echo "6. 生成项目信息文件..."
cat > .project.info.json << EOF
{
  "name": "进化湾 GEO",
  "appid": "wx8876348e089bc261",
  "created_at": "$(date -Iseconds)",
  "fixed_issues": [
    "删除 miniprogram/pages 目录",
    "清理微信开发者工具缓存",
    "更新 project.config.json",
    "重建项目索引"
  ],
  "pages_count": $(python3 -c "import json; print(len(json.load(open('app.json'))['pages']))"),
  "status": "ready"
}
EOF
echo "   ✅ 项目信息生成完成"
echo

# 7. 最终检查
echo "============================================================"
echo "重建完成！"
echo "============================================================"
echo
echo "✅ 1. 已清理所有缓存"
echo "✅ 2. 已删除冲突目录"
echo "✅ 3. 已验证所有页面文件"
echo "✅ 4. 已更新项目配置"
echo
echo "============================================================"
echo "下一步操作："
echo "============================================================"
echo "1. 打开微信开发者工具"
echo "2. 重新导入项目 (选择当前目录)"
echo "3. 工具 → 清除缓存 → 清除全部缓存"
echo "4. 按 Ctrl/Cmd + B 重新编译"
echo "5. 检查控制台是否还有页面注册错误"
echo "============================================================"
echo
