const { checkLoginStatus, getUserInfo, logout, getUserPermissions } = require('../../utils/auth.js');

Page({
  data: {
    userName: '',
    userId: '',
    userRole: '',
    userInitial: '',
    permissions: [
      {
        id: 'basic',
        name: '基础权限',
        description: '查看公共数据、基础搜索功能',
        granted: true
      },
      {
        id: 'history',
        name: '历史记录权限',
        description: '查看和管理个人历史记录',
        granted: false
      },
      {
        id: 'save',
        name: '保存结果权限',
        description: '保存和管理搜索结果',
        granted: false
      },
      {
        id: 'analyze',
        name: '高级分析权限',
        description: '使用高级分析功能',
        granted: false
      },
      {
        id: 'export',
        name: '导出权限',
        description: '导出报告和数据',
        granted: false
      }
    ]
  },

  onLoad: function(options) {
    this.loadUserInfo();
    this.updatePermissions();
  },

  onShow: function() {
    this.loadUserInfo();
    this.updatePermissions();
  },

  // 加载用户信息
  loadUserInfo: function() {
    if (checkLoginStatus()) {
      const userInfo = getUserInfo();
      if (userInfo) {
        this.setData({
          userName: userInfo.nickName || userInfo.username || '用户',
          userId: userInfo.openid || userInfo.id || 'N/A',
          userRole: userInfo.role || '普通用户',
          userInitial: (userInfo.nickName || userInfo.username || 'U').charAt(0).toUpperCase()
        });
      }
    } else {
      this.setData({
        userName: '未登录用户',
        userId: 'N/A',
        userRole: '访客',
        userInitial: 'G'
      });
    }
  },

  // 更新权限状态
  updatePermissions: function() {
    const userPermissions = getUserPermissions();
    const permissions = this.data.permissions.map(perm => {
      return {
        ...perm,
        granted: userPermissions.includes(perm.id)
      };
    });
    
    this.setData({
      permissions: permissions
    });
  },

  // 切换权限
  togglePermission: function(e) {
    const permissionId = e.currentTarget.dataset.permission;
    
    if (!checkLoginStatus()) {
      wx.showModal({
        title: '需要登录',
        content: '此功能需要登录后才能使用',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.redirectTo({
              url: '/pages/login/login'
            });
          }
        }
      });
      return;
    }
    
    wx.showModal({
      title: '权限变更',
      content: '权限变更需要联系管理员',
      showCancel: false,
      confirmText: '确定'
    });
  },

  // 退出登录
  logout: function() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          logout();
          wx.showToast({
            title: '已退出登录',
            icon: 'success'
          });
          
          // 返回首页
          wx.reLaunch({
            url: '/pages/index/index'
          });
        }
      }
    });
  },

  // 升级账户
  upgradeAccount: function() {
    if (!checkLoginStatus()) {
      wx.showModal({
        title: '需要登录',
        content: '请先登录后再升级账户',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.redirectTo({
              url: '/pages/login/login'
            });
          }
        }
      });
      return;
    }
    
    wx.showModal({
      title: '账户升级',
      content: '请联系客服升级您的账户权限',
      confirmText: '联系客服',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 这期可以添加联系客服的功能
          wx.showToast({
            title: '功能开发中',
            icon: 'none'
          });
        }
      }
    });
  }
})