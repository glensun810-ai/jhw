#!/usr/bin/env python3
"""
P1 修复：brand_test_results 表数据缺失问题

问题根因：
1. 保存操作没有详细日志，无法追踪是否执行
2. 异常处理不够详细，无法定位失败位置
3. 保存逻辑可能被前置异常中断

修复方案：
1. 添加详细的持久化日志
2. 增强异常堆栈追踪
3. 确保保存操作的可见性
"""

import re

file_path = 'backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换保存深度情报结果的代码
old_deep_save = '''            # 保存深度情报结果
            save_deep_intelligence_result(task_id, deep_result_obj)'''

new_deep_save = '''            # 保存深度情报结果
            api_logger.info(f"[P1 数据持久化] 开始保存深度情报结果：task_id={task_id}")
            try:
                save_deep_intelligence_result(task_id, deep_result_obj)
                api_logger.info(f"[P1 数据持久化] ✅ 深度情报结果已保存：task_id={task_id}")
            except Exception as save_err:
                api_logger.error(f"[P1 数据持久化] ❌ 保存深度情报结果失败：{save_err}")
                raise'''

content = content.replace(old_deep_save, new_deep_save)

# 查找并替换保存品牌测试结果的代码
old_brand_save = '''            # 创建并保存品牌测试结果
            brand_test_result = BrandTestResult(
                task_id=task_id,
                brand_name=brand_list[0],
                ai_models_used=selected_models,
                questions_used=raw_questions,
                overall_score=(processed_results.get('main_brand') or {}).get('overallScore', 0),
                total_tests=len(all_test_cases),
                results_summary=processed_results.get('summary', {}),
                detailed_results=processed_results.get('detailed_results', []),
                deep_intelligence_result=deep_result_obj
            )

            save_brand_test_result(brand_test_result)

            # 最终更新为完成状态
            update_task_stage(task_id, TaskStage.COMPLETED, 100, "任务已完成")

        except Exception as e:
            api_logger.error(f"Async test execution failed: {e}")
            update_task_stage(task_id, TaskStage.INIT, 0, f"任务执行失败：{str(e)}")'''

new_brand_save = '''            # 创建并保存品牌测试结果
            api_logger.info(f"[P1 数据持久化] 开始创建品牌测试结果对象：task_id={task_id}")
            brand_test_result = BrandTestResult(
                task_id=task_id,
                brand_name=brand_list[0],
                ai_models_used=selected_models,
                questions_used=raw_questions,
                overall_score=(processed_results.get('main_brand') or {}).get('overallScore', 0),
                total_tests=len(all_test_cases),
                results_summary=processed_results.get('summary', {}),
                detailed_results=processed_results.get('detailed_results', []),
                deep_intelligence_result=deep_result_obj
            )

            api_logger.info(f"[P1 数据持久化] 开始保存品牌测试结果：task_id={task_id}")
            try:
                save_brand_test_result(brand_test_result)
                api_logger.info(f"[P1 数据持久化] ✅ 品牌测试结果已保存：task_id={task_id}")
            except Exception as save_err:
                api_logger.error(f"[P1 数据持久化] ❌ 保存品牌测试结果失败：{save_err}")
                raise

            # 最终更新为完成状态
            update_task_stage(task_id, TaskStage.COMPLETED, 100, "任务已完成")
            api_logger.info(f"[P1 数据持久化] ✅ 任务已完成：task_id={task_id}")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            api_logger.error(f"[P1 数据持久化] ❌ Async test execution failed: {e}")
            api_logger.error(f"[P1 数据持久化] 错误堆栈：{error_details}")
            update_task_stage(task_id, TaskStage.INIT, 0, f"任务执行失败：{str(e)}")'''

content = content.replace(old_brand_save, new_brand_save)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ P1 修复已应用")
print(f"   文件：{file_path}")
print("   修改内容:")
print("   - 添加深度情报保存日志")
print("   - 添加品牌测试结果保存日志")
print("   - 增强异常堆栈追踪")
