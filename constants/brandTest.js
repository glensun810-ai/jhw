/**
 * 品牌测试相关常量定义
 */

// 品牌测试状态常量
const BRAND_TEST_STATUS = {
  INIT: 'init',                    // 初始化
  QUESTIONS_PARSING: 'questions_parsing',  // 问题解析中
  DISTRIBUTING: 'distributing',    // 任务分发中
  PROCESSING: 'processing',        // 处理中
  COMPLETED: 'completed',          // 已完成
  FAILED: 'failed'                 // 失败
};

// 问题类型常量
const QUESTION_TYPES = {
  BRAND_INTRODUCTION: 'brand_introduction',    // 品牌介绍
  PRODUCT_FEATURE: 'product_feature',          // 产品特性
  COMPETITIVE_ANALYSIS: 'competitive_analysis', // 竞品分析
  ADVANTAGE_DISADVANTAGE: 'advantage_disadvantage' // 优劣势分析
};

// 最大限制常量
const BRAND_TEST_LIMITS = {
  MAX_QUESTIONS_PER_REQUEST: 20,    // 单次请求最大问题数
  MAX_QUESTION_LENGTH: 500,         // 单个问题最大长度
  MAX_BRANDS_PER_TEST: 10           // 单次测试最大品牌数
};

module.exports = {
  BRAND_TEST_STATUS,
  QUESTION_TYPES,
  BRAND_TEST_LIMITS
};