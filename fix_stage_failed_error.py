#!/usr/bin/env python3
"""
修复前端轮询时后端返回 stage=failed 但 error=null 的问题

问题根因：
1. 后端 NxM 执行引擎在某个地方抛出异常
2. 异常被捕获后调用了 scheduler.fail_execution(error_message)
3. 但 error_message 可能为空
4. 前端收到 stage=failed 但 error=null，导致显示"诊断失败"

修复方案：
1. 确保 scheduler.fail_execution 总是有 error 消息
2. 确保 execution_store 中的 error 字段总是有值
3. 前端在 error 为空时显示更详细的调试信息
"""

import re

# ============================================================================
# 修复 1: nxm_scheduler.py - 确保 fail_execution 总是有 error 消息
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_scheduler.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_fail = '''    def fail_execution(self, error: str):
        """失败执行"""
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'failed'
                store['stage'] = 'failed'  # 【修复】同步 stage 与 status
                store['error'] = error
                store['end_time'] = datetime.now().isoformat()

        api_logger.error(f"[Scheduler] 执行失败：{self.execution_id}, 错误：{error}")'''

new_fail = '''    def fail_execution(self, error: str):
        """失败执行"""
        # 【P0 修复】确保 error 总是有值
        if not error or not error.strip():
            error = "执行失败，原因未知"
        
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'failed'
                store['stage'] = 'failed'  # 【修复】同步 stage 与 status
                store['error'] = error
                store['end_time'] = datetime.now().isoformat()

        api_logger.error(f"[Scheduler] 执行失败：{self.execution_id}, 错误：{error}")'''

content = content.replace(old_fail, new_fail)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复 1: nxm_scheduler.py - 确保 fail_execution 总是有 error 消息")

# ============================================================================
# 修复 2: 前端 brandTestService.js - 显示更详细的错误信息
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/services/brandTestService.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_error = '''          if (isCompleted && onComplete) {
            onComplete(parsedStatus);
          } else if (!isCompleted && onError) {
            onError(new Error(parsedStatus.error || '诊断失败'));
          }'''

new_error = '''          if (isCompleted && onComplete) {
            onComplete(parsedStatus);
          } else if (!isCompleted && onError) {
            // 【P0 修复】显示更详细的错误信息
            const errorMsg = parsedStatus.error || 
                            (parsedStatus.stage === 'failed' ? '任务执行失败（stage=failed）' : '诊断失败');
            
            logger.error('[brandTestService] 诊断失败详情:', {
              stage: parsedStatus.stage,
              status: parsedStatus.status,
              progress: parsedStatus.progress,
              is_completed: parsedStatus.is_completed,
              error: parsedStatus.error,
              results_count: parsedStatus.results?.length || 0,
              detailed_results_count: parsedStatus.detailed_results?.length || 0
            });
            
            onError(new Error(errorMsg));
          }'''

content = content.replace(old_error, new_error)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复 2: brandTestService.js - 显示更详细的错误信息")

print("\n" + "="*80)
print("修复完成！请重启后端并重新编译前端")
print("="*80)
print("\n修复内容:")
print("1. ✅ nxm_scheduler.py - 确保 fail_execution 总是有 error 消息")
print("2. ✅ brandTestService.js - 显示更详细的错误信息")
print("\n下一步:")
print("1. 重启后端服务")
print("2. 清除前端缓存并重新编译")
print("3. 测试诊断功能")
print("4. 如果仍然失败，查看控制台详细日志")
