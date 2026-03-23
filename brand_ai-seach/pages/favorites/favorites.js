// pages/favorites/favorites.js
/**
 * 收藏列表页
 * 
 * 功能:
 * - 展示用户收藏的所有报告
 * - 支持取消收藏
 * - 支持跳转到报告详情
 * - 支持下拉刷新
 * 
 * 数据来源:
 * - 从本地存储 wx.getStorageSync('favorites') 获取收藏列表
 * - 或从服务器 API 获取
 */

const app = getApp();
const logger = require('../../utils/logger');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    error: null,
    favorites: [],
    hasMore: false,
    page: 1,
    pageSize: 20
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    logger.info('收藏列表页加载');
    this.loadFavorites();
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {
    logger.debug('收藏列表页初次渲染完成');
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 每次显示时刷新数据，确保最新
    if (!this.data.loading) {
      this.loadFavorites();
    }
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    logger.debug('收藏列表页隐藏');
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    logger.debug('收藏列表页卸载');
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    logger.debug('用户下拉刷新');
    this.loadFavorites()
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
    // 如果有更多数据，加载下一页
    if (this.data.hasMore) {
      this.loadMoreFavorites();
    }
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: '我的收藏 - GEO 品牌诊断',
      path: '/pages/favorites/favorites'
    };
  },

  /**
   * 加载收藏列表
   */
  loadFavorites() {
    return new Promise((resolve, reject) => {
      try {
        this.setData({ loading: true, error: null });

        // 1. 从本地存储获取收藏数据
        const favorites = wx.getStorageSync('favorites') || [];
        logger.debug('本地存储的收藏数据', { count: favorites.length });

        if (favorites.length > 0) {
          // 按收藏时间倒序排列
          const sortedFavorites = favorites.sort((a, b) => {
            const timeA = a.favoritedAt || a.createdAt || 0;
            const timeB = b.favoritedAt || b.createdAt || 0;
            return timeB - timeA;
          });

          this.setData({
            loading: false,
            favorites: sortedFavorites,
            hasMore: false
          });
          resolve();
          return;
        }

        // 2. 如果没有本地数据，尝试从服务器获取
        this.fetchFavoritesFromServer()
          .then(resolve)
          .catch((error) => {
            logger.error('加载收藏失败', error);
            this.setData({
              loading: false,
              error: '加载失败，请检查网络连接'
            });
            reject(error);
          });
      } catch (error) {
        logger.error('加载收藏列表异常', error);
        this.setData({
          loading: false,
          error: '加载失败：' + (error.message || '未知错误')
        });
        reject(error);
      }
    });
  },

  /**
   * 从服务器获取收藏列表
   */
  fetchFavoritesFromServer() {
    return new Promise((resolve, reject) => {
      const apiUrl = app.globalData.apiBaseUrl || 'https://api.example.com';
      const userOpenid = app.globalData.userOpenid || 'anonymous';

      wx.request({
        url: `${apiUrl}/api/favorites/list`,
        method: 'GET',
        data: {
          userOpenid: userOpenid,
          page: this.data.page,
          pageSize: this.data.pageSize
        },
        timeout: 30000,
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            const data = res.data;
            const favorites = data.favorites || data.list || [];

            this.setData({
              loading: false,
              favorites: favorites,
              hasMore: data.hasMore || (favorites.length >= this.data.pageSize)
            });

            // 同步到本地存储
            wx.setStorageSync('favorites', favorites);

            resolve();
          } else {
            reject(new Error('服务器响应异常'));
          }
        },
        fail: (error) => {
          logger.error('请求收藏列表失败', error);
          reject(error);
        }
      });
    });
  },

  /**
   * 加载更多收藏
   */
  loadMoreFavorites() {
    const nextPage = this.data.page + 1;
    this.setData({ page: nextPage });
    this.fetchFavoritesFromServer();
  },

  /**
   * 查看收藏详情
   */
  viewDetail(e) {
    const item = e.currentTarget.dataset.item;
    logger.info('查看收藏详情', { item });

    if (item.executionId) {
      // 保存到全局存储，供详情页使用
      app.globalData.lastReport = item;
      
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
   * 取消收藏
   */
  removeFavorite(e) {
    const item = e.currentTarget.dataset.item;
    logger.info('取消收藏', { item });

    wx.showModal({
      title: '确认取消',
      content: `确定要取消收藏"${item.brandName || item.brand || '这份报告'}"吗？`,
      success: (res) => {
        if (res.confirm) {
          this.doRemoveFavorite(item);
        }
      }
    });
  },

  /**
   * 执行取消收藏操作
   */
  doRemoveFavorite(item) {
    try {
      // 1. 从本地存储移除
      const favorites = wx.getStorageSync('favorites') || [];
      const index = favorites.findIndex(f => f.executionId === item.executionId);
      
      if (index !== -1) {
        favorites.splice(index, 1);
        wx.setStorageSync('favorites', favorites);
      }

      // 2. 更新页面数据
      const newFavorites = this.data.favorites.filter(
        f => f.executionId !== item.executionId
      );
      this.setData({ favorites: newFavorites });

      // 3. 调用服务器 API（如果有）
      this.removeFromServer(item);

      wx.showToast({
        title: '已取消收藏',
        icon: 'success'
      });

      logger.info('取消收藏成功', { executionId: item.executionId });
    } catch (error) {
      logger.error('取消收藏失败', error);
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  /**
   * 从服务器移除收藏
   */
  removeFromServer(item) {
    const apiUrl = app.globalData.apiBaseUrl || 'https://api.example.com';
    const userOpenid = app.globalData.userOpenid || 'anonymous';

    wx.request({
      url: `${apiUrl}/api/favorites/remove`,
      method: 'POST',
      data: {
        userOpenid: userOpenid,
        executionId: item.executionId
      },
      timeout: 10000,
      fail: (error) => {
        logger.warn('从服务器移除收藏失败', error);
        // 不显示错误，因为本地已经移除成功
      }
    });
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
    this.loadFavorites();
  }
});
