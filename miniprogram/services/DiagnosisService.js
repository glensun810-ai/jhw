/**
 * 诊断服务
 * 处理品牌诊断相关的业务逻辑
 */

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
    message: (statusData && typeof statusData === 'object') ? statusData.message || '' : ''
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
      case 'init':
        parsed.progress = 10;
        parsed.statusText = '任务初始化中...';
        parsed.stage = 'init';
        break;
      case 'ai_fetching':
        parsed.progress = 30;
        parsed.statusText = '正在连接大模型...';
        parsed.stage = 'ai_fetching';
        break;
      case 'intelligence_evaluating':
      case 'intelligence_analyzing':
      case 'intelligence_analysis':
        parsed.progress = 60;
        parsed.statusText = '专家组正在生成评估结论...'; // 修复：明确的状态文本
        parsed.stage = 'intelligence_analyzing';
        break;
      case 'competition_analyzing':
      case 'competitor_analysis':
        parsed.progress = 80;
        parsed.statusText = '正在比对竞争对手...';
        parsed.stage = 'competition_analyzing';
        break;
      case 'completed':
        parsed.progress = 100;
        parsed.statusText = '诊断完成，正在生成报告...';
        parsed.stage = 'completed';
        break;
      default:
        parsed.statusText = '处理中...';
        parsed.stage = 'processing';
    }
  } else {
    parsed.statusText = '处理中...';
    parsed.stage = 'unknown';
  }

  // 如果后端提供了明确的进度值，则使用后端的值
  if (typeof statusData.progress === 'number') {
    parsed.progress = statusData.progress;
  }

  // 返回解析后的状态信息
  return parsed;
};

module.exports = {
  parseTaskStatus
};