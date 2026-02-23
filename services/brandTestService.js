/**
 * 品牌诊断执行服务
 * 负责诊断任务的启动、轮询、状态管理
 */

const { startBrandTestApi, getTaskStatusApi } = require('../api/home');
const { parseTaskStatus } = require('./taskStatusService');
const { aggregateReport } = require('./reportAggregator');

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
  
  // 每个模型对象应该包含 name 字段
  const processedSelectedModels = (selectedModels || []).map(item => {
    if (typeof item === 'object' && item !== null) {
      // 保持对象格式，优先使用 id 字段（英文），其次使用 name（中文）
      const modelName = (item.id || item.name || item.value || '').toLowerCase();
      return {
        name: modelName,
        checked: item.checked !== undefined ? item.checked : true
      };
    } else if (typeof item === 'string') {
      // 如果是字符串，转为对象
      return { name: item.toLowerCase(), checked: true };
    }
    return null;
  })
  // 过滤掉 null、空字符串和后端不支持的模型
  .filter(item => {
    if (!item || !item.name) return false;
    // 检查是否在后端支持的模型列表中
    const isSupported = SUPPORTED_MODELS.includes(item.name);
    if (!isSupported) {
      console.warn(`⚠️  过滤掉后端不支持的模型：${item.name}`);
    }
    return isSupported;
  });

  const custom_question = (customQuestions || []).join(' ');

  return {
    brand_list,
    selectedModels: processedSelectedModels,
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
  const maxDuration = 5 * 60 * 1000; // 5 分钟超时
  const startTime = Date.now();
  
  // Step 1: 错误计数器，实现熔断机制
  let consecutiveAuthErrors = 0;
  const MAX_AUTH_ERRORS = 2;  // 连续 2 次 403/401 错误即熔断

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
        console.error('轮询超时');
        if (onError) onError(new Error('诊断超时'));
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
          console.error('获取任务状态失败:', res);
        }
      } catch (err) {
        console.error('轮询异常:', err);
        
        // Step 1: 403/401 错误熔断机制
        if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
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
        }
        
        if (onError) onError(err);
      }
    }, interval);
  };

  return { start, stop, isStopped: () => isStopped };
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
