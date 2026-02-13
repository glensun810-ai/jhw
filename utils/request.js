/**
 * @file utils/request.js
 * @description 核心请求基座 - 严禁 AI 随意修改内部逻辑
 */

// 环境配置：方便未来切换开发/测试/生产环境
const ENV_CONFIG = {
  develop: 'https://dev.api.yourdomain.com', // 开发环境
  trial: 'https://test.api.yourdomain.com',   // 体验环境
  release: 'https://api.yourdomain.com'      // 线上环境
};

// 获取当前小程序环境
const { miniProgram } = wx.getAccountInfoSync();
const BASE_URL = ENV_CONFIG[miniProgram.envVersion] || ENV_CONFIG.release;

const request = (options) => {
  return new Promise((resolve, reject) => {
    // 1. 组装 Header（自动注入 Token）
    const header = {
      'content-type': 'application/json',
      ...options.header
    };
    const token = wx.getStorageSync('token');
    if (token) {
      header['Authorization'] = `Bearer ${token}`;
    }

    // 2. 显示加载状态（可选）
    if (options.loading !== false) {
      wx.showLoading({ title: '加载中...', mask: true });
    }

    wx.request({
      url: options.url.startsWith('http') ? options.url : `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data || {},
      header: header,
      timeout: 10000,
      success: (res) => {
        // 3. 业务状态码拦截（根据你的后端协议修改）
        const { statusCode, data } = res;

        if (statusCode >= 200 && statusCode < 300) {
          // 假设后端返回格式为 { code: 0, data: {...}, msg: "" }
          if (data.code === 0 || data.code === 200) {
            resolve(data.data);
          } else if (data.code === 401) {
            // Token 过期处理
            wx.removeStorageSync('token');
            wx.navigateTo({ url: '/pages/login/login' });
            reject(data);
          } else {
            wx.showToast({ title: data.msg || '业务错误', icon: 'none' });
            reject(data);
          }
        } else {
          wx.showToast({ title: `服务器异常: ${statusCode}`, icon: 'none' });
          reject(res);
        }
      },
      fail: (err) => {
        wx.showToast({ title: '网络连接失败', icon: 'error' });
        reject(err);
      },
      complete: () => {
        if (options.loading !== false) wx.hideLoading();
      }
    });
  });
};

export default request;