/**
 * 原始数据详情页 - P0 级空缺修复
 * 
 * 功能:
 * 1. 展示诊断原始数据
 * 2. 支持按品牌/模型/问题筛选
 * 3. 支持时间排序
 * 4. 支持数据导出
 */

const app = getApp();
const logger = require('../../../utils/logger');

Page({
  data: {
    loading: true,
    error: null,
    executionId: '',
    
    // 原始数据
    rawData: [],
    filteredData: [],
    
    // 摘要统计
    summary: {
      totalRecords: 0,
      totalBrands: 0,
      totalQuestions: 0,
      totalModels: 0
    },
    
    // 筛选状态
    currentFilter: 'all',
    sortOrder: 'desc' // desc: 最新在前，asc: 最旧在前
  },

  onLoad(options) {
    const { executionId } = options;
    
    if (executionId) {
      this.setData({ executionId });
      this.loadRawData(executionId);
    } else {
      // 尝试从全局获取最近的 executionId
      const lastReport = app.globalData.lastReport;
      if (lastReport && lastReport.executionId) {
        this.setData({ executionId: lastReport.executionId });
        this.loadRawData(lastReport.executionId);
      } else {
        this.setData({
          error: '未找到执行 ID，请从报告页面进入'
        });
      }
    }
  },

  /**
   * 加载原始数据
   */
  async loadRawData(executionId) {
    try {
      this.setData({ loading: true, error: null });
      
      // 从 Dashboard API 获取原始数据
      const response = await this.fetchDashboardData(executionId);
      
      if (response && response.dashboard) {
        const dashboard = response.dashboard;
        
        // 解析原始数据
        const rawData = this.parseRawData(dashboard);
        
        // 计算摘要统计
        const summary = this.calculateSummary(rawData);
        
        this.setData({
          loading: false,
          rawData,
          filteredData: rawData,
          summary
        });
        
        logger.info('Raw data loaded successfully', {
          executionId,
          recordCount: rawData.length
        });
      } else {
        throw new Error('数据格式错误');
      }
    } catch (error) {
      logger.error('Failed to load raw data', error);
      this.setData({
        loading: false,
        error: error.message || '加载失败，请重试'
      });
    }
  },

  /**
   * 获取 Dashboard 数据
   */
  fetchDashboardData(executionId) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.apiBaseUrl}/api/dashboard/aggregate`,
        method: 'GET',
        data: {
          executionId,
          userOpenid: app.globalData.userOpenid || 'anonymous'
        },
        timeout: 30000,
        success: (res) => {
          if (res.data && res.data.success) {
            resolve(res.data);
          } else {
            reject(new Error(res.data?.error || '获取数据失败'));
          }
        },
        fail: (error) => {
          reject(new Error('网络请求失败'));
        }
      });
    });
  },

  /**
   * 解析原始数据
   */
  parseRawData(dashboard) {
    const rawData = [];
    
    // 从 questionCards 解析
    if (dashboard.questionCards && Array.isArray(dashboard.questionCards)) {
      dashboard.questionCards.forEach((card, cardIndex) => {
        const responses = card.responses || [];
        responses.forEach((response, respIndex) => {
          rawData.push({
            id: `${cardIndex}-${respIndex}`,
            brand: card.brand || dashboard.summary?.brandName || '未知品牌',
            model: response.model || response.ai_model || '未知模型',
            question: card.question || '未知问题',
            response: response.content || response.response || '无响应',
            rank: response.rank || response.geo_data?.rank,
            sentiment: response.sentiment || response.geo_data?.sentiment,
            timestamp: response.timestamp || card.timestamp,
            sources: response.sources || response.geo_data?.cited_sources || []
          });
        });
      });
    }
    
    // 从 rawResults 解析 (如果有)
    if (dashboard.rawResults && Array.isArray(dashboard.rawResults)) {
      dashboard.rawResults.forEach((item, index) => {
        // 避免重复添加
        const exists = rawData.some(r => 
          r.brand === item.brand && 
          r.question === item.question &&
          r.model === item.model
        );
        
        if (!exists) {
          rawData.push({
            id: `raw-${index}`,
            brand: item.brand,
            model: item.model,
            question: item.question,
            response: item.response || item.content,
            rank: item.rank,
            sentiment: item.sentiment,
            timestamp: item.timestamp,
            sources: item.sources
          });
        }
      });
    }
    
    return rawData;
  },

  /**
   * 计算摘要统计
   */
  calculateSummary(rawData) {
    const brands = new Set(rawData.map(item => item.brand));
    const questions = new Set(rawData.map(item => item.question));
    const models = new Set(rawData.map(item => item.model));
    
    return {
      totalRecords: rawData.length,
      totalBrands: brands.size,
      totalQuestions: questions.size,
      totalModels: models.size
    };
  },

  /**
   * 筛选数据
   */
  filterData(filterType) {
    let filtered = [...this.data.rawData];
    
    switch (filterType) {
      case 'brand':
        // 按品牌分组
        filtered.sort((a, b) => a.brand.localeCompare(b.brand));
        break;
      case 'model':
        // 按模型分组
        filtered.sort((a, b) => a.model.localeCompare(b.model));
        break;
      case 'question':
        // 按问题分组
        filtered.sort((a, b) => a.question.localeCompare(b.question));
        break;
      default:
        // 全部
        break;
    }
    
    // 应用时间排序
    filtered = this.sortByTime(filtered);
    
    this.setData({ filteredData: filtered });
  },

  /**
   * 时间排序
   */
  sortByTime(data) {
    const { sortOrder } = this.data;
    
    return data.sort((a, b) => {
      const timeA = new Date(a.timestamp || 0).getTime();
      const timeB = new Date(b.timestamp || 0).getTime();
      
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });
  },

  /**
   * 事件处理
   */
  
  // 筛选点击
  onFilterTap(event) {
    const { filter } = event.currentTarget.dataset;
    this.setData({ currentFilter: filter });
    this.filterData(filter);
  },

  // 切换排序顺序
  toggleSortOrder() {
    const { sortOrder } = this.data;
    const newOrder = sortOrder === 'desc' ? 'asc' : 'desc';
    this.setData({ sortOrder: newOrder });
    this.filterData(this.data.currentFilter);
  },

  // 数据项点击
  onItemTap(event) {
    const { item } = event.currentTarget.dataset;
    
    // 展开/收起详情
    const index = this.data.filteredData.findIndex(d => d.id === item.id);
    if (index !== -1) {
      const key = `filteredData[${index}].expanded`;
      this.setData({
        [key]: !item.expanded
      });
    }
  },

  // 格式化时间
  formatTime(timestamp) {
    if (!timestamp) return '-';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // 1 分钟内
    if (diff < 60000) {
      return '刚刚';
    }
    // 1 小时内
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}分钟前`;
    }
    // 24 小时内
    if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)}小时前`;
    }
    // 超过 24 小时
    return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
  },

  // 重试
  retry() {
    this.loadRawData(this.data.executionId);
  },

  /**
   * 页面分享
   */
  onShareAppMessage() {
    return {
      title: '原始数据详情',
      path: `/pages/report/raw-data/raw-data?executionId=${this.data.executionId}`
    };
  }
});
