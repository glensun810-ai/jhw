/**
 * 等待页面 - 情报流水线
 * 功能：显示诊断进度和实时情报更新
 */

const app = getApp();
const { getSSEClient } = require('../../../utils/sseClient');
const { RemainingTimeCalculator } = require('../../../utils/remainingTimeCalculator');

Page({
  data: {
    // 进度数据
    progress: 0,
    statusText: '正在启动诊断...',
    stageDescription: '',
    
    // 时间数据
    remainingTime: 0,
    smoothedRemainingTime: '',
    timeRange: '',
    elapsedTime: 0,
    
    // 任务数据
    completedTasks: 0,
    totalTasks: 0,
    
    // 情报流水线数据
    intelligenceItems: [],
    
    // 执行 ID
    executionId: '',
    
    // 计时器
    startTime: 0,
    updateTimer: null,
    
    // SSE 客户端
    sseClient: null
  },

  /**
   * 页面加载
   */
  onLoad: function(options) {
    // 获取执行 ID
    if (options.executionId) {
      this.setData({ executionId: options.executionId });
    }
    
    // 初始化剩余时间计算器
    this.remainingTimeCalc = new RemainingTimeCalculator();
    
    // 记录开始时间
    this.startTime = Date.now();
    
    // 初始化并连接 SSE
    this.initSSE();
    
    // 启动进度更新（作为 SSE 的后备）
    this.startProgressUpdates();
    
    // 启动情报流水线（作为 SSE 的后备）
    this.startIntelligencePipeline();
  },

  /**
   * 初始化 SSE 连接
   */
  initSSE: function() {
    const sseClient = getSSEClient('');
    
    // 连接 SSE
    sseClient.connect(this.data.executionId);
    
    // 监听 SSE 事件
    sseClient.on('connected', (data) => {
      console.log('[Waiting] SSE connected:', data);
    });
    
    sseClient.on('progress', (data) => {
      console.log('[Waiting] SSE progress:', data);
      this.handleSSEProgress(data);
    });
    
    sseClient.on('intelligence', (data) => {
      console.log('[Waiting] SSE intelligence:', data);
      this.handleSSEIntelligence(data);
    });
    
    sseClient.on('complete', (data) => {
      console.log('[Waiting] SSE complete:', data);
      this.handleSSEComplete(data);
    });
    
    sseClient.on('error', (data) => {
      console.error('[Waiting] SSE error:', data);
      wx.showToast({
        title: '连接失败，请重试',
        icon: 'none'
      });
    });
    
    this.setData({ sseClient: sseClient });
  },

  /**
   * 处理 SSE 进度更新
   */
  handleSSEProgress: function(data) {
    const { progress, stage, statusText, completed, total } = data;
    
    const elapsed = (Date.now() - this.startTime) / 1000;
    const remainingResult = this.remainingTimeCalc.calculate(progress, elapsed);
    
    this.setData({
      progress: progress || 0,
      statusText: statusText || this.getStatusText(progress),
      stageDescription: this.getStageDescription(stage),
      remainingTime: remainingResult.seconds,
      smoothedRemainingTime: remainingResult.display,
      completedTasks: completed || 0,
      totalTasks: total || 0
    });
  },

  /**
   * 处理 SSE 情报更新
   */
  handleSSEIntelligence: function(data) {
    const { item } = data;
    
    if (!item) return;
    
    const newItem = {
      id: item.questionIndex || Date.now(),
      question: item.question || '',
      model: item.model || 'Unknown',
      status: item.status || 'pending',
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      latency: item.latency,
      brand: item.brand,
      preview: item.preview,
      error: item.error
    };
    
    const newItems = [...this.data.intelligenceItems, newItem];
    
    this.setData({
      intelligenceItems: newItems,
      completedTasks: newItems.filter(i => i.status !== 'pending').length
    });
  },

  /**
   * 处理 SSE 完成
   */
  handleSSEComplete: function(data) {
    console.log('[Waiting] Task completed:', data);
    
    wx.showToast({
      title: '诊断完成',
      icon: 'success'
    });
    
    // 延迟跳转到结果页面
    setTimeout(() => {
      wx.navigateTo({
        url: `/pages/report/dashboard/index?executionId=${this.data.executionId}`
      });
    }, 1500);
  },

  /**
   * 页面显示
   */
  onShow: function() {
    // 恢复后台运行时的更新
    if (!this.data.updateTimer) {
      this.startProgressUpdates();
    }
  },

  /**
   * 页面隐藏
   */
  onHide: function() {
    // 暂停更新
    if (this.data.updateTimer) {
      clearInterval(this.data.updateTimer);
      this.setData({ updateTimer: null });
    }
  },

  /**
   * 页面卸载
   */
  onUnload: function() {
    // 清理计时器
    if (this.data.updateTimer) {
      clearInterval(this.data.updateTimer);
    }
    if (this.pipelineTimer) {
      clearInterval(this.pipelineTimer);
    }
    
    // 断开 SSE 连接
    if (this.data.sseClient) {
      this.data.sseClient.disconnect();
    }
  },

  /**
   * 启动进度更新
   */
  startProgressUpdates: function() {
    // 模拟进度更新（实际项目中应从轮询或 SSE 获取）
    const timer = setInterval(() => {
      const elapsed = (Date.now() - this.startTime) / 1000;
      
      // 模拟进度增长（实际应来自后端）
      let progress = Math.min(80, Math.floor(elapsed / 3));
      
      // 计算剩余时间
      const remainingResult = this.remainingTimeCalc.calculate(progress, elapsed);
      
      this.setData({
        progress: progress,
        elapsedTime: elapsed,
        remainingTime: remainingResult.seconds,
        smoothedRemainingTime: remainingResult.display,
        statusText: this.getStatusText(progress),
        stageDescription: this.getStageDescription(progress)
      });
      
      // 检查是否完成
      if (progress >= 100) {
        clearInterval(timer);
        this.onTaskComplete();
      }
    }, 1000);
    
    this.setData({ updateTimer: timer });
  },

  /**
   * 启动情报流水线（模拟）
   */
  startIntelligencePipeline: function() {
    const models = ['DeepSeek', '豆包', '通义千问', '智谱 AI'];
    const questions = ['品牌认知度分析', '竞品对比分析', '情感倾向评估', '市场定位诊断'];
    
    let itemIndex = 0;
    
    // 每 2-3 秒添加一个新情报
    this.pipelineTimer = setInterval(() => {
      if (itemIndex >= 8) {
        clearInterval(this.pipelineTimer);
        return;
      }
      
      const model = models[Math.floor(Math.random() * models.length)];
      const question = questions[Math.floor(Math.random() * questions.length)];
      const status = ['processing', 'success'][Math.floor(Math.random() * 2)];
      
      const newItem = {
        id: Date.now(),
        question: `${question} - ${model}`,
        model: model,
        status: status,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      };
      
      this.setData({
        intelligenceItems: [...this.data.intelligenceItems, newItem],
        completedTasks: this.data.intelligenceItems.length + 1
      });
      
      itemIndex++;
    }, 2500);
  },

  /**
   * 获取状态文本
   */
  getStatusText: function(progress) {
    if (progress < 20) return '正在初始化诊断引擎...';
    if (progress < 40) return '正在分析品牌认知度...';
    if (progress < 60) return '正在进行竞品对比...';
    if (progress < 80) return '正在生成诊断报告...';
    if (progress < 100) return '正在聚合分析结果...';
    return '诊断完成！';
  },

  /**
   * 获取阶段描述
   */
  getStageDescription: function(progress) {
    if (progress < 20) return '阶段 1/4: 初始化';
    if (progress < 40) return '阶段 2/4: 品牌分析';
    if (progress < 60) return '阶段 3/4: 竞品对比';
    if (progress < 80) return '阶段 4/4: 报告生成';
    return '收尾阶段：结果聚合';
  },

  /**
   * 任务完成
   */
  onTaskComplete: function() {
    wx.showToast({
      title: '诊断完成',
      icon: 'success'
    });
    
    // 延迟跳转到结果页面
    setTimeout(() => {
      wx.navigateTo({
        url: `/pages/report/dashboard/index?executionId=${this.data.executionId}`
      });
    }, 1500);
  },

  /**
   * 格式化时间
   */
  formatTime: function(seconds) {
    if (!seconds || seconds <= 0) return '计算中...';
    
    if (seconds < 60) {
      return `${Math.round(seconds)}秒`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${mins}分${secs}秒`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}小时${mins}分钟`;
    }
  }
});
