App({
  globalData: {
    userInfo: null,
    openid: null,
    serverUrl: 'http://127.0.0.1:5001', // 后端服务器地址（使用 5001 避免与 macOS Control Center 冲突）
    deviceId: null, // 设备 ID，用于日志追踪
    errorToast: null // 全局错误提示组件引用
  },

  onLaunch: function () {
    console.log('应用启动');

    // 初始化页面过渡动画系统
    this.initPageTransition();

    // 初始化设备 ID（用于日志追踪）
    this.initDeviceId();

    // 检查用户授权状态
    this.checkAuthStatus();

    // 一次性清理逻辑：清理所有保存的文件
    this.clearSavedFiles();

    // 注册 Service Worker（离线缓存）
    this.registerServiceWorker();
  },

  /**
   * 初始化页面过渡动画系统
   */
  initPageTransition: function() {
    try {
      const { PageTransition } = require('./utils/page-transition');
      PageTransition.init();
      console.log('✅ 页面过渡动画系统已初始化');
    } catch (error) {
      console.warn('页面过渡动画系统初始化失败:', error);
    }
  },

  onShow: function (options) {
    console.log('应用显示', options);
  },

  onHide: function () {
    console.log('应用隐藏');
  },

  /**
   * 初始化设备 ID
   * 用于日志追踪和请求标识
   */
  initDeviceId: function() {
    // 尝试从缓存获取设备 ID
    let deviceId = wx.getStorageSync('device_id');
    
    if (!deviceId) {
      // 如果没有，生成一个新的
      deviceId = 'dev_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      wx.setStorageSync('device_id', deviceId);
      console.log('生成新设备 ID:', deviceId);
    } else {
      console.log('使用已有设备 ID:', deviceId);
    }
    
    this.globalData.deviceId = deviceId;
  },

  // 检查用户授权状态
  checkAuthStatus: function() {
    // 检查用户是否已授权获取用户信息
    wx.getSetting({
      success: (res) => {
        if (!res.authSetting['scope.userInfo']) {
          // 如果没有授权，则跳转到授权页面
          console.log('用户未授权获取用户信息');
        } else {
          console.log('用户已授权获取用户信息');
        }
      }
    });
  },

  // 获取全局用户信息
  getUserInfo: function(cb) {
    const userInfo = this.globalData.userInfo;
    if (userInfo) {
      typeof cb == "function" && cb(userInfo);
    } else {
      // 从本地缓存获取用户信息
      wx.getStorage({
        key: 'userInfo',
        success: (res) => {
          this.globalData.userInfo = res.data;
          typeof cb == "function" && cb(res.data);
        },
        fail: () => {
          // 如果本地也没有，则需要用户重新登录获取
          console.log('本地没有用户信息缓存');
        }
      });
    }
  },

  // 设置全局用户信息
  setUserInfo: function(userInfo) {
    this.globalData.userInfo = userInfo;
    // 同时保存到本地缓存
    wx.setStorage({
      key: 'userInfo',
      data: userInfo
    });
  },

  // 获取 OpenID
  getOpenId: function() {
    return this.globalData.openid || wx.getStorageSync('openid');
  },

  // 设置 OpenID
  setOpenId: function(openid) {
    this.globalData.openid = openid;
    // 同时保存到本地缓存
    wx.setStorageSync('openid', openid);
  },

  // 获取设备 ID
  getDeviceId: function() {
    return this.globalData.deviceId || wx.getStorageSync('device_id');
  },

  // 清理所有保存的文件（macOS 模拟器兼容）
  clearSavedFiles: function() {
    // macOS 模拟器兼容处理：getSavedFileList 可能因为目录不存在而失败
    // 这是正常现象，不需要报错
    wx.getFileSystemManager().getSavedFileList({
      success: (res) => {
        const fileList = res.fileList;
        if (fileList && fileList.length > 0) {
          console.log(`发现 ${fileList.length} 个保存的文件，开始清理...`);

          fileList.forEach((file) => {
            wx.removeSavedFile({
              filePath: file.filePath,
              success: () => {
                console.log(`成功删除文件：${file.filePath}`);
              },
              fail: (err) => {
                // 文件不存在时忽略错误（可能已被删除）
                if (err && err.errMsg && !err.errMsg.includes('ENOENT')) {
                  console.error(`删除文件失败：${file.filePath}`, err);
                }
              }
            });
          });
        } else {
          console.log('没有找到需要清理的保存文件');
        }
      },
      fail: (err) => {
        // macOS 模拟器兼容处理：
        // ENOENT 错误表示目录不存在，这是正常的（首次使用或已清理）
        // 不要报错，只需记录日志
        if (err && err.errMsg && err.errMsg.includes('ENOENT')) {
          console.log('模拟器存储目录尚未创建（首次使用属正常现象）');
        } else {
          // 其他错误才记录
          const errMsg = err ? (err.errMsg || JSON.stringify(err)) : '未知错误';
          console.log('获取保存文件列表失败:', errMsg);
        }
      }
    });
  },

  /**
   * 设置全局错误提示组件引用
   * @param {Object} component - 错误提示组件实例
   */
  setErrorToast: function(component) {
    this.globalData.errorToast = component;
  },

  /**
   * 显示全局错误提示
   * @param {Object} error - 错误对象
   * @param {Object} options - 选项
   */
  showError: function(error, options = {}) {
    const errorToast = this.globalData.errorToast;
    if (errorToast && typeof errorToast.showError === 'function') {
      errorToast.showError(error, options);
    }
  },

  /**
   * 隐藏全局错误提示
   */
  hideError: function() {
    const errorToast = this.globalData.errorToast;
    if (errorToast && typeof errorToast.hide === 'function') {
      errorToast.hide();
    }
  },

  /**
   * 显示成功提示
   * @param {string} title - 提示文本
   */
  showSuccess: function(title = '操作成功') {
    wx.showToast({
      title,
      icon: 'success',
      duration: 2000
    });
  },

  /**
   * 显示加载中
   * @param {string} title - 加载提示文本
   */
  showLoading: function(title = '加载中...') {
    wx.showLoading({
      title,
      mask: true
    });
  },

  /**
   * 隐藏加载中
   */
  hideLoading: function() {
    wx.hideLoading();
  },

  /**
   * 注册 Service Worker（离线缓存）
   */
  registerServiceWorker: function() {
    // 检查是否支持 Service Worker
    if (wx.canIUse('getSystemInfoSync')) {
      const systemInfo = wx.getSystemInfoSync();
      console.log('[SW] 系统信息:', systemInfo.platform, systemInfo.system);
      
      // 微信小程序基础库 2.30.0+ 支持 Service Worker
      const { SDKVersion } = systemInfo;
      
      // 尝试注册 Service Worker
      if (wx.canIUse('registerWorker')) {
        wx.registerWorker({
          url: '/miniprogram/service-worker.js',
          success: (res) => {
            console.log('[SW] Service Worker 注册成功');
            
            // 监听 Service Worker 消息
            this.setupServiceWorkerMessaging();
            
            // 获取缓存状态
            this.getCacheStatus();
          },
          fail: (err) => {
            console.log('[SW] Service Worker 注册失败:', err);
            // 注册失败不影响应用使用，只是没有离线缓存
          }
        });
      } else {
        console.log('[SW] 当前环境不支持 Service Worker');
      }
    }
  },

  /**
   * 设置 Service Worker 消息处理
   */
  setupServiceWorkerMessaging: function() {
    // 监听来自 Service Worker 的消息
    wx.onServiceWorkerMessageReceived((res) => {
      console.log('[SW] 收到 Service Worker 消息:', res.data);
    });
  },

  /**
   * 获取缓存状态
   */
  getCacheStatus: function() {
    // 通过 Service Worker 消息获取缓存状态
    this.sendServiceWorkerMessage({
      type: 'GET_CACHE_STATUS'
    }, (status) => {
      if (status && status.caches) {
        console.log('[SW] 缓存状态:', status);
      }
    });
  },

  /**
   * 发送消息到 Service Worker
   * @param {Object} data - 消息数据
   * @param {Function} callback - 回调函数
   */
  sendServiceWorkerMessage: function(data, callback) {
    try {
      // 创建消息通道
      const channel = wx.createServiceWorkerMessageChannel();
      
      // 监听响应
      channel.onmessage = (res) => {
        if (typeof callback === 'function') {
          callback(res.data);
        }
      };
      
      // 发送消息
      wx.sendServiceWorkerMessage({
        data: {
          ...data,
          channel: channel
        }
      });
    } catch (error) {
      console.log('[SW] 发送消息失败:', error);
      if (typeof callback === 'function') {
        callback(null);
      }
    }
  },

  /**
   * 清除缓存
   * @param {string} cacheName - 缓存名称（可选，不传则清除所有）
   * @param {Function} callback - 回调函数
   */
  clearCache: function(cacheName, callback) {
    this.sendServiceWorkerMessage({
      type: 'CLEAR_CACHE',
      payload: { cacheName }
    }, (result) => {
      console.log('[SW] 缓存清除完成:', result);
      if (typeof callback === 'function') {
        callback(result);
      }
    });
  },

  /**
   * 预缓存指定 URL 列表
   * @param {Array<string>} urls - URL 列表
   * @param {Function} callback - 回调函数
   */
  precacheUrls: function(urls, callback) {
    this.sendServiceWorkerMessage({
      type: 'PRECACHE_URLS',
      payload: { urls }
    }, (result) => {
      console.log('[SW] 预缓存完成:', result);
      if (typeof callback === 'function') {
        callback(result);
      }
    });
  }
})
