/**
 * 首页业务逻辑处理服务
 * 负责处理从 API 获取的数据并进行格式化、计算等业务逻辑
 */

/**
 * 数据清洗器 - 统一对后端返回和本地存储的数据进行类型强制转换
 */
const dataSanitizer = {
  /**
   * 字符串清洗：确保返回字符串类型
   * @param {*} value - 原始值
   * @param {string} defaultValue - 默认值
   * @returns {string} 清洗后的字符串
   */
  toString: (value, defaultValue = '') => {
    if (value === null || value === undefined) return defaultValue;
    return String(value);
  },

  /**
   * 数字清洗：确保返回数字类型
   * @param {*} value - 原始值
   * @param {number} defaultValue - 默认值
   * @returns {number} 清洗后的数字
   */
  toNumber: (value, defaultValue = 0) => {
    if (value === null || value === undefined) return defaultValue;
    const num = Number(value);
    return isNaN(num) ? defaultValue : num;
  },

  /**
   * 数组清洗：确保返回数组类型
   * @param {*} value - 原始值
   * @param {Array} defaultValue - 默认值
   * @returns {Array} 清洗后的数组
   */
  toArray: (value, defaultValue = []) => {
    return Array.isArray(value) ? value : defaultValue;
  },

  /**
   * 对象清洗：确保返回对象类型
   * @param {*} value - 原始值
   * @param {Object} defaultValue - 默认值
   * @returns {Object} 清洗后的对象
   */
  toObject: (value, defaultValue = {}) => {
    return (value && typeof value === 'object' && !Array.isArray(value)) ? value : defaultValue;
  },

  /**
   * 布尔值清洗：确保返回布尔类型
   * @param {*} value - 原始值
   * @param {boolean} defaultValue - 默认值
   * @returns {boolean} 清洗后的布尔值
   */
  toBoolean: (value, defaultValue = false) => {
    if (value === null || value === undefined) return defaultValue;
    return Boolean(value);
  },

  /**
   * 清洗诊断结果数据
   * @param {Object} rawData - 原始数据
   * @returns {Object} 清洗后的数据
   */
  sanitizeDiagnosticResult: (rawData) => {
    if (!rawData || typeof rawData !== 'object') {
      return {
        status: 'unknown',
        progress: 0,
        stage: 'init',
        results: [],
        detailed_results: {},
        error: null,
        message: ''
      };
    }

    return {
      status: dataSanitizer.toString(rawData.status, 'unknown'),
      progress: dataSanitizer.toNumber(rawData.progress, 0),
      stage: dataSanitizer.toString(rawData.stage, 'init'),
      results: dataSanitizer.toArray(rawData.results, []),
      detailed_results: dataSanitizer.toObject(rawData.detailed_results, {}),
      error: rawData.error || null,
      message: dataSanitizer.toString(rawData.message, '')
    };
  },

  /**
   * 清洗草稿数据
   * @param {Object} rawDraft - 原始草稿
   * @returns {Object|null} 清洗后的草稿
   */
  sanitizeDraft: (rawDraft) => {
    if (!rawDraft || typeof rawDraft !== 'object') {
      return null;
    }

    const brandName = dataSanitizer.toString(rawDraft.brandName, '');
    if (!brandName) {
      return null;
    }

    return {
      brandName: brandName,
      currentCompetitor: dataSanitizer.toString(rawDraft.currentCompetitor, ''),
      competitorBrands: dataSanitizer.toArray(rawDraft.competitorBrands, []),
      customQuestions: dataSanitizer.toArray(rawDraft.customQuestions, []),
      selectedModels: {
        domestic: dataSanitizer.toArray(rawDraft.selectedModels?.domestic, []),
        overseas: dataSanitizer.toArray(rawDraft.selectedModels?.overseas, [])
      },
      updatedAt: dataSanitizer.toNumber(rawDraft.updatedAt, 0)
    };
  }
};

/**
 * 处理测试进度数据
 * @param {Object} progressData - 进度数据
 * @param {number} currentProgress - 当前进度
 * @returns {Object} 处理后的进度信息
 */
const processTestProgress = (progressData, currentProgress) => {
  const data = progressData.data;
  const newProgress = Math.round(data.progress);

  return {
    shouldUpdateProgress: newProgress > currentProgress,
    newProgressValue: newProgress,
    status: data.status,
    results: data.results,
    competitiveAnalysis: data.competitiveAnalysis,
    error: data.error,
    progressText: data.progressText
  };
};

/**
 * 获取进度对应的状态文本
 * @param {number} progress - 当前进度
 * @returns {string} 状态文本
 */
const getProgressTextByValue = (progress) => {
  const progressSteps = [
    '正在连接 AI 认知引擎...',
    '正在生成诊断任务...',
    '正在向 AI 平台发起请求...',
    '正在分析 AI 回复...',
    '正在进行语义一致性检测...',
    '正在评估品牌纯净度...',
    '正在聚合竞品数据...',
    '正在生成深度洞察报告...'
  ];

  if (progress >= 100) {
    return '诊断完成，正在生成报告...';
  }

  const currentStepIndex = Math.min(
    Math.floor(progress / (100 / progressSteps.length)),
    progressSteps.length - 1
  );
  return progressSteps[currentStepIndex];
};

/**
 * 格式化测试结果
 * @param {Object} rawResults - 原始测试结果
 * @returns {Object} 格式化后的结果
 */
const formatTestResults = (rawResults) => {
  if (!rawResults) {
    return null;
  }

  // 这里可以添加对测试结果的进一步处理逻辑
  // 例如：数据清洗、格式化、计算统计数据等
  return {
    ...rawResults,
    // 添加额外的计算字段或格式化
    processedAt: Date.now(),
    hasResults: !!rawResults && Object.keys(rawResults).length > 0
  };
};

/**
 * 格式化竞品分析结果
 * @param {Object} rawAnalysis - 原始竞品分析
 * @returns {Object} 格式化后的分析结果
 */
const formatCompetitiveAnalysis = (rawAnalysis) => {
  if (!rawAnalysis) {
    return null;
  }

  // 这里可以添加对竞品分析结果的处理逻辑
  return {
    ...rawAnalysis,
    processedAt: Date.now(),
    hasAnalysis: !!rawAnalysis && Object.keys(rawAnalysis).length > 0
  };
};

/**
 * 检查测试是否完成
 * @param {string} status - 测试状态
 * @returns {boolean} 是否完成
 */
const isTestCompleted = (status) => {
  return status === 'completed';
};

/**
 * 检查测试是否失败
 * @param {string} status - 测试状态
 * @returns {boolean} 是否失败
 */
const isTestFailed = (status) => {
  return status === 'failed';
};

/**
 * 解析任务状态响应
 * @param {Object} statusData - 任务状态数据
 * @returns {Object} 解析后的状态信息
 */
const parseTaskStatus = (statusData) => {
  // 防御性处理：为所有字段设置默认值
  const parsed = {
    status: (statusData && typeof statusData === 'object') ? statusData.status || 'unknown' : 'unknown',
    progress: (statusData && typeof statusData === 'object') ? (typeof statusData.progress === 'number' ? statusData.progress : 0) : 0,
    stage: (statusData && typeof statusData === 'object') ? statusData.stage || 'init' : 'init',
    results: (statusData && typeof statusData === 'object') ? statusData.results || [] : [],
    detailed_results: (statusData && typeof statusData === 'object') ? statusData.detailed_results || {} : {},
    error: (statusData && typeof statusData === 'object') ? statusData.error || null : null,
    message: (statusData && typeof statusData === 'object') ? statusData.message || '' : ''
  };

  // 根据阶段设置进度百分比
  switch(parsed.stage) {
    case 'init':
      parsed.progress = 10;
      parsed.statusText = '任务初始化中...';
      break;
    case 'ai_fetching':
      parsed.progress = 30;
      parsed.statusText = '正在连接大模型...';
      break;
    case 'intelligence_analyzing':
      parsed.progress = 60;
      parsed.statusText = '正在进行语义冲突分析...';
      break;
    case 'competition_analyzing':
      parsed.progress = 80;
      parsed.statusText = '正在比对竞争对手...';
      break;
    case 'completed':
      parsed.progress = 100;
      parsed.statusText = '诊断完成，正在生成报告...';
      break;
    default:
      parsed.statusText = '处理中...';
  }

  return parsed;
};

module.exports = {
  dataSanitizer,
  processTestProgress,
  getProgressTextByValue,
  formatTestResults,
  formatCompetitiveAnalysis,
  isTestCompleted,
  isTestFailed,
  parseTaskStatus
};
