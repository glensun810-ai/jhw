const { login, checkLoginStatus } = require('../../utils/auth.js');
const { sendVerificationCode } = require('../../api/auth.js');

Page({
  data: {
    loginMethod: 'wechat', // 登录方式：wechat 或 phone
    phone: '',
    verificationCode: '',
    countdown: 0,
    showAgreementModal: false,
    agreementTitle: '',
    agreementContent: '',
  },

  onLoad: function(options) {
    // 检查是否已登录
    if (checkLoginStatus()) {
      wx.showToast({
        title: '您已登录',
        icon: 'none'
      });
      // 跳转到首页
      wx.reLaunch({
        url: '/pages/index/index'
      });
      return;
    }
  },

  // 切换登录方式
  switchMethod: function(e) {
    const method = e.currentTarget.dataset.method;
    this.setData({
      loginMethod: method
    });
  },

  // 微信登录
  onWechatLogin: function(e) {
    if (e.detail.errMsg !== 'getUserProfile:ok') {
      wx.showToast({
        title: '授权失败',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '登录中...'
    });

    // 调用登录函数
    login({
      userInfo: e.detail.userInfo
    }).then((userData) => {
      wx.hideLoading();
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      });

      // 跳转到首页或返回上一页
      const pages = getCurrentPages();
      if (pages.length > 1) {
        wx.navigateBack();
      } else {
        wx.reLaunch({
          url: '/pages/index/index'
        });
      }
    }).catch((error) => {
      wx.hideLoading();
      wx.showToast({
        title: error.message || '登录失败',
        icon: 'none'
      });
    });
  },

  // 手机号输入
  onPhoneInput: function(e) {
    this.setData({
      phone: e.detail.value
    });
  },

  // 验证码输入
  onVerificationCodeInput: function(e) {
    this.setData({
      verificationCode: e.detail.value
    });
  },

  // 获取验证码
  async getVerificationCode() {
    const phone = this.data.phone;

    if (!this.isValidPhone(phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      });
      return;
    }

    try {
      wx.showLoading({
        title: '发送中...'
      });

      const res = await sendVerificationCode({ phone });

      wx.hideLoading();
      if (res.status === 'success') {
        wx.showToast({
          title: '验证码已发送',
          icon: 'success'
        });

        // 开始倒计时
        this.startCountdown();
      } else {
        wx.showToast({
          title: res.message || '发送失败',
          icon: 'none'
        });
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({
        title: '网络错误',
        icon: 'none'
      });
    }
  },

  // 开始倒计时
  startCountdown: function() {
    let seconds = 60;
    this.setData({
      countdown: seconds
    });

    const timer = setInterval(() => {
      seconds--;
      if (seconds <= 0) {
        clearInterval(timer);
        this.setData({
          countdown: 0
        });
      } else {
        this.setData({
          countdown: seconds
        });
      }
    }, 1000);
  },

  // 手机号登录
  onPhoneLogin: function() {
    const { phone, verificationCode } = this.data;

    if (!this.isValidPhone(phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      });
      return;
    }

    if (!verificationCode) {
      wx.showToast({
        title: '请输入验证码',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '登录中...'
    });

    // 调用登录函数
    login({
      phone: phone,
      verificationCode: verificationCode
    }).then((userData) => {
      wx.hideLoading();
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      });

      // 跳转到首页或返回上一页
      const pages = getCurrentPages();
      if (pages.length > 1) {
        wx.navigateBack();
      } else {
        wx.reLaunch({
          url: '/pages/index/index'
        });
      }
    }).catch((error) => {
      wx.hideLoading();
      wx.showToast({
        title: error.message || '登录失败',
        icon: 'none'
      });
    });
  },

  // 验证手机号格式
  isValidPhone: function(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/;
    return phoneRegex.test(phone);
  },

  // 显示隐私协议
  showPrivacyAgreement: function() {
    this.setData({
      showAgreementModal: true,
      agreementTitle: '隐私协议',
      agreementContent: this.getPrivacyAgreementContent()
    });
  },

  // 显示用户协议
  showUserAgreement: function() {
    this.setData({
      showAgreementModal: true,
      agreementTitle: '用户协议',
      agreementContent: this.getUserAgreementContent()
    });
  },

  // 隐藏协议弹窗
  hideAgreementModal: function() {
    this.setData({
      showAgreementModal: false
    });
  },

  // 获取隐私协议内容
  getPrivacyAgreementContent: function() {
    return `
      <div>
        <h3>隐私协议</h3>
        <p>欢迎使用品牌洞察平台。本平台尊重并保护用户隐私，特此制定本隐私协议。</p>
        <h4>信息收集</h4>
        <p>我们可能会收集您主动提供的信息，如手机号、邮箱等。</p>
        <h4>信息使用</h4>
        <p>收集的信息仅用于为您提供服务，不会泄露给第三方。</p>
        <h4>信息保护</h4>
        <p>我们采取各种安全措施保护您的信息安全。</p>
      </div>
    `;
  },

  // 获取用户协议内容
  getUserAgreementContent: function() {
    return `
      <div>
        <h3>用户协议</h3>
        <p>欢迎使用品牌洞察平台。使用本平台服务前，请仔细阅读本协议。</p>
        <h4>服务条款</h4>
        <p>本平台提供的服务仅供合法使用，禁止任何违法活动。</p>
        <h4>用户责任</h4>
        <p>用户应遵守相关法律法规，不得传播违法不良信息。</p>
        <h4>服务变更</h4>
        <p>本平台有权根据需要修改服务条款，修改后会及时通知用户。</p>
      </div>
    `;
  }
})