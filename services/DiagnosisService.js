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
    message: (statusData && typeof statusData === 'object') ? statusData.message || '' : '',
    // 【P0 关键修复】添加 should_stop_polling 字段
    should_stop_polling: (statusData && typeof statusData === 'object') ? (typeof statusData.should_stop_polling === 'boolean' ? statusData.should_stop_polling : false) : false
  };

  // 【P0 关键修复】优先使用 status 字段而非 stage 字段
  // 原因：status 是后端状态机明确标记的终态标识，stage 可能只是阶段描述
  const status = statusData.status || statusData.stage;

  // 【P0 关键修复】如果后端明确标记 should_stop_polling=true，强制覆盖为完成状态
  if (parsed.should_stop_polling) {
    console.log('[parseTaskStatus] ✅ 后端标记 should_stop_polling=true，强制设置为完成状态');
    
    // 如果后端返回 status='completed' 或 status='failed'，直接使用
    if (statusData.status === 'completed' || statusData.status === 'failed') {
      parsed.stage = statusData.status;
      parsed.status = statusData.status;
      parsed.progress = 100;
      parsed.statusText = statusData.status === 'completed' ? '诊断完成，正在生成报告...' : '诊断完成（失败）';
    } else if (parsed.stage !== 'completed' && parsed.stage !== 'failed') {
      // 如果 stage 不是终态，但 should_stop_polling=true，说明是异常情况
      console.warn('[parseTaskStatus] ⚠️ 异常：should_stop_polling=true 但 stage 不是终态，强制设置为 completed');
      parsed.stage = 'completed';
      parsed.progress = 100;
      parsed.statusText = '诊断完成';
    }
  }

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