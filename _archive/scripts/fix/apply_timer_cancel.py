#!/usr/bin/env python3
"""
在 run_async_test 函数中添加计时器取消逻辑
"""

file_path = 'backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在成功处理结束时添加计时器取消
old_success = """                api_logger.info(f"[状态同步 -4/4] ✅ SSE 消息已发送：{execution_id}")

            except Exception as state_err:
                api_logger.error(f"[M004] ⚠️ 状态更新失败：{execution_id}, 错误：{state_err}")"""

new_success = """                api_logger.info(f"[状态同步 -4/4] ✅ SSE 消息已发送：{execution_id}")

                # 【P1-T2 新增】任务完成，取消超时计时器
                try:
                    timeout_manager.cancel_timer(execution_id)
                    api_logger.info(f"[超时管理] ✅ 计时器已取消：{execution_id}")
                except Exception as timer_err:
                    api_logger.warning(f"[超时管理] 计时器取消失败：{timer_err}")

            except Exception as state_err:
                api_logger.error(f"[M004] ⚠️ 状态更新失败：{execution_id}, 错误：{state_err}")"""

if old_success in content:
    content = content.replace(old_success, new_success)
    print("✅ 成功添加成功路径的计时器取消代码")
else:
    print("⚠️ 未找到成功路径的匹配位置")

# 2. 在异常处理中添加计时器取消
old_exception = """            except Exception as state_err:
                api_logger.error(f"[异常处理] ⚠️ 数据库更新失败：{state_err}")
    thread = Thread(target=run_async_test)"""

new_exception = """            except Exception as state_err:
                api_logger.error(f"[异常处理] ⚠️ 数据库更新失败：{state_err}")
            
            # 【P1-T2 新增】异常处理完成，取消超时计时器
            try:
                timeout_manager.cancel_timer(execution_id)
                api_logger.info(f"[超时管理] ✅ 计时器已取消（异常处理）：{execution_id}")
            except Exception as timer_err:
                api_logger.warning(f"[超时管理] 计时器取消失败：{timer_err}")
    
    thread = Thread(target=run_async_test)"""

if old_exception in content:
    content = content.replace(old_exception, new_exception)
    print("✅ 成功添加异常路径的计时器取消代码")
else:
    print("⚠️ 未找到异常路径的匹配位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 计时器取消逻辑添加完成")
