/**
 * 问题解析工具函数
 * 提供通用的问题解析和验证功能
 */

/**
 * 智能解析用户输入的复合问题
 * @param {string} input - 用户输入的文本
 * @returns {Array<string>} 解析后的问题数组
 */
const parseQuestionsFromInput = (input) => {
  if (!input || typeof input !== 'string') {
    return [];
  }

  // 定义多种可能的分隔符
  const sentenceEndings = [
    /[。！？.!?]/g,    // 基本句号、感叹号、问号
    /[；;]/g,         // 分号
    /\n+/g,           // 换行符
    /(?<!\d),(?!\d)/g // 不在数字中间的逗号
  ];

  // 依次应用各种分隔符
  let sentences = [input];
  
  sentenceEndings.forEach(separator => {
    const newSentences = [];
    sentences.forEach(sentence => {
      const parts = sentence.split(separator);
      parts.forEach(part => {
        newSentences.push(part.trim());
      });
    });
    sentences = newSentences;
  });

  // 过滤掉空字符串和太短的句子
  return sentences
    .filter(s => s.length > 0)
    .filter(s => s.length > 2) // 至少要有2个字符
    .map(s => s.trim());
};

/**
 * 验证问题是否符合要求
 * @param {string} question - 问题字符串
 * @returns {boolean} 是否有效
 */
const isValidQuestion = (question) => {
  if (!question || typeof question !== 'string') {
    return false;
  }

  // 检查长度
  if (question.length < 3 || question.length > 500) {
    return false;
  }

  // 检查是否包含有意义的内容
  const meaningfulPattern = /[a-zA-Z\u4e00-\u9fa5]/; // 至少包含字母或中文
  if (!meaningfulPattern.test(question)) {
    return false;
  }

  return true;
};

/**
 * 清理和标准化问题
 * @param {string} question - 原始问题
 * @returns {string} 清理后的问题
 */
const normalizeQuestion = (question) => {
  if (!question || typeof question !== 'string') {
    return '';
  }

  // 移除多余的空白字符
  let normalized = question.replace(/\s+/g, ' ').trim();

  // 移除首尾标点符号
  normalized = normalized.replace(/^[^\w\u4e00-\u9fa5]+|[^\w\u4e00-\u9fa5]+$/g, '').trim();

  // 确保以问号结尾（如果是疑问句）
  if (normalized.includes('?') || normalized.includes('？') || 
      normalized.includes('吗') || normalized.includes('呢') ||
      normalized.endsWith('么')) {
    if (!normalized.endsWith('?') && !normalized.endsWith('？')) {
      normalized += '?';
    }
  }

  return normalized;
};

/**
 * 从文本中提取有效问题
 * @param {string} text - 输入文本
 * @returns {Array<string>} 有效问题数组
 */
const extractValidQuestions = (text) => {
  const rawQuestions = parseQuestionsFromInput(text);
  const validQuestions = [];

  rawQuestions.forEach(rawQuestion => {
    const normalized = normalizeQuestion(rawQuestion);
    if (isValidQuestion(normalized)) {
      validQuestions.push(normalized);
    }
  });

  return validQuestions;
};

module.exports = {
  parseQuestionsFromInput,
  isValidQuestion,
  normalizeQuestion,
  extractValidQuestions
};