/**
 * MVP 业务逻辑服务层
 * 处理品牌诊断MVP的数据加工和状态转换
 * 遵循 DEVELOPMENT_SOP.md 第三阶段规范
 */

const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * MVP专用：启动品牌测试（同步执行，立即返回结果）
 * @param {Object} data - 请求数据
 * @returns {Promise}
 */
const startMVPBrandTestApi = (data) => {
  return post('/api/mvp/brand-test', data);
};

/**
 * 构建MVP品牌测试请求参数
 * @param {Object} params - 用户输入参数
 * @param {string} params.brandName - 品牌名称
 * @param {string} params.competitorBrand - 竞品名称（可选）
 * @param {string[]} params.questions - 问题列表
 * @returns {Object} 标准化的API请求参数
 */
const buildMVPTestRequest = (params) => {
  const { brandName, competitorBrand, questions } = params;
  
  // 构建品牌列表（主品牌 + 竞品，如果有）
  const brandList = [brandName];
  if (competitorBrand && competitorBrand.trim()) {
    brandList.push(competitorBrand.trim());
  }
  
  // 处理问题模板替换
  const processedQuestions = questions.map(question => {
    return question
      .replace(/{brandName}/g, brandName)
      .replace(/{competitorBrand}/g, competitorBrand || '竞品');
  }).filter(q => q.trim().length > 0);
  
  // MVP固定使用豆包平台
  const selectedModels = [{ name: '豆包', checked: true }];
  
  return {
    brand_list: brandList,
    selectedModels: selectedModels,
    customQuestions: processedQuestions
  };
};

/**
 * 验证MVP输入参数
 * @param {Object} params - 用户输入参数
 * @returns {Object} { valid: boolean, error?: string }
 */
const validateMVPInput = (params) => {
  const { brandName, questions } = params;
  
  if (!brandName || !brandName.trim()) {
    return { valid: false, error: '请输入品牌名称' };
  }
  
  if (brandName.trim().length > 50) {
    return { valid: false, error: '品牌名称不能超过50个字符' };
  }
  
  const validQuestions = questions.filter(q => q && q.trim().length > 0);
  if (validQuestions.length === 0) {
    return { valid: false, error: '请至少输入一个问题' };
  }
  
  if (validQuestions.length > 5) {
    return { valid: false, error: '问题数量不能超过5个' };
  }
  
  for (let i = 0; i < validQuestions.length; i++) {
    if (validQuestions[i].length > 500) {
      return { valid: false, error: `问题${i + 1}不能超过500个字符` };
    }
  }
  
  return { valid: true };
};

/**
 * 启动MVP品牌测试（同步执行版本，立即返回完整结果）
 * @param {Object} params - 用户输入参数
 * @returns {Promise<Object>} 结果 { success: boolean, results?: Array, executionId?: string, error?: string }
 */
const startMVPBrandTest = async (params) => {
  try {
    // 参数验证
    const validation = validateMVPInput(params);
    if (!validation.valid) {
      return { success: false, error: validation.error };
    }
    
    // 构建请求参数
    const requestData = buildMVPTestRequest(params);
    
    console.log('[MVP Service] 启动品牌测试:', requestData);
    
    // 调用MVP专用API（同步执行，等待完整结果）
    const response = await startMVPBrandTestApi(requestData);
    
    if (response.status === 'success' && response.results) {
      return { 
        success: true, 
        executionId: response.execution_id,
        results: response.results,
        message: response.message || '测试完成'
      };
    } else {
      return { 
        success: false, 
        error: response.error || '测试失败，未返回结果' 
      };
    }
  } catch (error) {
    console.error('[MVP Service] 启动测试失败:', error);
    return { 
      success: false, 
      error: error.message || '网络请求失败' 
    };
  }
};

/**
 * 获取任务状态文本
 * @param {string} stage - 任务阶段
 * @returns {string} 用户友好的状态描述
 */
const getTaskStageText = (stage) => {
  const stageMap = {
    'init': '初始化中...',
    'question_preparation': '准备问题...',
    'ai_testing': 'AI分析中...',
    'scoring': '评分计算中...',
    'analysis': '深度分析中...',
    'completed': '分析完成',
    'failed': '分析失败'
  };
  return stageMap[stage] || '处理中...';
};

/**
 * 查询MVP任务进度
 * @param {string} taskId - 任务ID
 * @returns {Promise<Object>} 进度信息
 */
const queryMVPTaskProgress = async (taskId) => {
  try {
    const response = await getTaskStatusApi(taskId);
    
    return {
      success: true,
      taskId: response.task_id,
      progress: response.progress || 0,
      stage: response.stage,
      stageText: getTaskStageText(response.stage),
      status: response.status,
      isCompleted: response.is_completed || response.status === 'completed',
      isFailed: response.status === 'failed',
      results: response.results,
      error: response.error
    };
  } catch (error) {
    console.error('[MVP Service] 查询进度失败:', error);
    return {
      success: false,
      error: error.message || '查询进度失败'
    };
  }
};

/**
 * 处理MVP测试结果
 * @param {Object} rawResults - 后端返回的原始结果
 * @param {string} brandName - 品牌名称
 * @returns {Object} 加工后的结果数据
 */
const processMVPResults = (rawResults, brandName) => {
  if (!rawResults) {
    return {
      brandName,
      results: [],
      summary: {
        totalQuestions: 0,
        completedQuestions: 0,
        averageResponseLength: 0
      }
    };
  }
  
  // 统一处理数组或对象格式
  const resultsArray = Array.isArray(rawResults) ? rawResults : [rawResults];
  
  // 提取并标准化结果项
  const processedResults = resultsArray.map((item, index) => {
    // 处理不同可能的数据结构
    const question = item.question || item.query || item.prompt || `问题 ${index + 1}`;
    const response = item.response || item.content || item.answer || item.result || '无响应';
    const platform = item.platform || item.ai_model || item.model || '豆包';
    const latency = item.latency || item.response_time || 0;
    
    return {
      id: index,
      question: question,
      response: response,
      platform: platform,
      latency: Math.round(latency),
      timestamp: item.timestamp || new Date().toISOString(),
      // 保留原始数据用于调试
      _raw: item
    };
  });
  
  // 计算摘要统计
  const totalQuestions = processedResults.length;
  const completedQuestions = processedResults.filter(r => 
    r.response && r.response !== '无响应' && r.response.length > 10
  ).length;
  
  const totalLength = processedResults.reduce((sum, r) => sum + r.response.length, 0);
  const averageResponseLength = completedQuestions > 0 
    ? Math.round(totalLength / completedQuestions) 
    : 0;
  
  return {
    brandName,
    results: processedResults,
    summary: {
      totalQuestions,
      completedQuestions,
      averageResponseLength
    }
  };
};

/**
 * 生成默认MVP问题模板
 * @param {string} brandName - 品牌名称
 * @param {string} competitorBrand - 竞品名称
 * @returns {string[]} 默认问题列表
 */
const getDefaultMVPQuestions = (brandName = '', competitorBrand = '') => {
  return [
    `介绍一下${brandName || '{brandName}'}`,
    `${brandName || '{brandName}'}的主要产品是什么`,
    competitorBrand 
      ? `${brandName || '{brandName}'}和${competitorBrand || '{competitorBrand}'}有什么区别`
      : `${brandName || '{brandName}'}的优势是什么`
  ];
};

module.exports = {
  // 核心功能
  startMVPBrandTest,
  queryMVPTaskProgress,
  processMVPResults,
  
  // 工具函数
  buildMVPTestRequest,
  validateMVPInput,
  getTaskStageText,
  getDefaultMVPQuestions
};
