/**
 * 问题深度诊断详情页 - 页面逻辑
 * 
 * 核心功能：
 * 1. 按问题索引加载特定问题的所有模型结果
 * 2. 模型切换对比
 * 3. 分片渲染（Chunked Rendering）防止大文本卡顿
 * 4. 归因分析与信源追踪
 */

const app = getApp();

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
    loadError: null
  },

  /**
   * 页面加载
   */
  onLoad: function(options) {
    try {
      this.setData({ loading: true, loadError: null });
      
      const qIndex = parseInt(options.index) || 0;
      
      // 从全局存储获取数据
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
    this.startChunkedRendering(modelData.content);
    
    // 轻微震动反馈
    wx.vibrateShort({ type: 'light' });
  },

  /**
   * 复制内容
   */
  copyContent: function() {
    const content = this.data.currentModelData?.content;
    
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
    
    wx.showToast({ title: '点击右上角分享', icon: 'none' });
  },

  /**
   * 重新加载
   */
  retry: function() {
    this.onLoad({ index: this.data.questionIndex });
  },

  /**
   * 页面分享 - 发送给好友
   */
  onShareAppMessage: function() {
    const brandName = this.data.currentModelData?.main_brand || '品牌';
    const questionText = this.data.questionText?.substring(0, 20) || '问题诊断';
    const rank = this.data.currentModelData?.geo_data?.rank || -1;
    
    return {
      title: `${brandName} GEO 诊断 - ${questionText}（排名：${rank > 0 ? '#' + rank : '未上榜'}）`,
      path: `/pages/report/dashboard/index`
    };
  },

  /**
   * 页面分享 - 分享到朋友圈
   */
  onShareTimeline: function() {
    const brandName = this.data.currentModelData?.main_brand || '品牌';
    const rank = this.data.currentModelData?.geo_data?.rank || -1;
    
    return {
      title: `${brandName} GEO 品牌诊断报告 - 排名#${rank > 0 ? rank : '未上榜'}`,
      query: '',
      imageUrl: ''
    };
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function() {
    this.onLoad({ index: this.data.questionIndex })
      .then(() => {
        wx.stopPullDownRefresh();
      })
      .catch(() => {
        wx.stopPullDownRefresh();
      });
  }
});
