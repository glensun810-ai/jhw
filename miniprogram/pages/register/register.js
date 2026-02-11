const { login } = require('../../utils/auth.js');

Page({
  data: {
    phone: '',
    verificationCode: '',
    password: '',
    confirmPassword: '',
    countdown: 0,
    showAgreementModal: false,
    agreementTitle: '',
    agreementContent: '',
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

  // 密码输入
  onPasswordInput: function(e) {
    this.setData({
      password: e.detail.value
    });
  },

  // 确认密码输入
  onConfirmPasswordInput: function(e) {
    this.setData({
      confirmPassword: e.detail.value
    });
  },

  // 获取验证码
  getVerificationCode: function() {
    const phone = this.data.phone;
    
    if (!this.isValidPhone(phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '发送中...'
    });

    // 这后端发送验证码请求
    wx.request({
      url: 'http://127.0.0.1:5001/api/send-verification-code',
      method: 'POST',
      data: {
        phone: phone
      },
      success: (res) => {
        wx.hideLoading();
        if (res.data.status === 'success') {
          wx.showToast({
            title: '验证码已发送',
            icon: 'success'
          });
          
          // 开始倒计时
          this.startCountdown();
        } else {
          wx.showToast({
            title: res.data.message || '发送失败',
            icon: 'none'
          });
        }
      },
      fail: (error) => {
        wx.hideLoading();
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
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

  // 注册
  onRegister: function() {
    const { phone, verificationCode, password, confirmPassword } = this.data;

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

    if (!password) {
      wx.showToast({
        title: '请输入密码',
        icon: 'none'
      });
      return;
    }

    if (password !== confirmPassword) {
      wx.showToast({
        title: '两次输入的密码不一致',
        icon: 'none'
      });
      return;
    }

    if (password.length < 6) {
      wx.showToast({
        title: '密码长度至少6位',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '注册中...'
    });

    // 这后端发送注册请求
    wx.request({
      url: 'http://127.0.0.1:5001/api/register',
      method: 'POST',
      data: {
        phone: phone,
        verificationCode: verificationCode,
        password: password
      },
      success: (res) => {
        wx.hideLoading();
        if (res.data.status === 'success') {
          wx.showToast({
            title: '注册成功',
            icon: 'success'
          });

          // 自动登录
          login({
            phone: phone,
            password: password
          }).then((userData) => {
            // 跳转到首页
            wx.reLaunch({
              url: '/pages/index/index'
            });
          }).catch((error) => {
            wx.showToast({
              title: error.message || '登录失败',
              icon: 'none'
            });
          });
        } else {
          wx.showToast({
            title: res.data.message || '注册失败',
            icon: 'none'
          });
        }
      },
      fail: (error) => {
        wx.hideLoading();
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
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
  },

  // 跳转到登录页面
  goToLogin: function() {
    wx.redirectTo({
      url: '/pages/login/login'
    });
  }
})