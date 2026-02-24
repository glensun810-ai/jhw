App({
  globalData: {
    userInfo: null,
    openid: null,
    serverUrl: 'http://127.0.0.1:5001', // 后端服务器地址（使用 5001 避免与 macOS Control Center 冲突）
    deviceId: null // 设备 ID，用于日志追踪
  },

  onLaunch: function () {
    console.log('应用启动');

    // 初始化设备 ID（用于日志追踪）
    this.initDeviceId();

    // 检查用户授权状态
    this.checkAuthStatus();

    // 一次性清理逻辑：清理所有保存的文件
    this.clearSavedFiles();
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
  }
})
