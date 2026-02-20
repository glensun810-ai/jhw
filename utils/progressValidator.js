/**
 * 进度验证器 - 检测进度真实性
 * 
 * 功能:
 * 1. 进度倒退检测
 * 2. 进度停滞检测
 * 3. 进度速度验证
 * 4. 异常警告
 */

class ProgressValidator {
  constructor() {
    this.lastProgress = 0;
    this.lastUpdateTime = 0;
    this.lastTimestamp = 0;
    this.expectedProgressRate = 2;  // 期望每秒 2%
    this.maxStallTime = 30000;  // 最大停滞 30 秒
    this.minProgressRate = 0.5;  // 最小进度速度 0.5%/s
  }

  /**
   * 验证进度
   * @param {number} progress - 当前进度
   * @param {number} timestamp - 时间戳
   * @returns {Object} { isValid, warnings, suggestions }
   */
  validate(progress, timestamp) {
    const result = {
      isValid: true,
      warnings: [],
      suggestions: [],
      status: 'normal'
    };

    // 首次调用，初始化
    if (this.lastUpdateTime === 0) {
      this.lastProgress = progress;
      this.lastUpdateTime = timestamp;
      this.lastTimestamp = timestamp;
      return result;
    }

    // 检查进度是否倒退
    if (progress < this.lastProgress) {
      result.isValid = false;
      result.status = 'regressed';
      result.warnings.push(`进度倒退：${this.lastProgress}% → ${progress}%`);
      result.suggestions.push('可能数据异常，建议刷新页面');
    }

    // 检查进度停滞
    const stallTime = timestamp - this.lastUpdateTime;
    if (stallTime > this.maxStallTime && progress < 100) {
      result.status = 'stalled';
      result.warnings.push(`进度停滞超过${Math.round(stallTime / 1000)}秒`);
      result.suggestions.push('显示安抚文案，告知用户正在处理');
    }

    // 检查进度速度
    const progressDelta = progress - this.lastProgress;
    const timeDelta = (timestamp - this.lastTimestamp) / 1000;
    
    if (timeDelta > 0 && progressDelta > 0) {
      const progressRate = progressDelta / timeDelta;

      if (progressRate < this.minProgressRate && progress < 80) {
        result.status = 'slow';
        result.warnings.push(`进度过慢：${progressRate.toFixed(2)}%/s`);
        result.suggestions.push('提示用户网络可能较慢');
      }

      if (progressRate > 10 && progress < 80) {
        result.warnings.push(`进度过快：${progressRate.toFixed(2)}%/s`);
        result.suggestions.push('可能数据异常');
      }
    }

    // 更新状态
    this.lastProgress = progress;
    if (progress > this.lastProgress) {
      this.lastUpdateTime = timestamp;
    }
    this.lastTimestamp = timestamp;

    return result;
  }

  /**
   * 获取停滞时间
   */
  getStallTime(currentTimestamp) {
    if (this.lastUpdateTime === 0) return 0;
    return currentTimestamp - this.lastUpdateTime;
  }

  /**
   * 获取平均进度速度
   */
  getAverageProgressRate(startProgress, startTime, currentProgress, currentTime) {
    const progressDelta = currentProgress - startProgress;
    const timeDelta = (currentTime - startTime) / 1000;
    
    if (timeDelta <= 0) return 0;
    return progressDelta / timeDelta;
  }

  /**
   * 重置验证器
   */
  reset() {
    this.lastProgress = 0;
    this.lastUpdateTime = 0;
    this.lastTimestamp = 0;
  }

  /**
   * 获取验证统计
   */
  getStats() {
    return {
      lastProgress: this.lastProgress,
      stallTime: this.getStallTime(Date.now()),
      expectedRate: this.expectedProgressRate,
      minRate: this.minProgressRate,
      maxStallTime: this.maxStallTime
    };
  }
}

module.exports = ProgressValidator;
