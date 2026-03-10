/**
 * 性能监控服务
 * 负责监控和优化小程序性能
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

const performanceMonitor = {
  // 性能数据
  metrics: {
    pageLoadTime: [],
    apiResponseTime: [],
    renderTime: [],
    memoryUsage: []
  },

  // 性能阈值
  thresholds: {
    pageLoadTime: 1000, // 1 秒
    apiResponseTime: 2000, // 2 秒
    renderTime: 500, // 0.5 秒
    memoryUsage: 100 // 100MB
  },

  /**
   * 初始化性能监控
   */
  init: function() {
    console.log('[Performance] 性能监控已初始化');
    this.startMonitoring();
  },

  /**
   * 开始监控
   */
  startMonitoring: function() {
    // 定期收集内存数据
    setInterval(() => {
      this.collectMemoryUsage();
    }, 10000); // 每 10 秒
  },

  /**
   * 记录页面加载时间
   */
  recordPageLoad: function(pageName, startTime) {
    const loadTime = Date.now() - startTime;
    this.metrics.pageLoadTime.push({
      page: pageName,
      time: loadTime,
      timestamp: Date.now()
    });

    // 检查是否超过阈值
    if (loadTime > this.thresholds.pageLoadTime) {
      console.warn(`[Performance] ${pageName} 加载时间过长：${loadTime}ms`);
    }

    console.log(`[Performance] ${pageName} 加载时间：${loadTime}ms`);
  },

  /**
   * 记录 API 响应时间
   */
  recordApiResponse: function(apiName, startTime, success = true) {
    const responseTime = Date.now() - startTime;
    this.metrics.apiResponseTime.push({
      api: apiName,
      time: responseTime,
      success,
      timestamp: Date.now()
    });

    // 检查是否超过阈值
    if (responseTime > this.thresholds.apiResponseTime) {
      console.warn(`[Performance] ${apiName} 响应时间过长：${responseTime}ms`);
    }
  },

  /**
   * 记录渲染时间
   */
  recordRenderTime: function(componentName, startTime) {
    const renderTime = Date.now() - startTime;
    this.metrics.renderTime.push({
      component: componentName,
      time: renderTime,
      timestamp: Date.now()
    });

    // 检查是否超过阈值
    if (renderTime > this.thresholds.renderTime) {
      console.warn(`[Performance] ${componentName} 渲染时间过长：${renderTime}ms`);
    }
  },

  /**
   * 收集内存使用数据
   */
  collectMemoryUsage: function() {
    try {
      const memoryInfo = wx.getSystemInfoSync();
      const memoryUsage = {
        used: memoryInfo.memorySize || 0,
        timestamp: Date.now()
      };

      this.metrics.memoryUsage.push(memoryUsage);

      // 保留最近 100 条数据
      if (this.metrics.memoryUsage.length > 100) {
        this.metrics.memoryUsage.shift();
      }

      // 检查是否超过阈值
      if (memoryInfo.memorySize > this.thresholds.memoryUsage * 1024 * 1024) {
        console.warn(`[Performance] 内存使用过高：${Math.round(memoryInfo.memorySize / 1024 / 1024)}MB`);
      }
    } catch (error) {
      console.error('[Performance] 收集内存数据失败:', error);
    }
  },

  /**
   * 获取性能报告
   */
  getPerformanceReport: function() {
    const report = {
      pageLoadTime: this.calculateAverage(this.metrics.pageLoadTime),
      apiResponseTime: this.calculateAverage(this.metrics.apiResponseTime),
      renderTime: this.calculateAverage(this.metrics.renderTime),
      memoryUsage: this.getAverageMemoryUsage(),
      timestamp: Date.now()
    };

    console.log('[Performance] 性能报告:', report);
    return report;
  },

  /**
   * 计算平均值
   */
  calculateAverage: function(data) {
    if (data.length === 0) return 0;
    const sum = data.reduce((acc, item) => acc + item.time, 0);
    return Math.round(sum / data.length);
  },

  /**
   * 获取平均内存使用
   */
  getAverageMemoryUsage: function() {
    if (this.metrics.memoryUsage.length === 0) return 0;
    const sum = this.metrics.memoryUsage.reduce((acc, item) => acc + item.used, 0);
    return Math.round(sum / this.metrics.memoryUsage.length / 1024 / 1024);
  },

  /**
   * 清除性能数据
   */
  clearMetrics: function() {
    this.metrics = {
      pageLoadTime: [],
      apiResponseTime: [],
      renderTime: [],
      memoryUsage: []
    };
    console.log('[Performance] 性能数据已清除');
  },

  /**
   * 导出性能数据
   */
  exportMetrics: function() {
    return JSON.stringify(this.metrics, null, 2);
  }
};

module.exports = {
  performanceMonitor
};
