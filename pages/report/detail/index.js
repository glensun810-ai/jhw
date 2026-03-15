// pages/report/detail/index.js
// P21 修复版 - 从 API 加载诊断详情

const app = getApp();
var API_BASE_URL = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';

Page({
  data: {
    questionIndex: 0,
    questionText: '',
    modelResults: [],
    currentModelIndex: 0,
    currentModelData: null,
    renderedText: '',
    isRendering: false,
    renderTimer: null,
    loading: true,
    loadError: null,
    executionId: null,
    reportData: null,
    brandName: '',
    competitorBrands: [],
    statistics: {},
    analysis: {}
  },

  onLoad: function(options) {
    console.log('[Detail] 页面加载，options:', options);
    this.setData({ loading: true, loadError: null });

    if (options && options.executionId) {
      console.log('[Detail] 从 API 加载:', options.executionId);
      this.loadDiagnosisFromAPI(options.executionId);
    } else {
      this.setData({
        loading: false,
        loadError: '缺少 executionId 参数'
      });
    }
  },

  onUnload: function() {
    if (this.data.renderTimer) {
      clearInterval(this.data.renderTimer);
      this.data.renderTimer = null;
    }
  },

  loadDiagnosisFromAPI: function(executionId) {
    var that = this;
    console.log('[Detail] 开始加载诊断详情:', executionId);
    
    wx.request({
      url: API_BASE_URL + '/api/diagnosis/history/' + executionId + '/detail',
      method: 'GET',
      data: { userOpenid: app.globalData.userOpenid || 'anonymous' },
      timeout: 30000,
      success: function(res) {
        console.log('[Detail] API 响应:', res.data);
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          var data = res.data.data;
          var report = data.report;
          var results = data.results || [];
          var analysis = data.analysis || {};
          var statistics = data.statistics || {};
          
          console.log('[Detail] 数据提取:', {
            reportId: report ? report.id : 'null',
            resultsCount: results.length,
            brandName: report ? report.brand_name : 'null'
          });
          
          if (results.length > 0) {
            var firstQuestion = results[0].question || '';
            var resultsForFirstQ = [];
            for (var i = 0; i < results.length; i++) {
              if (results[i].question === firstQuestion) {
                resultsForFirstQ.push(results[i]);
              }
            }
            
            console.log('[Detail] 第一个问题的结果数:', resultsForFirstQ.length);
            
            that.setData({
              executionId: executionId,
              reportData: report,
              brandName: report ? report.brand_name : '未知品牌',
              competitorBrands: report ? report.competitor_brands : [],
              statistics: statistics,
              analysis: analysis,
              questionText: firstQuestion,
              modelResults: resultsForFirstQ,
              currentModelIndex: 0,
              currentModelData: resultsForFirstQ[0],
              loading: false
            });
            
            if (resultsForFirstQ[0]) {
              var content = resultsForFirstQ[0].response_content || resultsForFirstQ[0].content || '';
              that.startChunkedRendering(content);
            }
            
            wx.showToast({ title: '加载成功', icon: 'success' });
          } else {
            that.setData({
              loading: false,
              loadError: '暂无诊断结果'
            });
          }
        } else {
          that.setData({
            loading: false,
            loadError: '数据加载失败：' + (res.data ? res.data.error : '未知错误')
          });
        }
      },
      fail: function(error) {
        console.error('[Detail] API 请求失败:', error);
        that.setData({
          loading: false,
          loadError: '网络请求失败，请检查网络连接'
        });
      }
    });
  },

  startChunkedRendering: function(fullText) {
    var that = this;
    
    if (this.data.renderTimer) {
      clearInterval(this.data.renderTimer);
    }
    
    this.setData({ renderedText: '', isRendering: true });
    
    var index = 0;
    var chunkSize = 300;
    var interval = 40;
    
    var timer = setInterval(function() {
      if (index >= fullText.length) {
        clearInterval(timer);
        that.setData({ isRendering: false });
        return;
      }
      
      var nextChunk = fullText.substring(index, index + chunkSize);
      var formattedChunk = that.formatText(nextChunk);
      
      that.setData({
        renderedText: that.data.renderedText + formattedChunk
      });
      
      index += chunkSize;
    }, interval);
    
    this.data.renderTimer = timer;
  },

  formatText: function(text) {
    if (!text) return '';
    return text
      .replace(/\n/g, '<br/>')
      .replace(/\s/g, '&nbsp;')
      .replace(/<br\/>\s*<br\/>/g, '<br/><br/>');
  },

  switchModel: function(e) {
    var index = e.currentTarget.dataset.index;
    if (index === this.data.currentModelIndex) return;
    
    var modelData = this.data.modelResults[index];
    this.setData({
      currentModelIndex: index,
      currentModelData: modelData
    });
    
    var content = modelData.response_content || modelData.content || '';
    this.startChunkedRendering(content);
    wx.vibrateShort({ type: 'light' });
  },

  copyContent: function() {
    var content = this.data.currentModelData ? 
      (this.data.currentModelData.response_content || this.data.currentModelData.content) : null;
    
    if (!content) {
      wx.showToast({ title: '无内容可复制', icon: 'none' });
      return;
    }
    
    wx.setClipboardData({
      data: content,
      success: function() { wx.showToast({ title: '已复制', icon: 'success' }); }
    });
  },

  viewBrandAnalysis: function() {
    var analysis = this.data.analysis;
    if (!analysis || !analysis.brandAnalysis) {
      wx.showToast({ title: '暂无品牌分析数据', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '品牌分析',
      content: JSON.stringify(analysis.brandAnalysis, null, 2),
      showCancel: false,
      confirmText: '关闭'
    });
  },

  viewTop3Brands: function() {
    var top3 = this.data.analysis ? this.data.analysis.top3Brands : [];
    if (!top3 || top3.length === 0) {
      wx.showToast({ title: '暂无 Top3 品牌数据', icon: 'none' });
      return;
    }
    
    var content = '';
    for (var i = 0; i < top3.length; i++) {
      content += (i + 1) + '. ' + top3[i].name + '\n   理由：' + top3[i].reason + '\n\n';
    }
    
    wx.showModal({
      title: 'Top3 品牌排名',
      content: content,
      showCancel: false,
      confirmText: '关闭'
    });
  },

  viewStatistics: function() {
    var stats = this.data.statistics;
    if (!stats) {
      wx.showToast({ title: '暂无统计信息', icon: 'none' });
      return;
    }
    
    var content = '总结果数：' + (stats.total_results || 0) + '\n' +
      '问题数：' + (stats.total_questions || 0) + '\n' +
      'AI 平台：' + (stats.platforms || []).join(', ');
    
    wx.showModal({
      title: '诊断统计',
      content: content,
      showCancel: false,
      confirmText: '关闭'
    });
  },

  goBack: function() {
    wx.navigateBack({
      delta: 1,
      fail: function() { wx.switchTab({ url: '/pages/index/index' }); }
    });
  }
});
