// pages/report/history/history.js
/**
 * 报告历史页
 * 
 * 功能:
 * - 展示所有历史诊断报告
 * - 支持按时间、品牌、评分筛选
 * - 支持跳转到报告详情
 * - 支持下拉刷新
 * 
 * 数据来源:
 * - 从本地存储 wx.getStorageSync('diagnosisHistory') 获取历史记录
 * - 或从服务器 API 获取
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
    reports: [],
    sortBy: 'time', // time | score | brand
    showExecutionId: false // 调试模式
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    logger.info('报告历史页加载');
    this.loadHistory();
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {
    logger.debug('报告历史页初次渲染完成');
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 每次显示时刷新数据，确保最新
    if (!this.data.loading) {
      this.loadHistory();
    }
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    logger.debug('报告历史页隐藏');
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    logger.debug('报告历史页卸载');
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    logger.debug('用户下拉刷新');
    this.loadHistory()
      .then(() => {
        wx.stopPullDownRefresh();
        wx.showToast({
          title: '刷新成功',
          icon: 'success'
        });
      })
      .catch(() => {
        wx.stopPullDownRefresh();
        wx.showToast({
          title: '刷新失败',
          icon: 'none'
        });
      });
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    // 暂无分页功能
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: '我的诊断报告 - GEO 品牌诊断',
      path: '/pages/report/history/history'
    };
  },

  /**
   * 加载历史记录
   */
  loadHistory() {
    return new Promise((resolve, reject) => {
      try {
        this.setData({ loading: true, error: null });

        // 1. 从本地存储获取历史数据
        const history = wx.getStorageSync('diagnosisHistory') || [];
        logger.debug('本地存储的历史数据', { count: history.length });

        if (history.length > 0) {
          // 根据排序方式排序
          const sortedHistory = this.sortReports(history);

          this.setData({
            loading: false,
            reports: sortedHistory
          });
          resolve();
          return;
        }

        // 2. 如果没有本地数据，尝试从服务器获取
        this.fetchHistoryFromServer()
          .then(resolve)
          .catch((error) => {
            logger.error('加载历史记录失败', error);
            this.setData({
              loading: false,
              error: '加载失败，请检查网络连接'
            });
            reject(error);
          });
      } catch (error) {
        logger.error('加载历史记录异常', error);
        this.setData({
          loading: false,
          error: '加载失败：' + (error.message || '未知错误')
        });
        reject(error);
      }
    });
  },

  /**
   * 从服务器获取历史记录
   */
  fetchHistoryFromServer() {
    return new Promise((resolve, reject) => {
      const apiUrl = app.globalData.apiBaseUrl || 'https://api.example.com';
      const userOpenid = app.globalData.userOpenid || 'anonymous';

      wx.request({
        url: `${apiUrl}/api/history/list`,
        method: 'GET',
        data: {
          userOpenid: userOpenid
        },
        timeout: 30000,
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            const data = res.data;
            const history = data.history || data.list || [];

            this.setData({
              loading: false,
              reports: this.sortReports(history)
            });

            // 同步到本地存储
            wx.setStorageSync('diagnosisHistory', history);

            resolve();
          } else {
            reject(new Error('服务器响应异常'));
          }
        },
        fail: (error) => {
          logger.error('请求历史记录失败', error);
          reject(error);
        }
      });
    });
  },

  /**
   * 排序报告列表
   */
  sortReports(reports) {
    const sortBy = this.data.sortBy;

    const sorted = [...reports].sort((a, b) => {
      if (sortBy === 'time') {
        // 按时间倒序
        const timeA = a.createdAt || a.diagnoseAt || 0;
        const timeB = b.createdAt || b.diagnoseAt || 0;
        return timeB - timeA;
      } else if (sortBy === 'score') {
        // 按评分倒序
        const scoreA = a.healthScore || a.score || 0;
        const scoreB = b.healthScore || b.score || 0;
        return scoreB - scoreA;
      } else if (sortBy === 'brand') {
        // 按品牌名称字母顺序
        const brandA = (a.brandName || a.brand || '').toLowerCase();
        const brandB = (b.brandName || b.brand || '').toLowerCase();
        return brandA.localeCompare(brandB);
      }
      return 0;
    });

    return sorted;
  },

  /**
   * 改变排序方式
   */
  changeSort(e) {
    const sort = e.currentTarget.dataset.sort;
    logger.info('改变排序方式', { sort });

    if (this.data.sortBy !== sort) {
      this.setData({ sortBy: sort });
      const sortedReports = this.sortReports(this.data.reports);
      this.setData({ reports: sortedReports });

      wx.showToast({
        title: `按${sort === 'time' ? '时间' : sort === 'score' ? '评分' : '品牌'}排序`,
        icon: 'none',
        duration: 1500
      });
    }
  },

  /**
   * 查看报告详情
   */
  viewDetail(e) {
    const item = e.currentTarget.dataset.item;
    logger.info('查看报告详情', { item });

    if (item.executionId) {
      // 保存到全局存储，供详情页使用
      app.globalData.lastReport = {
        executionId: item.executionId,
        dashboard: item,
        raw: item.rawResults || [],
        competitors: item.competitors || []
      };

      // 跳转到 Dashboard 页面
      wx.navigateTo({
        url: `/pages/report/dashboard/index?executionId=${item.executionId}`,
        success: () => {
          logger.debug('成功跳转到报告详情页');
        },
        fail: (err) => {
          logger.error('跳转到报告详情页失败', err);
          wx.showToast({
            title: '跳转失败',
            icon: 'none'
          });
        }
      });
    } else {
      wx.showToast({
        title: '报告数据不完整',
        icon: 'none'
      });
    }
  },

  /**
   * 返回首页
   */
  goHome() {
    wx.switchTab({
      url: '/pages/index/index',
      fail: () => {
        wx.navigateTo({
          url: '/pages/index/index'
        });
      }
    });
  },

  /**
   * 重试加载
   */
  retry() {
    this.loadHistory();
  }
});
