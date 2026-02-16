/**
 * MVP 结果页 - 简化版品牌诊断结果展示
 * 遵循 DEVELOPMENT_SOP.md 第四阶段规范
 * 不修改现有 pages/results/，创建独立页面
 */

const { processMVPResults } = require('../../services/mvpService');

Page({
  data: {
    brandName: '',
    results: [],
    summary: {
      totalQuestions: 0,
      completedQuestions: 0,
      averageResponseLength: 0
    },
    loading: true
  },

  onLoad(options) {
    const { results, brand } = options;
    
    if (!results) {
      wx.showToast({ 
        title: '未找到结果数据', 
        icon: 'none',
        duration: 2000
      });
      this.setData({ loading: false });
      return;
    }

    try {
      // 解析结果数据
      const parsedResults = JSON.parse(decodeURIComponent(results));
      const brandName = decodeURIComponent(brand || '');
      
      // 调用Service层处理结果
      const processedData = processMVPResults(parsedResults, brandName);
      
      this.setData({
        brandName: processedData.brandName,
        results: processedData.results,
        summary: processedData.summary,
        loading: false
      });
      
      console.log('[MVP Results] 结果数据:', processedData);
    } catch (error) {
      console.error('解析结果失败:', error);
      wx.showToast({ 
        title: '结果解析失败', 
        icon: 'none',
        duration: 2000
      });
      this.setData({ loading: false });
    }
  },

  /**
   * 复制回答内容
   */
  copyResponse(e) {
    const { content } = e.currentTarget.dataset;
    if (!content || content === '无响应') {
      wx.showToast({ title: '无内容可复制', icon: 'none' });
      return;
    }
    
    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({ title: '已复制到剪贴板', icon: 'success' });
      },
      fail: () => {
        wx.showToast({ title: '复制失败', icon: 'none' });
      }
    });
  },

  /**
   * 展开/收起长文本
   */
  toggleExpand(e) {
    const { index } = e.currentTarget.dataset;
    const results = [...this.data.results];
    const item = results[index];
    
    item.expanded = !item.expanded;
    this.setData({ results });
  },

  /**
   * 返回MVP首页
   */
  goBack() {
    wx.navigateBack();
  },

  /**
   * 前往完整版结果页
   */
  goToStandardResults() {
    wx.showModal({
      title: '提示',
      content: '完整版结果页需要更多数据支持，当前为MVP简化版',
      showCancel: false,
      confirmText: '知道了'
    });
  },

  /**
   * 分享结果
   */
  onShareAppMessage() {
    const { brandName } = this.data;
    return {
      title: `${brandName} 的AI品牌诊断报告`,
      path: '/pages/mvp-index/mvp-index'
    };
  }
});
