/**
 * 任务状态枚举定义
 *
 * P2 优化：统一状态定义，与后端保持一致
 * 【P0 优化 - 2026-03-05】添加明细阶段常量，后端直接返回明细
 */

/**
 * 任务状态枚举（明细版）
 * 【P0 优化】后端 API 直接返回这些明细阶段，前端负责翻译
 */
const TaskStatus = {
  // 初始化中
  INITIALIZING: 'initializing',
  // AI 调用中（明细阶段）
  AI_FETCHING: 'ai_fetching',
  // 结果保存中（明细阶段）
  RESULTS_SAVING: 'results_saving',
  // 结果验证中（明细阶段）
  RESULTS_VALIDATING: 'results_validating',
  // 背景分析中（明细阶段）
  BACKGROUND_ANALYSIS: 'background_analysis',
  // 报告聚合中（明细阶段）
  REPORT_AGGREGATING: 'report_aggregating',
  // 分析中（通用）
  ANALYZING: 'analyzing',
  // 已完成
  COMPLETED: 'completed',
  // 部分完成
  PARTIAL_COMPLETED: 'partial_completed',
  // 失败
  FAILED: 'failed',
};

/**
 * 任务阶段枚举（与状态对应）
 */
const TaskStage = {
  // 初始化
  INIT: 'init',
  // AI 调用中
  AI_FETCHING: 'ai_fetching',
  // 结果保存中
  RESULTS_SAVING: 'results_saving',
  // 结果验证中
  RESULTS_VALIDATING: 'results_validating',
  // 背景分析中
  BACKGROUND_ANALYSIS: 'background_analysis',
  // 报告聚合中
  REPORT_AGGREGATING: 'report_aggregating',
  // 分析中
  ANALYZING: 'analyzing',
  // 已完成
  COMPLETED: 'completed',
  // 失败
  FAILED: 'failed',
};

/**
 * 状态与阶段的映射关系
 */
const STATUS_STAGE_MAP = {
  [TaskStatus.INITIALIZING]: TaskStage.INIT,
  [TaskStatus.AI_FETCHING]: TaskStage.AI_FETCHING,
  [TaskStatus.RESULTS_SAVING]: TaskStage.RESULTS_SAVING,
  [TaskStatus.RESULTS_VALIDATING]: TaskStage.RESULTS_VALIDATING,
  [TaskStatus.BACKGROUND_ANALYSIS]: TaskStage.BACKGROUND_ANALYSIS,
  [TaskStatus.REPORT_AGGREGATING]: TaskStage.REPORT_AGGREGATING,
  [TaskStatus.ANALYZING]: TaskStage.ANALYZING,
  [TaskStatus.COMPLETED]: TaskStage.COMPLETED,
  [TaskStatus.PARTIAL_COMPLETED]: TaskStage.COMPLETED,
  [TaskStatus.FAILED]: TaskStage.FAILED,
};

/**
 * 阶段与状态的映射关系（反向）
 */
const STAGE_STATUS_MAP = {
  [TaskStage.INIT]: TaskStatus.INITIALIZING,
  [TaskStage.AI_FETCHING]: TaskStatus.AI_FETCHING,
  [TaskStage.RESULTS_SAVING]: TaskStatus.RESULTS_SAVING,
  [TaskStage.RESULTS_VALIDATING]: TaskStatus.RESULTS_VALIDATING,
  [TaskStage.BACKGROUND_ANALYSIS]: TaskStatus.BACKGROUND_ANALYSIS,
  [TaskStage.REPORT_AGGREGATING]: TaskStatus.REPORT_AGGREGATING,
  [TaskStage.ANALYZING]: TaskStatus.ANALYZING,
  [TaskStage.COMPLETED]: TaskStatus.COMPLETED,
  [TaskStage.FAILED]: TaskStatus.FAILED,
};

/**
 * 终端状态列表（不可变）
 */
const TERMINAL_STATUSES = [
  TaskStatus.COMPLETED,
  TaskStatus.PARTIAL_COMPLETED,
  TaskStatus.FAILED,
];

/**
 * 失败状态列表
 */
const FAILED_STATUSES = [TaskStatus.FAILED];

/**
 * 判断是否为终端状态
 * @param {string} status - 状态字符串
 * @returns {boolean} 是否为终端状态
 */
const isTerminalStatus = (status) => {
  return TERMINAL_STATUSES.includes(status);
};

/**
 * 判断是否为失败状态
 * @param {string} status - 状态字符串
 * @returns {boolean} 是否为失败状态
 */
const isFailedStatus = (status) => {
  return FAILED_STATUSES.includes(status);
};

/**
 * 获取用户友好的状态显示文本
 * @param {string} status - 状态字符串
 * @returns {string} 显示文本
 */
const getDisplayText = (status) => {
  const textMap = {
    [TaskStatus.INITIALIZING]: '初始化中',
    [TaskStatus.AI_FETCHING]: 'AI 调用中',
    [TaskStatus.RESULTS_SAVING]: '保存结果中',
    [TaskStatus.RESULTS_VALIDATING]: '验证结果中',
    [TaskStatus.BACKGROUND_ANALYSIS]: '背景分析中',
    [TaskStatus.REPORT_AGGREGATING]: '生成报告中',
    [TaskStatus.ANALYZING]: '分析中',
    [TaskStatus.COMPLETED]: '已完成',
    [TaskStatus.PARTIAL_COMPLETED]: '部分完成',
    [TaskStatus.FAILED]: '失败',
  };

  return textMap[status] || status;
};

// CommonJS 导出（微信小程序兼容）
module.exports = {
  TaskStatus,
  TaskStage,
  STATUS_STAGE_MAP,
  STAGE_STATUS_MAP,
  TERMINAL_STATUSES,
  FAILED_STATUSES,
  isTerminalStatus,
  isFailedStatus,
  getDisplayText,
};
