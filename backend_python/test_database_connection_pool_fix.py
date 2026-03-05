#!/usr/bin/env python3
"""
数据库连接池竞争条件修复验证脚本

测试场景：
1. 连接获取和归还功能验证
2. 连接健康检查验证
3. 并发连接获取测试
4. 连接泄漏检测验证
5. 超时处理验证
6. 长时间运行稳定性测试

@author: 系统架构组
@date: 2026-03-05
"""

import sys
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加路径
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.database_connection_pool import DatabaseConnectionPool
from wechat_backend.logging_config import db_logger


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_connection_get_return():
    """测试 1: 连接获取和归还功能验证"""
    print_section("测试 1: 连接获取和归还功能验证")
    
    pool = DatabaseConnectionPool(max_connections=10, timeout=5.0)
    
    # 获取连接
    conn1 = pool.get_connection()
    print(f"✅ 获取连接成功：id={id(conn1)}")
    
    # 验证连接可用
    result = conn1.execute('SELECT 1').fetchone()
    assert result == (1,), "连接不可用"
    print(f"✅ 连接健康检查通过")
    
    # 归还连接
    pool.return_connection(conn1)
    print(f"✅ 归还连接成功")
    
    # 再次获取应该是同一个连接
    conn2 = pool.get_connection()
    print(f"✅ 再次获取连接：id={id(conn2)}")
    
    # 验证是同一个连接（从池中复用）
    assert id(conn1) == id(conn2), "连接未被复用"
    print(f"✅ 连接复用验证通过")
    
    # 归还
    pool.return_connection(conn2)
    
    print("\n✅ 连接获取和归还功能验证通过")
    return True


def test_connection_health_check():
    """测试 2: 连接健康检查验证"""
    print_section("测试 2: 连接健康检查验证")
    
    pool = DatabaseConnectionPool(max_connections=10, timeout=5.0)
    
    # 获取连接
    conn = pool.get_connection()
    print(f"获取连接：id={id(conn)}")
    
    # 验证健康检查方法存在
    assert hasattr(pool, '_is_connection_healthy'), "缺少健康检查方法"
    
    # 验证健康连接
    is_healthy = pool._is_connection_healthy(conn)
    assert is_healthy, "健康连接被误判为 unhealthy"
    print(f"✅ 健康连接判断正确")
    
    # 模拟 unhealthy 连接（关闭后）
    conn.close()
    is_healthy = pool._is_connection_healthy(conn)
    assert not is_healthy, "unhealthy 连接被误判为健康"
    print(f"✅ unhealthy 连接判断正确")
    
    print("\n✅ 连接健康检查验证通过")
    return True


def test_concurrent_connections():
    """测试 3: 并发连接获取测试"""
    print_section("测试 3: 并发连接获取测试")
    
    pool = DatabaseConnectionPool(max_connections=20, timeout=10.0)
    
    def worker(worker_id: int):
        """工作线程函数"""
        try:
            # 获取连接
            conn = pool.get_connection()
            time.sleep(0.1)  # 模拟使用连接
            
            # 执行查询
            result = conn.execute('SELECT 1').fetchone()
            
            # 归还连接
            pool.return_connection(conn)
            
            return {
                'worker_id': worker_id,
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'worker_id': worker_id,
                'success': False,
                'error': str(e)
            }
    
    # 并发执行 50 个任务（超过最大连接数）
    num_workers = 50
    results = []
    
    print(f"启动 {num_workers} 个并发工作线程...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, i) for i in range(num_workers)]
        
        for future in as_completed(futures):
            results.append(future.result())
    
    duration = time.time() - start_time
    
    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    fail_count = num_workers - success_count
    
    print(f"执行时间：{duration:.2f}秒")
    print(f"成功：{success_count}/{num_workers}")
    print(f"失败：{fail_count}/{num_workers}")
    
    # 验证所有任务都成功
    assert success_count == num_workers, f"{fail_count} 个任务失败"
    
    # 验证连接池状态
    status = pool.get_pool_status()
    print(f"连接池状态:")
    print(f"  活跃连接：{status['active_connections']}")
    print(f"  可用连接：{status['available_connections']}")
    print(f"  总创建数：{status['total_created']}")
    print(f"  超时次数：{status['timeout_count']}")
    
    # 验证所有连接都已归还
    assert status['active_connections'] == 0, "有连接未归还"
    assert status['available_connections'] <= status['max_connections'], "连接数超限"
    
    print("\n✅ 并发连接获取测试通过")
    return True


def test_leak_detection():
    """测试 4: 连接泄漏检测验证"""
    print_section("测试 4: 连接泄漏检测验证")
    
    pool = DatabaseConnectionPool(max_connections=10, timeout=5.0)
    
    # 获取连接但不归还（模拟泄漏）
    conn = pool.get_connection()
    print(f"获取连接（模拟泄漏）：id={id(conn)}")
    
    # 等待一段时间
    print("等待 35 秒检测泄漏...")
    time.sleep(35)
    
    # 检测泄漏
    leaks = pool.detect_leaks()
    
    print(f"检测到 {len(leaks)} 个潜在泄漏")
    
    # 验证泄漏检测
    assert len(leaks) >= 1, "未检测到连接泄漏"
    
    for conn_id, info in leaks.items():
        print(f"  泄漏连接：id={conn_id}, 时长={info['duration']:.1f}秒")
    
    # 归还连接
    pool.return_connection(conn)
    
    # 再次检测应该没有泄漏
    time.sleep(1)
    leaks = pool.detect_leaks()
    assert len(leaks) == 0, "归还后仍有泄漏"
    
    print("\n✅ 连接泄漏检测验证通过")
    return True


def test_timeout_handling():
    """测试 5: 超时处理验证"""
    print_section("测试 5: 超时处理验证")
    
    pool = DatabaseConnectionPool(max_connections=5, timeout=2.0)
    
    # 获取所有连接
    connections = []
    for i in range(5):
        conn = pool.get_connection()
        connections.append(conn)
        print(f"获取连接 {i+1}/5: id={id(conn)}")
    
    # 尝试获取第 6 个连接（应该超时）
    print("尝试获取第 6 个连接（应该超时）...")
    
    try:
        conn = pool.get_connection(timeout=2.0)
        print("❌ 未超时，获取成功（不应该）")
        pool.return_connection(conn)
        assert False, "应该超时但未超时"
    except TimeoutError as e:
        print(f"✅ 超时处理正确：{e}")
    
    # 归还所有连接
    for conn in connections:
        pool.return_connection(conn)
    
    print("\n✅ 超时处理验证通过")
    return True


def test_long_running_stability():
    """测试 6: 长时间运行稳定性测试（简化版）"""
    print_section("测试 6: 长时间运行稳定性测试")
    
    pool = DatabaseConnectionPool(max_connections=20, timeout=5.0)
    
    print("模拟 10 轮连接获取和归还...")
    
    for round in range(10):
        # 获取多个连接
        connections = []
        for i in range(10):
            conn = pool.get_connection()
            connections.append(conn)
        
        # 模拟使用
        time.sleep(0.05)
        
        # 归还所有连接
        for conn in connections:
            pool.return_connection(conn)
        
        # 检查状态
        status = pool.get_pool_status()
        print(f"  轮次 {round + 1}/10: "
              f"活跃={status['active_connections']}, "
              f"可用={status['available_connections']}, "
              f"总创建={status['total_created']}")
    
    # 最终检查
    status = pool.get_pool_status()
    print(f"\n最终状态:")
    print(f"  活跃连接：{status['active_connections']}")
    print(f"  可用连接：{status['available_connections']}")
    print(f"  泄漏检测：{status['leak_detection_count']}")
    print(f"  健康状态：{status['health_status']}")
    
    # 验证所有连接都已归还
    assert status['active_connections'] == 0, "有连接未归还"
    assert status['health_status'] == 'healthy', "健康状态异常"
    
    print("\n✅ 长时间运行稳定性验证通过")
    return True


def test_pool_status_api():
    """测试 7: 连接池状态 API 验证"""
    print_section("测试 7: 连接池状态 API 验证")
    
    pool = DatabaseConnectionPool(max_connections=20, timeout=5.0)
    
    # 获取并归还一些连接
    connections = []
    for i in range(5):
        conn = pool.get_connection()
        connections.append(conn)
    
    time.sleep(0.1)
    
    for conn in connections:
        pool.return_connection(conn)
    
    # 获取状态
    status = pool.get_pool_status()
    metrics = pool.get_metrics()
    
    print("连接池状态信息:")
    for key, value in status.items():
        if key != 'leak_details':  # 跳过详细信息
            print(f"  {key}: {value}")
    
    print("\n连接池指标:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    # 验证必要字段存在
    required_fields = [
        'max_connections',
        'active_connections',
        'available_connections',
        'health_status',
        'leak_detection_count'
    ]
    
    for field in required_fields:
        assert field in status, f"缺少必要字段：{field}"
        assert field in metrics, f"指标缺少字段：{field}"
    
    print("\n✅ 连接池状态 API 验证通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print_section("数据库连接池竞争条件修复验证测试")
    print(f"测试开始时间：{datetime.now().isoformat()}")
    print(f"测试环境：Python {sys.version}")
    
    tests = [
        ("连接获取和归还功能验证", test_connection_get_return),
        ("连接健康检查验证", test_connection_health_check),
        ("并发连接获取测试", test_concurrent_connections),
        ("连接泄漏检测验证", test_leak_detection),
        ("超时处理验证", test_timeout_handling),
        ("长时间运行稳定性测试", test_long_running_stability),
        ("连接池状态 API 验证", test_pool_status_api),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            start_time = time.time()
            success = test_func()
            duration = time.time() - start_time
            results.append((name, success, duration, None))
        except AssertionError as e:
            results.append((name, False, 0, str(e)))
            print(f"\n❌ 测试失败：{name}")
            print(f"   错误信息：{e}")
        except Exception as e:
            results.append((name, False, 0, f"异常：{e}"))
            print(f"\n❌ 测试异常：{name}")
            print(f"   错误信息：{e}")
            import traceback
            traceback.print_exc()
    
    # 打印测试摘要
    print_section("测试摘要")
    
    passed_count = sum(1 for _, success, _, _ in results if success)
    total_count = len(results)
    
    print(f"总测试数：{total_count}")
    print(f"通过数：{passed_count}")
    print(f"失败数：{total_count - passed_count}")
    print(f"通过率：{passed_count / total_count:.1%}")
    print(f"总耗时：{sum(r[2] for r in results):.2f}秒")
    
    print("\n详细结果:")
    for name, success, duration, error in results:
        status = "✅ 通过" if success else "❌ 失败"
        error_msg = f" - {error}" if error else ""
        print(f"  {status} {name} ({duration:.2f}秒){error_msg}")
    
    # 最终判断
    if passed_count == total_count:
        print("\n" + "=" * 60)
        print("  🎉 所有测试通过！数据库连接池竞争条件修复验证成功！")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("  ⚠️ 部分测试失败，请检查修复实现")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
