#!/bin/bash
# 第 16 次修复 - 验证脚本

echo "============================================================"
echo "  第 16 次修复 - 验证脚本"
echo "  修复内容："
echo "  1. 品牌提取正则优化，清理括号和多余描述"
echo "  2. 数据库保存前品牌名称验证和清理"
echo "  3. 品牌分布计算容错处理"
echo "============================================================"
echo ""

# 1. 检查后端服务
echo "1. 检查后端服务..."
if curl -s http://localhost:5001/ | grep -q "1.0"; then
    echo "✅ 后端 HTTP 服务正常"
else
    echo "❌ 后端 HTTP 服务异常"
    exit 1
fi

# 2. 检查 WebSocket 服务
echo ""
echo "2. 检查 WebSocket 服务..."
if lsof -i :8765 | grep -q "Python"; then
    echo "✅ WebSocket 服务正常 (端口 8765)"
else
    echo "❌ WebSocket 服务异常"
    exit 1
fi

# 3. 检查最新诊断记录
echo ""
echo "3. 检查最新诊断记录..."
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
LATEST_EXECUTION=$(sqlite3 database.db "SELECT execution_id, status, brand FROM diagnosis_results ORDER BY created_at DESC LIMIT 1;")
if [ -n "$LATEST_EXECUTION" ]; then
    echo "✅ 最新诊断记录：$LATEST_EXECUTION"
else
    echo "⚠️  无诊断记录"
fi

# 4. 测试 API 返回
echo ""
echo "4. 测试最新诊断报告 API..."
LATEST_ID=$(sqlite3 database.db "SELECT execution_id FROM diagnosis_results ORDER BY created_at DESC LIMIT 1;")
if [ -n "$LATEST_ID" ]; then
    RESPONSE=$(curl -s "http://localhost:5001/api/diagnosis/report/$LATEST_ID")
    SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success', 'N/A'))" 2>/dev/null)
    BRAND_DATA=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(list(d.get('data', {}).get('brandDistribution', {}).get('data', {}).keys()))" 2>/dev/null)
    
    if [ "$SUCCESS" = "True" ]; then
        echo "✅ API 返回成功"
        echo "   品牌数据：$BRAND_DATA"
    else
        echo "⚠️  API 返回异常：$RESPONSE"
    fi
else
    echo "⚠️  无最新诊断 ID，跳过测试"
fi

# 5. 检查后端日志
echo ""
echo "5. 检查后端日志（最近 10 条）..."
tail -10 /Users/sgl/PycharmProjects/PythonProject/logs/app.log | grep -E "INFO|ERROR|WARNING" | while read line; do
    echo "   $line"
done

# 6. 检查修改的文件
echo ""
echo "6. 检查修改的文件..."
cd /Users/sgl/PycharmProjects/PythonProject

# P0 修复：更新文件路径检查
MINIPROGRAM_DIR="brand_ai-seach/miniprogram"

FILES_MODIFIED=(
    "backend_python/wechat_backend/nxm_concurrent_engine_v3.py"
    "backend_python/wechat_backend/diagnosis_report_repository.py"
    "$MINIPROGRAM_DIR/pages/diagnosis/diagnosis.js"
    "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js"
    "$MINIPROGRAM_DIR/services/reportService.js"
)

for file in "${FILES_MODIFIED[@]}"; do
    if [ -f "$file" ]; then
        MODIFIED_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d'.' -f1)
        echo "✅ $file (修改时间：$MODIFIED_TIME)"
    else
        echo "❌ $file (不存在)"
    fi
done

# 7. 验证后端品牌提取清理逻辑
echo ""
echo "7. 验证后端品牌提取清理逻辑..."
grep -q "def clean_brand" backend_python/wechat_backend/nxm_concurrent_engine_v3.py && echo "✅ clean_brand 方法已添加" || echo "❌ clean_brand 方法缺失"
grep -q "去除括号及括号内内容" backend_python/wechat_backend/nxm_concurrent_engine_v3.py && echo "✅ 括号清理逻辑已添加" || echo "❌ 括号清理逻辑缺失"
grep -q "去除常见后缀词" backend_python/wechat_backend/nxm_concurrent_engine_v3.py && echo "✅ 后缀词清理逻辑已添加" || echo "❌ 后缀词清理逻辑缺失"

# 8. 验证数据库保存前验证
echo ""
echo "8. 验证数据库保存前验证..."
grep -q "清理 extracted_brand 中的无效字符" backend_python/wechat_backend/diagnosis_report_repository.py && echo "✅ extracted_brand 清理逻辑已添加" || echo "❌ extracted_brand 清理逻辑缺失"
grep -q "验证清理后的品牌是否有效" backend_python/wechat_backend/diagnosis_report_repository.py && echo "✅ 品牌验证逻辑已添加" || echo "❌ 品牌验证逻辑缺失"

# 9. 验证前端数据保存保证
echo ""
echo "9. 验证前端数据保存保证..."
grep -q "_saveToGlobalData" "$MINIPROGRAM_DIR/pages/diagnosis/diagnosis.js" && echo "✅ _saveToGlobalData 方法已添加" || echo "❌ _saveToGlobalData 方法缺失"
grep -q "_backupToStorage" "$MINIPROGRAM_DIR/pages/diagnosis/diagnosis.js" && echo "✅ _backupToStorage 方法已添加" || echo "❌ _backupToStorage 方法缺失"
grep -q "await this._saveToGlobalData" "$MINIPROGRAM_DIR/pages/diagnosis/diagnosis.js" && echo "✅ 异步保存调用已添加" || echo "❌ 异步保存调用缺失"

# 10. 验证前端多数据源降级
echo ""
echo "10. 验证前端多数据源降级..."
grep -q "_loadFromGlobalData" "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js" && echo "✅ _loadFromGlobalData 方法已添加" || echo "❌ _loadFromGlobalData 方法缺失"
grep -q "_loadFromStorage" "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js" && echo "✅ _loadFromStorage 方法已添加" || echo "❌ _loadFromStorage 方法缺失"
grep -q "_loadFromAPI" "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js" && echo "✅ _loadFromAPI 方法已添加" || echo "❌ _loadFromAPI 方法缺失"
grep -q "尝试 1" "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js" && echo "✅ 尝试 1 注释已添加" || echo "❌ 尝试 1 注释缺失"
grep -q "尝试 2" "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js" && echo "✅ 尝试 2 注释已添加" || echo "❌ 尝试 2 注释缺失"
grep -q "尝试 3" "$MINIPROGRAM_DIR/pages/report-v2/report-v2.js" && echo "✅ 尝试 3 注释已添加" || echo "❌ 尝试 3 注释缺失"

# 11. 验证前端验证逻辑优化
echo ""
echo "11. 验证前端验证逻辑优化..."
grep -q "_calculateQualityScore" "$MINIPROGRAM_DIR/services/reportService.js" && echo "✅ _calculateQualityScore 方法已添加" || echo "❌ _calculateQualityScore 方法缺失"
grep -q "hasBrandData" "$MINIPROGRAM_DIR/services/reportService.js" && echo "✅ hasBrandData 逻辑已添加" || echo "❌ hasBrandData 逻辑缺失"

echo ""
echo "============================================================"
echo "  验证完成！"
echo ""
echo "  下一步操作："
echo "  1. 在微信开发者工具中清除缓存并重新编译"
echo "  2. 打开小程序"品牌诊断"页面"
echo "  3. 执行一次完整诊断"
echo "  4. 观察报告页是否正常显示"
echo "============================================================"
