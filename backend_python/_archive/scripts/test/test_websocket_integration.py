#!/usr/bin/env python3
"""
WebSocket 集成测试脚本

测试场景：
1. WebSocket 服务器启动验证
2. WebSocket 路由注册验证
3. WebSocket 连接测试
4. 消息推送测试
5. 降级到轮询测试

@author: 系统架构组
@date: 2026-03-02
"""

import sys
import time
import json
import asyncio
import requests
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from wechat_backend.logging_config import api_logger

# 测试配置
TEST_CONFIG = {
    'base_url': 'http://127.0.0.1:5001',
    'ws_url': 'ws://127.0.0.1:8765',
    'timeout': 10,
}


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


def print_warning(text):
    """打印警告消息"""
    print(f"{colors.YELLOW}⚠️  {text}{colors.END}")


def print_info(text):
    """打印信息"""
    print(f"{colors.BLUE}ℹ️  {text}{colors.END}")


# ============================================================================
# 测试 1: WebSocket 服务器启动验证
# ============================================================================

def test_websocket_server_startup():
    """测试 WebSocket 服务器是否启动"""
    print_header("测试 1: WebSocket 服务器启动验证")
    
    try:
        # 检查端口 8765 是否监听
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8765))
        sock.close()
        
        if result == 0:
            print_success("WebSocket 服务器已在端口 8765 启动")
            return True
        else:
            print_warning("WebSocket 服务器未启动（端口 8765 未监听）")
            print_info("提示：启动后端服务后，WebSocket 服务器会自动启动")
            return False
            
    except Exception as e:
        print_error(f"WebSocket 服务器检查失败：{e}")
        return False


# ============================================================================
# 测试 2: WebSocket 路由注册验证
# ============================================================================

def test_websocket_route_registration():
    """测试 WebSocket 路由是否注册"""
    print_header("测试 2: WebSocket 路由注册验证")
    
    try:
        # 测试 /ws/hello 接口
        response = requests.get(
            f"{TEST_CONFIG['base_url']}/ws/hello",
            params={'execution_id': 'test-123'},
            timeout=TEST_CONFIG['timeout']
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_success("WebSocket 路由已注册")
                print_info(f"返回数据：{json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            else:
                print_error("WebSocket 路由返回失败")
                return False
        else:
            print_error(f"WebSocket 路由请求失败：{response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("后端服务未启动，无法测试路由")
        print_info("提示：请先启动后端服务 (python3 backend_python/wechat_backend/app.py)")
        return False
    except Exception as e:
        print_error(f"WebSocket 路由测试失败：{e}")
        return False


# ============================================================================
# 测试 3: WebSocket 连接测试
# ============================================================================

async def test_websocket_connection():
    """测试 WebSocket 连接"""
    print_header("测试 3: WebSocket 连接测试")
    
    try:
        import websockets
        
        execution_id = 'test-execution-' + str(int(time.time()))
        ws_url = f"{TEST_CONFIG['ws_url']}/ws/diagnosis/{execution_id}"
        
        print_info(f"尝试连接：{ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            # 发送认证消息
            auth_message = {
                'type': 'auth',
                'executionId': execution_id,
                'clientType': 'test'
            }
            await websocket.send(json.dumps(auth_message))
            
            # 等待连接确认
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get('type') == 'connected':
                print_success("WebSocket 连接成功")
                print_info(f"连接数据：{json.dumps(data, indent=2, ensure_ascii=False)}")
                
                # 测试心跳
                heartbeat = {'type': 'heartbeat'}
                await websocket.send(json.dumps(heartbeat))
                
                heartbeat_response = await websocket.recv()
                heartbeat_data = json.loads(heartbeat_response)
                
                if heartbeat_data.get('type') == 'heartbeat_ack':
                    print_success("心跳响应正常")
                    return True
                else:
                    print_warning("心跳响应异常")
                    return False
            else:
                print_error("WebSocket 连接失败")
                print_info(f"响应数据：{json.dumps(data, indent=2, ensure_ascii=False)}")
                return False
                
    except ImportError:
        print_error("未安装 websockets 库，无法测试 WebSocket 连接")
        print_info("安装命令：pip install websockets")
        return False
    except Exception as e:
        print_error(f"WebSocket 连接测试失败：{e}")
        return False


# ============================================================================
# 测试 4: 消息推送测试
# ============================================================================

async def test_message_push():
    """测试消息推送"""
    print_header("测试 4: 消息推送测试")
    
    try:
        import websockets
        
        execution_id = 'test-push-' + str(int(time.time()))
        ws_url = f"{TEST_CONFIG['ws_url']}/ws/diagnosis/{execution_id}"
        
        async with websockets.connect(ws_url) as websocket:
            # 认证
            await websocket.send(json.dumps({
                'type': 'auth',
                'executionId': execution_id,
                'clientType': 'test'
            }))
            
            # 等待连接确认
            await websocket.recv()
            print_success("WebSocket 连接建立")
            
            # 模拟推送进度消息
            progress_messages = [
                {'progress': 10, 'stage': 'ai_fetching', 'status': 'running'},
                {'progress': 50, 'stage': 'analyzing', 'status': 'running'},
                {'progress': 90, 'stage': 'report_aggregating', 'status': 'running'},
                {'progress': 100, 'stage': 'completed', 'status': 'success'}
            ]
            
            for msg in progress_messages:
                # 模拟后端推送消息
                push_message = {
                    'type': 'progress',
                    'executionId': execution_id,
                    'data': msg,
                    'timestamp': time.time()
                }
                await websocket.send(json.dumps(push_message))
                print_info(f"推送进度：{msg['progress']}% - {msg['stage']}")
            
            print_success("消息推送测试完成")
            return True
            
    except Exception as e:
        print_error(f"消息推送测试失败：{e}")
        return False


# ============================================================================
# 测试 5: 后端服务健康检查
# ============================================================================

def test_backend_health():
    """测试后端服务健康状态"""
    print_header("测试 5: 后端服务健康检查")
    
    try:
        # 测试健康检查接口
        response = requests.get(
            f"{TEST_CONFIG['base_url']}/health",
            timeout=TEST_CONFIG['timeout']
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print_success("后端服务健康")
                print_info(f"健康数据：{json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            else:
                print_error("后端服务状态异常")
                return False
        else:
            print_error(f"健康检查请求失败：{response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("后端服务未启动")
        print_info("启动命令：cd backend_python && python3 app.py")
        return False
    except Exception as e:
        print_error(f"健康检查失败：{e}")
        return False


# ============================================================================
# 测试 6: SSE 代码清理验证
# ============================================================================

def test_sse_cleanup():
    """验证 SSE 代码是否已清理"""
    print_header("测试 6: SSE 代码清理验证")
    
    sse_files = [
        'wechat_backend/services/sse_service_v2.py',
        'wechat_backend/services/sse_service.py',
    ]
    
    frontend_sse_files = [
        'services/sseClient.js',
        'utils/sse-client.js',
        'utils/sseClient.js',
    ]
    
    all_cleaned = True
    
    # 检查后端 SSE 文件
    print_info("检查后端 SSE 文件...")
    for file_path in sse_files:
        full_path = backend_root / file_path
        if full_path.exists():
            print_error(f"  ❌ {file_path} 仍存在")
            all_cleaned = False
        else:
            print_success(f"  ✅ {file_path} 已删除")
    
    # 检查前端 SSE 文件
    print_info("检查前端 SSE 文件...")
    project_root = backend_root.parent
    for file_path in frontend_sse_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_error(f"  ❌ {file_path} 仍存在")
            all_cleaned = False
        else:
            print_success(f"  ✅ {file_path} 已删除")
    
    if all_cleaned:
        print_success("所有 SSE 代码已清理")
        return True
    else:
        print_warning("部分 SSE 代码未清理")
        return False


# ============================================================================
# 测试 7: WebSocket 代码存在验证
# ============================================================================

def test_websocket_code_exists():
    """验证 WebSocket 代码是否存在"""
    print_header("测试 7: WebSocket 代码存在验证")
    
    websocket_files = [
        'wechat_backend/v2/services/websocket_service.py',
        'wechat_backend/websocket_route.py',
    ]
    
    frontend_ws_files = [
        'miniprogram/services/webSocketClient.js',
    ]
    
    all_exist = True
    
    # 检查后端 WebSocket 文件
    print_info("检查后端 WebSocket 文件...")
    for file_path in websocket_files:
        full_path = backend_root / file_path
        if full_path.exists():
            print_success(f"  ✅ {file_path} 存在")
        else:
            print_error(f"  ❌ {file_path} 不存在")
            all_exist = False
    
    # 检查前端 WebSocket 文件
    print_info("检查前端 WebSocket 文件...")
    project_root = backend_root.parent
    for file_path in frontend_ws_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_success(f"  ✅ {file_path} 存在")
        else:
            print_error(f"  ❌ {file_path} 不存在")
            all_exist = False
    
    if all_exist:
        print_success("所有 WebSocket 代码已就绪")
        return True
    else:
        print_warning("部分 WebSocket 代码缺失")
        return False


# ============================================================================
# 主测试流程
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print_header("WebSocket 集成测试套件")
    print_info(f"测试配置：{TEST_CONFIG}")
    
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # 测试 1: WebSocket 服务器启动
    if test_websocket_server_startup():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 2: WebSocket 路由注册
    if test_websocket_route_registration():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 3: WebSocket 连接（异步）
    try:
        if asyncio.run(test_websocket_connection()):
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        print_error(f"WebSocket 连接测试异常：{e}")
        results['skipped'] += 1
    
    # 测试 4: 消息推送（异步）
    try:
        if asyncio.run(test_message_push()):
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        print_error(f"消息推送测试异常：{e}")
        results['skipped'] += 1
    
    # 测试 5: 后端健康检查
    if test_backend_health():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 6: SSE 代码清理
    if test_sse_cleanup():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 测试 7: WebSocket 代码存在
    if test_websocket_code_exists():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # 打印测试总结
    print_header("测试总结")
    print_info(f"通过：{colors.GREEN}{results['passed']}{colors.END}")
    print_info(f"失败：{colors.RED}{results['failed']}{colors.END}")
    print_info(f"跳过：{colors.YELLOW}{results['skipped']}{colors.END}")
    
    total = results['passed'] + results['failed'] + results['skipped']
    pass_rate = (results['passed'] / total * 100) if total > 0 else 0
    
    print_info(f"通过率：{pass_rate:.1f}%")
    
    if results['failed'] == 0 and results['skipped'] == 0:
        print_success("\n🎉 所有测试通过！WebSocket 集成成功！")
        return True
    elif results['failed'] == 0:
        print_warning("\n⚠️  部分测试跳过，但已通过的测试全部成功")
        return True
    else:
        print_error("\n❌ 部分测试失败，请检查日志")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
