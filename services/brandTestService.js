const { debug, info, warn, error } = require('../utils/logger');

/**
 * 品牌诊断执行服务
 * 负责诊断任务的启动、轮询、状态管理
 * 
 * P2 优化：使用统一状态枚举
 * P3 优化：集成 SSE 实时推送
 */

const { startBrandTestApi, getTaskStatusApi } = require('../api/home');
const { parseTaskStatus } = require('./taskStatusService');
const { aggregateReport } = require('./reportAggregator');

// P2 优化：导入状态枚举
const {
  TaskStatus,
  TaskStage,
  TERMINAL_STATUSES,
  FAILED_STATUSES,
  isTerminalStatus,
  isFailedStatus,
  getDisplayText,
} = require('./taskStatusEnums');

// P3 优化：导入 SSE 客户端
const { createPollingController: createSSEController } = require('./sseClient');

/**
 * P1-1 优化：智能动态轮询间隔
 * 根据后端实际响应时间和进度阶段动态调整
 * @param {number} progress - 当前进度 (0-100)
 * @param {string} stage - 当前阶段
 * @param {number} lastResponseTime - 上次响应时间（毫秒）
 * @returns {number} 轮询间隔（毫秒）
 */
const getPollingInterval = (progress, stage, lastResponseTime = 100) => {
  // P1-1 优化：缩短基础间隔，提升响应速度
  let baseInterval;
  if (progress < 10) {
    // 初期：刚启动，给后端一点时间（从 1500ms 降至 800ms）
    baseInterval = 800;
  } else if (progress < 30) {
    // 早期：AI 调用中（从 1000ms 降至 500ms）
    baseInterval = 500;
  } else if (progress < 70) {
    // 中期：分析中（从 800ms 降至 400ms）
    baseInterval = 400;
  } else if (progress < 90) {
    // 后期：即将完成（从 600ms 降至 300ms）
    baseInterval = 300;
  } else {
    // 完成阶段：快速响应（从 400ms 降至 200ms）
    baseInterval = 200;
  }

  // P1-1 优化：根据后端响应时间动态调整
  // 如果后端响应快，缩短间隔；响应慢，延长间隔
  const responseFactor = lastResponseTime / 100;
  const adjustedInterval = baseInterval * Math.max(0.3, Math.min(1.2, responseFactor));

  // 限制范围：150ms - 2000ms（从 200-3000ms 收紧）
  return Math.max(150, Math.min(2000, adjustedInterval));
};

/**
 * 验证输入数据
 * @param {Object} inputData - 输入数据
 * @returns {Object} 验证结果
 */
const validateInput = (inputData) => {
  const { brandName, selectedModels, customQuestions } = inputData;

  // 类型保护：确保 brandName 是字符串，或从对象中提取
  const nameToTrim = (typeof brandName === 'string') ? brandName : (brandName?.brandName || '');
  if (!nameToTrim || nameToTrim.trim() === '') {
    return { valid: false, message: '品牌名称不能为空' };
  }

  if (!selectedModels || selectedModels.length === 0) {
    return { valid: false, message: '请选择至少一个 AI 模型' };
  }

  return { valid: true };
};

/**
 * 构建请求载荷
 * @param {Object} inputData - 输入数据
 * @returns {Object} 请求载荷
 */
const buildPayload = (inputData) => {
  const { brandName, competitorBrands, selectedModels, customQuestions } = inputData;

  const brand_list = [brandName, ...(competitorBrands || [])];

  // P4 修复：前端逻辑保护 - 只保留后端支持的模型
  // 后端支持的模型列表：deepseek, qwen, doubao, chatgpt, gemini, zhipu, wenxin
  const SUPPORTED_MODELS = ['deepseek', 'qwen', 'doubao', 'chatgpt', 'gemini', 'zhipu', 'wenxin'];

  // P1-3 修复：直接发送字符串数组，简化后端处理
  const modelNames = (selectedModels || [])
    .map(item => {
      // 从对象或字符串中提取模型名称
      let modelName;
      if (typeof item === 'object' && item !== null) {
        modelName = (item.id || item.name || item.value || item.label || '').toLowerCase();
      } else if (typeof item === 'string') {
        modelName = item.toLowerCase();
      } else {
        return null;
      }

      // 验证模型名称
      if (!modelName || modelName.trim() === '') {
        return null;
      }

      return modelName;
    })
    .filter(name => {
      // 过滤掉后端不支持的模型
      const isSupported = SUPPORTED_MODELS.includes(name);
      if (!isSupported) {
        console.warn(`⚠️  过滤掉后端不支持的模型：${name}`);
      }
      return isSupported;
    });

  const custom_question = (customQuestions || []).join(' ');

  return {
    brand_list,
    selectedModels: modelNames,  // P1-3 修复：直接发送字符串数组
    custom_question
  };
};

/**
 * 启动品牌诊断
 * @param {Object} inputData - 输入数据
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 * @returns {Promise<string>} executionId
 */
const startDiagnosis = async (inputData, onProgress, onComplete, onError) => {
  const validation = validateInput(inputData);
  if (!validation.valid) {
    throw new Error(validation.message);
  }

  const payload = buildPayload(inputData);

  console.log('Sending request to API:', payload);

  try {
    const res = await startBrandTestApi(payload);
    const responseData = res.data || res;
    const executionId = responseData.execution_id || responseData.id || (responseData.data && responseData.data.execution_id);

    if (!executionId) {
      throw new Error('未能从响应中提取有效 ID');
    }

    console.log('✅ 诊断任务创建成功，执行 ID:', executionId);
    return executionId;
  } catch (error) {
    console.error('启动诊断失败:', error);
    throw error;
  }
};

/**
 * 创建轮询控制器（P3 优化：优先使用 SSE）
 * @param {string} executionId - 执行 ID
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 * @returns {Object} 轮询控制器
 */
const createPollingController = (executionId, onProgress, onComplete, onError) => {
  // P3 优化：优先使用 SSE，自动降级为轮询
  console.log('[brandTestService] 创建轮询控制器，优先使用 SSE');
  
  const sseController = createSSEController(executionId);
  
  sseController
    .on('progress', (data) => {
      console.log('[SSE] 进度更新:', data);
      if (onProgress) {
        onProgress({
          ...data,
          source: 'sse'  // 标记数据来源
        });
      }
    })
    .on('complete', (data) => {
      console.log('[SSE] 任务完成:', data);
      if (onComplete) {
        onComplete({
          ...data,
          source: 'sse'
        });
      }
    })
    .on('error', (error) => {
      console.warn('[SSE] 错误，降级为轮询模式:', error);
      // SSE 失败时降级为传统轮询
      startLegacyPolling(executionId, onProgress, onComplete, onError);
    })
    .start();
  
  return {
    start: () => {
      // SSE 已自动启动
      console.log('[brandTestService] SSE 已启动');
    },
    stop: () => {
      sseController.stop();
      console.log('[brandTestService] SSE 已停止');
    },
    isStopped: () => !sseController.isUsingSSE && sseController.pollingTimer === null
  };
};

/**
 * 传统轮询控制器（降级方案）
 * @param {string} executionId - 执行 ID
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 */
const startLegacyPolling = (executionId, onProgress, onComplete, onError) => {
  console.log('[brandTestService] 启动传统轮询模式');
  
  let pollInterval = null;
  let isStopped = false;
  const maxDuration = 10 * 60 * 1000; // 10 分钟超时
  const startTime = Date.now();

  // Step 1: 错误计数器，实现熔断机制
  let consecutiveAuthErrors = 0;
  const MAX_AUTH_ERRORS = 2;  // 连续 2 次 403/401 错误即熔断

  // P0 修复：无进度超时计数器
  let lastProgressTime = Date.now();
  const noProgressTimeout = 8 * 60 * 1000; // 8 分钟无进度更新则超时

  const controller = {
    stop: () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
        isStopped = true;
      }
    }
  };

  const start = (interval = 800, immediate = true) => {
    // P2 优化：立即触发第一次轮询
    if (immediate) {
      (async () => {
        try {
          const res = await getTaskStatusApi(executionId);
          if (res && (res.progress !== undefined || res.stage)) {
            const parsedStatus = parseTaskStatus(res);
            if (onProgress) onProgress(parsedStatus);

            if (parsedStatus.stage === 'completed' && onComplete) {
              controller.stop();
              onComplete(parsedStatus);
              return;
            }
          }
        } catch (err) {
          console.error('立即轮询失败:', err);
          if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
            controller.stop();
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        }
      })();
    }

    // 启动定时轮询
    let pollTimeout = null;
    let lastResponseTime = Date.now();

    const poll = async () => {
      const requestStartTime = Date.now();

      // 超时检查
      if (Date.now() - startTime > maxDuration) {
        controller.stop();
        console.error('轮询超时 (总超时 10 分钟)');
        if (onError) onError(new Error('诊断超时，请重试或联系管理员'));
        return;
      }

      // P0 修复：无进度超时检查
      if (Date.now() - lastProgressTime > noProgressTimeout) {
        controller.stop();
        console.error('轮询超时 (8 分钟无进度更新)');
        if (onError) onError(new Error('诊断超时，长时间无响应，请重试'));
        return;
      }

      if (isStopped) {
        return;
      }

      try {
        const res = await getTaskStatusApi(executionId);
        const responseTime = Date.now() - requestStartTime;
        lastResponseTime = Date.now();

        if (res && (res.progress !== undefined || res.stage)) {
          const parsedStatus = parseTaskStatus(res);

          // P0 修复：更新最后进度时间
          if (parsedStatus.progress > 0 || parsedStatus.stage !== 'init') {
            lastProgressTime = Date.now();
          }

          // BUG-004 修复：使用动态调整的轮询间隔
          const newInterval = getPollingInterval(parsedStatus.progress, parsedStatus.stage, responseTime);
          if (newInterval !== interval) {
            interval = newInterval;
            console.log(`[性能优化] 调整轮询间隔：${interval}ms (响应时间：${responseTime}ms, 进度：${parsedStatus.progress}%)`);
          }

          if (onProgress) {
            onProgress(parsedStatus);
          }

          // P2 优化：使用统一的状态判断函数
          const status = parsedStatus.status || parsedStatus.stage;
          
          if (isTerminalStatus(status)) {
            // 任务完成（包括部分完成）
            controller.stop();
            console.log('[轮询终止] 任务完成，status:', status);
            if (onComplete) {
              onComplete(parsedStatus);
            }
            return;
          }

          if (isFailedStatus(status)) {
            // 任务失败
            controller.stop();
            console.log('[轮询终止] 任务失败，status:', status);
            
            const hasResults = parsedStatus.results && parsedStatus.results.length > 0;
            const hasDetailedResults = parsedStatus.detailed_results && parsedStatus.detailed_results.length > 0;
            const hasAnyResults = hasResults || hasDetailedResults;

            if (hasAnyResults) {
              // 有结果的部分失败，视为部分完成
              console.warn('[品牌诊断] 部分失败但有结果，继续展示可用数据');
              if (onComplete) {
                onComplete(parsedStatus);
              }
            } else if (onError) {
              // 完全失败
              onError(new Error(parsedStatus.error || '诊断失败'));
            }
            return;
          }
        }
      } catch (err) {
        console.error('轮询异常:', err);

        const errorInfo = {
          originalError: err,
          statusCode: err.statusCode,
          isAuthError: err.isAuthError || err.statusCode === 403 || err.statusCode === 401,
          isNetworkError: err.errMsg && err.errMsg.includes('request:fail'),
          isTimeout: err.message && err.message.includes('timeout'),
          timestamp: Date.now()
        };

        if (errorInfo.isAuthError) {
          consecutiveAuthErrors++;
          if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
            controller.stop();
            console.error('认证错误熔断，停止轮询');
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        } else {
          consecutiveAuthErrors = 0;
          if (errorInfo.isNetworkError) {
            console.warn('网络连接异常，请检查网络设置');
          } else if (errorInfo.isTimeout) {
            console.warn('请求超时，服务器响应缓慢');
          }
        }

        if (onError) {
          const userFriendlyError = createUserFriendlyError(errorInfo);
          onError(userFriendlyError);
        }
      } finally {
        if (!isStopped) {
          pollTimeout = setTimeout(poll, interval);
        }
      }
    };

    poll();

    controller.stop = () => {
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
  };

  return { start, stop: controller.stop, isStopped: () => isStopped };
};

/**
 * P1-006 修复：生成用户友好的错误消息
 */
const createUserFriendlyError = (errorInfo) => {
  const errorMessages = {
    auth: '登录已过期，请重新登录',
    network: '网络连接失败，请检查网络设置',
    timeout: '请求超时，服务器响应缓慢',
    AI_PLATFORM_ERROR: 'AI 平台暂时不可用，请稍后重试',
    VALIDATION_ERROR: '输入数据格式错误，请检查后重试',
    AI_CONFIG_ERROR: 'AI 平台配置错误，请联系管理员',
    TASK_EXECUTION_ERROR: '诊断执行失败，已保存的进度不会丢失',
    TASK_TIMEOUT_ERROR: '诊断超时，请重试或联系管理员',
    RATE_LIMIT_ERROR: '请求过于频繁，请稍后再试',
    DATABASE_ERROR: '数据库错误，请联系技术支持',
    default: '诊断过程中断，已保存的进度不会丢失'
  };

  const suggestions = {
    auth: '\n\n建议：\n1. 重新登录\n2. 清除缓存后重试',
    network: '\n\n建议：\n1. 检查设备网络连接\n2. 确认后端服务已启动',
    timeout: '\n\n建议：\n1. 稍后重试\n2. 检查网络速度',
    AI_PLATFORM_ERROR: '\n\n建议：\n1. 稍后重试\n2. 更换其他 AI 模型',
    VALIDATION_ERROR: '\n\n建议：\n1. 检查品牌名称是否正确\n2. 确认已选择 AI 模型',
    AI_CONFIG_ERROR: '\n\n建议：\n1. 联系技术支持\n2. 检查后端配置',
    TASK_EXECUTION_ERROR: '\n\n建议：\n1. 查看历史记录\n2. 重新发起诊断',
    TASK_TIMEOUT_ERROR: '\n\n建议：\n1. 减少 AI 模型数量\n2. 减少问题数量',
    RATE_LIMIT_ERROR: '\n\n建议：\n1. 等待 1 分钟后重试',
    DATABASE_ERROR: '\n\n建议：\n1. 联系技术支持\n2. 提供错误发生时间',
    default: '\n\n建议：\n1. 查看历史记录\n2. 重新发起诊断'
  };

  let errorCode = 'default';
  if (errorInfo.isAuthError) errorCode = 'auth';
  else if (errorInfo.isNetworkError) errorCode = 'network';
  else if (errorInfo.isTimeout) errorCode = 'timeout';
  else if (errorInfo.statusCode === 400) errorCode = 'VALIDATION_ERROR';
  else if (errorInfo.statusCode === 401) errorCode = 'auth';
  else if (errorInfo.statusCode === 403) errorCode = 'auth';
  else if (errorInfo.statusCode === 408) errorCode = 'TASK_TIMEOUT_ERROR';
  else if (errorInfo.statusCode === 429) errorCode = 'RATE_LIMIT_ERROR';
  else if (errorInfo.statusCode === 503) errorCode = 'AI_PLATFORM_ERROR';
  else if (errorInfo.statusCode === 500) errorCode = 'TASK_EXECUTION_ERROR';

  const message = errorMessages[errorCode] || errorMessages.default;
  const suggestion = suggestions[errorCode] || suggestions.default;

  return new Error(message + suggestion);
};

/**
 * 生成战略看板数据
 */
const generateDashboardData = (processedReportData, pageContext) => {
  try {
    let rawResults = null;

    if (Array.isArray(processedReportData)) {
      rawResults = processedReportData;
    } else if (processedReportData && typeof processedReportData === 'object') {
      rawResults = processedReportData.detailed_results
        || processedReportData.results
        || processedReportData.data?.detailed_results
        || processedReportData.data?.results
        || [];
    }

    if (!rawResults || rawResults.length === 0) {
      console.warn('[generateDashboardData] ⚠️ 没有可用的原始结果数据');
      return {
        _error: 'NO_DATA',
        errorMessage: '没有可用的诊断结果数据',
        brandName: pageContext?.brandName || '',
        competitors: pageContext?.competitorBrands || [],
        brandScores: {},
        sov: {},
        risk: {},
        health: {},
        insights: {},
        attribution: {},
        semanticDriftData: null,
        recommendationData: null,
        overallScore: 0,
        timestamp: new Date().toISOString()
      };
    }

    const brandName = pageContext?.brandName || '';
    const competitors = pageContext?.competitorBrands || [];

    const additionalData = {
      semantic_drift_data: processedReportData?.semantic_drift_data || null,
      recommendation_data: processedReportData?.recommendation_data || null,
      negative_sources: processedReportData?.negative_sources || null,
      competitive_analysis: processedReportData?.competitive_analysis || null
    };

    const dashboardData = aggregateReport(rawResults, brandName, competitors, additionalData);

    console.log('[generateDashboardData] ✅ 看板数据生成成功');

    const app = getApp();
    if (app && app.globalData) {
      app.globalData.lastReport = {
        raw: rawResults,
        dashboard: dashboardData,
        competitors: competitors
      };
    }

    return dashboardData;
  } catch (error) {
    console.error('[generateDashboardData] 生成战略看板数据失败:', error);
    return {
      _error: 'GENERATION_ERROR',
      errorMessage: error.message || '生成看板数据失败',
      brandName: pageContext?.brandName || '',
      competitors: pageContext?.competitorBrands || [],
      brandScores: {},
      sov: {},
      risk: {},
      health: {},
      insights: {},
      attribution: {},
      semanticDriftData: null,
      recommendationData: null,
      overallScore: 0,
      timestamp: new Date().toISOString()
    };
  }
};

module.exports = {
  validateInput,
  buildPayload,
  startDiagnosis,
  createPollingController,
  generateDashboardData,
  // 导出传统轮询（向后兼容）
  startLegacyPolling,
  getPollingInterval,
  createUserFriendlyError
};
