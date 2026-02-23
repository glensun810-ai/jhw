#!/usr/bin/env node
/**
 * BUG-NEW-001 修复补丁：setInterval + async 并发问题
 * 
 * 使用方法:
 * node fix_setinterval_bug.js
 */

const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'services', 'brandTestService.js');

console.log('🔧 开始修复 BUG-NEW-001: setInterval + async 并发问题');
console.log(`📄 文件：${filePath}`);

let content = fs.readFileSync(filePath, 'utf-8');

// 查找并替换轮询逻辑
const oldPattern = /\/\/ 启动定时轮询\s+pollInterval = setInterval\(async \(\) => \{[\s\S]*?\}, interval\);/;

const newCode = `// 启动定时轮询 - BUG-NEW-001 修复：改用递归 setTimeout 避免并发请求
    let pollTimeout = null;
    
    const poll = async () => {
      // 超时检查
      if (Date.now() - startTime > maxDuration) {
        stop();
        console.error('轮询超时 (总超时 10 分钟)');
        if (onError) onError(new Error('诊断超时，请重试或联系管理员'));
        return;
      }

      // P0 修复：无进度超时检查
      if (Date.now() - lastProgressTime > noProgressTimeout) {
        stop();
        console.error('轮询超时 (8 分钟无进度更新)');
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
            console.log(\`[性能优化] 调整轮询间隔：\${interval}ms (进度：\${parsedStatus.progress}%)\`);
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
          console.warn('获取任务状态返回空数据，继续轮询');
        }
      } catch (err) {
        console.error('轮询异常:', err);

        // Step 1: 403/401 错误熔断机制
        if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
          consecutiveAuthErrors++;
          console.error(\`认证错误计数：\${consecutiveAuthErrors}/\${MAX_AUTH_ERRORS}\`);

          if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
            stop();
            console.error('认证错误熔断，停止轮询');
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        } else {
          // 非认证错误，重置计数器
          consecutiveAuthErrors = 0;
        }

        if (onError) {
          const userFriendlyError = createUserFriendlyError(err);
          onError(userFriendlyError);
        }
      } finally {
        // BUG-NEW-001 修复：使用 setTimeout 递归调用，确保前一个请求完成后再发起下一个
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
    };`;

if (oldPattern.test(content)) {
  content = content.replace(oldPattern, newCode);
  fs.writeFileSync(filePath, content, 'utf-8');
  console.log('✅ BUG-NEW-001 修复成功！');
  console.log('📝 修复内容:');
  console.log('  - setInterval 改为递归 setTimeout');
  console.log('  - 避免 async 导致的并发请求问题');
  console.log('  - 添加 finally 确保下次轮询在前一个完成后发起');
} else {
  console.log('⚠️  未找到匹配的代码模式，可能已修复或代码已变更');
}

console.log('\n✅ 修复完成！');
