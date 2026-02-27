#!/usr/bin/env python3
"""
BUG-NEW-001 修复脚本：setInterval + async 并发问题

使用方法:
python3 fix_bug_new_001.py
"""

import re
from pathlib import Path

file_path = Path(__file__).parent / 'services' / 'brandTestService.js'

print("="*70)
print("BUG-NEW-001 修复：setInterval + async 并发问题")
print("="*70)
print()

if not file_path.exists():
    print(f"❌ 文件不存在：{file_path}")
    exit(1)

print(f"📄 读取文件：{file_path}")
content = file_path.read_text(encoding='utf-8')

# 查找 setInterval 模式
old_pattern = r'    // 启动定时轮询\n    pollInterval = setInterval\(async \(\) => \{'

if old_pattern in content:
    print("✅ 找到需要修复的代码")
    
    # 读取完整文件，找到 createPollingController 函数
    lines = content.split('\n')
    
    # 找到 setInterval 行
    start_line = -1
    for i, line in enumerate(lines):
        if 'pollInterval = setInterval(async () => {' in line:
            start_line = i
            break
    
    if start_line == -1:
        print("❌ 未找到 setInterval 代码")
        exit(1)
    
    print(f"📍 setInterval 在第 {start_line + 1} 行")
    
    # 找到对应的结束位置（需要匹配括号）
    brace_count = 0
    end_line = -1
    in_setinterval = False
    
    for i in range(start_line, len(lines)):
        line = lines[i]
        
        if 'setInterval(async () => {' in line:
            in_setinterval = True
            brace_count = 1
            continue
        
        if in_setinterval:
            brace_count += line.count('{') - line.count('}')
            
            if brace_count == 0:
                end_line = i
                break
    
    if end_line == -1:
        print("❌ 未找到 setInterval 结束位置")
        exit(1)
    
    print(f"📍 setInterval 结束在第 {end_line + 1} 行")
    
    # 创建新的轮询逻辑
    new_poll_function = '''    // 启动定时轮询 - BUG-NEW-001 修复：改用递归 setTimeout 避免并发请求
    let pollTimeout = null;
    
    const poll = async () => {
      // 超时检查
      if (Date.now() - startTime > maxDuration) {
        stop();
        logger.error('轮询超时 (总超时 10 分钟)');
        if (onError) onError(new Error('诊断超时，请重试或联系管理员'));
        return;
      }

      // P0 修复：无进度超时检查
      if (Date.now() - lastProgressTime > noProgressTimeout) {
        stop();
        logger.error('轮询超时 (8 分钟无进度更新)');
        if (onError) onError(new Error('诊断超时，长时间无响应，请重试'));
        return;
      }

      // 已停止检查
      if (isStopped) {
        return;
      }

      try {
        const res = await getTaskStatusApi(executionId);

        if (res && (res.progress !== undefined || res.stage)) {
          const parsedStatus = parseTaskStatus(res);

          // P0 修复：更新最后进度时间
          if (parsedStatus.progress > 0 || parsedStatus.stage !== 'init') {
            lastProgressTime = Date.now();
          }

          // OPT-003 性能优化：动态调整轮询间隔
          const newInterval = getPollingInterval(parsedStatus.progress, parsedStatus.stage);
          if (newInterval !== interval) {
            interval = newInterval;
            logger.debug(`[性能优化] 调整轮询间隔：${interval}ms (进度：${parsedStatus.progress}%)`);
          }

          if (onProgress) {
            onProgress(parsedStatus);
          }

          // 终止条件
          if (parsedStatus.stage === 'completed' || parsedStatus.stage === 'failed') {
            stop();

            if (parsedStatus.stage === 'completed' && onComplete) {
              onComplete(parsedStatus);
            } else if (parsedStatus.stage === 'failed' && onError) {
              onError(new Error(parsedStatus.error || '诊断失败'));
            }
            return;
          }
        } else {
          logger.warn('获取任务状态返回空数据，继续轮询');
        }
      } catch (err) {
        logger.error('轮询异常:', err);

        // P1-2 修复：完善错误分类和处理
        const errorInfo = {
          originalError: err,
          statusCode: err.statusCode,
          isAuthError: err.isAuthError || err.statusCode === 403 || err.statusCode === 401,
          isNetworkError: err.errMsg && err.errMsg.includes('request:fail'),
          isTimeout: err.message && err.message.includes('timeout'),
          timestamp: Date.now()
        };

        // Step 1: 403/401 错误熔断机制
        if (errorInfo.isAuthError) {
          consecutiveAuthErrors++;
          logger.error(`认证错误计数：${consecutiveAuthErrors}/${MAX_AUTH_ERRORS}`);

          if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
            stop();
            logger.error('认证错误熔断，停止轮询');
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        } else {
          // 非认证错误，重置计数器
          consecutiveAuthErrors = 0;

          // P1-2 修复：网络错误和超时错误给予更友好的提示
          if (errorInfo.isNetworkError) {
            logger.warn('网络连接异常，请检查网络设置');
          } else if (errorInfo.isTimeout) {
            logger.warn('请求超时，服务器响应缓慢');
          }
        }

        if (onError) {
          const userFriendlyError = createUserFriendlyError(errorInfo);
          onError(userFriendlyError);
        }
      } finally {
        // BUG-NEW-001 关键修复：使用 setTimeout 递归调用，确保前一个请求完成后再发起下一个
        if (!isStopped) {
          pollTimeout = setTimeout(poll, interval);
        }
      }
    };
    
    // 启动第一次轮询
    poll();
    
    // 更新 stop 函数，同时清除 interval 和 timeout
    const originalStop = stop;
    stop = () => {
      if (pollTimeout) {
        clearTimeout(pollTimeout);
        pollTimeout = null;
      }
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      isStopped = true;
    };'''
    
    # 替换代码
    new_lines = lines[:start_line] + [new_poll_function] + lines[end_line+1:]
    new_content = '\n'.join(new_lines)
    
    # 写回文件
    file_path.write_text(new_content, encoding='utf-8')
    
    print("✅ 修复成功！")
    print()
    print("📝 修复内容:")
    print("  - setInterval 改为递归 setTimeout")
    print("  - 避免 async 导致的并发请求问题")
    print("  - 添加 finally 确保下次轮询在前一个完成后发起")
    print("  - 更新 stop 函数同时清除 interval 和 timeout")
    print()
    print("✅ 请运行以下命令验证:")
    print("  node -c services/brandTestService.js")
    
else:
    print("⚠️  未找到需要修复的代码，可能已修复或代码已变更")

print()
print("="*70)
