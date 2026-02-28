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
    resultsCount: 0,
    // 【P0 关键修复】添加 should_stop_polling 字段
    should_stop_polling: false
  };

  // 计算已用时间
  const elapsedSeconds = (Date.now() - startTime) / 1000;
  parsed.remainingTime = calculateRemainingTime(parsed.progress, elapsedSeconds);
  parsed.resultsCount = parsed.results.length || parsed.detailed_results.length;

  // 【P0 关键修复 - 架构师决策】优先使用后端返回的 should_stop_polling 字段
  // 这是判断是否停止轮询的最可靠依据
  const backendShouldStopPolling = (statusData && typeof statusData.should_stop_polling === 'boolean')
    ? statusData.should_stop_polling
    : false;
  
  parsed.should_stop_polling = backendShouldStopPolling;

  // 【P0 修复 - 架构师决策】优先使用后端返回的 is_completed 字段
  const backendIsCompleted = (statusData && typeof statusData.is_completed === 'boolean')
    ? statusData.is_completed
    : false;

  // 【P0 关键修复】优先使用 status 字段而非 stage 字段
  // 原因：status 是后端状态机明确标记的终态标识，stage 可能只是阶段描述
  // 例如：status='completed' 但 stage='processing' 时，应该以 status 为准
  const status = statusData.status || statusData.stage;

  console.log('[parseTaskStatus] 原始数据:', {
    stage: statusData?.stage,
    status: statusData?.status,
    progress: statusData?.progress,
    is_completed: statusData?.is_completed,
    results_count: parsed.resultsCount,
    backend_is_completed: backendIsCompleted
  });

  if (status) {
    const cleanStatus = typeof status === 'string' ? status.trim() : status;
    const lowerCaseStatus = cleanStatus.toLowerCase();

    switch(lowerCaseStatus) {
      case TASK_STAGES.INIT:
        parsed.progress = 10;
        parsed.statusText = '任务初始化中...';
        parsed.detailText = '正在准备诊断环境，即将开始 AI 分析';
        parsed.stage = TASK_STAGES.INIT;
        // 【P0 修复】如果后端明确标记为 completed，不要覆盖
        if (backendIsCompleted) {
          parsed.is_completed = true;
          parsed.stage = TASK_STAGES.COMPLETED;
          console.log('[parseTaskStatus] ⚠️ 后端标记为 completed，强制覆盖 stage');
        } else {
          parsed.is_completed = false;
        }
        break;
      case TASK_STAGES.AI_FETCHING:
        parsed.progress = 30;
        parsed.statusText = '正在连接 AI 大模型...';
        parsed.detailText = `已连接 ${parsed.resultsCount} 个 AI 平台，正在获取品牌认知数据`;
        parsed.stage = TASK_STAGES.AI_FETCHING;
        // 【P0 修复】如果后端明确标记为 completed，不要覆盖
        if (backendIsCompleted) {
          parsed.is_completed = true;
          parsed.stage = TASK_STAGES.COMPLETED;
          console.log('[parseTaskStatus] ⚠️ 后端标记为 completed，强制覆盖 stage');
        } else {
          parsed.is_completed = false;
        }
        break;
      case TASK_STAGES.INTELLIGENCE_EVALUATING:
      case TASK_STAGES.INTELLIGENCE_ANALYZING:
      case TASK_STAGES.INTELLIGENCE_ANALYSIS:
        parsed.progress = 60;
        parsed.statusText = '正在进行深度分析...';
        parsed.detailText = `已获取 ${parsed.resultsCount} 条数据，正在分析语义冲突和信源质量`;
        parsed.stage = TASK_STAGES.INTELLIGENCE_ANALYZING;
        // 【P0 修复】如果后端明确标记为 completed，不要覆盖
        if (backendIsCompleted) {
          parsed.is_completed = true;
          parsed.stage = TASK_STAGES.COMPLETED;
          console.log('[parseTaskStatus] ⚠️ 后端标记为 completed，强制覆盖 stage');
        } else {
          parsed.is_completed = false;
        }
        break;
      case TASK_STAGES.COMPETITION_ANALYZING:
      case TASK_STAGES.COMPETITOR_ANALYSIS:
        parsed.progress = 80;
        parsed.statusText = '正在生成竞争分析...';
        parsed.detailText = `已完成 ${parsed.resultsCount} 个品牌分析，正在比对竞争优势和拦截风险`;
        parsed.stage = TASK_STAGES.COMPETITION_ANALYZING;
        // 【P0 修复】如果后端明确标记为 completed，不要覆盖
        if (backendIsCompleted) {
          parsed.is_completed = true;
          parsed.stage = TASK_STAGES.COMPLETED;
          console.log('[parseTaskStatus] ⚠️ 后端标记为 completed，强制覆盖 stage');
        } else {
          parsed.is_completed = false;
        }
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
        // 【P0 关键修复】区分"真失败"和"失败但有结果"
        // 如果 progress=100 或后端标记 is_completed，说明执行已完成（即使是失败）
        if (parsed.progress >= 100 || backendIsCompleted) {
          console.warn('[任务状态] 检测到失败但执行已完成，视为完成状态');
          parsed.statusText = '诊断完成（部分失败）';
          parsed.detailText = `已获取 ${parsed.resultsCount} 条结果，部分 AI 调用失败`;
          parsed.stage = TASK_STAGES.COMPLETED;  // 改为 completed，让前端停止轮询
          parsed.is_completed = true;
          parsed.has_partial_failure = true;  // 标记有部分失败
          
          // 如果有错误信息，保留
          if (!parsed.error && statusData?.error) {
            parsed.error = statusData.error;
          }
        } else if (parsed.progress === 100 && parsed.resultsCount > 0) {
          // 进度 100% 且有结果，视为部分完成
          console.warn('[任务状态] 检测到进度 100% 且有结果，视为部分完成');
          parsed.statusText = '诊断完成（结果质量较低）';
          parsed.detailText = `已生成 ${parsed.resultsCount} 条诊断结果，但部分结果质量较低`;
          parsed.stage = TASK_STAGES.COMPLETED;
          parsed.is_completed = true;
          parsed.has_low_quality_results = true;
        } else {
          // 真正的失败（进度<100% 且没有完成标志）
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

  // 【P0 关键修复】如果后端明确标记 should_stop_polling=true，强制覆盖为完成状态
  // 这是最可靠的终止信号，优先级高于所有其他判断
  if (backendShouldStopPolling) {
    console.log('[parseTaskStatus] ✅ 后端标记 should_stop_polling=true，强制设置为完成状态');
    parsed.should_stop_polling = true;
    
    // 如果后端返回 status='completed' 或 status='failed'，直接使用
    if (statusData.status === 'completed' || statusData.status === 'failed') {
      parsed.stage = statusData.status;
      parsed.status = statusData.status;
      parsed.is_completed = (statusData.status === 'completed');
      parsed.progress = 100;
      parsed.statusText = statusData.status === 'completed' ? '诊断完成！' : '诊断完成（失败）';
    } else if (parsed.stage !== 'completed' && parsed.stage !== 'failed') {
      // 如果 stage 不是终态，但 should_stop_polling=true，说明是异常情况
      console.warn('[parseTaskStatus] ⚠️ 异常：should_stop_polling=true 但 stage 不是终态，强制设置为 completed');
      parsed.stage = 'completed';
      parsed.is_completed = true;
      parsed.progress = 100;
      parsed.statusText = '诊断完成';
    }
  }

  // 调试日志
  console.log('[parseTaskStatus] 解析结果:', {
    stage: parsed.stage,
    progress: parsed.progress,
    is_completed: parsed.is_completed,
    should_stop_polling: parsed.should_stop_polling,
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
