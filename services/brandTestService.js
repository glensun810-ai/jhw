const { debug, info, warn, error } = require('../../utils/logger');

/**
 * 品牌诊断执行服务
 * 负责诊断任务的启动、轮询、状态管理
 */

const { startBrandTestApi, getTaskStatusApi } = require('../api/home');
const { parseTaskStatus } = require('./taskStatusService');
const { aggregateReport } = require('./reportAggregator');

/**
 * P1-015 优化：智能动态轮询间隔
 * 根据后端实际响应时间和进度阶段动态调整
 * @param {number} progress - 当前进度 (0-100)
 * @param {string} stage - 当前阶段
 * @param {number} lastResponseTime - 上次响应时间（毫秒）
 * @returns {number} 轮询间隔（毫秒）
 */
const getPollingInterval = (progress, stage, lastResponseTime = 100) => {
  // 基础间隔：根据进度阶段
  let baseInterval;
  if (progress < 10) {
    // 初期：刚启动，给后端更多时间
    baseInterval = 1500;
  } else if (progress < 30) {
    // 早期：AI 调用中
    baseInterval = 1000;
  } else if (progress < 70) {
    // 中期：分析中
    baseInterval = 800;
  } else if (progress < 90) {
    // 后期：即将完成
    baseInterval = 600;
  } else {
    // 完成阶段：快速响应
    baseInterval = 400;
  }
  
  // P1-015 新增：根据后端响应时间动态调整
  // 如果后端响应快，缩短间隔；响应慢，延长间隔
  const responseFactor = lastResponseTime / 100;
  const adjustedInterval = baseInterval * Math.max(0.5, Math.min(1.5, responseFactor));
  
  // 限制范围：200ms - 3000ms
  return Math.max(200, Math.min(3000, adjustedInterval));
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

  // 使用对象持有 stop 函数，避免重新赋值导致的只读错误
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
              controller.stop();
              onComplete(parsedStatus);
              return;
            }
          }
        } catch (err) {
          console.error('立即轮询失败:', err);
          // Step 1: 检查是否为认证错误
          if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
            controller.stop();
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        }
      })();
    }

    // 启动定时轮询 - BUG-NEW-001 修复：改用递归 setTimeout 避免并发请求
    let pollTimeout = null;
    // BUG-004 修复：跟踪上次响应时间，用于动态调整轮询间隔
    let lastResponseTime = Date.now();

    const poll = async () => {
      // 记录本次请求开始时间
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

      // 已停止检查
      if (isStopped) {
        return;
      }

      try {
        const res = await getTaskStatusApi(executionId);

        // BUG-004 修复：计算响应时间
        const responseTime = Date.now() - requestStartTime;
        lastResponseTime = Date.now();

        // 【DEBUG】输出后端响应
        console.log('[brandTestService] 后端响应:', JSON.stringify(res, null, 2));

        if (res && (res.progress !== undefined || res.stage)) {
          const parsedStatus = parseTaskStatus(res);

          // 【DEBUG】输出解析后的状态
          console.log('[brandTestService] 解析后的状态:', {
            stage: parsedStatus.stage,
            progress: parsedStatus.progress,
            is_completed: parsedStatus.is_completed,
            error: parsedStatus.error
          });

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

          // 终止条件 - 修复：同时检查 stage 和 is_completed
          if (parsedStatus.stage === 'completed' || parsedStatus.stage === 'failed' || parsedStatus.is_completed === true) {
            controller.stop();

            // 【关键修复】区分"完全失败"和"部分完成"
            const isCompleted = parsedStatus.is_completed === true || parsedStatus.stage === 'completed';
            const hasResults = parsedStatus.results && parsedStatus.results.length > 0;
            const hasDetailedResults = parsedStatus.detailed_results && parsedStatus.detailed_results.length > 0;
            const hasAnyResults = hasResults || hasDetailedResults;

            // 部分完成的情况：有结果但状态是 failed
            if (!isCompleted && parsedStatus.stage === 'failed' && hasAnyResults) {
              console.warn('[品牌诊断] 部分完成：检测到结果但状态为 failed，可能是部分 AI 调用失败');
              // 仍然调用 onComplete，让前端展示可用结果
              if (onComplete) {
                onComplete(parsedStatus);
              }
              return;
            }

            // 正常完成
            if (isCompleted && onComplete) {
              onComplete(parsedStatus);
            } 
            // 完全失败（无结果）
            else if (!isCompleted && !hasAnyResults && onError) {
              onError(new Error(parsedStatus.error || '诊断失败'));
            }
            // 部分失败但有结果
            else if (!isCompleted && hasAnyResults && onComplete) {
              console.warn('[品牌诊断] 部分失败但有结果，继续展示可用数据');
              onComplete(parsedStatus);
            }
            return;
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
            controller.stop();
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
 * @param {Object} errorInfo - 错误信息对象
 * @returns {Error} 用户友好的错误对象
 */
const createUserFriendlyError = (errorInfo) => {
  // P1-006 新增：详细错误文案映射
  const errorMessages = {
    // 认证错误
    auth: '登录已过期，请重新登录',
    auth_suggestion: '\n\n建议：\n1. 重新登录\n2. 清除缓存后重试',
    
    // 网络错误
    network: '网络连接失败，请检查网络设置',
    network_suggestion: '\n\n建议：\n1. 检查设备网络连接\n2. 确认后端服务已启动\n3. 检查防火墙设置',
    
    // 超时错误
    timeout: '请求超时，服务器响应缓慢',
    timeout_suggestion: '\n\n建议：\n1. 稍后重试\n2. 检查网络速度',
    
    // AI 平台错误
    AI_PLATFORM_ERROR: 'AI 平台暂时不可用，请稍后重试',
    AI_PLATFORM_ERROR_suggestion: '\n\n建议：\n1. 稍后重试\n2. 更换其他 AI 模型\n3. 检查 API Key 配置',
    
    // 验证错误
    VALIDATION_ERROR: '输入数据格式错误，请检查后重试',
    VALIDATION_ERROR_suggestion: '\n\n建议：\n1. 检查品牌名称是否正确\n2. 确认已选择 AI 模型',
    
    // 配置错误
    AI_CONFIG_ERROR: 'AI 平台配置错误，请联系管理员',
    AI_CONFIG_ERROR_suggestion: '\n\n建议：\n1. 联系技术支持\n2. 检查后端配置',
    
    // 任务执行错误
    TASK_EXECUTION_ERROR: '诊断执行失败，已保存的进度不会丢失',
    TASK_EXECUTION_ERROR_suggestion: '\n\n建议：\n1. 查看历史记录\n2. 重新发起诊断',
    
    // 超时错误
    TASK_TIMEOUT_ERROR: '诊断超时，请重试或联系管理员',
    TASK_TIMEOUT_ERROR_suggestion: '\n\n建议：\n1. 减少 AI 模型数量\n2. 减少问题数量\n3. 稍后重试',
    
    // 频率限制
    RATE_LIMIT_ERROR: '请求过于频繁，请稍后再试',
    RATE_LIMIT_ERROR_suggestion: '\n\n建议：\n1. 等待 1 分钟后重试',
    
    // 数据库错误
    DATABASE_ERROR: '数据库错误，请联系技术支持',
    DATABASE_ERROR_suggestion: '\n\n建议：\n1. 联系技术支持\n2. 提供错误发生时间',
    
    // 默认错误
    default: '诊断过程中断，已保存的进度不会丢失',
    default_suggestion: '\n\n建议：\n1. 查看历史记录是否有保存\n2. 重新发起诊断'
  };

  // 提取错误代码
  let errorCode = 'default';
  if (errorInfo.isAuthError) {
    errorCode = 'auth';
  } else if (errorInfo.isNetworkError) {
    errorCode = 'network';
  } else if (errorInfo.isTimeout) {
    errorCode = 'timeout';
  } else if (errorInfo.statusCode === 400) {
    errorCode = 'VALIDATION_ERROR';
  } else if (errorInfo.statusCode === 401) {
    errorCode = 'auth';
  } else if (errorInfo.statusCode === 403) {
    errorCode = 'PERMISSION_ERROR';
  } else if (errorInfo.statusCode === 408) {
    errorCode = 'TASK_TIMEOUT_ERROR';
  } else if (errorInfo.statusCode === 429) {
    errorCode = 'RATE_LIMIT_ERROR';
  } else if (errorInfo.statusCode === 503) {
    errorCode = 'AI_PLATFORM_ERROR';
  } else if (errorInfo.statusCode === 500) {
    errorCode = 'TASK_EXECUTION_ERROR';
  }

  // 构建友好消息
  const message = errorMessages[errorCode] || errorMessages.default;
  const suggestion = errorMessages[`${errorCode}_suggestion`] || errorMessages.default_suggestion;
  const fullMessage = message + suggestion;

  console.error(`[错误详情] 代码：${errorCode}, 原始错误：${errorInfo.originalError?.message || '未知'}`);

  return new Error(fullMessage);
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

    // 【关键修复】处理空结果数据的情况
    if (!rawResults || rawResults.length === 0) {
      console.warn('⚠️ 没有可用的原始结果数据，尝试从其他字段提取');
      
      // 尝试从 processedReportData 的其他字段提取数据
      const fallbackResults = [];
      
      // 检查是否有 semantic_drift_data 等其他数据
      if (processedReportData.semantic_drift_data) {
        console.log('📊 尝试从 semantic_drift_data 提取数据');
      }
      if (processedReportData.recommendation_data) {
        console.log('📊 尝试从 recommendation_data 提取数据');
      }
      
      // 如果完全没有数据，返回一个包含错误信息的对象
      if (fallbackResults.length === 0) {
        console.error('❌ 确实没有任何可用的结果数据');
        // 返回一个包含错误标记的对象，而不是 null
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
      
      // 使用 fallback 数据继续处理
      return generateDashboardData(fallbackResults, pageContext);
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
    // 【关键修复】返回包含错误信息的对象，而不是 null
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
  generateDashboardData
};
