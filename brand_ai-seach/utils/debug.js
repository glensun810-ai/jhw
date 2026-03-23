/**
 * 前端 DEBUG_AI_CODE 调试日志工具
 * 统一管理前端调试信息输出，支持 execution_id 关联追踪
 */

// 全局开关
const ENABLE_DEBUG_AI_CODE = true;

/**
 * 统一的调试日志函数，符合 DEBUG_AI_CODE 标准
 * 格式: 2026-02-14 18:30:05 [DEBUG_AI_CODE] [<模块名>] [ID:<execution_id>] <内容>
 * 
 * @param {string} moduleName - 模块名称
 * @param {string} executionId - 执行ID，用于跨端关联
 * @param {string} message - 日志内容
 */
function debugLog(moduleName, executionId = 'unknown', message = '') {
  if (!ENABLE_DEBUG_AI_CODE) {
    return;
  }
  
  const timestamp = new Date().toLocaleString('sv-SE'); // 格式: YYYY-MM-DD HH:mm:ss
  const logMessage = `${timestamp} [DEBUG_AI_CODE] [${moduleName}] [ID:${executionId}] ${message}`;
  
  console.log(logMessage);
}

/**
 * AI I/O 操作专用日志
 * 
 * @param {string} executionId - 执行ID
 * @param {string} promptSummary - 输入提示摘要
 * @param {string} responseSummary - AI响应摘要
 */
function debugLogAiIo(executionId, promptSummary, responseSummary) {
  if (!ENABLE_DEBUG_AI_CODE) {
    return;
  }
  
  const timestamp = new Date().toLocaleString('sv-SE');
  const inputMsg = `${timestamp} [DEBUG_AI_CODE] [AI_IO] [ID:${executionId}] INPUT PROMPT: ${promptSummary}`;
  const outputMsg = `${timestamp} [DEBUG_AI_CODE] [AI_IO] [ID:${executionId}] AI RESPONSE: ${responseSummary}`;
  
  console.log(inputMsg);
  console.log(outputMsg);
}

/**
 * 状态流转专用日志
 * 
 * @param {string} executionId - 执行ID
 * @param {string} oldStage - 旧阶段
 * @param {string} newStage - 新阶段
 * @param {number} progressValue - 进度值
 */
function debugLogStatusFlow(executionId, oldStage, newStage, progressValue) {
  if (!ENABLE_DEBUG_AI_CODE) {
    return;
  }
  
  const timestamp = new Date().toLocaleString('sv-SE');
  const message = `${timestamp} [DEBUG_AI_CODE] [STATUS_FLOW] [ID:${executionId}] STAGE CHANGE: ${oldStage} -> ${newStage}, PROGRESS: ${progressValue}%`;
  
  console.log(message);
}

/**
 * 结果数据专用日志
 * 
 * @param {string} executionId - 执行ID
 * @param {number} resultsLength - 结果数组长度
 * @param {string} firstElementSummary - 首个元素摘要
 */
function debugLogResults(executionId, resultsLength, firstElementSummary = '') {
  if (!ENABLE_DEBUG_AI_CODE) {
    return;
  }
  
  const timestamp = new Date().toLocaleString('sv-SE');
  const message = `${timestamp} [DEBUG_AI_CODE] [RESULTS] [ID:${executionId}] RESULTS COUNT: ${resultsLength}, FIRST ELEMENT: ${firstElementSummary}`;
  
  console.log(message);
  
  // 如果结果为空，触发高亮警告
  if (resultsLength === 0) {
    console.warn(`${timestamp} [DEBUG_AI_CODE] [RESULTS] [ID:${executionId}] ⚠️ WARNING: RESULTS ARRAY IS EMPTY!`);
  }
}

/**
 * 异常信息专用日志
 * 
 * @param {string} executionId - 执行ID
 * @param {string} errorMessage - 错误信息
 */
function debugLogException(executionId, errorMessage) {
  if (!ENABLE_DEBUG_AI_CODE) {
    return;
  }
  
  const timestamp = new Date().toLocaleString('sv-SE');
  const message = `${timestamp} [DEBUG_AI_CODE] [EXCEPTION] [ID:${executionId}] [ERROR_TRACE] ${errorMessage}`;
  
  console.error(message);
}

module.exports = {
  debugLog,
  debugLogAiIo,
  debugLogStatusFlow,
  debugLogResults,
  debugLogException,
  ENABLE_DEBUG_AI_CODE
};