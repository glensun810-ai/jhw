/**
 * 时间预估与惊喜交付系统 - 任务负载感知算法
 * 
 * 核心逻辑：
 * 1. 基础连接耗时 (Connection): 3s
 * 2. 单元任务耗时 (Unit): 品牌数 * 模型数 * 问题数 * 1.5s (假设模型间有部分并发)
 * 3. 统计分析耗时 (Analysis): 5s
 * 4. 冗余系数 (Safety_Factor): 1.3 (用于创造惊喜空间)
 */

/**
 * 获取预估时间
 * @param {Object} params - 参数对象
 * @param {Array} params.brands - 品牌数组
 * @param {Array} params.models - 模型数组
 * @param {Array|String} params.questions - 问题数组或字符串
 * @returns {Number} 预估时间（秒）
 */
export const getEstimatedTime = (params) => {
  const { brands = [], models = [], questions = [] } = params;
  
  // 基础连接耗时
  const baseConnectionTime = 3;
  
  // 统计分析耗时
  const analysisTime = 5;
  
  // 计算工作负载：品牌数 * 模型数 * 问题数 * 单元耗时
  const questionCount = Array.isArray(questions) ? questions.length : (questions ? 1 : 0);
  const workLoad = brands.length * models.length * questionCount * 1.5;
  
  // 总预估时间 = (基础 + 工作负载) * 安全系数
  const safetyFactor = 1.3;
  const totalTime = Math.ceil((baseConnectionTime + workLoad + analysisTime) * safetyFactor);
  
  // 上限设为 60s 以免吓跑用户
  return Math.min(totalTime, 60);
};

/**
 * 获取进度文案
 * @param {Number} progress - 当前进度百分比 (0-100)
 * @returns {String} 进度文案
 */
export const getProgressText = (progress) => {
  if (progress <= 30) {
    return '正在分配各模型算力节点...';
  } else if (progress <= 70) {
    return '正在进行多品牌交叉语义研判...';
  } else if (progress <= 90) {
    return '正在聚合战略对阵矩阵...';
  } else {
    return '正在进行最后的视觉渲染...';
  }
};

/**
 * 获取进度条颜色
 * @param {Number} progress - 当前进度百分比 (0-100)
 * @returns {String} 渐变颜色值
 */
export const getProgressColor = (progress) => {
  // 从深蓝 (#0066FF) 随百分比向科技青 (#00F2FF) 渐变
  const ratio = progress / 100;
  const r = Math.round(0 * (1 - ratio) + 0 * ratio);
  const g = Math.round(102 * (1 - ratio) + 242 * ratio);
  const b = Math.round(255 * (1 - ratio) + 255 * ratio);

  return `rgb(${r}, ${g}, ${b})`;
};

/**
 * 获取惊喜文案
 * @param {Number} actualTime - 实际耗时
 * @param {Number} estimatedTime - 预估耗时
 * @returns {String} 惊喜文案
 */
export const getSurpriseText = (actualTime, estimatedTime) => {
  if (actualTime < estimatedTime * 0.7) {
    return '⚡️ AI 算力优化，研判大幅提前完成！正在为您生成战略大盘...';
  } else if (actualTime < estimatedTime * 0.9) {
    return '✅ AI 算力优化，研判提前完成！正在为您生成战略大盘...';
  } else {
    return '✅ 研判完成！正在为您生成战略大盘...';
  }
};

/**
 * 检查是否为惊喜完成
 * @param {Number} actualTime - 实际耗时
 * @param {Number} estimatedTime - 预估耗时
 * @returns {Boolean} 是否为惊喜完成
 */
export const isSurpriseCompletion = (actualTime, estimatedTime) => {
  return actualTime < estimatedTime * 0.9;
};

export default {
  getEstimatedTime,
  getProgressText,
  getProgressColor,
  getSurpriseText,
  isSurpriseCompletion
};