/**
 * 品牌问题解析与分发服务
 * 负责将用户输入的复合问题分解为独立的单个问题，并管理问题分发流程
 */

const { extractValidQuestions } = require('../utils/question-parser');

/**
 * 将用户输入的复合问题分解为独立的单个问题
 * @param {string} customQuestion - 用户输入的复合问题字符串
 * @returns {Array<string>} 分解后的问题数组
 */
const parseQuestions = (customQuestion) => {
  if (!customQuestion || typeof customQuestion !== 'string') {
    return [];
  }

  // 使用更智能的解析方法
  return extractValidQuestions(customQuestion);
};

/**
 * 验证问题的有效性
 * @param {Array<string>} questions - 问题数组
 * @returns {Object} 验证结果 {valid: boolean, errors: Array<string>}
 */
const validateQuestions = (questions) => {
  const errors = [];

  if (!Array.isArray(questions)) {
    errors.push('问题必须是数组格式');
    return { valid: false, errors };
  }

  if (questions.length === 0) {
    errors.push('至少需要提供一个问题');
    return { valid: false, errors };
  }

  if (questions.length > 20) { // 限制最大问题数量
    errors.push('单次请求最多支持20个问题');
  }

  for (let i = 0; i < questions.length; i++) {
    const question = questions[i];
    if (typeof question !== 'string' || question.trim().length === 0) {
      errors.push(`问题 ${i + 1} 不能为空`);
    }
    if (question.length > 500) { // 限制单个问题长度
      errors.push(`问题 ${i + 1} 长度不能超过500字符`);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
};

/**
 * 为品牌测试准备问题数据
 * @param {Object} testData - 原始测试数据
 * @returns {Object} 处理后的测试数据
 */
const prepareBrandTestData = (testData) => {
  const { brand_list, selectedModels, custom_question } = testData;

  // 解析问题
  const questions = parseQuestions(custom_question || '');

  // 验证问题
  const validation = validateQuestions(questions);
  if (!validation.valid) {
    throw new Error(`问题验证失败: ${validation.errors.join('; ')}`);
  }

  // 返回重构后的测试数据
  return {
    brand_list: brand_list || [],
    selectedModels: selectedModels || [],
    customQuestions: questions, // 使用分解后的问题数组
    originalCustomQuestion: custom_question
  };
};

/**
 * 生成问题分发任务
 * @param {Object} preparedData - 准备好的测试数据
 * @returns {Array<Object>} 问题分发任务数组
 */
const generateQuestionDistributionTasks = (preparedData) => {
  const { brand_list, selectedModels, customQuestions } = preparedData;
  
  const tasks = [];
  
  // 为每个问题生成任务
  customQuestions.forEach((question, questionIndex) => {
    // 为每个模型生成任务
    selectedModels.forEach((model, modelIndex) => {
      if (model.checked) { // 只处理选中的模型
        tasks.push({
          taskId: `task_${Date.now()}_${questionIndex}_${modelIndex}`,
          question: question,
          model: model.name,
          brand_list: brand_list,
          questionIndex,
          modelIndex
        });
      }
    });
  });

  return tasks;
};

/**
 * 执行问题分发测试
 * @param {Object} testData - 测试数据
 * @returns {Promise<Object>} 测试结果
 */
const executeQuestionDistributionTest = async (testData) => {
  try {
    // 准备测试数据
    const preparedData = prepareBrandTestData(testData);
    
    // 生成任务
    const tasks = generateQuestionDistributionTasks(preparedData);
    
    // 验证任务数量
    if (tasks.length === 0) {
      throw new Error('没有有效的测试任务生成');
    }

    // 返回重构后的数据结构，用于API调用
    return {
      ...preparedData,
      tasksCount: tasks.length,
      distributionTasks: tasks
    };
  } catch (error) {
    console.error('问题分发测试执行失败:', error);
    throw error;
  }
};

module.exports = {
  parseQuestions,
  validateQuestions,
  prepareBrandTestData,
  generateQuestionDistributionTasks,
  executeQuestionDistributionTest
};