// components/auth-wrapper/auth-wrapper.js
const { checkLoginStatus, hasPermission } = require('../../utils/auth.js');

Component({
  properties: {
    // 需要的权限
    requiredPermission: {
      type: String,
      value: ''
    },
    // 是否显示登录提示
    showLoginPrompt: {
      type: Boolean,
      value: true
    },
    // 登录提示文本
    promptText: {
      type: String,
      value: '此功能需要登录后才能使用'
    }
  },

  data: {
    isLoggedIn: false,
    hasPermission: false
  },

  lifetimes: {
    attached() {
      this.checkAuth();
    }
  },

  methods: {
    checkAuth() {
      const isLoggedIn = checkLoginStatus();
      const hasPerm = this.data.requiredPermission ? 
        hasPermission(this.data.requiredPermission) : true;
      
      this.setData({
        isLoggedIn,
        hasPermission: hasPerm
      });
    },

    // 触发登录
    triggerLogin() {
      if (this.data.showLoginPrompt) {
        wx.showModal({
          title: '需要登录',
          content: this.data.promptText,
          confirmText: '去登录',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              wx.navigateTo({
                url: '/pages/login/login'
              });
            }
          }
        });
      }
    },

    // 检查权限
    checkPermission() {
      return this.data.isLoggedIn && this.data.hasPermission;
    }
  }
});