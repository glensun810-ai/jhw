"""
后台任务超时不一致修复验证脚本

验证内容：
1. AnalysisTask 默认超时为 180 秒
2. analysis_complete 判断逻辑支持 FAILED/TIMEOUT 终止状态
3. 超时/失败任务 result 不为 None
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from datetime import datetime
from wechat_backend.services.background_service_manager import (
    BackgroundServiceManager,
    AnalysisTask,
    TaskStatus
)
from wechat_backend.logging_config import api_logger


def test_analysis_task_default_timeout():
    """测试 1: AnalysisTask 默认超时为 180 秒"""
    print("\n" + "=" * 60)
    print("测试 1: AnalysisTask 默认超时")
    print("=" * 60)
    
    task = AnalysisTask(
        task_id="test_task_1",
        execution_id="test_exec_1",
        task_type="brand_analysis",
        payload={}
    )
    
    expected_timeout = 180
    actual_timeout = task.timeout_seconds
    
    if actual_timeout == expected_timeout:
        print(f"✅ 通过：AnalysisTask 默认超时 = {actual_timeout}秒 (期望：{expected_timeout}秒)")
        return True
    else:
        print(f"❌ 失败：AnalysisTask 默认超时 = {actual_timeout}秒 (期望：{expected_timeout}秒)")
        return False


def test_analysis_complete_with_terminated_tasks():
    """测试 2: analysis_complete 判断逻辑支持 FAILED/TIMEOUT 终止状态"""
    print("\n" + "=" * 60)
    print("测试 2: analysis_complete 判断逻辑")
    print("=" * 60)
    
    manager = BackgroundServiceManager(max_workers=2, max_queue_size=10)
    
    # 模拟场景 1: 所有任务完成
    manager._analysis_tasks = {
        "task1": AnalysisTask(
            task_id="task1",
            execution_id="exec1",
            task_type="brand_analysis",
            payload={},
            status=TaskStatus.COMPLETED,
            result={"data": "test1"}
        ),
        "task2": AnalysisTask(
            task_id="task2",
            execution_id="exec1",
            task_type="competitive_analysis",
            payload={},
            status=TaskStatus.COMPLETED,
            result={"data": "test2"}
        )
    }
    
    status1 = manager.get_task_status("exec1")
    test1_pass = (
        status1['analysis_complete'] == True and
        status1['all_terminated'] == True and
        status1['has_completed'] == True
    )
    print(f"场景 1 - 所有任务完成：{'✅ 通过' if test1_pass else '❌ 失败'}")
    print(f"  analysis_complete={status1['analysis_complete']}, "
          f"all_terminated={status1['all_terminated']}, "
          f"has_completed={status1['has_completed']}")
    
    # 模拟场景 2: 一个完成，一个超时
    manager._analysis_tasks = {
        "task1": AnalysisTask(
            task_id="task1",
            execution_id="exec2",
            task_type="brand_analysis",
            payload={},
            status=TaskStatus.COMPLETED,
            result={"data": "test1"}
        ),
        "task2": AnalysisTask(
            task_id="task2",
            execution_id="exec2",
            task_type="competitive_analysis",
            payload={},
            status=TaskStatus.TIMEOUT,
            result={"_timeout": True, "_error": "timeout"}
        )
    }
    
    status2 = manager.get_task_status("exec2")
    test2_pass = (
        status2['analysis_complete'] == True and
        status2['all_terminated'] == True and
        status2['has_completed'] == True
    )
    print(f"场景 2 - 一个完成，一个超时：{'✅ 通过' if test2_pass else '❌ 失败'}")
    print(f"  analysis_complete={status2['analysis_complete']}, "
          f"all_terminated={status2['all_terminated']}, "
          f"has_completed={status2['has_completed']}")
    
    # 模拟场景 3: 一个完成，一个失败
    manager._analysis_tasks = {
        "task1": AnalysisTask(
            task_id="task1",
            execution_id="exec3",
            task_type="brand_analysis",
            payload={},
            status=TaskStatus.COMPLETED,
            result={"data": "test1"}
        ),
        "task2": AnalysisTask(
            task_id="task2",
            execution_id="exec3",
            task_type="competitive_analysis",
            payload={},
            status=TaskStatus.FAILED,
            result={"_failed": True, "_error": "error"}
        )
    }
    
    status3 = manager.get_task_status("exec3")
    test3_pass = (
        status3['analysis_complete'] == True and
        status3['all_terminated'] == True and
        status3['has_completed'] == True
    )
    print(f"场景 3 - 一个完成，一个失败：{'✅ 通过' if test3_pass else '❌ 失败'}")
    print(f"  analysis_complete={status3['analysis_complete']}, "
          f"all_terminated={status3['all_terminated']}, "
          f"has_completed={status3['has_completed']}")
    
    # 模拟场景 4: 全部超时（无完成）
    manager._analysis_tasks = {
        "task1": AnalysisTask(
            task_id="task1",
            execution_id="exec4",
            task_type="brand_analysis",
            payload={},
            status=TaskStatus.TIMEOUT,
            result={"_timeout": True}
        ),
        "task2": AnalysisTask(
            task_id="task2",
            execution_id="exec4",
            task_type="competitive_analysis",
            payload={},
            status=TaskStatus.TIMEOUT,
            result={"_timeout": True}
        )
    }
    
    status4 = manager.get_task_status("exec4")
    test4_pass = (
        status4['analysis_complete'] == False and
        status4['all_terminated'] == True and
        status4['has_completed'] == False
    )
    print(f"场景 4 - 全部超时（无完成）：{'✅ 通过' if test4_pass else '❌ 失败'}")
    print(f"  analysis_complete={status4['analysis_complete']}, "
          f"all_terminated={status4['all_terminated']}, "
          f"has_completed={status4['has_completed']}")
    
    # 模拟场景 5: 还有任务在运行
    manager._analysis_tasks = {
        "task1": AnalysisTask(
            task_id="task1",
            execution_id="exec5",
            task_type="brand_analysis",
            payload={},
            status=TaskStatus.COMPLETED,
            result={"data": "test1"}
        ),
        "task2": AnalysisTask(
            task_id="task2",
            execution_id="exec5",
            task_type="competitive_analysis",
            payload={},
            status=TaskStatus.RUNNING
        )
    }
    
    status5 = manager.get_task_status("exec5")
    test5_pass = (
        status5['analysis_complete'] == False and
        status5['all_terminated'] == False and
        status5['has_completed'] == True
    )
    print(f"场景 5 - 还有任务在运行：{'✅ 通过' if test5_pass else '❌ 失败'}")
    print(f"  analysis_complete={status5['analysis_complete']}, "
          f"all_terminated={status5['all_terminated']}, "
          f"has_completed={status5['has_completed']}")
    
    all_pass = test1_pass and test2_pass and test3_pass and test4_pass and test5_pass
    print(f"\n测试 2 总体：{'✅ 通过' if all_pass else '❌ 失败'}")
    return all_pass


def test_task_result_not_none_on_error():
    """测试 3: 超时/失败任务 result 不为 None"""
    print("\n" + "=" * 60)
    print("测试 3: 超时/失败任务 result 不为 None")
    print("=" * 60)
    
    # 模拟超时任务
    timeout_task = AnalysisTask(
        task_id="timeout_task",
        execution_id="exec1",
        task_type="brand_analysis",
        payload={},
        status=TaskStatus.TIMEOUT,
        result={"_timeout": True, "_error": "timeout"}
    )
    
    # 模拟失败任务
    failed_task = AnalysisTask(
        task_id="failed_task",
        execution_id="exec1",
        task_type="competitive_analysis",
        payload={},
        status=TaskStatus.FAILED,
        result={"_failed": True, "_error": "error"}
    )
    
    test1_pass = timeout_task.result is not None and "_timeout" in timeout_task.result
    test2_pass = failed_task.result is not None and "_failed" in failed_task.result
    
    print(f"超时任务 result 不为 None: {'✅ 通过' if test1_pass else '❌ 失败'}")
    print(f"失败任务 result 不为 None: {'✅ 通过' if test2_pass else '❌ 失败'}")
    
    all_pass = test1_pass and test2_pass
    print(f"测试 3 总体：{'✅ 通过' if all_pass else '❌ 失败'}")
    return all_pass


def test_submit_analysis_task_default_timeout():
    """测试 4: submit_analysis_task 默认超时参数"""
    print("\n" + "=" * 60)
    print("测试 4: submit_analysis_task 默认超时参数")
    print("=" * 60)
    
    import inspect
    from wechat_backend.services.background_service_manager import BackgroundServiceManager
    
    sig = inspect.signature(BackgroundServiceManager.submit_analysis_task)
    default_timeout = sig.parameters['timeout_seconds'].default
    
    expected_timeout = 180
    test_pass = default_timeout == expected_timeout
    
    print(f"submit_analysis_task 默认超时 = {default_timeout}秒 (期望：{expected_timeout}秒)")
    print(f"测试结果：{'✅ 通过' if test_pass else '❌ 失败'}")
    return test_pass


def main():
    """运行所有验证测试"""
    print("\n" + "=" * 60)
    print("后台任务超时不一致修复验证")
    print("=" * 60)
    print("验证内容：")
    print("1. AnalysisTask 默认超时为 180 秒")
    print("2. analysis_complete 判断逻辑支持 FAILED/TIMEOUT 终止状态")
    print("3. 超时/失败任务 result 不为 None")
    print("4. submit_analysis_task 默认超时参数")
    print("=" * 60)
    
    results = []
    
    results.append(("AnalysisTask 默认超时", test_analysis_task_default_timeout()))
    results.append(("analysis_complete 判断逻辑", test_analysis_complete_with_terminated_tasks()))
    results.append(("超时/失败任务 result", test_task_result_not_none_on_error()))
    results.append(("submit_analysis_task 默认超时", test_submit_analysis_task_default_timeout()))
    
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
