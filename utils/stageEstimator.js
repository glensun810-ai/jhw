/**
 * 分阶段时间预估器
 * 
 * 功能:
 * 1. 分阶段定义
 * 2. 基于阶段的时间预估
 * 3. 阶段转换处理
 */

class StageEstimator {
  constructor() {
    // 阶段定义
    this.stages = {
      initializing: { 
        name: '初始化',
        progress: 0, 
        time: 5 
      },
      analyzing: { 
        name: '分析中',
        progress: 50, 
        timePerPercent: 2 
      },
      aggregating: { 
        name: '聚合中',
        progress: 80, 
        timePerPercent: 3 
      },
      generating: { 
        name: '生成中',
        progress: 95, 
        timePerPercent: 5 
      }
    };
    
    this.currentStage = 'initializing';
  }

  /**
   * 基于阶段预估剩余时间
   */
  estimate(currentProgress, currentStage) {
    if (!currentStage) {
      return this.fallbackEstimate(currentProgress);
    }

    this.currentStage = currentStage;
    const stage = this.stages[currentStage];
    
    if (!stage) {
      return this.fallbackEstimate(currentProgress);
    }

    // 计算剩余阶段时间
    let remainingTime = 0;
    
    if (currentStage === 'initializing') {
      remainingTime = stage.time;  // 初始化时间
      remainingTime += 50 * this.stages.analyzing.timePerPercent;  // analyzing 阶段
      remainingTime += 30 * this.stages.aggregating.timePerPercent;  // aggregating 阶段
      remainingTime += 5 * this.stages.generating.timePerPercent;  // generating 阶段
    } else if (currentStage === 'analyzing') {
      if (currentProgress < 50) {
        remainingTime += (50 - currentProgress) * stage.timePerPercent;
      }
      remainingTime += 30 * this.stages.aggregating.timePerPercent;
      remainingTime += 5 * this.stages.generating.timePerPercent;
    } else if (currentStage === 'aggregating') {
      if (currentProgress < 80) {
        remainingTime += (80 - currentProgress) * stage.timePerPercent;
      }
      remainingTime += 5 * this.stages.generating.timePerPercent;
    } else if (currentStage === 'generating') {
      remainingTime += (100 - currentProgress) * stage.timePerPercent;
    }

    return Math.round(remainingTime);
  }

  /**
   * 后备预估方法
   */
  fallbackEstimate(currentProgress) {
    const remaining = 100 - currentProgress;
    return Math.round(remaining * 2);  // 简单按每秒 2% 计算
  }

  /**
   * 获取当前阶段名称
   */
  getStageName(stage) {
    return this.stages[stage]?.name || '处理中';
  }

  /**
   * 获取阶段说明
   */
  getStageDescription(stage) {
    const descriptions = {
      initializing: '正在准备诊断环境',
      analyzing: '正在分析 AI 平台响应',
      aggregating: '正在聚合分析结果',
      generating: '正在生成诊断报告'
    };
    return descriptions[stage] || '诊断进行中';
  }

  /**
   * 重置预估器
   */
  reset() {
    this.currentStage = 'initializing';
  }
}

module.exports = StageEstimator;
