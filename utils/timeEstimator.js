/**
 * 智能时间预估器 - 基于历史数据学习
 * 
 * 功能:
 * 1. 基于历史数据预估诊断时间
 * 2. 考虑网络延迟因子
 * 3. 考虑模型复杂度因子
 * 4. 提供置信区间
 * 5. 自动记录和学习
 */

const STORAGE_KEY = 'diagnosis_time_history';
const MAX_HISTORY = 50;  // 最多保留 50 条历史记录

class TimeEstimator {
  constructor() {
    this.historyData = this.loadHistory();
  }

  /**
   * 加载历史数据
   */
  loadHistory() {
    try {
      const data = wx.getStorageSync(STORAGE_KEY);
      return Array.isArray(data) ? data : [];
    } catch (e) {
      console.error('加载历史数据失败', e);
      return [];
    }
  }

  /**
   * 保存历史数据
   */
  saveHistory() {
    try {
      wx.setStorageSync(STORAGE_KEY, this.historyData);
    } catch (e) {
      console.error('保存历史数据失败', e);
    }
  }

  /**
   * 记录任务数据
   * @param {Object} taskData - 任务数据
   */
  recordTask(taskData) {
    const record = {
      timestamp: Date.now(),
      brandCount: taskData.brandCount,
      modelCount: taskData.modelCount,
      questionCount: taskData.questionCount,
      duration: taskData.duration,  // 实际耗时 (秒)
      avgLatency: taskData.avgLatency,  // 平均 API 延迟 (毫秒)
      success: taskData.success  // 是否成功完成
    };

    this.historyData.push(record);

    // 保留最近 N 条
    if (this.historyData.length > MAX_HISTORY) {
      this.historyData = this.historyData.slice(-MAX_HISTORY);
    }

    this.saveHistory();
    console.log('✅ 记录任务数据:', record);
  }

  /**
   * 预估诊断时间
   * @param {number} brandCount - 品牌数量
   * @param {number} modelCount - 模型数量
   * @param {number} questionCount - 问题数量
   * @returns {Object} { min, max, expected }
   */
  estimate(brandCount, modelCount, questionCount) {
    // 1. 获取历史平均时间
    const baseTime = this.getHistoricalAverage(brandCount, modelCount);

    // 2. 计算网络延迟因子
    const networkFactor = this.getNetworkFactor();

    // 3. 计算模型复杂度因子
    const modelFactor = this.getModelComplexityFactor(modelCount);

    // 4. 计算问题数量因子
    const questionFactor = 1 + (questionCount - 3) * 0.1;

    // 5. 计算最终预估
    const estimatedTime = baseTime * networkFactor * modelFactor * questionFactor;

    // 6. 计算置信区间
    const confidenceLevel = this.getConfidenceLevel(brandCount, modelCount);
    const variance = confidenceLevel < 0.8 ? 0.5 : confidenceLevel < 0.9 ? 0.3 : 0.2;

    return {
      min: Math.round(estimatedTime * (1 - variance)),
      max: Math.round(estimatedTime * (1 + variance)),
      expected: Math.round(estimatedTime),
      confidence: confidenceLevel,
      breakdown: {
        baseTime: Math.round(baseTime),
        networkFactor: networkFactor.toFixed(2),
        modelFactor: modelFactor.toFixed(2),
        questionFactor: questionFactor.toFixed(2)
      }
    };
  }

  /**
   * 获取历史平均时间
   */
  getHistoricalAverage(brandCount, modelCount) {
    // 查找相似配置的历史任务
    const similarTasks = this.historyData.filter(h => 
      h.success &&
      Math.abs(h.brandCount - brandCount) <= 1 &&
      Math.abs(h.modelCount - modelCount) <= 2
    );

    if (similarTasks.length >= 3) {
      // 有足够历史数据，使用加权平均
      const weights = similarTasks.map((_, i) => i + 1);  // 越近权重越大
      const totalWeight = weights.reduce((a, b) => a + b, 0);
      
      const weightedSum = similarTasks.reduce((sum, task, i) => 
        sum + task.duration * weights[i], 0
      );
      
      return weightedSum / totalWeight;
    }

    // 数据不足，使用默认公式
    // 基础 8 秒 + 每任务 3 秒
    return 8 + (brandCount * modelCount * 3);
  }

  /**
   * 获取网络延迟因子
   */
  getNetworkFactor() {
    // 获取最近 3 次任务的平均延迟
    const recentTasks = this.historyData.slice(-3);
    
    if (recentTasks.length === 0) {
      return 1.0;  // 无历史数据，使用基准
    }

    const avgLatency = recentTasks.reduce((sum, task) => 
      sum + (task.avgLatency || 2000), 0
    ) / recentTasks.length;

    const baselineLatency = 2000;  // 2 秒基准
    return Math.max(1.0, Math.min(2.0, avgLatency / baselineLatency));
  }

  /**
   * 获取模型复杂度因子
   */
  getModelComplexityFactor(modelCount) {
    // 不同模型的权重
    const modelWeights = {
      'doubao': 1.0,
      'qwen': 1.1,
      'deepseek': 1.0,
      'kimi': 1.2,
      'chatgpt': 1.5,
      'gemini': 1.5,
      'claude': 1.4,
      'default': 1.1
    };

    // 从历史数据中统计使用的模型
    const modelUsage = {};
    this.historyData.slice(-10).forEach(task => {
      if (task.models) {
        task.models.forEach(model => {
          modelUsage[model] = (modelUsage[model] || 0) + 1;
        });
      }
    });

    // 计算加权平均复杂度
    let totalWeight = 0;
    let totalCount = 0;

    Object.entries(modelUsage).forEach(([model, count]) => {
      const weight = modelWeights[model] || modelWeights.default;
      totalWeight += weight * count;
      totalCount += count;
    });

    if (totalCount > 0) {
      return 1.0 + (totalWeight / totalCount - 1.0) * 0.5;
    }

    // 无历史数据，使用简化公式
    return 1.0 + (modelCount * 0.05);
  }

  /**
   * 获取置信度
   */
  getConfidenceLevel(brandCount, modelCount) {
    const similarTasks = this.historyData.filter(h => 
      h.success &&
      Math.abs(h.brandCount - brandCount) <= 1 &&
      Math.abs(h.modelCount - modelCount) <= 2
    );

    // 相似任务越多，置信度越高
    if (similarTasks.length >= 10) return 0.95;
    if (similarTasks.length >= 5) return 0.90;
    if (similarTasks.length >= 3) return 0.80;
    return 0.60;
  }

  /**
   * 格式化时间显示
   */
  formatTime(seconds) {
    if (seconds < 60) {
      return `${seconds}秒`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${mins}分${secs}秒`;
    }
    return `${Math.floor(seconds / 3600)}小时${Math.floor((seconds % 3600) / 60)}分`;
  }

  /**
   * 清除历史数据
   */
  clearHistory() {
    this.historyData = [];
    wx.removeStorageSync(STORAGE_KEY);
  }

  /**
   * 获取统计信息
   */
  getStats() {
    if (this.historyData.length === 0) {
      return { count: 0, avgDuration: 0 };
    }

    const successfulTasks = this.historyData.filter(h => h.success);
    const avgDuration = successfulTasks.reduce((sum, task) => sum + task.duration, 0) / successfulTasks.length;

    return {
      count: this.historyData.length,
      successfulCount: successfulTasks.length,
      avgDuration: Math.round(avgDuration),
      minDuration: Math.round(Math.min(...successfulTasks.map(t => t.duration))),
      maxDuration: Math.round(Math.max(...successfulTasks.map(t => t.duration)))
    };
  }
}

module.exports = TimeEstimator;
