#!/bin/bash
# =============================================================================
# 阶段一集成测试运行脚本
# =============================================================================
# 功能：
# 1. 运行所有集成测试
# 2. 生成覆盖率报告
# 3. 生成 HTML 测试报告
# 4. 清理测试数据
#
# 使用方式：
#   ./scripts/run_integration_tests.sh [--clean] [--report]
#
# 参数：
#   --clean   测试后清理临时文件
#   --report  生成详细报告（默认）
#
# 作者：系统架构组
# 日期：2026-02-27
# 版本：1.0.0
# =============================================================================

set -e

echo "========================================="
echo "运行阶段一集成测试"
echo "========================================="
echo ""

# 设置测试环境变量
export TEST_ENV=integration
export PYTHONPATH=.

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 创建测试报告目录
mkdir -p test_reports/integration

# 解析参数
CLEAN=false
GENERATE_REPORT=true

for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN=true
            shift
            ;;
        --no-report)
            GENERATE_REPORT=false
            shift
            ;;
        *)
            echo "未知参数：$arg"
            echo "使用方式：$0 [--clean] [--no-report]"
            exit 1
            ;;
    esac
done

# 检查依赖
echo "检查测试依赖..."
if ! command -v pytest &> /dev/null; then
    echo "错误：pytest 未安装，请先运行：pip install pytest pytest-asyncio pytest-cov pytest-html"
    exit 1
fi

echo "✓ pytest 已安装"

# 检查测试数据库配置
echo "检查测试配置..."
if [ ! -d "tests/integration" ]; then
    echo "错误：集成测试目录不存在"
    exit 1
fi

echo "✓ 测试目录存在"
echo ""

# 运行集成测试
echo "========================================="
echo "运行集成测试套件"
echo "========================================="
echo ""

START_TIME=$(date +%s)

# 运行所有集成测试
pytest tests/integration/ \
    -v \
    --cov=wechat_backend.v2 \
    --cov-report=html:test_reports/integration/coverage_all \
    --cov-report=xml:test_reports/integration/coverage.xml \
    --cov-report=term-missing \
    --html=test_reports/integration/report.html \
    --self-contained-html \
    --tb=short \
    -x \
    --asyncio-mode=auto

EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "========================================="
echo "测试执行完成"
echo "========================================="
echo ""
echo "执行时间：${DURATION}秒"
echo ""

# 生成覆盖率摘要
echo "========================================="
echo "覆盖率报告"
echo "========================================="
echo ""

if [ -f "test_reports/integration/coverage.xml" ]; then
    echo "✓ 覆盖率 XML 报告：test_reports/integration/coverage.xml"
fi

if [ -d "test_reports/integration/coverage_all" ]; then
    echo "✓ 覆盖率 HTML 报告：test_reports/integration/coverage_all/index.html"
fi

if [ -f "test_reports/integration/report.html" ]; then
    echo "✓ 测试报告 HTML: test_reports/integration/report.html"
fi

echo ""

# 清理临时文件
if [ "$CLEAN" = true ]; then
    echo "========================================="
    echo "清理临时测试文件..."
    echo "========================================="
    
    # 清理 Python 缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理 pytest 缓存
    rm -rf .pytest_cache 2>/dev/null || true
    
    echo "✓ 临时文件已清理"
    echo ""
fi

# 检查测试结果
if [ $EXIT_CODE -eq 0 ]; then
    echo "========================================="
    echo "✅ 所有集成测试通过"
    echo "========================================="
    echo ""
    echo "下一步："
    echo "1. 查看测试报告：open test_reports/integration/report.html"
    echo "2. 查看覆盖率：open test_reports/integration/coverage_all/index.html"
    echo "3. 运行清理脚本：python scripts/cleanup_test_data.py"
    echo ""
    exit 0
else
    echo "========================================="
    echo "❌ 集成测试失败"
    echo "========================================="
    echo ""
    echo "请查看测试报告获取详细信息："
    echo "  test_reports/integration/report.html"
    echo ""
    exit $EXIT_CODE
fi
