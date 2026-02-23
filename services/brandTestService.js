/**
 * 品牌诊断执行服务
 * 负责诊断任务的启动、轮询、状态管理
 */

const { startBrandTestApi, getTaskStatusApi } = require('../api/home');
const { parseTaskStatus } = require('./taskStatusService');
const { aggregateReport } = require('./reportAggregator');

/**
 * P2 性能优化：计算动态轮询间隔
 * @param {number} progress - 当前进度 (0-100)
 * @param {string} stage - 当前阶段
 * @returns {number} 轮询间隔（毫秒）
 */
const getPollingInterval = (progress, stage) => {
  // 初期阶段（0-30%）：2 秒，给后端足够时间启动
  if (progress < 30) {
    return 2000;
  }
  // 中期阶段（30-70%）：1.5 秒，平衡响应速度和服务器压力
  if (progress < 70) {
    return 1500;
  }
  // 后期阶段（70-90%）：1 秒，加快响应
  if (progress < 90) {
    return 1000;
  }
  // 完成阶段（90-100%）：500ms，快速响应完成
  return 500;
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
      // 过滤掉 null 和空字符串
      if (!name) return false;
      
      // 检查是否在后端支持的模型列表中
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
 * 创建轮询控制器
 * @param {string} executionId - 执行 ID
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 * @returns {Object} 轮询控制器
 */
const createPollingController = (executionId, onProgress, onComplete, onError) => {
  let pollInterval = null;
  let isStopped = false;
  const maxDuration = 10 * 60 * 1000; // 10 分钟超时 (P0 修复：增加超时时间，防止复杂诊断任务超时)
  const startTime = Date.now();

  // Step 1: 错误计数器，实现熔断机制
  let consecutiveAuthErrors = 0;
  const MAX_AUTH_ERRORS = 2;  // 连续 2 次 403/401 错误即熔断
  
  // P0 修复：无进度超时计数器（如果长时间没有进度更新，也视为超时）
  let lastProgressTime = Date.now();
  const noProgressTimeout = 8 * 60 * 1000; // 8 分钟无进度更新则超时

  const stop = () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
      isStopped = true;
    }
  };

  const start = (interval = 800, immediate = true) => {
    // P2 优化：立即触发第一次轮询，减少等待延迟
    if (immediate) {
      (async () => {
        try {
          const res = await getTaskStatusApi(executionId);
          if (res && (res.progress !== undefined || res.stage)) {
            const parsedStatus = parseTaskStatus(res);
            if (onProgress) onProgress(parsedStatus);

            // 如果已完成，直接触发完成回调
            if (parsedStatus.stage === 'completed' && onComplete) {
              stop();
              onComplete(parsedStatus);
              return;
            }
          }
        } catch (err) {
          console.error('立即轮询失败:', err);
          // Step 1: 检查是否为认证错误
          if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
            stop();
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        }
      })();
    }

    // 启动定时轮询
    pollInterval = setInterval(async () => {
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
        stop();
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
          if (newInterval !== interval && pollInterval) {
            clearInterval(pollInterval);
            interval = newInterval;
            pollInterval = setInterval(arguments.callee, interval);
            console.log(`[性能优化] 调整轮询间隔：${interval}ms -> ${newInterval}ms (进度：${parsedStatus.progress}%)`);
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
          }
        } else {
          console.warn('获取任务状态返回空数据，继续轮询');
        }
      } catch (err) {
        console.error('轮询异常:', err);

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
          console.error(`认证错误计数：${consecutiveAuthErrors}/${MAX_AUTH_ERRORS}`);

          if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
            stop();
            console.error('认证错误熔断，停止轮询');
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        } else {
          // 非认证错误，重置计数器
          consecutiveAuthErrors = 0;
          
          // P1-2 修复：网络错误和超时错误给予更友好的提示
          if (errorInfo.isNetworkError) {
            console.warn('网络连接异常，请检查网络设置');
          } else if (errorInfo.isTimeout) {
            console.warn('请求超时，服务器响应缓慢');
          }
        }

        // P1-2 修复：传递详细的错误信息给前端
        if (onError) {
          const userFriendlyError = createUserFriendlyError(errorInfo);
          onError(userFriendlyError);
        }
      }
    }, interval);
  };

  return { start, stop, isStopped: () => isStopped };
};

/**
 * P1-2 修复：生成用户友好的错误消息
 * @param {Object} errorInfo - 错误信息对象
 * @returns {Error} 用户友好的错误对象
 */
const createUserFriendlyError = (errorInfo) => {
  const errorMessages = {
    // 认证错误
    auth: '登录已过期，请重新登录',
    // 网络错误
    network: '网络连接异常，请检查网络设置',
    // 超时错误
    timeout: '请求超时，服务器响应缓慢',
    // AI 调用错误
    ai_error: 'AI 服务暂时不可用，请稍后重试',
    // 默认错误
    default: '诊断过程出现异常，请重试'
  };

  // 确定错误类型
  let errorType = 'default';
  let httpStatusCode = null;

  if (errorInfo.isAuthError) {
    errorType = 'auth';
    httpStatusCode = errorInfo.statusCode;
  } else if (errorInfo.isNetworkError) {
    errorType = 'network';
  } else if (errorInfo.isTimeout) {
    errorType = 'timeout';
  } else if (errorInfo.statusCode === 500) {
    errorType = 'ai_error';
    httpStatusCode = errorInfo.statusCode;
  }

  // 创建错误对象
  const error = new Error(errorMessages[errorType]);
  error.errorType = errorType;
  error.httpStatusCode = httpStatusCode;
  error.originalError = errorInfo.originalError;
  error.timestamp = errorInfo.timestamp;

  return error;
};

/**
 * 生成战略看板数据
 * @param {Object} processedReportData - 处理后的报告数据
 * @param {Object} pageContext - 页面上下文（用于获取 brandName 等）
 * @returns {Object} 看板数据
 */
const generateDashboardData = (processedReportData, pageContext) => {
  try {
    const rawResults = Array.isArray(processedReportData)
      ? processedReportData
      : (processedReportData.detailed_results || processedReportData.results || []);

    if (!rawResults || rawResults.length === 0) {
      console.warn('没有可用的原始结果数据');
      return null;
    }

    const brandName = pageContext.brandName;
    const competitors = pageContext.competitorBrands || [];

    const additionalData = {
      semantic_drift_data: processedReportData.semantic_drift_data || null,
      semantic_contrast_data: processedReportData.semantic_contrast_data || null,
      recommendation_data: processedReportData.recommendation_data || null,
      negative_sources: processedReportData.negative_sources || null,
      brand_scores: processedReportData.brand_scores || null,
      competitive_analysis: processedReportData.competitive_analysis || null,
      overall_score: processedReportData.overall_score || null
    };

    const dashboardData = aggregateReport(rawResults, brandName, competitors, additionalData);

    // 保存到全局存储
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
    console.error('生成战略看板数据失败:', error);
    return null;
  }
};

module.exports = {
  validateInput,
  buildPayload,
  startDiagnosis,
  createPollingController,
  generateDashboardData
};
