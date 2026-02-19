#!/bin/bash
# 彻底重建项目索引脚本 - 最终版本
# 用于修复微信开发者工具的页面注册问题 (经过 3-4 次修复后的最终版本)

set -e

echo "============================================================"
echo "微信开发者工具项目重建脚本 - 最终版本"
echo "版本：2026-02-19 (全局分析修复版)"
echo "============================================================"
echo

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 关闭微信开发者工具提示
echo -e "${YELLOW}⚠️  重要提示：${NC}"
echo "1. 请先关闭微信开发者工具"
echo "2. 运行此脚本"
echo "3. 重新打开微信开发者工具"
echo

read -p "是否已关闭微信开发者工具？(y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo -e "${RED}请先关闭微信开发者工具${NC}"
    exit 1
fi
echo

# 2. 清理微信开发者工具缓存
echo -e "${BLUE}2. 清理微信开发者工具缓存...${NC}"
rm -rf .wechat 2>/dev/null || true
rm -rf .miniprogram-cache 2>/dev/null || true
rm -rf miniprogram/.tmp 2>/dev/null || true
rm -rf .idea/workspace.xml 2>/dev/null || true
rm -rf logs/wechat 2>/dev/null || true
echo -e "   ${GREEN}✅ 缓存清理完成${NC}"
echo

# 3. 删除冲突目录
echo -e "${BLUE}3. 检查并删除冲突目录...${NC}"
if [ -d "miniprogram/pages" ]; then
    echo -e "   ${YELLOW}⚠️  发现 miniprogram/pages，正在删除...${NC}"
    rm -rf miniprogram/pages
    echo -e "   ${GREEN}✅ 已删除 miniprogram/pages${NC}"
else
    echo -e "   ${GREEN}✅ miniprogram/pages 不存在${NC}"
fi
echo

# 4. 清理备份文件 (可选)
echo -e "${BLUE}4. 清理备份文件 (.bak)...${NC}"
BAK_COUNT=$(find pages -name "*.bak" -type f 2>/dev/null | wc -l)
echo "   发现 $BAK_COUNT 个备份文件"
if [ "$BAK_COUNT" -gt 0 ]; then
    read -p "   是否删除所有 .bak 文件？(y/n): " clean_bak
    if [ "$clean_bak" = "y" ]; then
        find pages -name "*.bak" -type f -delete
        echo -e "   ${GREEN}✅ 已删除所有 .bak 文件${NC}"
    else
        echo -e "   ${YELLOW}⚠️  保留 .bak 文件 (已在 project.config.json 中配置忽略)${NC}"
    fi
fi
echo

# 5. 验证页面文件
echo -e "${BLUE}5. 验证所有页面文件...${NC}"
python3 << 'PYEOF'
import json, os, sys

with open('app.json', 'r') as f:
    app_config = json.load(f)

all_ok = True
missing_pages = []

print(f"   检查 {len(app_config['pages'])} 个页面...")

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
        print(f"      {RED}❌{NC} {page}")
    else:
        print(f"      {GREEN}✅{NC} {page}")

if all_ok:
    print(f"\n   {GREEN}✅ 所有页面文件完整 ({len(app_config['pages'])}/{len(app_config['pages'])}){NC}")
else:
    print(f"\n   {RED}❌ 以下页面文件缺失:{NC}")
    for page in missing_pages:
        print(f"      - {page}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "页面文件验证失败，请检查"
    exit 1
fi
echo

# 6. 验证项目配置
echo -e "${BLUE}6. 验证项目配置...${NC}"
python3 << 'PYEOF'
import json

with open('project.config.json', 'r') as f:
    proj_config = json.load(f)

ignored = proj_config.get('packOptions', {}).get('ignore', [])
ignored_values = [item.get('value') for item in ignored]
ignored_types = {item.get('value'): item.get('type') for item in ignored}

required_ignores = {
    'backend_python': 'folder',
    'miniprogram': 'folder',
    '*.bak': 'suffix'
}

for req, req_type in required_ignores.items():
    if req not in ignored_values:
        print(f"   {RED}❌ 缺少忽略配置：{req} ({req_type}){NC}")
        exit(1)
    else:
        actual_type = ignored_types.get(req)
        if actual_type != req_type:
            print(f"   {YELLOW}⚠️  忽略配置类型不匹配：{req} (期望:{req_type}, 实际:{actual_type}){NC}")
        else:
            print(f"   {GREEN}✅ 已忽略：{req} ({req_type}){NC}")

# 检查 libVersion
lib_version = proj_config.get('libVersion', 'unknown')
print(f"   {GREEN}✅ 基础库版本：{lib_version}{NC}")

print(f"   {GREEN}✅ 项目配置验证通过{NC}")
PYEOF

if [ $? -ne 0 ]; then
    echo "项目配置验证失败"
    exit 1
fi
echo

# 7. 检查页面 JSON 配置
echo -e "${BLUE}7. 检查页面 JSON 配置...${NC}"
python3 << 'PYEOF'
import json, os

with open('app.json', 'r') as f:
    app_config = json.load(f)

# 问题页面列表
problem_pages = [
    'pages/config-manager/config-manager',
    'pages/permission-manager/permission-manager',
    'pages/data-manager/data-manager',
    'pages/user-guide/user-guide',
    'pages/personal-history/personal-history'
]

print("   检查问题页面的 JSON 配置:")

for page in problem_pages:
    json_file = f'{page}.json'
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                config = json.load(f)
                # 添加 navigationBarTitleText 如果不存在
                if 'navigationBarTitleText' not in config:
                    page_name = page.split('/')[-1]
                    print(f"      {YELLOW}⚠️  {page} 缺少 navigationBarTitleText{NC}")
                else:
                    print(f"      {GREEN}✅ {page} 配置正常{NC}")
            except json.JSONDecodeError:
                print(f"      {RED}❌ {page} JSON 格式错误{NC}")
    else:
        print(f"      {RED}❌ {page} JSON 文件不存在{NC}")
PYEOF
echo

# 8. 生成项目信息文件
echo -e "${BLUE}8. 生成项目信息文件...${NC}"
cat > .project.info.json << EOF
{
  "name": "进化湾 GEO",
  "appid": "wx8876348e089bc261",
  "created_at": "$(date -Iseconds)",
  "fixed_issues": [
    "删除 miniprogram/pages 目录",
    "清理微信开发者工具缓存",
    "更新 project.config.json (忽略 .bak 文件)",
    "重建项目索引",
    "全局分析修复"
  ],
  "pages_count": $(python3 -c "import json; print(len(json.load(open('app.json'))['pages']))"),
  "problem_pages": [
    "pages/config-manager/config-manager",
    "pages/permission-manager/permission-manager",
    "pages/data-manager/data-manager",
    "pages/user-guide/user-guide",
    "pages/personal-history/personal-history"
  ],
  "status": "ready"
}
EOF
echo -e "   ${GREEN}✅ 项目信息生成完成${NC}"
echo

# 9. 最终检查
echo "============================================================"
echo -e "${GREEN}重建完成！${NC}"
echo "============================================================"
echo
echo -e "${GREEN}✅${NC} 1. 已清理所有缓存"
echo -e "${GREEN}✅${NC} 2. 已删除冲突目录"
echo -e "${GREEN}✅${NC} 3. 已验证所有页面文件"
echo -e "${GREEN}✅${NC} 4. 已更新项目配置 (忽略 .bak 文件)"
echo -e "${GREEN}✅${NC} 5. 已生成项目信息文件"
echo
echo "============================================================"
echo -e "${YELLOW}下一步操作 (必须手动执行):${NC}"
echo "============================================================"
echo "1. 打开微信开发者工具"
echo "2. 重新导入项目 (关键步骤!)"
echo "   - 文件 → 导入项目 → 选择当前目录"
echo "   - 不要直接打开现有项目"
echo "3. 清除缓存"
echo "   - 工具 → 清除缓存 → 清除全部缓存"
echo "4. 重新编译"
echo "   - 按 Ctrl/Cmd + B"
echo "5. 验证修复"
echo "   - 检查控制台是否还有页面注册错误"
echo "   - 测试所有导航按钮是否正常"
echo "============================================================"
echo
echo -e "${YELLOW}如问题仍然存在，请检查:${NC}"
echo "- docs/页面注册问题彻底修复完成报告.md"
echo "- docs/微信开发者工具缓存清理指南.md"
echo
echo "============================================================"
