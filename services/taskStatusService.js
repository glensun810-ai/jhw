/**
 * 任务状态处理服务
 * 
 * P1-009 新增：
 * - 详细进度提示
 * - 预计剩余时间
 * - 实时结果计数
 */
const { TASK_STAGES } = require('../constants/index');

/**
 * 计算预计剩余时间
 * @param {number} progress - 当前进度百分比
 * @param {number} elapsed - 已用时间（秒）
 * @returns {string} 预计剩余时间文本
 */
const calculateRemainingTime = (progress, elapsed) => {
  if (progress <= 0 || elapsed <= 0) {
    return '计算中...';
  }
  
  const total = elapsed / (progress / 100);
  const remaining = total - elapsed;
  
  if (remaining < 60) {
    return `约${Math.ceil(remaining)}秒`;
  } else if (remaining < 3600) {
    return `约${Math.ceil(remaining / 60)}分钟`;
  } else {
    return `约${Math.ceil(remaining / 3600)}小时`;
  }
};

/**
 * 解析任务状态
 * @param {Object} statusData - 后端返回的状态数据
 * @param {number} startTime - 开始时间戳（用于计算剩余时间）
 * @returns {Object} 解析后的状态信息
 */
const parseTaskStatus = (statusData, startTime = Date.now()) => {
  // 防御性处理：为所有字段设置默认值
  const parsed = {
    status: (statusData && typeof statusData === 'object') ? statusData.status || 'unknown' : 'unknown',
    progress: (statusData && typeof statusData === 'object') ? (typeof statusData.progress === 'number' ? statusData.progress : 0) : 0,
    stage: (statusData && typeof statusData === 'object') ? statusData.stage || 'init' : 'init',
    results: (statusData && typeof statusData === 'object') ? (Array.isArray(statusData.results) ? statusData.results : []) : [],
    detailed_results: (statusData && typeof statusData === 'object') ? (Array.isArray(statusData.detailed_results) ? statusData.detailed_results : []) : [],
    error: (statusData && typeof statusData === 'object') ? statusData.error || null : null,
    message: (statusData && typeof statusData === 'object') ? statusData.message || '' : '',
    is_completed: (statusData && typeof statusData === 'object') ? (typeof statusData.is_completed === 'boolean' ? statusData.is_completed : false) : false,
    // P1-009 新增：详细进度信息
    detailText: '',
    remainingTime: '',
    resultsCount: 0
  };

  // 计算已用时间
  const elapsedSeconds = (Date.now() - startTime) / 1000;
  parsed.remainingTime = calculateRemainingTime(parsed.progress, elapsedSeconds);
  parsed.resultsCount = parsed.results.length || parsed.detailed_results.length;

  // 优先使用 stage 字段而非 status 字段
  const status = statusData.stage || statusData.status;

  if (status) {
    const cleanStatus = typeof status === 'string' ? status.trim() : status;
    const lowerCaseStatus = cleanStatus.toLowerCase();

    switch(lowerCaseStatus) {
      case TASK_STAGES.INIT:
        parsed.progress = 10;
        parsed.statusText = '任务初始化中...';
        parsed.detailText = '正在准备诊断环境，即将开始 AI 分析';
        parsed.stage = TASK_STAGES.INIT;
        parsed.is_completed = false;
        break;
      case TASK_STAGES.AI_FETCHING:
        parsed.progress = 30;
        parsed.statusText = '正在连接 AI 大模型...';
        parsed.detailText = `已连接 ${parsed.resultsCount} 个 AI 平台，正在获取品牌认知数据`;
        parsed.stage = TASK_STAGES.AI_FETCHING;
        parsed.is_completed = false;
        break;
      case TASK_STAGES.INTELLIGENCE_EVALUATING:
      case TASK_STAGES.INTELLIGENCE_ANALYZING:
      case TASK_STAGES.INTELLIGENCE_ANALYSIS:
        parsed.progress = 60;
        parsed.statusText = '正在进行深度分析...';
        parsed.detailText = `已获取 ${parsed.resultsCount} 条数据，正在分析语义冲突和信源质量`;
        parsed.stage = TASK_STAGES.INTELLIGENCE_ANALYZING;
        parsed.is_completed = false;
        break;
      case TASK_STAGES.COMPETITION_ANALYZING:
      case TASK_STAGES.COMPETITOR_ANALYSIS:
        parsed.progress = 80;
        parsed.statusText = '正在生成竞争分析...';
        parsed.detailText = `已完成 ${parsed.resultsCount} 个品牌分析，正在比对竞争优势和拦截风险`;
        parsed.stage = TASK_STAGES.COMPETITION_ANALYZING;
        parsed.is_completed = false;
        break;
      case TASK_STAGES.COMPLETED:
      case TASK_STAGES.FINISHED:
      case TASK_STAGES.DONE:
        parsed.progress = 100;
        parsed.statusText = '诊断完成！';
        parsed.detailText = `已生成 ${parsed.resultsCount} 条诊断结果，正在准备报告`;
        parsed.stage = TASK_STAGES.COMPLETED;
        parsed.is_completed = true;
        break;
      case TASK_STAGES.FAILED:
        // 【修复】区分"真失败"和"质量低但有结果"
        // 如果 progress=100 且有结果，说明是质量低但任务已完成
        if (parsed.progress === 100 && parsed.resultsCount > 0) {
          console.warn('[任务状态] 检测到质量低但有结果，视为部分完成');
          parsed.statusText = '诊断完成（结果质量较低）';
          parsed.detailText = `已生成 ${parsed.resultsCount} 条诊断结果，但部分结果质量较低`;
          parsed.stage = TASK_STAGES.COMPLETED;  // 改为 completed
          parsed.is_completed = true;
          parsed.has_low_quality_results = true;  // 标记质量低
        } else {
          // 真正的失败
          parsed.progress = 0;
          parsed.statusText = '诊断中断';
          parsed.detailText = parsed.error || '诊断过程中遇到错误，已保存的进度不会丢失';
          parsed.stage = TASK_STAGES.FAILED;
          parsed.is_completed = false;
        }
        break;
      default:
        parsed.statusText = `处理中...`;
        parsed.detailText = `当前阶段：${cleanStatus}，已获取 ${parsed.resultsCount} 条数据`;
        parsed.stage = 'processing';
        parsed.is_completed = false;
    }
  } else {
    parsed.statusText = '处理中...';
    parsed.detailText = `已获取 ${parsed.resultsCount} 条数据，${parsed.remainingTime}后完成`;
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

  // 调试日志
  console.log('[parseTaskStatus] 解析结果:', {
    stage: parsed.stage,
    progress: parsed.progress,
    is_completed: parsed.is_completed,
    status: parsed.status,
    results_count: parsed.resultsCount,
    remaining_time: parsed.remainingTime,
    detail_text: parsed.detailText
  });

  return parsed;
};

module.exports = {
  parseTaskStatus,
  calculateRemainingTime
};
