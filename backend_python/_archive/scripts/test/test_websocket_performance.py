#!/usr/bin/env python3
"""
WebSocket 性能优化测试脚本

测试场景：
1. 连接池性能测试
2. 消息压缩性能测试
3. 延迟对比测试
4. 吞吐量测试

@author: 系统架构组
@date: 2026-03-09
"""

import sys
import time
import json
import asyncio
import statistics
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from wechat_backend.v2.services.websocket_service import WebSocketService, WS_CONFIG
from wechat_backend.logging_config import api_logger


class colors:
    """终端颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """打印标题"""
    print(f"\n{colors.BOLD}{colors.CYAN}{'='*70}{colors.END}")
    print(f"{colors.BOLD}{colors.CYAN}{text:^70}{colors.END}")
    print(f"{colors.BOLD}{colors.CYAN}{'='*70}{colors.END}\n")


def print_success(text):
    """打印成功消息"""
    print(f"{colors.GREEN}✅ {text}{colors.END}")


def print_info(text):
    """打印信息"""
    print(f"{colors.BLUE}ℹ️  {text}{colors.END}")


def print_metric(name, value, unit, improvement=None):
    """打印性能指标"""
    if improvement:
        print(f"{name}: {colors.BOLD}{value:.2f}{unit}{colors.END} ({colors.GREEN}↑ {improvement:.1f}% 改进{colors.END})")
    else:
        print(f"{name}: {colors.BOLD}{value:.2f}{unit}{colors.END}")


# ============================================================================
# 测试 1: 消息压缩性能
# ============================================================================

async def test_message_compression():
    """测试消息压缩性能"""
    print_header("测试 1: 消息压缩性能")
    
    ws_service = WebSocketService()
    
    # 测试不同大小的消息
    test_messages = {
        '小消息 (1KB)': 'x' * 1024,
        '中消息 (10KB)': 'x' * 10240,
        '大消息 (100KB)': 'x' * 102400,
        'JSON 消息 (5KB)': json.dumps({'data': 'x' * 5000, 'count': 100}),
        '诊断进度消息': json.dumps({
            'type': 'progress',
            'execution_id': 'test-123',
            'progress': 50,
            'stage': 'analyzing',
            'status': 'running',
            'details': {'current': 5, 'total': 10}
        })
    }
    
    results = {}
    
    for name, message in test_messages.items():
        # 压缩
        start = time.perf_counter()
        compressed_data, is_compressed = ws_service._compress_message(message)
        compress_time = (time.perf_counter() - start) * 1000
        
        # 解压
        start = time.perf_counter()
        decompressed = ws_service._decompress_message(compressed_data, is_compressed)
        decompress_time = (time.perf_counter() - start) * 1000
        
        # 验证
        assert decompressed == message, f"{name} 解压后不匹配"
        
        # 计算压缩比
        original_size = len(message.encode('utf-8'))
        compressed_size = len(compressed_data)
        compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
        
        results[name] = {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': compression_ratio,
            'compress_time_ms': compress_time,
            'decompress_time_ms': decompress_time,
            'is_compressed': is_compressed
        }
        
        # 打印结果
        print(f"\n{name}:")
        print(f"  原始大小：{original_size:,} 字节")
        print(f"  压缩后大小：{compressed_size:,} 字节")
        
        if compression_ratio > 0:
            print_metric("  压缩比", compression_ratio, "%")
        else:
            print(f"  压缩比：{colors.YELLOW}0% (消息太小，跳过压缩){colors.END}")
        
        print(f"  压缩耗时：{compress_time:.3f} ms")
        print(f"  解压耗时：{decompress_time:.3f} ms")
    
    print_success("消息压缩测试完成")
    return results


# ============================================================================
# 测试 2: 连接池性能
# ============================================================================

async def test_connection_pool():
    """测试连接池性能"""
    print_header("测试 2: 连接池性能")
    
    ws_service = WebSocketService()
    
    # 模拟连接注册和返回池中
    test_iterations = 100
    execution_id = 'test-pool-123'
    
    print_info(f"执行 {test_iterations} 次连接池操作...")
    
    # 测试连接池获取和返回
    start = time.perf_counter()
    
    for i in range(test_iterations):
        # 模拟创建连接
        async def mock_send(data):
            pass
        
        mock_websocket = type('MockWebSocket', (), {'open': True, 'send': mock_send})()
        
        # 注册连接
        ws_service.connection_metadata[mock_websocket] = {
            'execution_id': execution_id,
            'connected_at': time.time(),
            'last_heartbeat': time.time(),
            'message_count': 0,
            'bytes_sent': 0,
            'bytes_received': 0
        }
        
        # 返回到池中
        await ws_service._return_connection_to_pool(execution_id, mock_websocket)
        
        # 从池中获取
        retrieved = await ws_service._get_connection_from_pool(execution_id)
    
    elapsed = (time.perf_counter() - start) * 1000
    avg_time = elapsed / test_iterations
    
    print_metric("平均连接池操作耗时", avg_time, "ms/次")
    print_metric("总耗时", elapsed, "ms")
    print_metric("操作次数", test_iterations, "次")
    
    # 获取指标
    metrics = await ws_service.get_metrics()
    print(f"\n连接池大小：{metrics['pool_size']}")
    
    print_success("连接池性能测试完成")
    return {
        'avg_time_ms': avg_time,
        'total_time_ms': elapsed,
        'iterations': test_iterations
    }


# ============================================================================
# 测试 3: 批量广播性能
# ============================================================================

async def test_broadcast_performance():
    """测试批量广播性能"""
    print_header("测试 3: 批量广播性能")
    
    ws_service = WebSocketService()
    
    # 创建模拟客户端
    num_clients = 10
    execution_id = 'test-broadcast-123'
    ws_service.clients[execution_id] = set()
    
    for i in range(num_clients):
        async def mock_send(data):
            await asyncio.sleep(0.001)
        
        mock_websocket = type('MockWebSocket', (), {
            'open': True,
            'send': mock_send
        })()
        ws_service.clients[execution_id].add(mock_websocket)
        ws_service.connection_metadata[mock_websocket] = {
            'execution_id': execution_id,
            'connected_at': time.time(),
            'last_heartbeat': time.time(),
            'message_count': 0,
            'bytes_sent': 0,
            'bytes_received': 0
        }
    
    # 测试消息
    test_message = {
        'progress': 50,
        'stage': 'analyzing',
        'status': 'running',
        'data': 'x' * 1000  # 1KB 数据
    }
    
    # 测试广播性能
    iterations = 50
    print_info(f"执行 {iterations} 次广播，每次发送给 {num_clients} 个客户端...")
    
    start = time.perf_counter()
    
    for i in range(iterations):
        await ws_service.broadcast(execution_id, test_message)
    
    elapsed = (time.perf_counter() - start) * 1000
    avg_time = elapsed / iterations
    
    # 获取指标
    metrics = await ws_service.get_metrics()
    
    print_metric("平均广播耗时", avg_time, "ms/次")
    print_metric("总耗时", elapsed, "ms")
    print_metric("发送消息数", metrics['messages_sent'], "条")
    print_metric("平均延迟", metrics['avg_latency_ms'], "ms")
    
    if metrics['bytes_sent_original'] > 0:
        print_metric(
            "压缩比",
            metrics['compression_ratio'],
            "%",
            metrics['compression_ratio']
        )
        print(f"  原始字节：{metrics['bytes_sent_original']:,}")
        print(f"  压缩后字节：{metrics['bytes_sent_compressed']:,}")
    
    print_success("批量广播性能测试完成")
    return {
        'avg_broadcast_ms': avg_time,
        'total_time_ms': elapsed,
        'messages_sent': metrics['messages_sent'],
        'compression_ratio': metrics['compression_ratio']
    }


# ============================================================================
# 测试 4: 配置验证
# ============================================================================

def test_configuration():
    """测试配置参数"""
    print_header("测试 4: 配置参数验证")
    
    print_info("WebSocket 配置:")
    print(f"  最大连接数：{WS_CONFIG['max_connections']}")
    print(f"  空闲超时：{WS_CONFIG['idle_timeout']} 秒")
    print(f"  连接池大小：{WS_CONFIG['connection_pool_size']}")
    print(f"  启用压缩：{WS_CONFIG['enable_compression']}")
    print(f"  压缩阈值：{WS_CONFIG['compression_threshold']} 字节")
    print(f"  压缩级别：{WS_CONFIG['compression_level']} (1-9)")
    print(f"  心跳间隔：{WS_CONFIG['ping_interval']} 秒")
    print(f"  心跳超时：{WS_CONFIG['ping_timeout']} 秒")
    
    # 验证配置合理性
    assert WS_CONFIG['max_connections'] > 0, "最大连接数必须大于 0"
    assert WS_CONFIG['idle_timeout'] > 0, "空闲超时必须大于 0"
    assert WS_CONFIG['connection_pool_size'] > 0, "连接池大小必须大于 0"
    assert 1 <= WS_CONFIG['compression_level'] <= 9, "压缩级别必须在 1-9 之间"
    assert WS_CONFIG['compression_threshold'] >= 0, "压缩阈值必须非负"
    
    print_success("配置参数验证通过")


# ============================================================================
# 主测试流程
# ============================================================================

async def run_all_tests():
    """运行所有性能测试"""
    print_header("WebSocket 性能优化测试套件")
    print_info(f"测试时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 测试 1: 配置验证
    test_configuration()
    
    # 测试 2: 消息压缩
    results['compression'] = await test_message_compression()
    
    # 测试 3: 连接池
    results['pool'] = await test_connection_pool()
    
    # 测试 4: 广播性能
    results['broadcast'] = await test_broadcast_performance()
    
    # 打印总结
    print_header("性能测试总结")
    
    # 压缩性能总结
    compressed_messages = [
        name for name, data in results['compression'].items()
        if data['compression_ratio'] > 0
    ]
    if compressed_messages:
        avg_ratio = statistics.mean([
            results['compression'][name]['compression_ratio']
            for name in compressed_messages
        ])
        print_metric("平均压缩比", avg_ratio, "%")
    
    # 连接池性能总结
    print_metric("连接池平均操作耗时", results['pool']['avg_time_ms'], "ms")
    
    # 广播性能总结
    print_metric("广播平均耗时", results['broadcast']['avg_broadcast_ms'], "ms")
    print_metric("消息压缩率", results['broadcast']['compression_ratio'], "%")
    
    print_success("\n🎉 所有性能测试完成！")
    
    return results


if __name__ == '__main__':
    results = asyncio.run(run_all_tests())
    
    # 输出 JSON 结果（用于 CI/CD）
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        import json
        # 转换结果为 JSON 可序列化格式
        json_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                json_results[key] = {}
                for name, data in value.items():
                    json_results[key][name] = {
                        k: v for k, v in data.items()
                        if isinstance(v, (int, float, bool, str))
                    }
            else:
                json_results[key] = value
        
        print(f"\n{json.dumps(json_results, indent=2)}")
    
    sys.exit(0)
