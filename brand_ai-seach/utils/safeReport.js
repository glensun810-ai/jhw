/**
 * 安全上报工具 - 兼容性增强版
 * 
 * 功能:
 * 1. 自动检测 API 可用性
 * 2. 优雅降级处理
 * 3. 避免 Worker 线程报错
 * 
 * 使用示例:
 * safeReport.reportAnalytics('event_name', { key: 'value' });
 * safeReport.reportMonitor('monitor_id', value);
 */

const logger = require('./logger');

/**
 * 安全上报工具类
 */
class SafeReport {
  constructor() {
    this.enabled = true;
    this.checkApiSupport();
  }

  /**
   * 检查 API 支持情况
   */
  checkApiSupport() {
    this.supports = {
      reportAnalytics: typeof wx.reportAnalytics === 'function',
      reportMonitor: typeof wx.reportMonitor === 'function',
      reportEvent: typeof wx.reportEvent === 'function',
      reportPerformance: typeof wx.reportPerformance === 'function',
      reportRealtimeAction: typeof wx.reportRealtimeAction === 'function'
    };

    // 记录不支持的 API
    Object.keys(this.supports).forEach(api => {
      if (!this.supports[api]) {
        logger.debug(`API 不支持：${api}`);
      }
    });
  }

  /**
   * 安全调用上报接口
   * @param {string} apiName - API 名称
   * @param {Function} apiCall - API 调用函数
   * @param {Object} params - 参数
   */
  safeCall(apiName, apiCall, params) {
    if (!this.enabled) {
      return;
    }

    try {
      // 检查 API 是否支持
      if (typeof apiCall !== 'function') {
        logger.warn(`上报接口不可用：${apiName}`);
        return;
      }

      // 调用 API
      apiCall(params);
    } catch (error) {
      // 捕获所有错误，避免影响主流程
      logger.warn(`上报失败：${apiName}`, error);
    }
  }

  /**
   * 安全上报分析数据
   * @param {string} eventId - 事件 ID
   * @param {Object} params - 参数
   */
  reportAnalytics(eventId, params) {
    this.safeCall('reportAnalytics', wx.reportAnalytics, {
      eventId: eventId,
      params: params
    });
  }

  /**
   * 安全上报监控数据
   * @param {string} name - 监控名称
   * @param {number} value - 数值
   */
  reportMonitor(name, value) {
    this.safeCall('reportMonitor', wx.reportMonitor, {
      name: name,
      value: value
    });
  }

  /**
   * 安全上报事件
   * @param {string} eventId - 事件 ID
   * @param {Object} params - 参数
   */
  reportEvent(eventId, params) {
    this.safeCall('reportEvent', wx.reportEvent, {
      event_id: eventId,
      event_params: params
    });
  }

  /**
   * 安全上报性能数据
   * @param {string} metricId - 指标 ID
   * @param {Object} params - 参数
   */
  reportPerformance(metricId, params) {
    this.safeCall('reportPerformance', wx.reportPerformance, {
      metricId: metricId,
      ...params
    });
  }

  /**
   * 安全上报实时行为（如果支持）
   * @param {Object} params - 参数
   */
  reportRealtimeAction(params) {
    // 特殊处理：reportRealtimeAction 在某些环境不支持
    if (this.supports.reportRealtimeAction) {
      this.safeCall('reportRealtimeAction', wx.reportRealtimeAction, params);
    } else {
      // 静默跳过，不报错
      logger.debug('当前环境不支持 reportRealtimeAction，已跳过');
    }
  }

  /**
   * 禁用上报
   */
  disable() {
    this.enabled = false;
    logger.info('上报功能已禁用');
  }

  /**
   * 启用上报
   */
  enable() {
    this.enabled = true;
    logger.info('上报功能已启用');
  }
}

// 创建单例
const safeReport = new SafeReport();

module.exports = {
  safeReport,
  SafeReport
};
