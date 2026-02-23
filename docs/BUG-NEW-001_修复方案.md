# BUG-NEW-001 修复方案

## 问题描述

**当前代码** (brandTestService.js:204):
```javascript
pollInterval = setInterval(async () => {
  // ❌ 问题：setInterval 不会等待 async 函数完成
  // ❌ 可能导致并发请求
  try {
    const res = await getTaskStatusApi(executionId);
    // 处理响应...
  } catch (err) {
    // 处理错误...
  }
}, interval);
```

**问题**:
1. setInterval 每 interval 毫秒触发一次，不管 async 函数是否完成
2. 如果 API 调用耗时 > interval，会导致并发请求
3. 可能导致请求堆积、资源浪费、数据不一致

---

## 修复方案

**修复后代码**:
```javascript
// BUG-NEW-001 修复：改用递归 setTimeout 避免并发请求
let pollTimeout = null;

const poll = async () => {
  try {
    // 超时检查
    if (Date.now() - startTime > maxDuration) {
      stop();
      console.error('轮询超时 (总超时 10 分钟)');
      if (onError) onError(new Error('诊断超时，请重试或联系管理员'));
      return;
    }

    // 无进度超时检查
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

    // 发起请求
    const res = await getTaskStatusApi(executionId);

    if (res && (res.progress !== undefined || res.stage)) {
      const parsedStatus = parseTaskStatus(res);

      // 更新最后进度时间
      if (parsedStatus.progress > 0 || parsedStatus.stage !== 'init') {
        lastProgressTime = Date.now();
      }

      // 动态调整轮询间隔
      const newInterval = getPollingInterval(parsedStatus.progress, parsedStatus.stage);
      if (newInterval !== interval) {
        interval = newInterval;
        console.log(`[性能优化] 调整轮询间隔：${interval}ms (进度：${parsedStatus.progress}%)`);
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
    }
  } catch (err) {
    console.error('轮询异常:', err);
    // ... 错误处理 ...
    if (onError) {
      const userFriendlyError = createUserFriendlyError(err);
      onError(userFriendlyError);
    }
  } finally {
    // ✅ BUG-NEW-001 关键修复：使用 setTimeout 递归调用
    // ✅ 确保前一个请求完成后再发起下一个
    if (!isStopped) {
      pollTimeout = setTimeout(poll, interval);
    }
  }
};

// 启动第一次轮询
poll();

// 更新 stop 函数
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
};
```

---

## 修复效果

**修复前**:
- ❌ setInterval + async 导致并发请求
- ❌ 如果 API 耗时 5 秒，interval 800ms，会有 6 个并发请求
- ❌ 请求堆积，资源浪费

**修复后**:
- ✅ setTimeout 递归调用，确保串行执行
- ✅ 前一个请求完成后才发起下一个
- ✅ 无并发问题，资源合理利用

---

## 手动修复步骤

1. 打开 `services/brandTestService.js`
2. 找到第 204 行：`pollInterval = setInterval(async () => {`
3. 替换整个 setInterval 块为上述递归 setTimeout 代码
4. 保存文件
5. 运行 `node -c services/brandTestService.js` 验证语法
6. 提交代码

---

**预计修复时间**: 10 分钟
**影响范围**: 仅 brandTestService.js
**风险等级**: 低（逻辑等价替换）
