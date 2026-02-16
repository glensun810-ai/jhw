/**
 * 常量入口文件
 */

// 任务状态相关常量
const { TASK_STAGES, TASK_STATUS } = require('./taskStatus');

// 品牌测试相关常量
const { BRAND_TEST_STATUS, QUESTION_TYPES, BRAND_TEST_LIMITS } = require('./brandTest');

module.exports = {
  TASK_STAGES,
  TASK_STATUS,
  BRAND_TEST_STATUS,
  QUESTION_TYPES,
  BRAND_TEST_LIMITS
};