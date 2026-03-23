// components/login-prompt/login-prompt.js
const { checkLoginStatus } = require('../../utils/auth.js');

Component({
  properties: {
    // 提示文本
    promptText: {
      type: String,
      value: '登录后可享受完整功能'
    },
    // 按钮文本
    buttonText: {
      type: String,
      value: '立即登录'
    },
    // 是否显示
    show: {
      type: Boolean,
      value: true
    }
  },

  data: {
    isLoggedIn: false
  },

  lifetimes: {
    attached() {
      this.checkLoginStatus();
    }
  },

  methods: {
    checkLoginStatus() {
      const isLoggedIn = checkLoginStatus();
      this.setData({
        isLoggedIn
      });
    },

    // 跳转到登录页面
    goToLogin() {
      if (!this.data.isLoggedIn) {
        wx.navigateTo({
          url: '/pages/login/login'
        });
      }
    }
  }
});