#!/usr/bin/env python3
"""
WebSocket 集成静态验证测试

不需要启动后端服务，只验证代码正确性

测试覆盖：
1. 代码语法验证
2. 导入验证
3. 配置验证
4. 函数签名验证

@author: 系统架构组
@date: 2026-03-02
"""

import sys
import ast
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))


class colors:
    """终端颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """打印标题"""
    print(f"\n{colors.BOLD}{colors.BLUE}{'='*60}{colors.END}")
    print(f"{colors.BOLD}{colors.BLUE}{text:^60}{colors.END}")
    print(f"{colors.BOLD}{colors.BLUE}{'='*60}{colors.END}\n")


def print_success(text):
    """打印成功消息"""
    print(f"{colors.GREEN}✅ {text}{colors.END}")


def print_error(text):
    """打印错误消息"""
    print(f"{colors.RED}❌ {text}{colors.END}")


def print_info(text):
    """打印信息"""
    print(f"{colors.BLUE}ℹ️  {text}{colors.END}")


# ============================================================================
# 测试 1: 语法验证
# ============================================================================

def test_syntax():
    """验证 Python 文件语法"""
    print_header("测试 1: 语法验证")
    
    files_to_check = [
        'wechat_backend/app.py',
        'wechat_backend/websocket_route.py',
        'wechat_backend/services/realtime_push_service.py',
        'wechat_backend/services/background_service_manager.py',
    ]
    
    all_valid = True
    
    for file_path in files_to_check:
        full_path = backend_root / file_path
        if not full_path.exists():
            print_error(f"{file_path} 不存在")
            all_valid = False
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # 尝试解析 AST
            ast.parse(source)
            print_success(f"{file_path} 语法正确")
            
        except SyntaxError as e:
            print_error(f"{file_path} 语法错误：{e}")
            all_valid = False
        except Exception as e:
            print_error(f"{file_path} 检查失败：{e}")
            all_valid = False
    
    return all_valid


# ============================================================================
# 测试 2: 导入验证
# ============================================================================

def test_imports():
    """验证模块导入"""
    print_header("测试 2: 模块导入验证")
    
    imports_to_test = [
        ('wechat_backend.websocket_route', 'register_websocket_routes'),
        ('wechat_backend.v2.services.websocket_service', 'get_websocket_service'),
        ('wechat_backend.services.realtime_push_service', 'get_realtime_push_service'),
    ]
    
    all_valid = True
    
    for module_name, function_name in imports_to_test:
        try:
            module = __import__(module_name, fromlist=[function_name])
            function = getattr(module, function_name)
            print_success(f"{module_name}.{function_name}() 可导入")
        except ImportError as e:
            print_error(f"{module_name} 导入失败：{e}")
            all_valid = False
        except AttributeError as e:
            print_error(f"{module_name}.{function_name} 不存在：{e}")
            all_valid = False
    
    return all_valid


# ============================================================================
# 测试 3: WebSocket 路由函数签名验证
# ============================================================================

def test_websocket_route_signature():
    """验证 WebSocket 路由函数签名"""
    print_header("测试 3: WebSocket 路由函数签名验证")
    
    try:
        from wechat_backend.websocket_route import register_websocket_routes
        import inspect
        
        # 获取函数签名
        sig = inspect.signature(register_websocket_routes)
        params = list(sig.parameters.keys())
        
        if 'app' in params:
            print_success(f"register_websocket_routes(app) 签名正确")
            print_info(f"参数：{params}")
            return True
        else:
            print_error(f"register_websocket_routes 缺少 app 参数")
            print_info(f"当前参数：{params}")
            return False
            
    except Exception as e:
        print_error(f"函数签名验证失败：{e}")
        return False


# ============================================================================
# 测试 4: SSE 清理验证
# ============================================================================

def test_sse_cleanup():
    """验证 SSE 代码是否已清理"""
    print_header("测试 4: SSE 代码清理验证")
    
    sse_files = [
        'wechat_backend/services/sse_service_v2.py',
        'wechat_backend/services/sse_service.py',
    ]
    
    all_cleaned = True
    
    print_info("检查后端 SSE 文件...")
    for file_path in sse_files:
        full_path = backend_root / file_path
        if full_path.exists():
            print_error(f"  {file_path} 仍存在")
            all_cleaned = False
        else:
            print_success(f"  {file_path} 已删除")
    
    # 检查引用
    print_info("检查 SSE 引用...")
    files_to_check = [
        'wechat_backend/app.py',
        'wechat_backend/services/realtime_push_service.py',
    ]
    
    for file_path in files_to_check:
        full_path = backend_root / file_path
        if not full_path.exists():
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否还有 SSE 导入（排除注释）
        import_lines = [line for line in content.split('\n') if 'from wechat_backend.services.sse_service' in line and not line.strip().startswith('#')]
        
        if import_lines:
            print_error(f"  {file_path} 仍有 SSE 导入")
            all_cleaned = False
        else:
            print_success(f"  {file_path} 无 SSE 导入")
    
    # background_service_manager.py 检查
    bgm_path = backend_root / 'wechat_backend' / 'services' / 'background_service_manager.py'
    if bgm_path.exists():
        with open(bgm_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有活跃的 SSE 导入（排除注释）
        import_lines = [line for line in content.split('\n') if 'from wechat_backend.services.sse_service' in line and not line.strip().startswith('#')]
        
        if import_lines:
            print_error(f"  background_service_manager.py 仍有 SSE 导入")
            all_cleaned = False
        else:
            print_success(f"  background_service_manager.py 无活跃 SSE 导入（注释中的引用已忽略）")
    
    return all_cleaned


# ============================================================================
# 测试 5: WebSocket 集成验证
# ============================================================================

def test_websocket_integration():
    """验证 WebSocket 集成"""
    print_header("测试 5: WebSocket 集成验证")
    
    # 检查 app.py 中的 WebSocket 启动代码
    app_path = backend_root / 'wechat_backend' / 'app.py'
    
    if not app_path.exists():
        print_error("app.py 不存在")
        return False
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'WebSocket 导入': 'from wechat_backend.websocket_route import register_websocket_routes',
        'WebSocket 注册': 'register_websocket_routes(app)',
        'WebSocket 日志': 'WebSocket 服务已启动',
    }
    
    all_valid = True
    
    for check_name, check_string in checks.items():
        if check_string in content:
            print_success(f"{check_name} 存在")
        else:
            print_error(f"{check_name} 缺失")
            all_valid = False
    
    return all_valid


# ============================================================================
# 测试 6: 前端代码验证
# ============================================================================

def test_frontend_code():
    """验证前端代码"""
    print_header("测试 6: 前端代码验证")
    
    project_root = backend_root.parent
    
    # 检查 WebSocket 客户端
    ws_client_path = project_root / 'miniprogram' / 'services' / 'webSocketClient.js'
    
    if ws_client_path.exists():
        print_success("webSocketClient.js 存在")
        
        with open(ws_client_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键函数
        if 'class WebSocketClient' in content:
            print_success("WebSocketClient 类已定义")
        else:
            print_error("WebSocketClient 类未定义")
            return False
        
        if 'connect(' in content:
            print_success("connect() 方法已定义")
        else:
            print_error("connect() 方法未定义")
            return False
        
        if 'isConnected()' in content:
            print_success("isConnected() 方法已定义")
        else:
            print_error("isConnected() 方法未定义")
            return False
        
        return True
    else:
        print_error("webSocketClient.js 不存在")
        return False


# ============================================================================
# 测试 7: brandTestService.js 验证
# ============================================================================

def test_brandtest_service():
    """验证 brandTestService.js"""
    print_header("测试 7: brandTestService.js 验证")
    
    project_root = backend_root.parent
    service_path = project_root / 'services' / 'brandTestService.js'
    
    if not service_path.exists():
        print_error("brandTestService.js 不存在")
        return False
    
    with open(service_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'WebSocket 导入': 'const WebSocketClient = require',
        'WebSocket 使用': 'new WebSocketClient()',
        'WebSocket 连接': 'wsClient.connect(',
        '降级处理': 'onFallback',
    }
    
    all_valid = True
    
    for check_name, check_string in checks.items():
        if check_string in content:
            print_success(f"{check_name} 存在")
        else:
            print_error(f"{check_name} 缺失")
            all_valid = False
    
    return all_valid


# ============================================================================
# 主测试流程
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print_header("WebSocket 集成静态验证测试套件")
    
    results = {
        'passed': 0,
        'failed': 0
    }
    
    # 测试 1: 语法验证
    if test_syntax():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 2: 导入验证
    if test_imports():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 3: 函数签名验证
    if test_websocket_route_signature():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 4: SSE 清理验证
    if test_sse_cleanup():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 5: WebSocket 集成验证
    if test_websocket_integration():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 6: 前端代码验证
    if test_frontend_code():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 7: brandTestService.js 验证
    if test_brandtest_service():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 打印测试总结
    print_header("测试总结")
    print_info(f"通过：{colors.GREEN}{results['passed']}{colors.END}")
    print_info(f"失败：{colors.RED}{results['failed']}{colors.END}")
    
    total = results['passed'] + results['failed']
    pass_rate = (results['passed'] / total * 100) if total > 0 else 0
    
    print_info(f"通过率：{pass_rate:.1f}%")
    
    if results['failed'] == 0:
        print_success("\n🎉 所有静态验证通过！WebSocket 集成代码正确！")
        print_info("\n下一步：启动后端服务进行动态测试")
        print_info("命令：cd backend_python && python3 app.py")
        return True
    else:
        print_error("\n❌ 部分验证失败，请检查日志")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
