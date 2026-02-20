/**
 * 剩余时间计算器 - 指数移动平均平滑算法
 * 
 * 功能:
 * 1. 指数移动平均平滑
 * 2. 初期不稳定处理
 * 3. 时间格式化显示
 * 4. 异常值过滤
 */

class RemainingTimeCalculator {
  constructor() {
    this.timeHistory = [];  // 时间预估历史
    this.smoothingFactor = 0.3;  // 平滑系数 (0.3 表示新数据占 30% 权重)
    this.maxHistory = 5;  // 最多保留 5 条历史记录
    this.minProgressForExact = 5;  // 进度≥5% 才显示精确值
  }

  /**
   * 计算剩余时间
   * @param {number} progress - 当前进度 (0-100)
   * @param {number} elapsed - 已用时间 (秒)
   * @returns {Object} { type, seconds, display }
   */
  calculate(progress, elapsed) {
    // 进度为 0 或 100，特殊处理
    if (progress <= 0) {
      return {
        type: 'unknown',
        seconds: 0,
        display: '计算中...'
      };
    }

    if (progress >= 100) {
      return {
        type: 'complete',
        seconds: 0,
        display: '完成'
      };
    }

    // 初期不稳定，显示范围
    if (progress < this.minProgressForExact) {
      const minTime = 60;
      const maxTime = 300;
      return {
        type: 'range',
        min: minTime,
        max: maxTime,
        display: `${this.formatTime(minTime)}-${this.formatTime(maxTime)}`
      };
    }

    // 线性外推
    const progressRatio = progress / 100;
    const estimatedTotal = elapsed / progressRatio;
    const rawRemaining = estimatedTotal - elapsed;

    // 异常值过滤
    if (rawRemaining < 0 || rawRemaining > 3600) {
      return {
        type: 'unknown',
        seconds: 0,
        display: '计算中...'
      };
    }

    // 平滑处理
    this.timeHistory.push(rawRemaining);
    if (this.timeHistory.length > this.maxHistory) {
      this.timeHistory.shift();
    }

    const smoothedRemaining = this.exponentialMovingAverage();

    return {
      type: 'exact',
      seconds: Math.round(smoothedRemaining),
      display: this.formatTime(smoothedRemaining)
    };
  }

  /**
   * 指数移动平均
   */
  exponentialMovingAverage() {
    if (this.timeHistory.length === 0) return 0;
    
    let ema = this.timeHistory[0];
    for (let i = 1; i < this.timeHistory.length; i++) {
      ema = this.timeHistory[i] * this.smoothingFactor + ema * (1 - this.smoothingFactor);
    }
    return ema;
  }

  /**
   * 格式化时间
   */
  formatTime(seconds) {
    if (seconds < 0) return '0 秒';
    
    if (seconds < 60) {
      return `${Math.round(seconds)}秒`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      if (secs === 0) {
        return `${mins}分钟`;
      }
      return `${mins}分${secs}秒`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}小时${mins}分钟`;
    }
  }

  /**
   * 重置计算器
   */
  reset() {
    this.timeHistory = [];
  }

  /**
   * 获取统计信息
   */
  getStats() {
    if (this.timeHistory.length === 0) {
      return {
        count: 0,
        avg: 0,
        min: 0,
        max: 0
      };
    }

    return {
      count: this.timeHistory.length,
      avg: Math.round(this.timeHistory.reduce((a, b) => a + b, 0) / this.timeHistory.length),
      min: Math.round(Math.min(...this.timeHistory)),
      max: Math.round(Math.max(...this.timeHistory))
    };
  }
}

module.exports = RemainingTimeCalculator;
