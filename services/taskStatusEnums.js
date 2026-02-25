/**
 * 任务状态枚举定义
 * 
 * P2 优化：统一状态定义，与后端保持一致
 */

/**
 * 任务状态枚举
 */
export const TaskStatus = {
  // 初始化中
  INITIALIZING: 'initializing',
  // AI 调用中
  AI_FETCHING: 'ai_fetching',
  // 分析中
  ANALYZING: 'analyzing',
  // 已完成
  COMPLETED: 'completed',
  // 部分完成
  PARTIAL_COMPLETED: 'partial_completed',
  // 失败
  FAILED: 'failed',
};

/**
 * 任务阶段枚举
 */
export const TaskStage = {
  // 初始化
  INIT: 'init',
  // AI 调用中
  AI_FETCHING: 'ai_fetching',
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
export const STATUS_STAGE_MAP = {
  [TaskStatus.INITIALIZING]: TaskStage.INIT,
  [TaskStatus.AI_FETCHING]: TaskStage.AI_FETCHING,
  [TaskStatus.ANALYZING]: TaskStage.ANALYZING,
  [TaskStatus.COMPLETED]: TaskStage.COMPLETED,
  [TaskStatus.PARTIAL_COMPLETED]: TaskStage.COMPLETED,
  [TaskStatus.FAILED]: TaskStage.FAILED,
};

/**
 * 阶段与状态的映射关系（反向）
 */
export const STAGE_STATUS_MAP = {
  [TaskStage.INIT]: TaskStatus.INITIALIZING,
  [TaskStage.AI_FETCHING]: TaskStatus.AI_FETCHING,
  [TaskStage.ANALYZING]: TaskStatus.ANALYZING,
  [TaskStage.COMPLETED]: TaskStatus.COMPLETED,
  [TaskStage.FAILED]: TaskStatus.FAILED,
};

/**
 * 状态与进度的映射关系
 */
export const STATUS_PROGRESS_MAP = {
  [TaskStatus.INITIALIZING]: 0,
  [TaskStatus.AI_FETCHING]: 50,
  [TaskStatus.ANALYZING]: 80,
  [TaskStatus.COMPLETED]: 100,
  [TaskStatus.PARTIAL_COMPLETED]: 100,
  [TaskStatus.FAILED]: 0,
};

/**
 * 状态展示文本（中文）
 */
export const STATUS_DISPLAY_TEXT = {
  [TaskStatus.INITIALIZING]: '正在初始化',
  [TaskStatus.AI_FETCHING]: '正在连接 AI 平台',
  [TaskStatus.ANALYZING]: '正在分析数据',
  [TaskStatus.COMPLETED]: '诊断完成',
  [TaskStatus.PARTIAL_COMPLETED]: '诊断部分完成',
  [TaskStatus.FAILED]: '诊断失败',
};

/**
 * 前端轮询终止状态（这些状态表示任务结束，无需继续轮询）
 */
export const TERMINAL_STATUSES = [
  TaskStatus.COMPLETED,
  TaskStatus.PARTIAL_COMPLETED,
];

/**
 * 前端需要特殊处理的失败状态
 */
export const FAILED_STATUSES = [
  TaskStatus.FAILED,
];

/**
 * 根据状态获取阶段
 * @param {string} status - 任务状态
 * @returns {string} 对应的任务阶段
 */
export function getStageFromStatus(status) {
  return STATUS_STAGE_MAP[status] || TaskStage.FAILED;
}

/**
 * 根据阶段获取状态
 * @param {string} stage - 任务阶段
 * @returns {string} 对应的任务状态
 */
export function getStatusFromStage(stage) {
  return STAGE_STATUS_MAP[stage] || TaskStatus.FAILED;
}

/**
 * 根据状态获取默认进度
 * @param {string} status - 任务状态
 * @returns {number} 默认进度值（0-100）
 */
export function getProgressFromStatus(status) {
  return STATUS_PROGRESS_MAP[status] || 0;
}

/**
 * 获取状态的展示文本
 * @param {string} status - 任务状态
 * @returns {string} 中文展示文本
 */
export function getDisplayText(status) {
  return STATUS_DISPLAY_TEXT[status] || '未知状态';
}

/**
 * 判断是否为终止状态
 * @param {string} status - 任务状态
 * @returns {boolean} 是否为终止状态
 */
export function isTerminalStatus(status) {
  return TERMINAL_STATUSES.includes(status);
}

/**
 * 判断是否为失败状态
 * @param {string} status - 任务状态
 * @returns {boolean} 是否为失败状态
 */
export function isFailedStatus(status) {
  return FAILED_STATUSES.includes(status);
}

/**
 * 解析状态字符串为枚举值
 * @param {string} statusStr - 状态字符串
 * @returns {string} TaskStatus 枚举值
 */
export function parseStatus(statusStr) {
  // 兼容旧数据
  const statusMap = {
    'running': TaskStatus.AI_FETCHING,
    'processing': TaskStatus.AI_FETCHING,
    'done': TaskStatus.COMPLETED,
    'finished': TaskStatus.COMPLETED,
  };
  return statusMap[statusStr] || TaskStatus.FAILED;
}

/**
 * 解析阶段字符串为枚举值
 * @param {string} stageStr - 阶段字符串
 * @returns {string} TaskStage 枚举值
 */
export function parseStage(stageStr) {
  // 兼容旧数据
  const stageMap = {
    'running': TaskStage.AI_FETCHING,
    'processing': TaskStage.AI_FETCHING,
    'done': TaskStage.COMPLETED,
    'finished': TaskStage.COMPLETED,
  };
  return stageMap[stageStr] || TaskStage.FAILED;
}
