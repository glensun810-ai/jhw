#!/usr/bin/env python3
"""
测试 NxM 执行引擎重构后的功能

验证点：
1. 同步写入机制：每个 (Question, Model) 请求完成后立即写入日志
2. 原子化状态更新：线程安全的 results 数组更新 + 唯一哈希值
3. 报告生成前置检查：IO_Wait 检查点确认日志文件句柄关闭且内容完整
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """测试导入是否正常"""
    print("=" * 60)
    print("测试 1: 导入模块")
    print("=" * 60)
    
    try:
        from wechat_backend.nxm_execution_engine import (
            execute_nxm_test,
            verify_nxm_execution,
            _generate_result_hash,
            _get_or_create_logger,
            _close_logger,
            _verify_log_file_integrity,
            _atomic_update_execution_store
        )
        print("✅ 所有函数导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_result_hash_generation():
    """测试结果哈希值生成"""
    print("\n" + "=" * 60)
    print("测试 2: 结果哈希值生成")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _generate_result_hash
    
    # 测试用例 1: 基本结果项
    result_item_1 = {
        'execution_id': 'test-123',
        'question_id': 0,
        'model': 'deepseek',
        'timestamp': '2026-02-20T10:00:00.000000'
    }
    hash_1 = _generate_result_hash(result_item_1)
    print(f"哈希 1: {hash_1}")
    
    # 测试用例 2: 相同内容应生成相同哈希
    result_item_2 = {
        'execution_id': 'test-123',
        'question_id': 0,
        'model': 'deepseek',
        'timestamp': '2026-02-20T10:00:00.000000'
    }
    hash_2 = _generate_result_hash(result_item_2)
    print(f"哈希 2: {hash_2}")
    
    if hash_1 == hash_2:
        print("✅ 相同内容生成相同哈希")
    else:
        print("❌ 相同内容生成了不同哈希")
        return False
    
    # 测试用例 3: 不同内容应生成不同哈希
    result_item_3 = {
        'execution_id': 'test-123',
        'question_id': 1,  # 不同
        'model': 'deepseek',
        'timestamp': '2026-02-20T10:00:00.000000'
    }
    hash_3 = _generate_result_hash(result_item_3)
    print(f"哈希 3: {hash_3}")
    
    if hash_1 != hash_3:
        print("✅ 不同内容生成不同哈希")
    else:
        print("❌ 不同内容生成了相同哈希")
        return False
    
    # 测试哈希长度
    if len(hash_1) == 16:
        print(f"✅ 哈希长度正确：{len(hash_1)} 字符")
    else:
        print(f"❌ 哈希长度错误：{len(hash_1)} 字符（期望 16）")
        return False
    
    return True


def test_logger_lifecycle():
    """测试日志写入器生命周期管理"""
    print("\n" + "=" * 60)
    print("测试 3: 日志写入器生命周期管理")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _get_or_create_logger, _close_logger
    
    execution_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 测试 1: 创建日志写入器
    logger, log_file_path = _get_or_create_logger(execution_id)
    print(f"✅ 创建日志写入器：{execution_id}")
    print(f"   日志文件路径：{log_file_path}")
    
    # 测试 2: 获取已存在的日志写入器（应返回同一个）
    logger2, log_file_path2 = _get_or_create_logger(execution_id)
    if logger is logger2:
        print("✅ 重复获取返回同一实例")
    else:
        print("❌ 重复获取返回了不同实例")
        return False
    
    # 测试 3: 关闭日志写入器
    closed = _close_logger(execution_id)
    if closed:
        print("✅ 关闭日志写入器成功")
    else:
        print("❌ 关闭日志写入器失败")
        return False
    
    # 测试 4: 关闭不存在的日志写入器
    closed2 = _close_logger("non-existent-id")
    if not closed2:
        print("✅ 关闭不存在的 ID 返回 False")
    else:
        print("❌ 关闭不存在的 ID 返回了 True")
        return False
    
    return True


def test_log_file_verification():
    """测试日志文件完整性验证"""
    print("\n" + "=" * 60)
    print("测试 4: 日志文件完整性验证")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _verify_log_file_integrity
    from utils.ai_response_logger_v2 import log_ai_response
    
    # 创建测试日志
    execution_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 写入 3 条测试记录
    log_file_path = None
    for i in range(3):
        record = log_ai_response(
            question=f"测试问题 {i+1}",
            response=f"测试回答 {i+1}",
            platform="test",
            model="test-model",
            brand="测试品牌",
            success=True,
            execution_id=execution_id,
            question_index=i+1,
            total_questions=3
        )
        if log_file_path is None:
            # 从记录器获取文件路径
            from utils.ai_response_logger_v2 import get_logger
            logger = get_logger()
            log_file_path = logger.log_file
    
    print(f"日志文件路径：{log_file_path}")
    print(f"写入记录数：3")
    
    # 验证日志文件
    verification = _verify_log_file_integrity(
        log_file_path,
        expected_records=3,
        execution_id=execution_id
    )
    
    print(f"验证结果:")
    print(f"  - 文件存在：{verification['file_exists']}")
    print(f"  - 文件已关闭：{verification['file_closed']}")
    print(f"  - 记录数量：{verification['record_count']}")
    print(f"  - 最后记录有效：{verification['last_record_valid']}")
    print(f"  - 整体有效：{verification['valid']}")
    
    if verification['valid']:
        print("✅ 日志文件完整性验证通过")
        return True
    else:
        print(f"❌ 日志文件完整性验证失败：{verification['errors']}")
        return False


def test_atomic_update():
    """测试原子化状态更新"""
    print("\n" + "=" * 60)
    print("测试 5: 原子化状态更新")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _atomic_update_execution_store
    
    # 创建测试 execution_store
    execution_store = {
        'test-exec': {
            'status': 'testing',
            'results': [],
            'progress': 0
        }
    }
    
    all_results_hashes = set()
    
    # 测试 1: 首次更新
    result_item_1 = {
        'execution_id': 'test-exec',
        'question_id': 0,
        'model': 'deepseek',
        'timestamp': '2026-02-20T10:00:00.000000',
        'content': '测试内容 1'
    }
    
    success_1 = _atomic_update_execution_store(
        execution_store,
        'test-exec',
        result_item_1,
        total_executions=3,
        all_results_hashes=all_results_hashes
    )
    
    if success_1:
        print("✅ 首次更新成功")
        print(f"   结果数量：{len(execution_store['test-exec']['results'])}")
        print(f"   进度：{execution_store['test-exec']['progress']}%")
    else:
        print("❌ 首次更新失败")
        return False
    
    # 测试 2: 重复更新（相同哈希值）
    result_item_2 = {
        'execution_id': 'test-exec',
        'question_id': 0,
        'model': 'deepseek',
        'timestamp': '2026-02-20T10:00:00.000000',
        'content': '测试内容 2'  # 内容不同但哈希值相同
    }
    
    success_2 = _atomic_update_execution_store(
        execution_store,
        'test-exec',
        result_item_2,
        total_executions=3,
        all_results_hashes=all_results_hashes
    )
    
    if not success_2:
        print("✅ 重复更新被正确拒绝")
    else:
        print("❌ 重复更新未被拒绝")
        return False
    
    # 测试 3: 不同结果更新
    result_item_3 = {
        'execution_id': 'test-exec',
        'question_id': 1,
        'model': 'deepseek',
        'timestamp': '2026-02-20T10:00:01.000000',
        'content': '测试内容 3'
    }
    
    success_3 = _atomic_update_execution_store(
        execution_store,
        'test-exec',
        result_item_3,
        total_executions=3,
        all_results_hashes=all_results_hashes
    )
    
    if success_3:
        print("✅ 不同结果更新成功")
        print(f"   结果数量：{len(execution_store['test-exec']['results'])}")
    else:
        print("❌ 不同结果更新失败")
        return False
    
    # 验证哈希值唯一性
    if len(all_results_hashes) == 2:
        print(f"✅ 哈希集合大小正确：{len(all_results_hashes)}")
    else:
        print(f"❌ 哈希集合大小错误：{len(all_results_hashes)}（期望 2）")
        return False
    
    return True


def test_full_workflow():
    """测试完整工作流程（模拟）"""
    print("\n" + "=" * 60)
    print("测试 6: 完整工作流程（模拟）")
    print("=" * 60)
    
    # 由于实际执行需要 API Key，这里只做结构验证
    from wechat_backend.nxm_execution_engine import execute_nxm_test
    
    execution_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    execution_store = {}
    
    # 初始化 execution_store
    execution_store[execution_id] = {
        'status': 'init',
        'progress': 0,
        'results': []
    }
    
    # 注意：这个测试不会真正调用 AI API（会失败），只验证函数签名和错误处理
    print(f"执行 ID: {execution_id}")
    print("注意：此测试不会真正调用 AI API，将验证错误处理逻辑")
    
    # 模拟执行（会因为没有 API Key 而失败，但应正确记录错误）
    result = execute_nxm_test(
        execution_id=execution_id,
        main_brand="测试品牌",
        competitor_brands=["竞品 1"],
        selected_models=[{'name': 'deepseek'}],
        raw_questions=["测试问题？"],
        user_id="test-user",
        user_level="Free",
        execution_store=execution_store
    )
    
    print(f"执行结果：{result.get('success', 'N/A')}")
    print(f"执行 ID: {result.get('execution_id', 'N/A')}")
    
    # 验证 execution_store 状态
    if execution_id in execution_store:
        store_status = execution_store[execution_id].get('status', 'unknown')
        print(f"Store 状态：{store_status}")
        
        # 验证是否有 IO_Wait 相关字段
        if 'io_wait' in execution_store[execution_id]:
            print(f"✅ IO_Wait 字段存在：{execution_store[execution_id]['io_wait']}")
        else:
            print("⚠️  IO_Wait 字段不存在（可能是早期失败）")
        
        if 'io_verified' in execution_store[execution_id]:
            print(f"✅ IO_Verified 字段存在：{execution_store[execution_id]['io_verified']}")
        else:
            print("⚠️  IO_Verified 字段不存在（可能是早期失败）")
    else:
        print("❌ Execution ID 不在 store 中")
        return False
    
    # 由于没有 API Key，预期会失败，但应该有错误记录
    if not result.get('success'):
        print("✅ 预期失败（无 API Key），错误处理正常")
        print(f"   错误信息：{result.get('error', 'N/A')[:100]}...")
    else:
        print("⚠️  意外成功（可能配置了测试 API Key）")
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("NxM 执行引擎重构验证测试")
    print(f"执行时间：{datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_imports),
        ("结果哈希值生成", test_result_hash_generation),
        ("日志写入器生命周期", test_logger_lifecycle),
        ("日志文件完整性验证", test_log_file_verification),
        ("原子化状态更新", test_atomic_update),
        ("完整工作流程", test_full_workflow)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} 测试异常：{e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！重构功能验证完成。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
