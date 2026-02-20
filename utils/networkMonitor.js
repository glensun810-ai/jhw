/**
 * 网络质量监测器 - 个性化学习基础
 * 
 * 功能:
 * 1. 实时监测网络延迟
 * 2. 记录用户网络环境
 * 3. 网络质量评分
 * 4. 历史趋势分析
 */

const STORAGE_KEY = 'network_quality_history';
const MAX_RECORDS = 100;

class NetworkMonitor {
  constructor() {
    this.history = this.loadHistory();
    this.currentLatency = 0;
    this.qualityScore = 100;
  }

  /**
   * 加载历史记录
   */
  loadHistory() {
    try {
      const data = wx.getStorageSync(STORAGE_KEY);
      return Array.isArray(data) ? data : [];
    } catch (e) {
      console.error('加载网络历史失败', e);
      return [];
    }
  }

  /**
   * 保存历史记录
   */
  saveHistory() {
    try {
      wx.setStorageSync(STORAGE_KEY, this.history);
    } catch (e) {
      console.error('保存网络历史失败', e);
    }
  }

  /**
   * 记录网络延迟
   * @param {number} latency - 延迟 (毫秒)
   * @param {string} networkType - 网络类型 (wifi/4g/5g 等)
   */
  recordLatency(latency, networkType = 'unknown') {
    const record = {
      timestamp: Date.now(),
      latency: latency,
      networkType: networkType,
      quality: this.calculateQuality(latency)
    };

    this.history.push(record);
    this.currentLatency = latency;
    this.qualityScore = record.quality;

    // 保留最近 N 条
    if (this.history.length > MAX_RECORDS) {
      this.history = this.history.slice(-MAX_RECORDS);
    }

    this.saveHistory();
    return record;
  }

  /**
   * 计算网络质量评分
   */
  calculateQuality(latency) {
    if (latency < 500) return 100;  // 优秀
    if (latency < 1000) return 80;  // 良好
    if (latency < 2000) return 60;  // 一般
    if (latency < 3000) return 40;  // 较差
    return 20;  // 差
  }

  /**
   * 获取平均延迟
   */
  getAverageLatency() {
    if (this.history.length === 0) return 2000;
    
    const recent = this.history.slice(-10);
    const sum = recent.reduce((s, r) => s + r.latency, 0);
    return Math.round(sum / recent.length);
  }

  /**
   * 获取网络质量等级
   */
  getQualityLevel() {
    const avg = this.getAverageLatency();
    
    if (avg < 500) return { level: 'excellent', text: '优秀', color: '#22c55e' };
    if (avg < 1000) return { level: 'good', text: '良好', color: '#3b82f6' };
    if (avg < 2000) return { level: 'fair', text: '一般', color: '#f59e0b' };
    if (avg < 3000) return { level: 'poor', text: '较差', color: '#ef4444' };
    return { level: 'bad', text: '差', color: '#dc2626' };
  }

  /**
   * 获取网络类型分布
   */
  getNetworkTypeDistribution() {
    const distribution = {};
    this.history.forEach(record => {
      distribution[record.networkType] = (distribution[record.networkType] || 0) + 1;
    });
    return distribution;
  }

  /**
   * 获取网络质量趋势
   */
  getTrend() {
    if (this.history.length < 10) return 'stable';
    
    const recent = this.history.slice(-10);
    const older = this.history.slice(-20, -10);
    
    const recentAvg = recent.reduce((s, r) => s + r.latency, 0) / recent.length;
    const olderAvg = older.reduce((s, r) => s + r.latency, 0) / older.length;
    
    const change = (recentAvg - olderAvg) / olderAvg;
    
    if (change < -0.1) return 'improving';
    if (change > 0.1) return 'worsening';
    return 'stable';
  }

  /**
   * 获取网络质量因子 (用于时间预估)
   */
  getQualityFactor() {
    const avg = this.getAverageLatency();
    const baseline = 1000;
    return Math.max(1.0, Math.min(2.0, avg / baseline));
  }

  /**
   * 清除历史记录
   */
  clearHistory() {
    this.history = [];
    wx.removeStorageSync(STORAGE_KEY);
  }

  /**
   * 获取统计信息
   */
  getStats() {
    if (this.history.length === 0) {
      return {
        count: 0,
        avgLatency: 0,
        minLatency: 0,
        maxLatency: 0,
        qualityScore: 100
      };
    }

    const latencies = this.history.map(h => h.latency);
    
    return {
      count: this.history.length,
      avgLatency: Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length),
      minLatency: Math.min(...latencies),
      maxLatency: Math.max(...latencies),
      qualityScore: this.qualityScore,
      currentLatency: this.currentLatency,
      trend: this.getTrend()
    };
  }
}

module.exports = NetworkMonitor;
