/**
 * 问题深度诊断详情页 - 页面逻辑（P21 增强版 - 2026-03-14）
 *
 * 核心功能：
 * 1. 按问题索引加载特定问题的所有模型结果
 * 2. 模型切换对比
 * 3. 分片渲染（Chunked Rendering）防止大文本卡顿
 * 4. 归因分析和信源追踪
 * 5. P21 新增：从 API 加载历史诊断数据
 */

const app = getApp();
const API_BASE_URL = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';

Page({
  data: {
    // 问题数据
    questionIndex: 0,
    questionText: '',

    // 模型结果
    modelResults: [],
    currentModelIndex: 0,
    currentModelData: null,

    // 分片渲染
    renderedText: '',
    isRendering: false,
    renderTimer: null,

    // 状态
    loading: true,
    loadError: null,
    
    // P21 新增：诊断详情数据
    executionId: null,
    reportData: null,
    brandName: '',
    competitorBrands: [],
    statistics: {}
  },

  /**
   * 页面加载（P21 增强：支持从 API 加载历史数据）
   */
  onLoad: function(options) {
    try {
      this.setData({ loading: true, loadError: null });

      // P21 新增：优先从 API 加载数据
      if (options.executionId) {
        // 从 API 加载历史诊断数据
        this.loadDiagnosisFromAPI(options.executionId);
        return;
      }

      // 原有逻辑：从全局存储获取数据
      const qIndex = parseInt(options.index) || 0;
      const lastReport = app.globalData.lastReport;

      if (!lastReport || !lastReport.raw) {
        this.setData({
          loading: false,
          loadError: '未找到报告数据，请重新执行测试'
        });
        return;
      }

      const rawData = lastReport.raw;

      // 过滤出该问题下的所有模型结果
      const resultsForThisQ = rawData.filter(r => r.question_id == qIndex);

      if (!resultsForThisQ || resultsForThisQ.length === 0) {
        this.setData({
          loading: false,
          loadError: '未找到该问题的诊断数据'
        });
        return;
      }

      // 设置页面数据
      this.setData({
        questionIndex: qIndex,
        questionText: resultsForThisQ[0]?.question_text || '未知问题',
        modelResults: resultsForThisQ,
        currentModelIndex: 0,
        currentModelData: resultsForThisQ[0],
        loading: false
      });

      // 开始分片渲染
      this.startChunkedRendering(resultsForThisQ[0].content);

    } catch (error) {
      console.error('加载诊断详情失败:', error);
      this.setData({
        loading: false,
        loadError: '加载失败：' + error.message
      });
    }
  },

  /**
   * P21 新增：从 API 加载诊断数据
   */
  loadDiagnosisFromAPI: function(executionId) {
    const that = this;
    
    wx.request({
      url: `${API_BASE_URL}/api/diagnosis/history/${executionId}/detail`,
      method: 'GET',
      data: {
        userOpenid: app.globalData.userOpenid || 'anonymous'
      },
      timeout: 30000,
      success: function(res) {
        if (res.statusCode === 200 && res.data.success) {
          const data = res.data.data;
          
          // 提取报告信息
          const report = data.report;
          const results = data.results || [];
          const analysis = data.analysis || {};
          const statistics = data.statistics || {};
          
          // 提取第一个问题的结果进行展示
          const firstQuestion = results[0]?.question || '';
          const resultsForFirstQ = results.filter(r => r.question === firstQuestion);
          
          that.setData({
            executionId: executionId,
            reportData: report,
            brandName: report.brand_name || '未知品牌',
            competitorBrands: report.competitor_brands || [],
            statistics: statistics,
            questionText: firstQuestion,
            modelResults: resultsForFirstQ,
            currentModelIndex: 0,
            currentModelData: resultsForFirstQ[0],
            loading: false
          });
          
          // 开始分片渲染
          if (resultsForFirstQ[0]) {
            that.startChunkedRendering(resultsForFirstQ[0].response_content || resultsForFirstQ[0].content || '');
          }
          
          wx.showToast({
            title: '加载成功',
            icon: 'success'
          });
        } else {
          that.setData({
            loading: false,
            loadError: '数据加载失败：' + (res.data.error || '未知错误')
          });
        }
      },
      fail: function(error) {
        console.error('API 请求失败:', error);
        that.setData({
          loading: false,
          loadError: '网络请求失败，请检查网络连接'
        });
      }
    });
  },

  /**
   * 页面卸载时清理定时器
   */
  onUnload: function() {
    if (this.data.renderTimer) {
      clearInterval(this.data.renderTimer);
      this.data.renderTimer = null;
    }
  },

  /**
   * 分片渲染逻辑：防止大文本导致页面卡顿
   * 每 40ms 渲染 300 字，保持流畅体验
   */
  startChunkedRendering: function(fullText) {
    // 清理之前的定时器
    if (this.data.renderTimer) {
      clearInterval(this.data.renderTimer);
    }

    this.setData({
      renderedText: '',
      isRendering: true
    });

    let index = 0;
    const chunkSize = 300; // 每片 300 字
    const interval = 40;   // 40ms 渲染一次

    const timer = setInterval(() => {
      if (index >= fullText.length) {
        clearInterval(timer);
        this.setData({ isRendering: false });
        return;
      }

      // 获取下一个片段
      const nextChunk = fullText.substring(index, index + chunkSize);

      // 格式化文本（处理换行和空格）
      const formattedChunk = this.formatText(nextChunk);

      // 追加到已渲染内容
      this.setData({
        renderedText: this.data.renderedText + formattedChunk
      });

      index += chunkSize;
    }, interval);

    this.data.renderTimer = timer;
  },

  /**
   * 格式化文本：转换为 rich-text 可读的 HTML
   */
  formatText: function(text) {
    if (!text) return '';

    return text
      .replace(/\n/g, '<br/>')      // 换行符转<br/>
      .replace(/\s/g, '&nbsp;')     // 空格转&nbsp;
      .replace(/<br\/>\s*<br\/>/g, '<br/><br/>'); // 合并多余换行
  },

  /**
   * 切换模型
   */
  switchModel: function(e) {
    const index = e.currentTarget.dataset.index;

    if (index === this.data.currentModelIndex) {
      return; // 已经是当前模型，无需切换
    }

    const modelData = this.data.modelResults[index];

    this.setData({
      currentModelIndex: index,
      currentModelData: modelData
    });

    // 重新分片渲染新模型的内容
    this.startChunkedRendering(modelData.response_content || modelData.content || '');

    // 轻微震动反馈
    wx.vibrateShort({ type: 'light' });
  },

  /**
   * 复制内容
   */
  copyContent: function() {
    const content = this.data.currentModelData?.response_content || this.data.currentModelData?.content;

    if (!content) {
      wx.showToast({ title: '无内容可复制', icon: 'none' });
      return;
    }

    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      }
    });
  },

  /**
   * 分享分析
   */
  shareAnalysis: function() {
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    });
  },

  /**
   * 分享好友
   */
  onShareAppMessage: function() {
    const brandName = this.data.brandName || '品牌';
    return {
      title: `${brandName} - AI 品牌诊断报告`,
      path: `/pages/report/detail/index?executionId=${this.data.executionId}`
    };
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline: function() {
    const brandName = this.data.brandName || '品牌';
    return {
      title: `${brandName} - AI 品牌诊断报告`,
      query: `executionId=${this.data.executionId}`,
      imageUrl: ''
    };
  },

  /**
   * 返回上一页
   */
  goBack: function() {
    wx.navigateBack({
      delta: 1,
      fail: () => {
        wx.switchTab({
          url: '/pages/index/index'
        });
      }
    });
  },

  /**
   * 查看品牌分析
   */
  viewBrandAnalysis: function() {
    const analysis = this.data.analysis;
    if (!analysis || !analysis.brandAnalysis) {
      wx.showToast({
        title: '暂无品牌分析数据',
        icon: 'none'
      });
      return;
    }

    wx.showModal({
      title: '品牌分析',
      content: JSON.stringify(analysis.brandAnalysis, null, 2),
      showCancel: false,
      confirmText: '关闭'
    });
  },

  /**
   * 查看 Top3 品牌
   */
  viewTop3Brands: function() {
    const top3 = this.data.analysis?.top3Brands || [];
    if (!top3 || top3.length === 0) {
      wx.showToast({
        title: '暂无 Top3 品牌数据',
        icon: 'none'
      });
      return;
    }

    const content = top3.map((brand, index) => {
      return `${index + 1}. ${brand.name}\n   理由：${brand.reason}`;
    }).join('\n\n');

    wx.showModal({
      title: 'Top3 品牌排名',
      content: content,
      showCancel: false,
      confirmText: '关闭'
    });
  }
});
