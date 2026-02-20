/**
 * 任务权重处理器 - 差异化处理不同任务
 * 
 * 功能:
 * 1. 根据模型类型设置权重
 * 2. 根据问题复杂度设置权重
 * 3. 计算加权进度
 * 4. 优先级调度
 */

class TaskWeightProcessor {
  constructor() {
    // 模型权重 (响应时间越慢权重越高)
    this.modelWeights = {
      'doubao': 1.0,
      'qwen': 1.1,
      'deepseek': 1.0,
      'kimi': 1.2,
      'chatgpt': 1.5,
      'gemini': 1.5,
      'claude': 1.4,
      'default': 1.1
    };

    // 问题复杂度权重
    this.complexityWeights = {
      'simple': 1.0,      // 简单介绍类问题
      'comparison': 1.3,  // 对比类问题
      'analysis': 1.5,    // 分析类问题
      'recommendation': 1.4  // 推荐类问题
    };
  }

  /**
   * 获取模型权重
   */
  getModelWeight(modelName) {
    return this.modelWeights[modelName] || this.modelWeights.default;
  }

  /**
   * 获取问题复杂度权重
   */
  getComplexityWeight(questionText) {
    const text = questionText.toLowerCase();
    
    if (text.includes('对比') || text.includes('vs') || text.includes('和哪个')) {
      return this.complexityWeights.comparison;
    }
    if (text.includes('分析') || text.includes('评价') || text.includes('优缺点')) {
      return this.complexityWeights.analysis;
    }
    if (text.includes('推荐') || text.includes('哪个更好')) {
      return this.complexityWeights.recommendation;
    }
    return this.complexityWeights.simple;
  }

  /**
   * 计算任务总权重
   */
  calculateTaskWeight(modelName, questionText) {
    const modelWeight = this.getModelWeight(modelName);
    const complexityWeight = this.getComplexityWeight(questionText);
    return modelWeight * complexityWeight;
  }

  /**
   * 计算加权进度
   * @param {Array} tasks - 任务列表 [{completed, weight}]
   * @returns {number} 加权进度 (0-100)
   */
  calculateWeightedProgress(tasks) {
    if (tasks.length === 0) return 0;

    const totalWeight = tasks.reduce((sum, task) => sum + task.weight, 0);
    const completedWeight = tasks
      .filter(task => task.completed)
      .reduce((sum, task) => sum + task.weight, 0);

    return Math.round((completedWeight / totalWeight) * 100);
  }

  /**
   * 获取任务优先级
   */
  getTaskPriority(modelName, questionIndex) {
    // 海外模型优先级低 (响应慢，先启动)
    const overseasModels = ['chatgpt', 'gemini', 'claude'];
    if (overseasModels.includes(modelName)) {
      return 'high';
    }
    
    // 问题索引小的优先级高
    if (questionIndex < 2) {
      return 'high';
    }
    if (questionIndex < 5) {
      return 'medium';
    }
    return 'low';
  }

  /**
   * 获取预估时间 (考虑权重)
   */
  getEstimatedTime(modelName, questionText, baseTime = 3000) {
    const weight = this.calculateTaskWeight(modelName, questionText);
    return Math.round(baseTime * weight);
  }

  /**
   * 获取所有模型的平均权重
   */
  getAverageModelWeight(modelList) {
    if (!modelList || modelList.length === 0) {
      return this.modelWeights.default;
    }

    const sum = modelList.reduce((s, model) => 
      s + this.getModelWeight(model), 0
    );
    return sum / modelList.length;
  }

  /**
   * 获取复杂度分布
   */
  getComplexityDistribution(questions) {
    const distribution = {
      simple: 0,
      comparison: 0,
      analysis: 0,
      recommendation: 0
    };

    questions.forEach(q => {
      const weight = this.getComplexityWeight(q);
      const type = Object.keys(this.complexityWeights).find(
        key => this.complexityWeights[key] === weight
      );
      if (type) distribution[type]++;
    });

    return distribution;
  }
}

module.exports = TaskWeightProcessor;
