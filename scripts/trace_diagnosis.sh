#!/bin/bash
# 诊断链路追踪脚本
# 用法：./scripts/trace_diagnosis.sh <execution_id>

set -e

EXECUTION_ID=$1

if [ -z "$EXECUTION_ID" ]; then
    echo "用法：$0 <execution_id>"
    echo ""
    echo "示例:"
    echo "  $0 4b91ec6f-8225-4d65-835c-4af6b8ac8fd4"
    echo ""
    echo "获取最近的 execution_id:"
    echo "  sqlite3 backend_python/database.db \"SELECT execution_id FROM diagnosis_results ORDER BY created_at DESC LIMIT 5;\""
    exit 1
fi

LOG_FILE="logs/app.log"
DB_PATH="backend_python/database.db"

echo "========================================================================"
echo "  诊断链路追踪：$EXECUTION_ID"
echo "========================================================================"
echo ""

# 检查文件存在
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ 日志文件不存在：$LOG_FILE"
    exit 1
fi

if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在：$DB_PATH"
    exit 1
fi

# Step 1: API 接收
echo "[Step 1] API 接收诊断请求"
echo "------------------------------------------------------------------------"
grep -E "(收到诊断请求|perform-brand-test|DiagnosisOrchestrator.*$EXECUTION_ID)" "$LOG_FILE" | grep "$EXECUTION_ID" | tail -3 || echo "  (未找到相关日志)"
echo ""

# Step 2: 执行器启动
echo "[Step 2] NxM 执行器启动"
echo "------------------------------------------------------------------------"
grep -E "(NxM.*启动|NxMParallelExecutor|并行执行器.*$EXECUTION_ID)" "$LOG_FILE" | grep "$EXECUTION_ID" | tail -3 || echo "  (未找到相关日志)"
echo ""

# Step 3: AI 调用
echo "[Step 3] AI 调用执行"
echo "------------------------------------------------------------------------"
grep -E "(\[NxM-Parallel\].*$EXECUTION_ID|Q1×.*成功|Q1×.*失败)" "$LOG_FILE" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 4: tokens_used 日志
echo "[Step 4] Token 使用日志"
echo "------------------------------------------------------------------------"
grep -E "(tokens=|tokens_used)" "$LOG_FILE" | grep -v "grep" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 5: 数据库保存
echo "[Step 5] 数据库保存"
echo "------------------------------------------------------------------------"
grep -E "(批量添加结果 | 添加结果 | add_results|diagnosis_results.*INSERT)" "$LOG_FILE" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 6: 后台分析
echo "[Step 6] 后台分析"
echo "------------------------------------------------------------------------"
grep -E "(后台分析|brand_analysis|competitive_analysis|BACKGROUND_ANALYSIS)" "$LOG_FILE" | grep "$EXECUTION_ID" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 7: 报告聚合
echo "[Step 7] 报告聚合"
echo "------------------------------------------------------------------------"
grep -E "(报告聚合 | aggregate_report|REPORT_AGGREGATING)" "$LOG_FILE" | grep "$EXECUTION_ID" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 8: 分析数据保存
echo "[Step 8] 分析数据保存到 diagnosis_analysis"
echo "------------------------------------------------------------------------"
grep -E "(品牌分析已保存 | 竞争分析已保存 | diagnosis_analysis.*INSERT|add_analysis)" "$LOG_FILE" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 9: 快照创建
echo "[Step 9] 报告快照创建"
echo "------------------------------------------------------------------------"
grep -E "(报告快照 | create_snapshot|diagnosis_snapshots.*INSERT)" "$LOG_FILE" | tail -5 || echo "  (未找到相关日志)"
echo ""

# Step 10: 完成状态
echo "[Step 10] 诊断完成状态"
echo "------------------------------------------------------------------------"
grep -E "(completed|诊断完成|status.*completed)" "$LOG_FILE" | grep "$EXECUTION_ID" | tail -3 || echo "  (未找到相关日志)"
echo ""

# 数据库验证
echo "========================================================================"
echo "  数据库验证"
echo "========================================================================"
echo ""

echo "[DB 1] diagnosis_results 表记录:"
echo "------------------------------------------------------------------------"
sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
.width 40 15 10 10 10
SELECT 
    substr(execution_id, 1, 40) as execution_id,
    brand,
    model,
    tokens_used,
    created_at
FROM diagnosis_results 
WHERE execution_id = '$EXECUTION_ID'
ORDER BY created_at DESC;
EOF
echo ""

echo "[DB 2] diagnosis_analysis 表记录:"
echo "------------------------------------------------------------------------"
sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
.width 40 20 30
SELECT 
    substr(execution_id, 1, 40) as execution_id,
    analysis_type,
    substr(analysis_data, 1, 30) as data_preview
FROM diagnosis_analysis 
WHERE execution_id = '$EXECUTION_ID'
ORDER BY created_at DESC;
EOF
echo ""

echo "[DB 3] diagnosis_snapshots 表记录:"
echo "------------------------------------------------------------------------"
sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
.width 40 20 30
SELECT 
    substr(execution_id, 1, 40) as execution_id,
    snapshot_reason,
    substr(snapshot_data, 1, 30) as data_preview
FROM diagnosis_snapshots 
WHERE execution_id = '$EXECUTION_ID'
ORDER BY created_at DESC;
EOF
echo ""

# 统计摘要
echo "========================================================================"
echo "  统计摘要"
echo "========================================================================"
echo ""

RESULT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = '$EXECUTION_ID';")
ANALYSIS_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM diagnosis_analysis WHERE execution_id = '$EXECUTION_ID';")
SNAPSHOT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM diagnosis_snapshots WHERE execution_id = '$EXECUTION_ID';")

echo "  diagnosis_results:   $RESULT_COUNT 条记录"
echo "  diagnosis_analysis:  $ANALYSIS_COUNT 条记录"
echo "  diagnosis_snapshots: $SNAPSHOT_COUNT 条记录"
echo ""

# 验证结果
echo "========================================================================"
echo "  验证结果"
echo "========================================================================"
echo ""

ERRORS=0
WARNINGS=0

# 检查 brand 字段
EMPTY_BRAND=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = '$EXECUTION_ID' AND (brand = '' OR brand IS NULL);")
if [ "$EMPTY_BRAND" -gt 0 ]; then
    echo "❌ brand 字段为空：$EMPTY_BRAND 条记录"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ brand 字段完整"
fi

# 检查 tokens_used
ZERO_TOKENS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = '$EXECUTION_ID' AND tokens_used = 0;")
if [ "$ZERO_TOKENS" -gt 0 ]; then
    echo "⚠️  tokens_used=0: $ZERO_TOKENS 条记录"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ tokens_used 有值"
fi

# 检查 analysis 数据
if [ "$ANALYSIS_COUNT" -eq 0 ]; then
    echo "❌ diagnosis_analysis 无记录"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ diagnosis_analysis 有记录"
fi

# 检查 snapshot 数据
if [ "$SNAPSHOT_COUNT" -eq 0 ]; then
    echo "⚠️  diagnosis_snapshots 无记录"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ diagnosis_snapshots 有记录"
fi

echo ""
echo "========================================================================"
echo "  总结：$ERRORS 个错误，$WARNINGS 个警告"
echo "========================================================================"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "建议："
    echo "  1. 查看完整日志：tail -200 logs/app.log | grep '$EXECUTION_ID'"
    echo "  2. 运行端到端测试：python3 scripts/end_to_end_test.py"
    exit 1
else
    echo ""
    echo "🎉 验证通过！"
    exit 0
fi
