#!/usr/bin/env python3
"""
在 run_async_test 函数成功路径中添加计时器取消逻辑
"""

file_path = 'backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 SSE 通知发送后添加计时器取消
old_sse = """                    except Exception as sse_err:
                        api_logger.error(f"[SSE] ⚠️ 通知发送失败：{sse_err}")

                except Exception as snapshot_err:"""

new_sse = """                    except Exception as sse_err:
                        api_logger.error(f"[SSE] ⚠️ 通知发送失败：{sse_err}")

                    # 【P1-T2 新增】任务完成，取消超时计时器
                    try:
                        timeout_manager.cancel_timer(execution_id)
                        api_logger.info(f"[超时管理] ✅ 计时器已取消：{execution_id}")
                    except Exception as timer_err:
                        api_logger.warning(f"[超时管理] 计时器取消失败：{timer_err}")

                except Exception as snapshot_err:"""

if old_sse in content:
    content = content.replace(old_sse, new_sse)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 成功添加成功路径的计时器取消代码")
else:
    print("⚠️ 未找到匹配位置")
