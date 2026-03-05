#!/usr/bin/env python3
"""P1 修复补充 - 使用行处理方式"""

file_path = 'backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 在 save_brand_test_result 之前添加日志
    if 'save_brand_test_result(brand_test_result)' in line and 'api_logger.info' not in lines[i-1]:
        indent = ' ' * 12
        new_lines.append(f"{indent}api_logger.info(f\"[P1 数据持久化] 开始保存品牌测试结果：task_id={{task_id}}\")\n")
        new_lines.append(f"{indent}try:\n")
        new_lines.append(f"{indent}    {line.strip()}\n")
        new_lines.append(f"{indent}    api_logger.info(f\"[P1 数据持久化] ✅ 品牌测试结果已保存：task_id={{task_id}}\")\n")
        new_lines.append(f"{indent}except Exception as save_err:\n")
        new_lines.append(f"{indent}    api_logger.error(f\"[P1 数据持久化] ❌ 保存品牌测试结果失败：{{save_err}}\")\n")
        new_lines.append(f"{indent}    raise\n")
    # 更新异常处理
    elif 'api_logger.error(f"Async test execution failed: {e}")' in line:
        indent = ' ' * 12
        new_lines.append(f"{indent}import traceback\n")
        new_lines.append(f"{indent}error_details = traceback.format_exc()\n")
        new_lines.append(f"{indent}api_logger.error(f\"[P1 数据持久化] ❌ Async test execution failed: {{e}}\")\n")
        new_lines.append(f"{indent}api_logger.error(f\"[P1 数据持久化] 错误堆栈：{{error_details}}\")\n")
    elif 'update_task_stage(task_id, TaskStage.COMPLETED, 100, "任务已完成")' in line and 'api_logger.info' not in lines[i+1]:
        new_lines.append(line)
        indent = ' ' * 12
        new_lines.append(f"{indent}api_logger.info(f\"[P1 数据持久化] ✅ 任务已完成：task_id={{task_id}}\")\n")
    else:
        new_lines.append(line)
    
    i += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ P1 修复补充完成")
