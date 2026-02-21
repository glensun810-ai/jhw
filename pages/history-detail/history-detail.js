// pages/history-detail/history-detail.js
/**
 * 历史记录详情页
 * 展示单次测试的完整详情
 */

const { getSavedResults } = require('../../utils/saved-results-sync');
const { exportPdfReport } = require('../../api/export');
const logger = require('../../utils/logger');

Page({
  data: {
    brandName: '',
    timestamp: 0,
    overallScore: 0,
    overallGrade: 'D',
    overallSummary: '暂无评价',
    overallAuthority: 0,
    overallVisibility: 0,
    overallPurity: 0,
    overallConsistency: 0,
    detailedResults: [],
    aiModels: [],
    competitors: [],
    questions: [],
    loading: true,
    recordId: null,
    executionId: null
  },

  onLoad: function(options) {
    // 从参数获取记录 ID 或执行 ID
    const recordId = options.id;
    const executionId = options.executionId;

    if (!recordId && !executionId) {
      wx.showToast({
        title: '缺少记录 ID',
        icon: 'none'
      });
      return;
    }

    this.setData({ 
      recordId, 
      executionId,
      loading: true 
    });

    // 加载历史记录
    if (executionId) {
      this.loadFromServer(executionId);
    } else {
      this.loadHistoryRecord(recordId);
    }
  },

  // 从服务器加载
  loadFromServer: function(executionId) {
    const token = wx.getStorageSync('token');
    
    wx.request({
      url: `${getApp().globalData.serverUrl}/api/test-history`,
      header: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      data: {
        executionId: executionId
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          const record = res.data.records?.[0];
          if (record) {
            this.processHistoryData(record);
          } else {
            this.loadHistoryRecord(executionId); // 降级到本地
          }
        } else {
          this.loadHistoryRecord(executionId); // 降级到本地
        }
      },
      fail: (err) => {
        logger.error('加载失败', err);
        this.loadHistoryRecord(executionId); // 降级到本地
      }
    });
  },

  // 加载历史记录
  loadHistoryRecord: function(recordId) {
    const that = this;
    
    getSavedResults()
      .then(searchResults => {
        // 查找指定 ID 的记录
        const record = searchResults.find(item => 
          item.id === recordId || 
          item.executionId === recordId ||
          item.result_id === recordId
        );

        if (!record) {
          wx.showToast({
            title: '未找到记录',
            icon: 'none'
          });
          that.setData({ loading: false });
          return;
        }

        that.processHistoryData(record);
      })
      .catch(error => {
        console.error('加载历史记录失败', error);
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        });
        that.setData({ loading: false });
      });
  },

  // 处理历史数据
  processHistoryData: function(record) {
    const results = record.results || record.result || record;
    const detailedResults = results.detailed_results || results.detailedResults || [];
    
    // 提取 AI 模型列表
    const aiModels = [...new Set(detailedResults.map(r => r.aiModel || r.ai_model || 'Unknown'))];
    
    // 提取竞品列表
    const competitors = record.competitors || record.competitorBrands || [];
    
    // 提取问题列表
    const questions = [...new Set(detailedResults.map(r => r.question || ''))];

    this.setData({
      brandName: record.brandName || record.brand_name || '未知品牌',
      timestamp: record.timestamp || record.test_date || Date.now(),
      overallScore: results.overallScore || results.overall_score || 0,
      overallGrade: this.calculateGrade(results.overallScore || results.overall_score || 0),
      overallSummary: this.getSummary(results.overallScore || results.overall_score || 0),
      overallAuthority: results.overallAuthority || results.authority || 0,
      overallVisibility: results.overallVisibility || results.visibility || 0,
      overallPurity: results.overallPurity || results.purity || 0,
      overallConsistency: results.overallConsistency || results.consistency || 0,
      detailedResults: detailedResults,
      aiModels: aiModels,
      competitors: competitors,
      questions: questions,
      loading: false,
      executionId: record.executionId || record.result_id || record.id
    });
  },

  // 计算等级
  calculateGrade: function(score) {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'E';
  },

  // 获取评价
  getSummary: function(score) {
    if (score >= 90) return '表现优秀';
    if (score >= 80) return '表现良好';
    if (score >= 70) return '表现中等';
    if (score >= 60) return '有待改进';
    return '需要加强';
  },

  // 格式化日期
  formatDate: function(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  // 查看历史
  viewHistory: function() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  // 生成报告
  generateReport: function() {
    if (!this.data.executionId) {
      wx.showToast({
        title: '无法生成报告',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '正在生成报告...',
      mask: true
    });

    exportPdfReport({
      executionId: this.data.executionId
    })
    .then(() => {
      wx.hideLoading();
      wx.showToast({
        title: '报告已保存',
        icon: 'success'
      });
    })
    .catch(error => {
      wx.hideLoading();
      wx.showToast({
        title: error.message || '生成失败',
        icon: 'none'
      });
    });
  },

  // 分享
  onShareAppMessage: function() {
    return {
      title: `${this.data.brandName} - AI 诊断报告`,
      path: `/pages/history-detail/history-detail?id=${this.data.recordId || this.data.executionId}`
    };
  }
});
