#!/usr/bin/env python3
"""
为 perform_brand_test 函数添加全局超时保护
"""

file_path = 'backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到第 281 行（索引 280），在其后插入代码
# 第 281 行是：execution_id = str(uuid.uuid4())

insert_after_line = 280  # 0-indexed, 所以是第 281 行

timeout_code = """
    # 【P1-T2 新增】启动全局超时计时器（10 分钟）
    timeout_manager = TimeoutManager()
    
    def on_timeout(eid: str):
        \"\"\"超时回调：记录日志并标记任务超时\"\"\"
        api_logger.error(
            "global_timeout_triggered",
            extra={
                'event': 'global_timeout_triggered',
                'execution_id': eid,
                'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
            }
        )
        # 更新内存状态
        if eid in execution_store:
            execution_store[eid].update({
                'status': 'timeout',
                'stage': 'timeout',
                'progress': 100,
                'is_completed': True,
                'should_stop_polling': True,
                'error': f'诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）'
            })
        # 尝试更新数据库状态
        try:
            from wechat_backend.state_manager import get_state_manager
            state_manager = get_state_manager(execution_store)
            state_manager.update_state(
                execution_id=eid,
                status='timeout',
                stage='timeout',
                progress=100,
                is_completed=True,
                error_message=f'诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）',
                write_to_db=True,
                user_id=user_id or "anonymous",
                brand_name=main_brand,
                competitor_brands=competitor_brands if 'competitor_brands' in locals() else [],
                selected_models=selected_models,
                custom_questions=raw_questions if 'raw_questions' in locals() else []
            )
        except Exception as timeout_db_err:
            api_logger.error(f"[超时处理] 数据库状态更新失败：{timeout_db_err}")

    # 启动 10 分钟全局超时计时器
    timeout_manager.start_timer(
        execution_id=execution_id,
        on_timeout=on_timeout,
        timeout_seconds=TimeoutManager.MAX_EXECUTION_TIME
    )
    api_logger.info(
        "global_timeout_timer_started",
        extra={
            'event': 'global_timeout_timer_started',
            'execution_id': execution_id,
            'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
        }
    )

"""

# 插入代码
new_lines = lines[:insert_after_line + 1] + [timeout_code] + lines[insert_after_line + 1:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 成功添加全局超时保护代码")
print(f"   插入位置：第 {insert_after_line + 1} 行之后")
print(f"   原文件行数：{len(lines)}")
print(f"   新文件行数：{len(new_lines)}")
