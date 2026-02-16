App({
  globalData: {
    userInfo: null,
    openid: null,
    serverUrl: 'http://127.0.0.1:5001' // 后端服务器地址
  },

  onLaunch: function () {
    console.log('应用启动');

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

  // 清理所有保存的文件
  clearSavedFiles: function() {
    wx.getFileSystemManager().getSavedFileList({
      success: (res) => {
        const fileList = res.fileList;
        if (fileList && fileList.length > 0) {
          console.log(`发现 ${fileList.length} 个保存的文件，开始清理...`);

          fileList.forEach((file) => {
            wx.removeSavedFile({
              filePath: file.filePath,
              success: () => {
                console.log(`成功删除文件: ${file.filePath}`);
              },
              fail: (err) => {
                console.error(`删除文件失败: ${file.filePath}`, err);
              }
            });
          });
        } else {
          console.log('没有找到需要清理的保存文件');
        }
      },
      fail: (err) => {
        console.error('获取保存文件列表失败', err);
      }
    });
  }
})