/**
 * 权限中间件
 * 用于统一处理页面权限验证
 */

const { checkLoginStatus, hasPermission } = require('./auth.js');

/**
 * 权限验证中间件
 * @param {string} requiredPermission 需要的权限
 * @param {string} redirectUrl 未通过权限验证时的跳转页面
 * @returns {Function} 中间件函数
 */
function requireAuth(requiredPermission = null, redirectUrl = '/pages/login/login') {
  return function(pageInstance) {
    // 保存原始的onLoad方法
    const originalOnLoad = pageInstance.onLoad;
    
    // 重写onLoad方法
    pageInstance.onLoad = function(options) {
      // 检查登录状态
      if (!checkLoginStatus()) {
        wx.showModal({
          title: '需要登录',
          content: '此功能需要登录后才能使用',
          confirmText: '去登录',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              wx.redirectTo({
                url: redirectUrl
              });
            } else {
              // 如果用户取消，返回上一页
              wx.navigateBack();
            }
          }
        });
        return; // 阻止页面继续加载
      }
      
      // 检查特定权限
      if (requiredPermission && !hasPermission(requiredPermission)) {
        wx.showModal({
          title: '权限不足',
          content: '您没有访问此功能的权限',
          showCancel: false,
          confirmText: '确定',
          success: () => {
            wx.navigateBack();
          }
        });
        return; // 阻止页面继续加载
      }
      
      // 如果权限验证通过，执行原始的onLoad
      if (originalOnLoad) {
        originalOnLoad.call(this, options);
      }
    };
    
    return pageInstance;
  };
}

/**
 * 权限检查函数
 * @param {string} requiredPermission 需要的权限
 * @returns {boolean} 是否有权限
 */
function checkAuth(requiredPermission = null) {
  // 检查登录状态
  if (!checkLoginStatus()) {
    return false;
  }
  
  // 检查特定权限
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return false;
  }
  
  return true;
}

/**
 * 需要登录的装饰器
 * @param {string} redirectUrl 未登录时的跳转页面
 */
function requireLogin(redirectUrl = '/pages/login/login') {
  return requireAuth(null, redirectUrl);
}

/**
 * 需要特定权限的装饰器
 * @param {string} permission 权限标识
 * @param {string} redirectUrl 未通过权限验证时的跳转页面
 */
function requirePermission(permission, redirectUrl = '/pages/login/login') {
  return requireAuth(permission, redirectUrl);
}

/**
 * 权限保护的导航函数
 * @param {string} url 目标页面
 * @param {string} requiredPermission 需要的权限
 * @param {string} loginUrl 登录页面
 */
function navigateWithAuth(url, requiredPermission = null, loginUrl = '/pages/login/login') {
  // 检查登录状态
  if (!checkLoginStatus()) {
    wx.showModal({
      title: '需要登录',
      content: '此功能需要登录后才能使用',
      confirmText: '去登录',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          wx.redirectTo({
            url: loginUrl
          });
        }
      }
    });
    return;
  }
  
  // 检查特定权限
  if (requiredPermission && !hasPermission(requiredPermission)) {
    wx.showModal({
      title: '权限不足',
      content: '您没有访问此功能的权限',
      showCancel: false,
      confirmText: '确定'
    });
    return;
  }
  
  // 有权限，执行导航
  wx.navigateTo({
    url: url
  });
}

module.exports = {
  requireAuth,
  checkAuth,
  requireLogin,
  requirePermission,
  navigateWithAuth
};