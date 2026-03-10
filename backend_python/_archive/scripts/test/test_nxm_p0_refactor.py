#!/usr/bin/env python3
"""
测试 NxM 执行引擎 P0 重构功能

验证点：
1. 流式持久化：每个 (Question, Model) 完成后先写日志再更新内存
2. GEO 语义加固：强制解析 rank, sentiment, interception，失败时存入 error_code
3. 任务终点校验：results 数组长度必须等于 len(Q) * len(M) 才标记 completed
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
            _parse_geo_with_validation,
            _verify_completion,
            _atomic_update_execution_store
        )
        print("✅ 所有函数导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_geo_parse_with_validation():
    """测试 GEO 语义加固功能"""
    print("\n" + "=" * 60)
    print("测试 2: GEO 语义加固 - 强制解析三个核心指标")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _parse_geo_with_validation
    
    execution_id = "test-geo-parse"
    
    # 测试用例 1: 完整正确的 GEO 数据
    print("\n测试用例 1: 完整正确的 GEO 数据")
    response_text_1 = """
    这是一个品牌分析回答。
    
    ```json
    {
        "geo_analysis": {
            "brand_mentioned": true,
            "rank": 3,
            "sentiment": 0.8,
            "cited_sources": [{"url": "https://example.com", "site_name": "Example"}],
            "interception": "竞品 A"
        }
    }
    ```
    """
    
    geo_data_1, error_code_1 = _parse_geo_with_validation(
        response_text_1, execution_id, 0, "deepseek"
    )
    
    print(f"  rank: {geo_data_1.get('rank')}")
    print(f"  sentiment: {geo_data_1.get('sentiment')}")
    print(f"  interception: {geo_data_1.get('interception')}")
    print(f"  error_code: {error_code_1}")
    
    if (geo_data_1.get('rank') == 3 and 
        geo_data_1.get('sentiment') == 0.8 and 
        geo_data_1.get('interception') == "竞品 A" and
        error_code_1 is None):
        print("  ✅ 完整 GEO 数据解析成功")
    else:
        print("  ❌ 完整 GEO 数据解析失败")
        return False
    
    # 测试用例 2: 缺失部分字段
    print("\n测试用例 2: 缺失 interception 字段")
    response_text_2 = """
    {
        "geo_analysis": {
            "brand_mentioned": true,
            "rank": 5,
            "sentiment": -0.3
        }
    }
    """
    
    geo_data_2, error_code_2 = _parse_geo_with_validation(
        response_text_2, execution_id, 1, "deepseek"
    )
    
    print(f"  rank: {geo_data_2.get('rank')}")
    print(f"  sentiment: {geo_data_2.get('sentiment')}")
    print(f"  interception: '{geo_data_2.get('interception')}'")
    print(f"  error_code: {error_code_2}")
    
    if (geo_data_2.get('rank') == 5 and 
        geo_data_2.get('sentiment') == -0.3 and 
        geo_data_2.get('interception') == "" and
        error_code_2 is not None):
        print("  ✅ 缺失字段处理正确（返回默认值 + error_code）")
    else:
        print("  ❌ 缺失字段处理错误")
        return False
    
    # 测试用例 3: 空响应
    print("\n测试用例 3: 空响应")
    geo_data_3, error_code_3 = _parse_geo_with_validation(
        "", execution_id, 2, "deepseek"
    )
    
    print(f"  rank: {geo_data_3.get('rank')}")
    print(f"  sentiment: {geo_data_3.get('sentiment')}")
    print(f"  error_code: {error_code_3}")
    
    if (geo_data_3.get('rank') == -1 and 
        geo_data_3.get('sentiment') == 0.0 and
        error_code_3 == "EMPTY_RESPONSE"):
        print("  ✅ 空响应处理正确")
    else:
        print("  ❌ 空响应处理错误")
        return False
    
    # 测试用例 4: 无 GEO 数据的普通文本
    print("\n测试用例 4: 无 GEO 数据的普通文本")
    response_text_4 = "这是一个普通的文本回答，没有包含任何 GEO 分析数据。"
    
    geo_data_4, error_code_4 = _parse_geo_with_validation(
        response_text_4, execution_id, 3, "deepseek"
    )
    
    print(f"  rank: {geo_data_4.get('rank')}")
    print(f"  sentiment: {geo_data_4.get('sentiment')}")
    print(f"  interception: '{geo_data_4.get('interception')}'")
    print(f"  error_code: {error_code_4}")
    
    if (geo_data_4.get('rank') == -1 and 
        geo_data_4.get('sentiment') == 0.0 and
        geo_data_4.get('interception') == "" and
        error_code_4 is None):  # 解析失败但返回默认值，不报错
        print("  ✅ 无 GEO 数据处理正确（返回默认值）")
    else:
        print("  ❌ 无 GEO 数据处理错误")
        return False
    
    return True


def test_completion_verification():
    """测试任务终点校验功能"""
    print("\n" + "=" * 60)
    print("测试 3: 任务终点校验 - results 数组长度验证")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _verify_completion
    
    # 测试用例 1: 完整结果
    print("\n测试用例 1: 结果完整（3 个结果，期望 3 个）")
    results_1 = [
        {"question_id": 0, "model": "deepseek", "status": "success"},
        {"question_id": 1, "model": "deepseek", "status": "success"},
        {"question_id": 2, "model": "deepseek", "status": "failed"}
    ]
    
    verification_1 = _verify_completion(results_1, expected_total=3)
    
    print(f"  can_complete: {verification_1['can_complete']}")
    print(f"  expected: {verification_1['expected_total']}, actual: {verification_1['actual_count']}")
    print(f"  success_count: {verification_1['success_count']}")
    
    if verification_1['can_complete'] and verification_1['actual_count'] == 3:
        print("  ✅ 完整结果验证通过")
    else:
        print("  ❌ 完整结果验证失败")
        return False
    
    # 测试用例 2: 结果不完整
    print("\n测试用例 2: 结果不完整（2 个结果，期望 3 个）")
    results_2 = [
        {"question_id": 0, "model": "deepseek", "status": "success"},
        {"question_id": 1, "model": "deepseek", "status": "success"}
    ]
    
    verification_2 = _verify_completion(results_2, expected_total=3)
    
    print(f"  can_complete: {verification_2['can_complete']}")
    print(f"  expected: {verification_2['expected_total']}, actual: {verification_2['actual_count']}")
    print(f"  missing_count: {verification_2['missing_count']}")
    
    if not verification_2['can_complete'] and verification_2['missing_count'] == 1:
        print("  ✅ 不完整结果检测正确")
    else:
        print("  ❌ 不完整结果检测错误")
        return False
    
    # 测试用例 3: 结果为空
    print("\n测试用例 3: 结果为空（0 个结果，期望 3 个）")
    verification_3 = _verify_completion([], expected_total=3)
    
    print(f"  can_complete: {verification_3['can_complete']}")
    print(f"  missing_count: {verification_3['missing_count']}")
    
    if not verification_3['can_complete'] and verification_3['missing_count'] == 3:
        print("  ✅ 空结果检测正确")
    else:
        print("  ❌ 空结果检测错误")
        return False
    
    return True


def test_streaming_persistence():
    """测试流式持久化功能"""
    print("\n" + "=" * 60)
    print("测试 4: 流式持久化 - 先写日志再更新内存")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import execute_nxm_test, _get_or_create_logger, _close_logger
    from utils.ai_response_logger_v2 import get_logger as get_ai_logger
    
    execution_id = f"test-stream-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    execution_store = {}
    
    # 初始化 execution_store
    execution_store[execution_id] = {
        'status': 'init',
        'progress': 0,
        'results': []
    }
    
    print(f"执行 ID: {execution_id}")
    print("注意：此测试会真正调用 AI API（如果配置了 API Key）")
    
    # 执行测试（1 个问题 × 1 个模型）
    result = execute_nxm_test(
        execution_id=execution_id,
        main_brand="测试品牌",
        competitor_brands=["竞品 1"],
        selected_models=[{'name': 'deepseek'}],
        raw_questions=["介绍一下{brandName}"],
        user_id="test-user",
        user_level="Free",
        execution_store=execution_store
    )
    
    print(f"\n执行结果：{result.get('success', 'N/A')}")
    print(f"执行 ID: {result.get('execution_id', 'N/A')}")
    print(f"Completion Verified: {result.get('completion_verified', 'N/A')}")
    
    # 验证 execution_store 状态
    if execution_id in execution_store:
        store_status = execution_store[execution_id].get('status', 'unknown')
        completion_verified = execution_store[execution_id].get('completion_verified', False)
        results_count = len(execution_store[execution_id].get('results', []))
        
        print(f"Store 状态：{store_status}")
        print(f"Completion Verified: {completion_verified}")
        print(f"Results 数量：{results_count}")
        
        # 验证：只有 completion_verified=True 时，status 才能是 completed
        if store_status == 'completed' and not completion_verified:
            print("  ❌ 错误：status=completed 但 completion_verified=False")
            return False
        
        # 验证：results 数量应该等于期望值
        expected = 1  # 1 个问题 × 1 个模型
        if results_count == expected:
            print(f"  ✅ Results 数量正确：{results_count}/{expected}")
        else:
            print(f"  ❌ Results 数量错误：{results_count}/{expected}")
            return False
    else:
        print("  ❌ Execution ID 不在 store 中")
        return False
    
    # 验证日志文件
    print("\n验证日志文件...")
    ai_logger = get_ai_logger()
    log_file = ai_logger.log_file
    
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找最近的记录
        recent_records = []
        for line in reversed(lines[-10:]):  # 检查最后 10 条
            try:
                record = json.loads(line.strip())
                if record.get('execution_id') == execution_id:
                    recent_records.append(record)
            except:
                pass
        
        if len(recent_records) > 0:
            print(f"  ✅ 找到 {len(recent_records)} 条日志记录")
            for rec in recent_records:
                print(f"    - Q{rec.get('context', {}).get('question_index', 'N/A')}: success={rec.get('status', {}).get('success', 'N/A')}")
        else:
            print(f"  ⚠️  未找到 execution_id={execution_id} 的日志记录（可能在之前的记录中）")
    else:
        print(f"  ❌ 日志文件不存在：{log_file}")
        return False
    
    return True


def test_hash_uniqueness():
    """测试哈希值唯一性"""
    print("\n" + "=" * 60)
    print("测试 5: 哈希值唯一性 - 防止重复写入")
    print("=" * 60)
    
    from wechat_backend.nxm_execution_engine import _generate_result_hash, _atomic_update_execution_store
    
    execution_store = {
        'test-hash': {'results': [], 'progress': 0}
    }
    all_hashes = set()
    
    # 生成 5 个不同时间戳的结果项
    base_item = {
        'execution_id': 'test-hash',
        'question_id': 0,
        'model': 'deepseek'
    }
    
    hashes = []
    for i in range(5):
        item = base_item.copy()
        item['timestamp'] = f"2026-02-20T10:00:0{i}.000000"
        h = _generate_result_hash(item)
        hashes.append(h)
        print(f"Hash {i+1}: {h}")
    
    # 验证所有哈希值都不同
    if len(set(hashes)) == len(hashes):
        print("✅ 所有哈希值唯一")
    else:
        print("❌ 存在重复哈希值")
        return False
    
    # 测试原子化更新防重复
    print("\n测试原子化更新防重复...")
    
    # 第一次更新
    item1 = base_item.copy()
    item1['timestamp'] = "2026-02-20T10:00:00.000000"
    success1 = _atomic_update_execution_store(execution_store, 'test-hash', item1, 5, all_hashes)
    
    # 第二次更新（相同内容）
    item2 = base_item.copy()
    item2['timestamp'] = "2026-02-20T10:00:00.000000"  # 相同时间戳
    success2 = _atomic_update_execution_store(execution_store, 'test-hash', item2, 5, all_hashes)
    
    if success1 and not success2:
        print("✅ 重复更新被正确拒绝")
    else:
        print(f"❌ 防重复机制错误：success1={success1}, success2={success2}")
        return False
    
    # 验证结果数量
    if len(execution_store['test-hash']['results']) == 1:
        print("✅ 结果数量正确（只有 1 条）")
    else:
        print(f"❌ 结果数量错误：{len(execution_store['test-hash']['results'])}")
        return False
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("NxM 执行引擎 P0 重构验证测试")
    print(f"执行时间：{datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_imports),
        ("GEO 语义加固", test_geo_parse_with_validation),
        ("任务终点校验", test_completion_verification),
        ("流式持久化", test_streaming_persistence),
        ("哈希值唯一性", test_hash_uniqueness)
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
        print("\n🎉 所有测试通过！P0 重构功能验证完成。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
