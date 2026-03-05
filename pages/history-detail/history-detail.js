// pages/history-detail/history-detail.js
/**
 * 历史记录详情页 - 专业版
 * 
 * 功能：
 * 1. 完整报告详情展示
 * 2. 删除报告
 * 3. 导出/分享报告
 * 4. 重新诊断
 * 
 * 作者：前端工程师 & UI 设计大师
 * 日期：2026-03-04
 * 版本：2.0
 */

const { getSavedResults } = require('../../utils/saved-results-sync');
const { exportPdfReport } = require('../../api/export');
const { deleteHistoryReport } = require('../../api/history');
const { clearDiagnosisResult } = require('../../utils/storage-manager');
const logger = require('../../utils/logger');

Page({
  data: {
    // 基础信息
    brandName: '',
    timestamp: 0,
    formattedTime: '',
    executionId: null,
    reportId: null,
    
    // 评分信息
    overallScore: 0,
    overallGrade: 'D',
    overallSummary: '暂无评价',
    overallAuthority: 0,
    overallVisibility: 0,
    overallPurity: 0,
    overallConsistency: 0,
    
    // 详细数据
    detailedResults: [],
    aiModels: [],
    competitors: [],
    questions: [],
    
    // UI 状态
    loading: true,
    showActions: false,
    recordId: null
  },

  onLoad: function(options) {
    // 从参数获取记录 ID 或执行 ID
    const recordId = options.id;
    const executionId = options.executionId;
    const brandName = options.brandName ? decodeURIComponent(options.brandName) : '';

    if (!recordId && !executionId) {
      wx.showToast({
        title: '缺少记录 ID',
        icon: 'none'
      });
      return;
    }

    this.setData({
      recordId,
      executionId: executionId || recordId,
      brandName,
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

    // 格式化时间
    const timestamp = record.timestamp || record.test_date || record.created_at || Date.now();
    
    this.setData({
      brandName: record.brandName || record.brand_name || this.data.brandName || '未知品牌',
      timestamp,
      formattedTime: this.formatDateTime(timestamp),
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
      executionId: record.executionId || record.result_id || record.id,
      reportId: record.id || record.reportId
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

  // 格式化日期时间
  formatDateTime: function(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // 少于 1 分钟
    if (diff < 60000) return '刚刚';
    // 少于 1 小时
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    // 少于 24 小时
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    // 少于 7 天
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
    
    // 超过 7 天显示具体日期
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  },

  // 切换操作菜单
  toggleActions: function() {
    this.setData({
      showActions: !this.data.showActions
    });
  },

  // 删除报告
  onDeleteReport: function() {
    const { executionId, reportId, brandName } = this.data;
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除"${brandName}"的诊断报告吗？此操作不可恢复。`,
      confirmText: '删除',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' });
          
          try {
            // 调用删除 API
            if (reportId) {
              await deleteHistoryReport(executionId, reportId);
            }
            
            // 清除本地缓存
            clearDiagnosisResult(executionId);
            
            wx.hideLoading();
            
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            });
            
            // 返回历史列表
            setTimeout(() => {
              wx.navigateBack();
            }, 1500);
            
          } catch (error) {
            console.error('删除失败:', error);
            wx.hideLoading();
            wx.showToast({
              title: '删除失败，请重试',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  // 导出报告
  onExportReport: function() {
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

  // 重新诊断
  onReDiagnose: function() {
    const { brandName, competitors } = this.data;
    
    // 跳转到诊断页面，带上品牌信息
    wx.navigateTo({
      url: `/pages/index/index?brandName=${encodeURIComponent(brandName)}&competitors=${encodeURIComponent(JSON.stringify(competitors))}`
    });
  },

  // 分享
  onShareAppMessage: function() {
    const { brandName, overallScore } = this.data;
    return {
      title: `${brandName} AI 诊断报告 - 得分${overallScore}`,
      path: `/pages/history-detail/history-detail?executionId=${this.data.executionId}`
    };
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  // 查看历史
  viewHistory: function() {
    wx.navigateBack();
  }
});
