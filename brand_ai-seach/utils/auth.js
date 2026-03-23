/**
 * 用户鉴权管理模块
 * 负责用户登录状态管理、会话维护等功能
 */

const { userLogin, validateToken, refreshToken } = require('../api/auth');
const { API_ENDPOINTS } = require('../utils/config');

class AuthManager {
  constructor() {
    this.userInfo = null;
    this.token = null;
    this.isLoggedIn = false;
    this.init();
  }

  /**
   * 初始化用户状态
   */
  init() {
    // 从本地存储加载用户信息
    const storedUserInfo = wx.getStorageSync('userInfo');
    const storedToken = wx.getStorageSync('userToken');
    const loginStatus = wx.getStorageSync('isLoggedIn') || false;

    if (storedUserInfo && storedToken) {
      this.userInfo = storedUserInfo;
      this.token = storedToken;
      this.isLoggedIn = loginStatus;
    }
  }

  /**
   * 用户登录
   * @param {Object} loginData 登录数据
   * @returns {Promise}
   */
  async login(loginData) {
    return new Promise((resolve, reject) => {
      // 模拟微信登录
      wx.login({
        success: async (res) => {
          if (res.code) {
            try {
              // 向后端发送登录请求
              const loginRes = await userLogin({
                code: res.code,
                ...loginData
              });

              if (loginRes.status === 'success') {
                const userData = loginRes.data;

                // 保存用户信息
                this.userInfo = userData;
                this.token = userData.session_key; // 实际项目中应使用JWT token
                this.isLoggedIn = true;

                // 存储到本地
                wx.setStorageSync('userInfo', userData);
                wx.setStorageSync('userToken', this.token);
                wx.setStorageSync('isLoggedIn', true);

                resolve(userData);
              } else {
                reject(new Error(loginRes.error || '登录失败'));
              }
            } catch (error) {
              reject(error);
            }
          } else {
            reject(new Error('获取登录凭证失败'));
          }
        },
        fail: (error) => {
          reject(error);
        }
      });
    });
  }

  /**
   * 用户登出
   */
  logout() {
    this.userInfo = null;
    this.token = null;
    this.isLoggedIn = false;

    // 清除本地存储
    wx.removeStorageSync('userInfo');
    wx.removeStorageSync('userToken');
    wx.removeStorageSync('isLoggedIn');
    wx.removeStorageSync('userPermissions');
  }

  /**
   * 获取当前用户信息
   */
  getUserInfo() {
    return this.userInfo;
  }

  /**
   * 检查用户是否已登录
   */
  checkLoginStatus() {
    return this.isLoggedIn;
  }

  /**
   * 获取用户权限
   */
  getUserPermissions() {
    if (!this.isLoggedIn) {
      return ['basic']; // 未登录用户只有基础权限
    }

    // 从本地存储获取权限信息，或从服务器获取
    const permissions = wx.getStorageSync('userPermissions') || ['basic', 'history', 'save'];
    return permissions;
  }

  /**
   * 检查用户是否有特定权限
   * @param {string} permission 权限标识
   */
  hasPermission(permission) {
    const permissions = this.getUserPermissions();
    return permissions.includes(permission);
  }

  /**
   * 刷新用户令牌
   */
  async refreshToken() {
    // 模拟令牌刷新逻辑
    if (this.token) {
      try {
        const res = await refreshToken(wx.getStorageSync('refreshToken'));
        if (res.status === 'success') {
          this.token = res.token;
          wx.setStorageSync('userToken', this.token);
        }
      } catch (error) {
        console.error('刷新令牌失败:', error);
      }
    }
  }

  /**
   * 自动登录
   */
  async autoLogin() {
    if (this.token && this.userInfo) {
      try {
        const res = await validateToken();
        if (res.status === 'valid') {
          return this.userInfo;
        } else {
          // 令牌无效，清除登录状态
          this.logout();
          throw new Error('令牌已失效');
        }
      } catch (error) {
        // 请求失败，可能网络问题，暂时保持登录状态
        // 令牌验证失败时，也要清除登录状态以确保安全
        this.logout();
        throw error;
      }
    }
    throw new Error('未找到登录信息');
  }
}

// 创建全局实例
const authManager = new AuthManager();

module.exports = {
  authManager,
  login: authManager.login.bind(authManager),
  logout: authManager.logout.bind(authManager),
  getUserInfo: authManager.getUserInfo.bind(authManager),
  checkLoginStatus: authManager.checkLoginStatus.bind(authManager),
  hasPermission: authManager.hasPermission.bind(authManager),
  getUserPermissions: authManager.getUserPermissions.bind(authManager),
  autoLogin: authManager.autoLogin.bind(authManager)
};