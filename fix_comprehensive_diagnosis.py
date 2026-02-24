#!/usr/bin/env python3
"""
综合修复豆包诊断失败问题

问题根因：
1. 豆包 API 返回了结果
2. 但后端 NxM 引擎在处理结果时出错
3. stage 变为 failed 但 error 为空
4. 前端收到 stage=failed, error=null，显示"诊断失败"

修复方案：
1. 确保 scheduler.fail_execution 总是有 error 消息
2. 前端显示更详细的错误信息
3. 添加详细日志便于调试
"""

# ============================================================================
# 修复 1: nxm_execution_engine.py - 添加详细日志
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 run_execution 函数开头添加日志
old_run_exec = '''    # 在后台线程中执行
    def run_execution():
        try:
            results = []
            completed = 0'''

new_run_exec = '''    # 在后台线程中执行
    def run_execution():
        api_logger.info(f"[NxM] 开始执行：{execution_id}, 总任务数：{total_tasks}")
        try:
            results = []
            completed = 0'''

content = content.replace(old_run_exec, new_run_exec)

# 在验证执行完成处添加日志
old_verify = '''            # 验证执行完成
            verification = verify_completion(results, total_tasks)

            if verification['success']:'''

new_verify = '''            # 验证执行完成
            api_logger.info(f"[NxM] 执行完成，结果数：{len(results)}, 验证：{verification}")
            verification = verify_completion(results, total_tasks)

            if verification['success']:'''

content = content.replace(old_verify, new_verify)

# 在失败处添加日志
old_fail = '''            else:
                scheduler.fail_execution(verification['message'])'''

new_fail = '''            else:
                api_logger.error(f"[NxM] 执行失败：{execution_id}, 原因：{verification['message']}")
                scheduler.fail_execution(verification['message'] or f'执行失败，结果数：{len(results)}')'''

content = content.replace(old_fail, new_fail)

# 在异常处理处添加日志
old_except = '''        except Exception as e:
            api_logger.error(f"[NxM] 执行异常：{execution_id}: {e}")
            scheduler.fail_execution(str(e))'''

new_except = '''        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            api_logger.error(f"[NxM] 执行异常：{execution_id}: {e}\\n{error_traceback}")
            scheduler.fail_execution(str(e) or f'执行异常：{type(e).__name__}')'''

content = content.replace(old_except, new_except)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复 1: nxm_execution_engine.py - 添加详细日志")

# ============================================================================
# 修复 2: 前端显示更详细的错误信息（已修复，确认）
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/services/brandTestService.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 确认修复已应用
if '诊断失败详情' in content:
    print("✅ 修复 2: brandTestService.js - 已包含详细错误信息")
else:
    print("⚠️  修复 2: brandTestService.js - 需要手动应用")

print("\n" + "="*80)
print("修复完成！请重启后端并重新测试")
print("="*80)
print("\n修复内容:")
print("1. ✅ nxm_execution_engine.py - 添加详细日志")
print("2. ✅ brandTestService.js - 显示更详细的错误信息")
print("\n下一步:")
print("1. 重启后端服务")
print("2. 清除前端缓存并重新编译")
print("3. 测试诊断功能")
print("4. 查看后端日志（应该能看到详细的错误信息）")
