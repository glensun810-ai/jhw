/**
 * P0 关键修复 - 前端轮询重叠问题修复补丁
 * 
 * 问题描述：
 * 1. 前端日志显示在同一个秒数内发起了多次相同的请求
 * 2. 这会增加服务器负担，如果后端有数据库锁，密集的轮询会加剧"假死"现象
 * 
 * 修复方案：
 * 1. 添加 isPollingInProgress 标志，防止轮询重叠
 * 2. 在 finally 块中重置标志，确保下次轮询可以正常进行
 * 3. 添加日志记录，便于调试
 * 
 * 使用方法：
 * 将以下代码中的关键修改应用到 brandTestService.js 的 startLegacyPolling 函数中
 */

// ========== 修改 1: 添加轮询重叠保护标志 ==========
// 在 startLegacyPolling 函数中，找到以下位置（大约 330 行）:
//
//     let pollTimeout = null;
//     let lastResponseTime = Date.now();
//
// 在其后添加:
let isPollingInProgress = false;  // 【P0 关键修复】防止轮询重叠的标志

// ========== 修改 2: 在 poll 函数开始时检查标志 ==========
// 在 poll = async () => { 后的第一行添加:
/*
const poll = async () => {
  // 【P0 关键修复 - 2026-03-02】防止轮询重叠
  if (isPollingInProgress) {
    console.warn('[轮询跳过] 上次轮询仍在进行中，跳过本次请求');
    return;
  }
  
  const requestStartTime = Date.now();
  pollCount++;
  isPollingInProgress = true;  // 标记轮询开始
  
  try {
    // ... 原有代码 ...
*/

// ========== 修改 3: 在 finally 块中重置标志 ==========
// 找到 finally 块（大约 570 行）:
//
//     } finally {
//       if (!isStopped) {
//         pollTimeout = setTimeout(poll, interval);
//       }
//     }
//
// 修改为:
/*
    } finally {
      isPollingInProgress = false;  // 标记轮询结束
      
      if (!isStopped) {
        // 【P0 关键修复】使用动态调整的间隔，确保不会重叠
        const nextInterval = getPollingInterval(
          lastLoggedProgress,
          '',  // stage will be checked in next poll
          Date.now() - requestStartTime,
          consecutiveNoProgressCount
        );
        
        pollTimeout = setTimeout(poll, nextInterval);
      }
    }
*/

// ========== 完整修改示例 ==========
// 以下是修改后的 poll 函数关键部分:

const poll_fixed = async () => {
  // 【P0 关键修复 - 2026-03-02】防止轮询重叠
  if (isPollingInProgress) {
    console.warn('[轮询跳过] 上次轮询仍在进行中，跳过本次请求');
    return;
  }

  const requestStartTime = Date.now();
  pollCount++;
  isPollingInProgress = true;  // 标记轮询开始

  try {
    // ... 原有业务逻辑代码保持不变 ...
    
    // 注意：不需要修改 try 块内部的代码
    // 只需要在入口和出口添加标志检查
  } catch (err) {
    // ... 原有错误处理代码保持不变 ...
  } finally {
    isPollingInProgress = false;  // 标记轮询结束
    
    if (!isStopped) {
      // 使用动态调整的间隔
      const nextInterval = getPollingInterval(
        lastLoggedProgress,
        '',
        Date.now() - requestStartTime,
        consecutiveNoProgressCount
      );
      
      pollTimeout = setTimeout(poll, nextInterval);
    }
  }
};

// ========== 预期效果 ==========
/*
修复前的问题：
[23:23:00.100] [轮询请求] 第 30 次
[23:23:00.150] [轮询请求] 第 31 次  <- 重叠请求
[23:23:00.200] [轮询请求] 第 32 次  <- 重叠请求

修复后的效果：
[23:23:00.100] [轮询请求] 第 30 次
[23:23:00.150] [轮询跳过] 上次轮询仍在进行中，跳过本次请求
[23:23:02.100] [轮询请求] 第 31 次  <- 等待上次完成后才发起
*/

console.log('[P0 修复补丁] 前端轮询重叠修复说明已加载');
console.log('[P0 修复补丁] 请按照上述说明修改 brandTestService.js 文件');
