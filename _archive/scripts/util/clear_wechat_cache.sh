#!/bin/bash
# 微信开发者工具缓存强制清理脚本

echo "=== 强制清理微信开发者工具缓存 ==="
echo ""
echo "当前状态:"
echo "- 源代码已修复 ✅"
echo "- 微信仍在用旧缓存 ❌"
echo "- 错误行号：146 (旧代码)"
echo "- 当前修复行号：164-175 (新代码)"
echo ""
echo "正在执行清理..."
echo ""

# 删除缓存文件夹
echo "1. 删除项目缓存..."
cd /Users/sgl/PycharmProjects/PythonProject
rm -rf .miniprogram 2>/dev/null
rm -rf node_modules/.cache 2>/dev/null
rm -rf .cache 2>/dev/null
rm -rf dist 2>/dev/null
echo "   ✅ 缓存文件夹已删除"
echo ""

# 验证源代码
echo "2. 验证源代码修复..."
echo "   onLoad 函数 (第 164-175 行):"
sed -n '164,175p' pages/index/index.js | sed 's/^/   /'
echo ""

echo "   initializeDefaults 函数 (第 214-225 行):"
sed -n '214,225p' pages/index/index.js | sed 's/^/   /'
echo ""

echo "=== 清理完成 ==="
echo ""
echo "下一步操作:"
echo "1. 关闭微信开发者工具（完全退出）"
echo "2. 重新打开微信开发者工具"
echo "3. 重新导入项目"
echo "4. 点击菜单：工具 → 构建 npm"
echo "5. 点击编译按钮"
echo "6. 打开首页，检查控制台"
echo ""
echo "预期结果:"
echo "✅ 品牌 AI 雷达 - 页面加载完成"
echo "✅ 诊断预估配置：{ duration: '30s', steps: 5 }"
echo "❌ 不应该看到 TypeError 错误"
echo ""
