const { getTestHistory } = require('../../api/history.js');

Page({
  data: {
    historyList: [],
    isLoading: true,
    openid: '',
    
    // P2-1 趋势图相关数据
    trendChartData: [],  // 趋势图数据点
    trendLinePoints: '', // SVG 连线坐标
    trendStats: {        // 趋势统计
      averageScore: 0,
      maxScore: 0,
      minScore: 0,
      trend: 'flat',     // up/down/flat
      trendText: '平稳'
    }
  },

  onLoad: function (options) {
    const openid = wx.getStorageSync('openid');
    if (openid) {
      this.setData({ openid: openid });
      this.loadHistory();
    } else {
      // 如果没有 openid，可以提示用户先登录
      wx.showToast({
        title: '请先登录以查看历史记录',
        icon: 'none',
        duration: 2000,
        complete: () => {
          setTimeout(() => {
            wx.navigateBack();
          }, 2000);
        }
      });
    }
  },

  // 下拉刷新
  onPullDownRefresh: function () {
    this.loadHistory();
  },

  // 加载历史记录
  async loadHistory() {
    this.setData({ isLoading: true });
    try {
      const res = await getTestHistory({
        userOpenid: this.data.openid
      });

      if (res.statusCode === 200 && res.data.status === 'success') {
        // 格式化时间
        const formattedHistory = res.data.history.map(item => {
          item.created_at = new Date(item.created_at).toLocaleString();
          return item;
        });
        
        // P2-1 修复：处理趋势图数据
        const trendData = this.processTrendData(formattedHistory);
        
        this.setData({
          historyList: formattedHistory,
          trendChartData: trendData.trendChartData,
          trendLinePoints: trendData.trendLinePoints,
          trendStats: trendData.trendStats,
          isLoading: false
        });
      } else {
        this.setData({ isLoading: false });
        wx.showToast({ title: '加载失败', icon: 'error' });
      }
    } catch (err) {
      this.setData({ isLoading: false });
      console.error('加载历史记录失败:', err);
      wx.showToast({ title: '网络请求失败', icon: 'error' });
    } finally {
      wx.stopPullDownRefresh();
    }
  },

  // 查看详情
  viewDetail: function (e) {
    const recordId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?id=${recordId}`
    });
  },

  // 查看最近一次的诊断结果
  viewLatestResult: function() {
    const cachedResults = wx.getStorageSync('latestTestResults');
    const cachedAnalysis = wx.getStorageSync('latestCompetitiveAnalysis');
    const cachedBrand = wx.getStorageSync('latestTargetBrand');

    if (cachedResults && cachedAnalysis && cachedBrand) {
      const params = {
        results: JSON.stringify(cachedResults),
        competitiveAnalysis: encodeURIComponent(JSON.stringify(cachedAnalysis)),
        targetBrand: cachedBrand
      };

      const queryString = Object.keys(params)
        .map(key => `${key}=${params[key]}`)
        .join('&');

      wx.navigateTo({ url: `/pages/results/results?${queryString}` });
    } else {
      wx.showToast({
        title: '暂无最近的诊断结果',
        icon: 'none'
      });
    }
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  },

  // 查看已保存的结果
  viewSavedResults: function() {
    wx.navigateTo({
      url: '/pages/saved-results/saved-results'
    });
  },

  // 查看公共历史记录
  viewPublicHistory: function() {
    wx.navigateTo({
      url: '/pages/public-history/public-history'
    });
  },

  // 查看个人历史记录
  viewPersonalHistory: function() {
    wx.navigateTo({
      url: '/pages/personal-history/personal-history'
    });
  },

  /**
   * P2-1 修复：处理趋势图数据
   */
  processTrendData: function(historyList) {
    try {
      if (!historyList || historyList.length === 0) {
        return {
          trendChartData: [],
          trendLinePoints: '',
          trendStats: {
            averageScore: 0,
            maxScore: 0,
            minScore: 0,
            trend: 'flat',
            trendText: '平稳'
          }
        };
      }
      
      // 按时间排序
      const sortedList = [...historyList].sort((a, b) => {
        return new Date(a.created_at) - new Date(b.created_at);
      });
      
      // 计算趋势图数据点
      const chartData = sortedList.map((item, index) => {
        const score = item.overall_score || 0;
        const totalPoints = sortedList.length;
        
        // 计算位置百分比
        const leftPercent = totalPoints > 1 ? (index / (totalPoints - 1)) * 100 : 50;
        const topPercent = 100 - (score / 100) * 100; // Y 轴翻转，分数越高位置越靠上
        
        // 格式化日期
        const date = new Date(item.created_at);
        const shortDate = `${date.getMonth() + 1}/${date.getDate()}`;
        
        return {
          id: item.id,
          score: Math.round(score),
          leftPercent: leftPercent,
          topPercent: topPercent,
          shortDate: shortDate,
          fullDate: item.created_at
        };
      });
      
      // 计算 SVG 连线坐标
      let linePoints = '';
      if (chartData.length > 1) {
        linePoints = chartData.map(point => {
          const x = (point.leftPercent / 100) * 300; // 假设图表宽度 300
          const y = (point.topPercent / 100) * 200;  // 假设图表高度 200
          return `${x},${y}`;
        }).join(' ');
      }
      
      // 计算趋势统计
      const scores = sortedList.map(item => item.overall_score || 0);
      const averageScore = Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
      const maxScore = Math.round(Math.max(...scores));
      const minScore = Math.round(Math.min(...scores));
      
      // 计算趋势方向
      let trend = 'flat';
      let trendText = '平稳';
      if (sortedList.length >= 2) {
        const firstScore = sortedList[0].overall_score || 0;
        const lastScore = sortedList[sortedList.length - 1].overall_score || 0;
        const diff = lastScore - firstScore;
        
        if (diff > 5) {
          trend = 'up';
          trendText = '上升 ↑';
        } else if (diff < -5) {
          trend = 'down';
          trendText = '下降 ↓';
        }
      }
      
      return {
        trendChartData: chartData,
        trendLinePoints: linePoints,
        trendStats: {
          averageScore: averageScore,
          maxScore: maxScore,
          minScore: minScore,
          trend: trend,
          trendText: trendText
        }
      };
    } catch (e) {
      console.error('处理趋势图数据失败:', e);
      return {
        trendChartData: [],
        trendLinePoints: '',
        trendStats: {
          averageScore: 0,
          maxScore: 0,
          minScore: 0,
          trend: 'flat',
          trendText: '平稳'
        }
      };
    }
  }
})