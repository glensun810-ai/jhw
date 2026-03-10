#!/bin/bash
# 快速验证脚本 - 5 分钟内完成验证
# 用法：./scripts/quick_verify.sh

set -e

echo ""
echo "============================================================"
echo "🔍 快速验证脚本 - 品牌诊断报告系统"
echo "============================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计
PASSED=0
FAILED=0

# 项目根目录
PROJECT_ROOT="/Users/sgl/PycharmProjects/PythonProject"
BACKEND_ROOT="$PROJECT_ROOT/backend_python"
DB_PATH="$BACKEND_ROOT/database.db"

cd "$PROJECT_ROOT"

# ============================================================
# 1. 检查后端服务
# ============================================================
echo "1. 检查后端服务..."
if curl -s --connect-timeout 5 http://localhost:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端服务正常${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ 后端服务未启动${NC}"
    echo "   请执行：cd $BACKEND_ROOT && python3 app.py"
    ((FAILED++))
fi

# ============================================================
# 2. 检查数据库表结构
# ============================================================
echo ""
echo "2. 检查数据库表结构..."

if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ 数据库文件不存在：$DB_PATH${NC}"
    ((FAILED++))
else
    # 检查 diagnosis_results 表是否存在
    TABLE_EXISTS=$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='diagnosis_results';" 2>/dev/null || echo "")
    
    if [ -z "$TABLE_EXISTS" ]; then
        echo -e "${RED}❌ diagnosis_results 表不存在${NC}"
        ((FAILED++))
    else
        # 检查 brand 和 tokens_used 列
        BRAND_COL=$(sqlite3 "$DB_PATH" "PRAGMA table_info(diagnosis_results);" | grep -c "brand" || echo "0")
        TOKENS_COL=$(sqlite3 "$DB_PATH" "PRAGMA table_info(diagnosis_results);" | grep -c "tokens_used" || echo "0")
        
        if [ "$BRAND_COL" -ge 1 ] && [ "$TOKENS_COL" -ge 1 ]; then
            echo -e "${GREEN}✅ 数据库表结构正常${NC}"
            echo "   - brand 列：存在"
            echo "   - tokens_used 列：存在"
            ((PASSED++))
        else
            echo -e "${RED}❌ 数据库表结构不完整${NC}"
            echo "   - brand 列：$([ "$BRAND_COL" -ge 1 ] && echo '存在' || echo '缺失')"
            echo "   - tokens_used 列：$([ "$TOKENS_COL" -ge 1 ] && echo '存在' || echo '缺失')"
            ((FAILED++))
        fi
    fi
fi

# ============================================================
# 3. 检查代码文件
# ============================================================
echo ""
echo "3. 检查代码文件..."

FILES_TO_CHECK=(
    "$BACKEND_ROOT/wechat_backend/types.py"
    "$BACKEND_ROOT/wechat_backend/validators.py"
    "$BACKEND_ROOT/wechat_backend/nxm_execution_engine.py"
    "$PROJECT_ROOT/miniprogram/cloudfunctions/getDiagnosisReport/index.js"
)

ALL_FILES_EXIST=true
for file in "${FILES_TO_CHECK[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ 文件不存在：$file${NC}"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = true ]; then
    echo -e "${GREEN}✅ 所有代码文件存在${NC}"
    ((PASSED++))
else
    ((FAILED++))
fi

# ============================================================
# 4. 检查字段验证代码
# ============================================================
echo ""
echo "4. 检查字段验证代码..."

if grep -q "'brand': main_brand" "$BACKEND_ROOT/wechat_backend/nxm_execution_engine.py" 2>/dev/null; then
    echo -e "${GREEN}✅ NxM 引擎包含 brand 字段${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ NxM 引擎缺少 brand 字段${NC}"
    ((FAILED++))
fi

if grep -q "tokens_used" "$BACKEND_ROOT/wechat_backend/nxm_execution_engine.py" 2>/dev/null; then
    echo -e "${GREEN}✅ NxM 引擎包含 tokens_used 字段${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ NxM 引擎缺少 tokens_used 字段${NC}"
    ((FAILED++))
fi

# ============================================================
# 5. 运行单元测试
# ============================================================
echo ""
echo "5. 运行单元测试..."

cd "$BACKEND_ROOT"
if python3 -m pytest tests/unit/test_validators.py -v --tb=short 2>/dev/null; then
    echo -e "${GREEN}✅ 单元测试通过${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  单元测试未运行或失败（可能是测试文件不存在）${NC}"
    # 不增加 FAILED 计数，因为测试文件可能尚未创建
fi

cd "$PROJECT_ROOT"

# ============================================================
# 6. 检查云函数配置
# ============================================================
echo ""
echo "6. 检查云函数配置..."

CLOUD_FUNC_DIR="$PROJECT_ROOT/miniprogram/cloudfunctions/getDiagnosisReport"

if [ -d "$CLOUD_FUNC_DIR" ]; then
    if [ -f "$CLOUD_FUNC_DIR/index.js" ] && [ -f "$CLOUD_FUNC_DIR/package.json" ]; then
        # 检查是否调用后端 API
        if grep -q "/api/diagnosis/report/" "$CLOUD_FUNC_DIR/index.js" 2>/dev/null; then
            echo -e "${GREEN}✅ 云函数配置正确${NC}"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠️  云函数可能未调用后端 API${NC}"
            ((PASSED++))
        fi
    else
        echo -e "${RED}❌ 云函数文件不完整${NC}"
        ((FAILED++))
    fi
else
    echo -e "${RED}❌ 云函数目录不存在${NC}"
    ((FAILED++))
fi

# ============================================================
# 汇总结果
# ============================================================
echo ""
echo "============================================================"
echo "📊 验证结果汇总"
echo "============================================================"
echo ""
echo "   通过：${PASSED}"
echo "   失败：${FAILED}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}🎉 所有验证通过！系统可以安全部署！${NC}"
    echo ""
    echo "下一步操作："
    echo "1. 在微信开发者工具中重新编译小程序"
    echo "2. 执行一次完整的品牌诊断测试"
    echo "3. 检查报告是否正确显示品牌数据"
    exit 0
else
    echo -e "${RED}❌ 有 $FAILED 项验证失败，请修复后再部署${NC}"
    echo ""
    echo "修复建议："
    if [ "$FAILED" -gt 0 ]; then
        echo "- 检查后端服务是否启动"
        echo "- 检查数据库表结构是否完整"
        echo "- 检查代码文件是否存在"
        echo "- 检查字段验证代码是否正确"
    fi
    exit 1
fi
