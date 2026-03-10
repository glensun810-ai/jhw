/**
 * 前端轮询与 WebSocket 修复补丁
 * 
 * 应用说明：将此补丁应用到对应文件
 * 
 * 修复内容：
 * 1. brandTestService.js - 单例模式 + 最小轮询间隔
 * 2. webSocketClient.js - 降级前清理（已应用）
 */

// ==================== brandTestService.js 补丁 ====================

// 在第 318 行之后添加（startLegacyPolling 函数开头）：
/*
  // 【P0 关键修复 - 2026-03-05】单例模式：确保全局只有一个轮询控制器
  if (this.pollingInstance && this.pollingInstance.isActive) {
    console.warn('[brandTestService] ⚠️ 轮询已在运行中，跳过重复启动 (单例模式)');
    return this.pollingInstance;
  }
*/

// 在第 328 行之后添加（let pollInterval = null; 之后）：
/*
  let pollTimeout = null;  // 【P0 修复】添加 pollTimeout 声明
*/

// 在第 345 行之后添加（let lastLoggedProgress = -1; 之后）：
/*
  // 【P0 关键修复 - 2026-03-05】设置最小轮询间隔，防止过度请求
  const MIN_POLLING_INTERVAL = 1500; // 1.5 秒
*/

// 替换第 347-360 行的 controller 定义：
/*
  const controller = {
    isActive: true,  // 【P0 修复】添加 isActive 标志
    executionId,
    startTime,
    stop: () => {
      // 【P0 关键修复 - 2026-03-04】清除定时器，确保不会继续触发
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      if (pollTimeout) {
        clearTimeout(pollTimeout);
        pollTimeout = null;
      }
      isStopped = true;
      controller.isActive = false;  // 【P0 修复】设置非激活状态
      console.log('[brandTestService] 轮询已停止，总轮询次数:', pollCount);
    }
  };

  // 【P0 关键修复 - 2026-03-05】保存单例实例
  this.pollingInstance = controller;
*/

// 在第 370 行左右的 start 函数中修改：
/*
  const start = (interval = 800, immediate = true) => {
    // 【P0 修复】确保轮询间隔不小于最小值
    const safeInterval = Math.max(interval, MIN_POLLING_INTERVAL);
    console.log(`[轮询] 使用安全间隔：${safeInterval}ms (原始：${interval}ms)`);
    
    // P2 优化：立即触发第一次轮询
    if (immediate) {
      (async () => {
        // ... 原有逻辑 ...
      })();
    }
    
    // 在调度下一次轮询时使用 safeInterval
    pollTimeout = setTimeout(() => {
      if (!isStopped) {
        poll();
      }
    }, safeInterval);
  };
*/

// ==================== home.js 补丁 ====================

// 在第 45 行左右的 getTaskStatusApi 函数中，确保有最小间隔检查：
/*
const getTaskStatusApi = (executionId) => {
  const requestKey = `status_${executionId}`;

  if (pendingRequests.has(requestKey)) {
    console.warn(`[API] ⚠️ 重复请求被拦截：${requestKey}`);
    return pendingRequests.get(requestKey);
  }

  const apiUrl = `${API_ENDPOINTS.BRAND.STATUS}/${executionId}`;
  
  const requestPromise = get(apiUrl)
    .then(result => {
      pendingRequests.delete(requestKey);
      return result;
    })
    .catch(error => {
      pendingRequests.delete(requestKey);
      throw error;
    });

  pendingRequests.set(requestKey, requestPromise);
  return requestPromise;
};
*/

// ==================== 验证测试 ====================
/*
// 在小程序开发者工具控制台运行：

// 测试 1：单例模式
const service1 = require('./services/brandTestService');
const instance1 = service1.startLegacyPolling('test-123', () => {}, () => {}, () => {});
const instance2 = service1.startLegacyPolling('test-123', () => {}, () => {}, () => {});
console.assert(instance1 === instance2, '单例模式失败');
console.log('✅ 单例模式测试通过');

// 测试 2：WebSocket 清理
const wsClient = require('./miniprogram/services/webSocketClient').default;
wsClient.connect('test-123', {
  onFallback: () => {
    console.log('降级回调已调用');
    console.assert(wsClient.socket === null, 'WebSocket 未关闭');
    console.assert(wsClient.callbacks.onConnected === null, 'onConnected 未清空');
    console.log('✅ WebSocket 清理测试通过');
  }
});
// 模拟重连失败触发降级
wsClient.reconnectAttempts = wsClient.constructor.MAX_RECONNECT_ATTEMPTS;
wsClient._attemptReconnect();
*/
