/**
 * 品牌问题解析与分发服务
 * 负责将用户输入的复合问题分解为独立的单个问题，并管理问题分发流程
 *
 * 【P2 增强 - 2026-03-05】增强输入验证，添加更严格的数据校验和安全性检查
 */

const { extractValidQuestions } = require('../utils/question-parser');

// 【P2 增强】常量定义
const VALIDATION_CONSTANTS = {
  MIN_BRAND_NAME_LENGTH: 1,
  MAX_BRAND_NAME_LENGTH: 100,
  MIN_QUESTION_LENGTH: 1,
  MAX_QUESTION_LENGTH: 500,
  MAX_QUESTIONS_COUNT: 20,
  MAX_BRANDS_COUNT: 10,
  ALLOWED_BRAND_PATTERN: /^[\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\-_.()（）]+$/,
};

/**
 * 【P2 增强】验证品牌名称的有效性
 * @param {string} brandName - 品牌名称
 * @returns {Object} 验证结果 {valid: boolean, error?: string}
 */
const validateBrandName = (brandName) => {
  if (!brandName) {
    return { valid: false, error: '品牌名称不能为空' };
  }

  if (typeof brandName !== 'string') {
    return { valid: false, error: '品牌名称必须是字符串' };
  }

  const trimmed = brandName.trim();
  if (!trimmed) {
    return { valid: false, error: '品牌名称不能全为空白字符' };
  }

  if (trimmed.length < VALIDATION_CONSTANTS.MIN_BRAND_NAME_LENGTH ||
      trimmed.length > VALIDATION_CONSTANTS.MAX_BRAND_NAME_LENGTH) {
    return {
      valid: false,
      error: `品牌名称长度应在 ${VALIDATION_CONSTANTS.MIN_BRAND_NAME_LENGTH}-${VALIDATION_CONSTANTS.MAX_BRAND_NAME_LENGTH} 字符之间`
    };
  }

  // 检查是否包含非法字符
  if (!VALIDATION_CONSTANTS.ALLOWED_BRAND_PATTERN.test(trimmed)) {
    return { valid: false, error: '品牌名称包含非法字符，仅支持中英文、数字、常见符号' };
  }

  // 检查是否包含过多的重复字符
  const maxRepeat = 50;
  let currentRepeat = 1;
  for (let i = 1; i < trimmed.length; i++) {
    if (trimmed[i] === trimmed[i - 1]) {
      currentRepeat++;
      if (currentRepeat > maxRepeat) {
        return { valid: false, error: '品牌名称包含过多的重复字符' };
      }
    } else {
      currentRepeat = 1;
    }
  }

  return { valid: true };
};

/**
 * 【P2 增强】验证问题文本的有效性
 * @param {string} question - 问题文本
 * @param {number} index - 问题索引（用于错误提示）
 * @returns {Object} 验证结果 {valid: boolean, error?: string}
 */
const validateQuestion = (question, index = 0) => {
  if (!question) {
    return { valid: false, error: `问题 ${index + 1} 不能为空` };
  }

  if (typeof question !== 'string') {
    return { valid: false, error: `问题 ${index + 1} 必须是字符串` };
  }

  const trimmed = question.trim();
  if (!trimmed) {
    return { valid: false, error: `问题 ${index + 1} 不能全为空白字符` };
  }

  if (trimmed.length < VALIDATION_CONSTANTS.MIN_QUESTION_LENGTH ||
      trimmed.length > VALIDATION_CONSTANTS.MAX_QUESTION_LENGTH) {
    return {
      valid: false,
      error: `问题 ${index + 1} 长度应在 ${VALIDATION_CONSTANTS.MIN_QUESTION_LENGTH}-${VALIDATION_CONSTANTS.MAX_QUESTION_LENGTH} 字符之间`
    };
  }

  // 检查是否包含不可控制的字符
  for (let i = 0; i < trimmed.length; i++) {
    const code = trimmed.charCodeAt(i);
    // 允许的控制字符：\t (9), \n (10), \r (13)
    if (code < 32 && ![9, 10, 13].includes(code)) {
      return { valid: false, error: `问题 ${index + 1} 包含非法控制字符` };
    }
    // 检查 Unicode 代理对
    if (code >= 0xD800 && code <= 0xDFFF) {
      return { valid: false, error: `问题 ${index + 1} 包含无效 Unicode 字符` };
    }
  }

  return { valid: true };
};

/**
 * 【P2 增强】验证模型列表的有效性
 * @param {Array} selectedModels - 选中的模型列表
 * @returns {Object} 验证结果 {valid: boolean, error?: string, models?: Array}
 */
const validateModelList = (selectedModels) => {
  if (!selectedModels) {
    return { valid: false, error: '必须选择至少一个 AI 模型' };
  }

  if (!Array.isArray(selectedModels)) {
    return { valid: false, error: '模型列表必须是数组格式' };
  }

  if (selectedModels.length === 0) {
    return { valid: false, error: '必须选择至少一个 AI 模型' };
  }

  // 后端支持的模型列表
  const SUPPORTED_MODELS = ['deepseek', 'qwen', 'doubao', 'chatgpt', 'gemini', 'zhipu', 'wenxin', 'kimi'];

  const validModels = [];
  for (let i = 0; i < selectedModels.length; i++) {
    const model = selectedModels[i];
    let modelName = null;

    // 从对象或字符串中提取模型名称
    if (typeof model === 'object' && model !== null) {
      modelName = (model.id || model.name || model.value || model.label || '').toLowerCase();
    } else if (typeof model === 'string') {
      modelName = model.toLowerCase();
    } else {
      return { valid: false, error: `模型 ${i + 1} 格式错误，应为字符串或对象` };
    }

    if (!modelName || modelName.trim() === '') {
      return { valid: false, error: `模型 ${i + 1} 名称不能为空` };
    }

    // 检查是否支持该模型
    if (!SUPPORTED_MODELS.includes(modelName)) {
      console.warn(`⚠️  过滤掉后端不支持的模型：${modelName}`);
      continue;
    }

    validModels.push({
      name: modelName,
      checked: model.checked !== false  // 默认为 true
    });
  }

  if (validModels.length === 0) {
    return { valid: false, error: '没有有效的 AI 模型（所有模型都被过滤或不支持）' };
  }

  return { valid: true, models: validModels };
};

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

  if (questions.length > VALIDATION_CONSTANTS.MAX_QUESTIONS_COUNT) {
    errors.push(`单次请求最多支持${VALIDATION_CONSTANTS.MAX_QUESTIONS_COUNT}个问题`);
  }

  for (let i = 0; i < questions.length; i++) {
    const validation = validateQuestion(questions[i], i);
    if (!validation.valid) {
      errors.push(validation.error);
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

  // 【P2 增强】验证品牌列表
  if (!brand_list || !Array.isArray(brand_list)) {
    throw new Error('品牌列表必须是数组格式');
  }

  if (brand_list.length === 0) {
    throw new Error('至少需要一个品牌');
  }

  if (brand_list.length > VALIDATION_CONSTANTS.MAX_BRANDS_COUNT) {
    throw new Error(`单次请求最多支持${VALIDATION_CONSTANTS.MAX_BRANDS_COUNT}个品牌`);
  }

  // 验证每个品牌名称
  for (let i = 0; i < brand_list.length; i++) {
    const brandValidation = validateBrandName(brand_list[i]);
    if (!brandValidation.valid) {
      throw new Error(`品牌 ${i + 1} 验证失败：${brandValidation.error}`);
    }
  }

  // 【P2 增强】验证模型列表
  const modelValidation = validateModelList(selectedModels);
  if (!modelValidation.valid) {
    throw new Error(modelValidation.error);
  }

  // 解析问题
  const questions = parseQuestions(custom_question || '');

  // 验证问题
  const questionValidation = validateQuestions(questions);
  if (!questionValidation.valid) {
    throw new Error(`问题验证失败：${questionValidation.errors.join('; ')}`);
  }

  // 返回重构后的测试数据
  return {
    brand_list: brand_list.map(b => b.trim()),  // 去除品牌名称首尾空白
    selectedModels: modelValidation.models,  // 使用验证后的模型列表
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

    // 返回重构后的数据结构，用于 API 调用
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
  executeQuestionDistributionTest,
  // 【P2 增强】导出验证工具函数
  validateBrandName,
  validateQuestion,
  validateModelList,
  VALIDATION_CONSTANTS
};
