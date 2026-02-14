/**
 * 任务状态常量定义
 */

// 任务阶段常量
const TASK_STAGES = {
  INIT: 'init',
  AI_FETCHING: 'ai_fetching',
  INTELLIGENCE_EVALUATING: 'intelligence_evaluating',
  INTELLIGENCE_ANALYZING: 'intelligence_analyzing',
  INTELLIGENCE_ANALYSIS: 'intelligence_analysis',
  COMPETITION_ANALYZING: 'competition_analyzing',
  COMPETITOR_ANALYSIS: 'competitor_analysis',
  COMPLETED: 'completed',
  FINISHED: 'finished',
  DONE: 'done',
  FAILED: 'failed',
  PROCESSING: 'processing',
  UNKNOWN: 'unknown'
};

// 任务状态常量
const TASK_STATUS = {
  UNKNOWN: 'unknown',
  PROCESSING: 'processing',
  SUCCESS: 'success',
  FAILED: 'failed'
};

module.exports = {
  TASK_STAGES,
  TASK_STATUS
};