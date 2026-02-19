/**
 * 任务状态处理服务
 * 根据后端返回的状态数据，解析出合适的进度文本和状态
 */
const { TASK_STAGES } = require('../constants/index');

/**
 * 解析任务状态
 * @param {Object} statusData - 后端返回的状态数据
 * @param {string} [statusData.status] - 任务状态
 * @param {string} [statusData.stage] - 任务阶段
 * @param {number} [statusData.progress] - 进度百分比
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
    message: (statusData && typeof statusData === 'object') ? statusData.message || '' : '',
    is_completed: (statusData && typeof statusData === 'object') ? (statusData.is_completed || false) : false
  };

  // 优先使用 stage 字段而非 status 字段，因为 stage 更精确地描述了任务的当前阶段
  // 如果 stage 不存在，则使用 status 作为备选
  const status = statusData.stage || statusData.status;

  if (status) {
    // 确保状态值是字符串并去除可能的空白字符
    const cleanStatus = typeof status === 'string' ? status.trim() : status;

    // 使用更灵活的匹配方式，以防万一有大小写或格式差异
    const lowerCaseStatus = cleanStatus.toLowerCase();

    switch(lowerCaseStatus) {
      case TASK_STAGES.INIT:
        parsed.progress = 10;
        parsed.statusText = '任务初始化中...';
        parsed.stage = TASK_STAGES.INIT;
        
        parsed.is_completed = false;
        break;
      case TASK_STAGES.AI_FETCHING:
        parsed.progress = 30;
        parsed.statusText = '正在连接大模型...';
        parsed.stage = TASK_STAGES.AI_FETCHING;
        
        parsed.is_completed = false;
        break;
      case TASK_STAGES.INTELLIGENCE_EVALUATING:
      case TASK_STAGES.INTELLIGENCE_ANALYZING:
      case TASK_STAGES.INTELLIGENCE_ANALYSIS:
        parsed.progress = 60;
        parsed.statusText = '正在进行语义冲突分析...';
        parsed.stage = TASK_STAGES.INTELLIGENCE_ANALYZING;
        
        parsed.is_completed = false;
        break;
      case TASK_STAGES.COMPETITION_ANALYZING:
      case TASK_STAGES.COMPETITOR_ANALYSIS:
        parsed.progress = 80;
        parsed.statusText = '正在比对竞争对手...';
        parsed.stage = TASK_STAGES.COMPETITION_ANALYZING;
        
        parsed.is_completed = false;
        break;
      case TASK_STAGES.COMPLETED:
      case TASK_STAGES.FINISHED:
      case TASK_STAGES.DONE:
        parsed.progress = 100;
        parsed.statusText = '诊断完成，正在生成报告...';
        parsed.stage = TASK_STAGES.COMPLETED;
        
        parsed.is_completed = true;
        break;
      case TASK_STAGES.FAILED:
        parsed.progress = 0; // 失败时进度为0或保持原值
        parsed.statusText = '任务执行失败...';
        parsed.stage = TASK_STAGES.FAILED;
        
        parsed.is_completed = false;
        break;
      default:
        parsed.statusText = '处理中...';
        parsed.stage = 'processing';
    }
  } else {
    parsed.statusText = '处理中...';
    parsed.stage = 'unknown';
    parsed.is_completed = false;
  }

  // 如果后端提供了明确的进度值，则使用后端的值
  if (typeof statusData.progress === 'number') {
    parsed.progress = statusData.progress;
  }
  
  // 如果后端提供了 is_completed 字段，优先使用
  if (typeof statusData.is_completed === 'boolean') {
    parsed.is_completed = statusData.is_completed;
  }

  // 返回解析后的状态信息
  return parsed;
};

module.exports = {
  parseTaskStatus
};