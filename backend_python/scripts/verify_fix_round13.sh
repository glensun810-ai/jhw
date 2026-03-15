#!/bin/bash
# 第 13 次修复 - 快速验证脚本
# 使用方式：bash backend_python/scripts/verify_fix_round13.sh

set -e

echo "============================================================"
echo "第 13 次修复 - 快速验证脚本"
echo "============================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查计数
CHECKS_PASSED=0
CHECKS_FAILED=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

# Step 1: 检查进程
echo "1. 检查后端进程..."
if ps aux | grep -E "python.*run.py" | grep -v grep > /dev/null; then
    check_pass "HTTP 服务进程运行中"
else
    check_fail "HTTP 服务进程未运行"
fi

if ps aux | grep -E "websocket|start_websocket" | grep -v grep > /dev/null; then
    check_pass "WebSocket 服务进程运行中"
else
    check_fail "WebSocket 服务进程未运行"
fi
echo ""

# Step 2: 检查端口
echo "2. 检查端口监听..."
if lsof -i :5001 | grep LISTEN > /dev/null 2>&1; then
    check_pass "端口 5001 (HTTP) 正在监听"
else
    check_fail "端口 5001 (HTTP) 未监听"
fi

if lsof -i :8765 | grep LISTEN > /dev/null 2>&1; then
    check_pass "端口 8765 (WebSocket) 正在监听"
else
    check_fail "端口 8765 (WebSocket) 未监听"
fi
echo ""

# Step 3: 检查 HTTP 服务
echo "3. 检查 HTTP 服务..."
HTTP_RESPONSE=$(curl -s http://localhost:5001/ 2>/dev/null || echo "")
if [ "$HTTP_RESPONSE" = "1.0" ]; then
    check_pass "HTTP 服务响应正常 (返回：$HTTP_RESPONSE)"
else
    check_fail "HTTP 服务响应异常 (返回：$HTTP_RESPONSE)"
fi
echo ""

# Step 4: 检查 WebSocket 路由
echo "4. 检查 WebSocket 路由..."
if curl -s http://localhost:5001/ws/hello?execution_id=test > /dev/null 2>&1; then
    check_pass "WebSocket 路由可访问"
else
    check_warn "WebSocket 路由访问失败（可能是正常的，因为这是 WebSocket 端点）"
fi
echo ""

# Step 5: 检查代码修复
echo "5. 检查代码修复..."
WEBSOCKET_ROUTE="backend_python/wechat_backend/websocket_route.py"

if grep -q "import websockets" "$WEBSOCKET_ROUTE" 2>/dev/null; then
    check_pass "websockets 导入已添加"
else
    check_fail "websockets 导入缺失"
fi

if grep -q "await ws_service.register(execution_id, websocket)" "$WEBSOCKET_ROUTE" 2>/dev/null; then
    check_pass "register 方法调用已修复"
else
    check_fail "register 方法调用未修复"
fi

if grep -q "await ws_service.unregister(execution_id, websocket)" "$WEBSOCKET_ROUTE" 2>/dev/null; then
    check_pass "unregister 方法调用已修复"
else
    check_fail "unregister 方法调用未修复"
fi

if grep -q "register_connection" "$WEBSOCKET_ROUTE" 2>/dev/null; then
    check_fail "发现旧的 register_connection 调用（应该已删除）"
else
    check_pass "旧的 register_connection 调用已清除"
fi

if grep -q "unregister_connection" "$WEBSOCKET_ROUTE" 2>/dev/null; then
    check_fail "发现旧的 unregister_connection 调用（应该已删除）"
else
    check_pass "旧的 unregister_connection 调用已清除"
fi
echo ""

# Step 6: 检查数据库
echo "6. 检查数据库..."
if [ -f "backend_python/database.db" ]; then
    check_pass "数据库文件存在"
    
    TABLE_COUNT=$(sqlite3 backend_python/database.db "SELECT COUNT(*) FROM diagnosis_results;" 2>/dev/null || echo "0")
    if [ "$TABLE_COUNT" -gt 0 ]; then
        check_pass "数据库可访问，记录数：$TABLE_COUNT"
    else
        check_warn "数据库表为空或不可访问"
    fi
else
    check_fail "数据库文件不存在"
fi
echo ""

# Step 7: 检查日志
echo "7. 检查日志..."
if [ -f "backend_python/logs/app.log" ]; then
    check_pass "日志文件存在"
    
    if tail -100 backend_python/logs/app.log | grep -q "WebSocket.*服务器已启动"; then
        check_pass "WebSocket 服务启动日志正常"
    else
        check_warn "WebSocket 服务启动日志未找到"
    fi
    
    if tail -100 backend_python/logs/app.log | grep -q "ERROR"; then
        RECENT_ERRORS=$(tail -100 backend_python/logs/app.log | grep -c "ERROR" || echo "0")
        check_warn "最近日志中有 $RECENT_ERRORS 个错误"
    else
        check_pass "最近日志中没有错误"
    fi
else
    check_fail "日志文件不存在"
fi
echo ""

# 总结
echo "============================================================"
echo "验证总结"
echo "============================================================"
echo -e "通过的检查：${GREEN}$CHECKS_PASSED${NC}"
echo -e "失败的检查：${RED}$CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！${NC}"
    echo ""
    echo "下一步："
    echo "1. 打开微信开发者工具"
    echo "2. 进入'品牌诊断'页面"
    echo "3. 执行一次完整诊断"
    echo "4. 观察 WebSocket 连接和报告页显示"
    echo ""
    echo "实时监控日志："
    echo "  tail -f backend_python/logs/app.log | grep -E 'WebSocket|连接 | 注册 | 广播'"
    exit 0
else
    echo -e "${RED}❌ 部分检查失败，请检查上述输出${NC}"
    echo ""
    echo "建议操作："
    echo "1. 停止所有后端进程：pkill -f 'backend_python'"
    echo "2. 清理缓存：find backend_python -name '__pycache__' -exec rm -rf {} +"
    echo "3. 重启服务：cd backend_python && python3 run.py &"
    exit 1
fi
