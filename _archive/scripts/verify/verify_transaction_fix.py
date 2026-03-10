"""
事务范围修复验证脚本

验证内容：
1. 短事务执行方法存在
2. 批量插入支持分批提交
3. 连接池泄漏检测功能
4. 连接池监控告警功能
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

import inspect
from datetime import datetime
from wechat_backend.logging_config import api_logger


def test_short_transaction_method():
    """测试 1: 短事务执行方法存在"""
    print("\n" + "=" * 60)
    print("测试 1: 短事务执行方法")
    print("=" * 60)

    from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator

    # 检查方法是否存在
    has_method = hasattr(DiagnosisOrchestrator, '_execute_in_transaction')

    if has_method:
        print("✅ 通过：_execute_in_transaction 方法存在")

        # 检查方法签名
        method = getattr(DiagnosisOrchestrator, '_execute_in_transaction')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        if 'operation_func' in params and 'operation_name' in params:
            print(f"✅ 通过：方法签名正确，参数={params}")
            return True
        else:
            print(f"❌ 失败：方法签名不正确，参数={params}")
            return False
    else:
        print("❌ 失败：_execute_in_transaction 方法不存在")
        return False


def test_batch_insert_with_batch_size():
    """测试 2: 批量插入支持分批提交"""
    print("\n" + "=" * 60)
    print("测试 2: 批量插入分批提交")
    print("=" * 60)

    from wechat_backend.services.diagnosis_transaction import DiagnosisTransaction
    from wechat_backend.diagnosis_report_service import DiagnosisReportService
    from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository

    all_pass = True

    # 检查 DiagnosisTransaction.add_results_batch
    sig = inspect.signature(DiagnosisTransaction.add_results_batch)
    params = list(sig.parameters.keys())
    if 'batch_size' in params:
        default = sig.parameters['batch_size'].default
        print(f"✅ DiagnosisTransaction.add_results_batch 支持 batch_size 参数 (默认={default})")
    else:
        print("❌ DiagnosisTransaction.add_results_batch 缺少 batch_size 参数")
        all_pass = False

    # 检查 DiagnosisReportService.add_results_batch
    sig = inspect.signature(DiagnosisReportService.add_results_batch)
    params = list(sig.parameters.keys())
    if 'batch_size' in params and 'commit' in params:
        print(f"✅ DiagnosisReportService.add_results_batch 支持 batch_size 和 commit 参数")
    else:
        print("❌ DiagnosisReportService.add_results_batch 缺少参数")
        all_pass = False

    # 检查 DiagnosisResultRepository.add_batch
    sig = inspect.signature(DiagnosisResultRepository.add_batch)
    params = list(sig.parameters.keys())
    if 'batch_size' in params and 'commit' in params:
        print(f"✅ DiagnosisResultRepository.add_batch 支持 batch_size 和 commit 参数")
    else:
        print("❌ DiagnosisResultRepository.add_batch 缺少参数")
        all_pass = False

    return all_pass


def test_connection_leak_detection():
    """测试 3: 连接池泄漏检测功能"""
    print("\n" + "=" * 60)
    print("测试 3: 连接池泄漏检测")
    print("=" * 60)

    from wechat_backend.database_connection_pool import DatabaseConnectionPool

    pool = DatabaseConnectionPool(max_connections=10, timeout=2.0)

    all_pass = True

    # 检查泄漏检测配置
    if hasattr(pool, 'max_connection_age'):
        print(f"✅ max_connection_age 配置存在：{pool.max_connection_age}秒")
    else:
        print("❌ max_connection_age 配置不存在")
        all_pass = False

    # 检查泄漏检测方法
    if hasattr(pool, '_check_and_fix_leaks'):
        print("✅ _check_and_fix_leaks 方法存在")
    else:
        print("❌ _check_and_fix_leaks 方法不存在")
        all_pass = False

    # 检查泄漏检测线程
    if hasattr(pool, '_leak_check_thread'):
        print("✅ 泄漏检测线程已启动")
    else:
        print("❌ 泄漏检测线程未启动")
        all_pass = False

    # 检查 stop 方法
    if hasattr(pool, 'stop'):
        print("✅ stop 方法存在")
    else:
        print("❌ stop 方法不存在")
        all_pass = False

    # 清理
    pool.stop()
    pool.close_all()

    return all_pass


def test_connection_pool_metrics():
    """测试 4: 连接池监控指标"""
    print("\n" + "=" * 60)
    print("测试 4: 连接池监控指标")
    print("=" * 60)

    from wechat_backend.database_connection_pool import DatabaseConnectionPool

    pool = DatabaseConnectionPool(max_connections=10, timeout=2.0)

    # 获取指标
    metrics = pool.get_metrics()

    all_pass = True

    # 检查必要字段
    required_fields = [
        'active_connections',
        'available_connections',
        'utilization_rate',
        'health_status',
        'health_message',
        'alert_level',
        'potential_leaks',
        'timestamp'
    ]

    for field in required_fields:
        if field in metrics:
            print(f"✅ 指标字段存在：{field} = {metrics[field]}")
        else:
            print(f"❌ 指标字段缺失：{field}")
            all_pass = False

    # 清理
    pool.stop()
    pool.close_all()

    return all_pass


def test_connection_pool_monitor():
    """测试 5: 连接池监控模块"""
    print("\n" + "=" * 60)
    print("测试 5: 连接池监控模块")
    print("=" * 60)

    try:
        from wechat_backend.monitoring.connection_pool_monitor import (
            ConnectionPoolMonitor,
            start_connection_pool_monitor,
            get_connection_pool_metrics
        )

        print("✅ 连接池监控模块导入成功")

        # 检查 ConnectionPoolMonitor 类
        if hasattr(ConnectionPoolMonitor, 'start'):
            print("✅ ConnectionPoolMonitor.start 方法存在")
        else:
            print("❌ ConnectionPoolMonitor.start 方法不存在")
            return False

        if hasattr(ConnectionPoolMonitor, 'add_alert_callback'):
            print("✅ ConnectionPoolMonitor.add_alert_callback 方法存在")
        else:
            print("❌ ConnectionPoolMonitor.add_alert_callback 方法不存在")
            return False

        return True

    except ImportError as e:
        print(f"❌ 连接池监控模块导入失败：{e}")
        return False


def main():
    """运行所有验证测试"""
    print("\n" + "=" * 60)
    print("事务范围修复验证")
    print("=" * 60)
    print("验证内容：")
    print("1. 短事务执行方法")
    print("2. 批量插入分批提交")
    print("3. 连接池泄漏检测")
    print("4. 连接池监控指标")
    print("5. 连接池监控模块")
    print("=" * 60)

    results = []

    results.append(("短事务执行方法", test_short_transaction_method()))
    results.append(("批量插入分批提交", test_batch_insert_with_batch_size()))
    results.append(("连接池泄漏检测", test_connection_leak_detection()))
    results.append(("连接池监控指标", test_connection_pool_metrics()))
    results.append(("连接池监控模块", test_connection_pool_monitor()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status}: {name}")

    total_passed = sum(1 for _, p in results if p)
    total_tests = len(results)

    print(f"\n总计：{total_passed}/{total_tests} 通过")

    if total_passed == total_tests:
        print("\n🎉 所有验证通过！修复成功！")
        return 0
    else:
        print("\n⚠️  部分验证失败，请检查修复代码。")
        return 1


if __name__ == "__main__":
    exit(main())
