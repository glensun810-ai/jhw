// pages/report/source-graph/detail.js
/**
 * 信源图谱详情页
 * 展示信源引用排名、类型分布、可信度分析
 */

const app = getApp();
const logger = require('../../../utils/logger');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    error: null,
    
    // 品牌名称
    brandName: '',
    
    // 信源数据
    sourceData: null,
    
    // 信源概览
    totalSources: 0,
    citedSources: 0,
    citationRate: 0,
    
    // 信源排名
    sourceRanking: [],
    
    // 信源类型分布
    sourceTypes: [],
    
    // 可信度分析
    credibilityData: null,
    
    // 执行 ID
    executionId: null
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    logger.info('信源图谱详情页加载', { options });
    
    // 获取执行 ID
    if (options && options.executionId) {
      this.setData({ executionId: options.executionId });
    }
    
    // 加载信源数据
    this.loadSourceData();
  },

  /**
   * 加载信源数据
   */
  loadSourceData() {
    try {
      this.setData({ loading: true, error: null });
      
      const executionId = this.data.executionId;
      
      if (executionId) {
        // 从服务器获取数据
        this.fetchFromServer(executionId);
      } else {
        // 从本地存储获取
        this.loadFromLocal();
      }
    } catch (error) {
      logger.error('加载信源数据失败', error);
      this.setData({ 
        loading: false, 
        error: '加载失败' 
      });
    }
  },

  /**
   * 从服务器获取数据
   */
  fetchFromServer(executionId) {
    const token = wx.getStorageSync('token');
    
    wx.request({
      url: `${app.globalData.serverUrl}/api/source-intelligence/${executionId}`,
      header: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          this.processSourceData(res.data);
        } else {
          throw new Error(res.data.error || '请求失败');
        }
      },
      fail: (err) => {
        logger.error('请求失败', err);
        // 降级到本地数据
        this.loadFromLocal();
      }
    });
  },

  /**
   * 从本地存储加载
   */
  loadFromLocal() {
    const sourceData = wx.getStorageSync('source_intelligence_data');
    
    if (sourceData && sourceData.source_intelligence) {
      this.processSourceData(sourceData);
    } else {
      this.setData({ 
        loading: false, 
        error: '暂无数据' 
      });
    }
  },

  /**
   * 处理信源数据
   */
  processSourceData(rawData) {
    const sourceIntelligence = rawData.source_intelligence || rawData;
    
    // 提取信源列表
    const sources = sourceIntelligence.sources || sourceIntelligence.source_list || [];
    
    // 计算信源概览
    const totalSources = sources.length;
    const citedSources = sources.filter(s => s.cited === true || s.citations > 0).length;
    const citationRate = totalSources > 0 ? Math.round((citedSources / totalSources) * 100) : 0;
    
    // 生成信源排名
    const sourceRanking = sources
      .map((source, index) => ({
        rank: index + 1,
        name: source.name || source.title || '未知信源',
        domain: source.domain || source.url || '',
        citations: source.citations || 0,
        percentage: totalSources > 0 ? Math.round((source.citations / sources.reduce((sum, s) => sum + (s.citations || 0), 0)) * 100) : 0
      }))
      .sort((a, b) => b.citations - a.citations)
      .slice(0, 10);
    
    // 计算信源类型分布
    const typeMap = {};
    sources.forEach(source => {
      const type = source.type || source.category || '其他';
      if (!typeMap[type]) {
        typeMap[type] = { type, count: 0 };
      }
      typeMap[type].count++;
    });
    
    const sourceTypes = Object.values(typeMap)
      .map(item => ({
        ...item,
        percentage: totalSources > 0 ? Math.round((item.count / totalSources) * 100) : 0
      }))
      .sort((a, b) => b.count - a.count);
    
    // 计算可信度分布
    const credibilityData = {
      high: sources.filter(s => s.credibility === 'high' || s.trust_score >= 80).length,
      medium: sources.filter(s => s.credibility === 'medium' || (s.trust_score >= 50 && s.trust_score < 80)).length,
      low: sources.filter(s => s.credibility === 'low' || s.trust_score < 50).length
    };
    
    // 更新页面数据
    this.setData({
      loading: false,
      sourceData: sourceIntelligence,
      brandName: sourceIntelligence.brand_name || rawData.brand_name || '未知品牌',
      totalSources,
      citedSources,
      citationRate,
      sourceRanking,
      sourceTypes,
      credibilityData
    });
    
    logger.info('信源数据加载成功', { totalSources, citedSources });
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.loadSourceData();
    wx.stopPullDownRefresh();
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: `${this.data.brandName} - 信源图谱分析`,
      path: `/pages/report/source-graph/detail?executionId=${this.data.executionId}`
    };
  }
});
