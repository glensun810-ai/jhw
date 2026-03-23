/**
 * 进度条管理器 - 优化版
 * 
 * 功能:
 * 1. 基于任务数的进度计算
 * 2. 平滑过渡动画
 * 3. 智能文案更新
 * 4. 详细进度显示
 */

class ProgressManager {
  constructor(pageContext) {
    this.page = pageContext;
    this.totalTasks = 0;
    this.completedTasks = 0;
    this.progressTexts = {
      '0-10': '准备诊断环境...',
      '11-20': '正在连接 AI 模型...',
      '21-40': '正在分析问题...',
      '41-60': '正在收集 AI 回答...',
      '61-80': '正在聚合分析结果...',
      '81-90': '正在生成诊断报告...',
      '91-99': '正在做最后校验...',
      '100': '诊断完成！✅'
    };
  }

  /**
   * 初始化进度
   */
  init(questionCount, modelCount) {
    this.totalTasks = questionCount * modelCount;
    this.completedTasks = 0;
    
    this.page.setData({
      progress: 0,
      progressText: '准备诊断...',
      progressDetail: `0/${this.totalTasks} 任务完成`
    });
  }

  /**
   * 更新进度 (基于任务完成数)
   */
  updateProgress(completedCount) {
    this.completedTasks = completedCount;
    const progress = this.calculateProgress();
    
    this.page.setData({
      progress: progress,
      progressText: this.getProgressText(progress),
      progressDetail: `${this.completedTasks}/${this.totalTasks} 任务完成`
    });
  }

  /**
   * 增加进度 (完成任务时调用)
   */
  incrementProgress() {
    this.completedTasks++;
    this.updateProgress(this.completedTasks);
  }

  /**
   * 计算进度百分比
   */
  calculateProgress() {
    if (this.totalTasks === 0) return 0;
    return Math.round((this.completedTasks / this.totalTasks) * 100);
  }

  /**
   * 获取进度文案
   */
  getProgressText(progress) {
    const range = Object.keys(this.progressTexts).find(r => {
      const [min, max] = r.split('-').map(Number);
      return progress >= min && progress <= max;
    });
    
    return this.progressTexts[range] || '诊断进行中...';
  }

  /**
   * 平滑过渡到目标进度
   */
  smoothTransition(targetProgress, duration = 500) {
    const currentProgress = this.page.data.progress;
    const diff = targetProgress - currentProgress;
    
    if (Math.abs(diff) < 1) return;
    
    const steps = 10;
    const stepSize = diff / steps;
    const stepDuration = duration / steps;
    
    let step = 0;
    const transitionInterval = setInterval(() => {
      step++;
      const newProgress = Math.round(currentProgress + (step * stepSize));
      
      this.page.setData({ progress: newProgress });
      
      if (step >= steps) {
        clearInterval(transitionInterval);
      }
    }, stepDuration);
  }

  /**
   * 设置进度文案
   */
  setProgressText(text) {
    this.page.setData({ progressText: text });
  }

  /**
   * 完成进度
   */
  complete() {
    this.page.setData({
      progress: 100,
      progressText: '诊断完成！✅',
      progressDetail: `${this.totalTasks}/${this.totalTasks} 任务完成`
    });
  }

  /**
   * 获取详细进度信息
   */
  getProgressInfo() {
    return {
      total: this.totalTasks,
      completed: this.completedTasks,
      percentage: this.calculateProgress(),
      text: this.getProgressText(this.calculateProgress())
    };
  }
}

module.exports = ProgressManager;
