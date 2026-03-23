/**
 * UI 辅助工具
 *
 * 提供常用的 UI 交互辅助函数
 */

const { handleApiError, ErrorCodes, ErrorMessages } = require('./errorHandler');

/**
 * 显示成功提示
 * @param {Object} options - 选项
 */
function showToast(options) {
  const defaultOptions = {
    icon: 'success',
    duration: 1500,  // 【修复 - 2026-03-12】默认 1.5 秒自动消失
    mask: false      // 【修复 - 2026-03-12】不显示遮罩层，允许用户操作
  };

  wx.showToast({
    ...defaultOptions,
    ...options
  });
}

/**
 * 显示错误提示（友好样式）
 * @param {Object} error - 错误对象
 * @param {Object} options - 选项
 */
function showErrorToast(error, options = {}) {
  const handled = handleApiError(error);

  const defaultOptions = {
    title: handled.message,
    icon: 'none',
    duration: 3000,
    mask: true
  };

  wx.showToast({
    ...defaultOptions,
    ...options
  });

  return handled;
}

/**
 * 显示警告提示
 * @param {Object} options - 选项
 */
function showWarningToast(options) {
  const defaultOptions = {
    title: options.title || '警告',
    icon: 'none',
    duration: 2500,
    mask: true
  };

  wx.showToast({
    ...defaultOptions,
    ...options
  });
}

/**
 * 显示加载中
 * @param {string} title - 加载提示文本
 * @param {Object} options - 选项
 */
function showLoading(title = '加载中...', options = {}) {
  const defaultOptions = {
    title,
    icon: 'loading',
    duration: 60000,
    mask: true
  };

  wx.showLoading({
    ...defaultOptions,
    ...options
  });
}

/**
 * 隐藏加载中
 */
function hideLoading() {
  wx.hideLoading();
}

/**
 * 显示确认对话框
 * @param {Object} options - 选项
 * @returns {Promise} 用户选择结果
 */
function showModal(options) {
  return new Promise((resolve, reject) => {
    const defaultOptions = {
      title: options.title || '提示',
      content: options.content || '',
      showCancel: true,
      cancelText: '取消',
      cancelColor: '#999999',
      confirmText: '确定',
      confirmColor: '#4A7BFF'
    };

    wx.showModal({
      ...defaultOptions,
      ...options,
      success: (res) => {
        if (res.confirm) {
          resolve({ confirmed: true });
        } else if (res.cancel) {
          resolve({ confirmed: false, cancel: true });
        }
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
}

/**
 * 显示输入对话框
 * @param {Object} options - 选项
 * @returns {Promise} 用户输入结果
 */
function showInput(options = {}) {
  return new Promise((resolve, reject) => {
    const defaultOptions = {
      title: options.title || '输入',
      editable: true,
      placeholderText: options.placeholder || '',
      defaultValue: options.defaultValue || '',
      confirmText: '确定',
      cancelText: '取消'
    };

    wx.showModal({
      ...defaultOptions,
      ...options,
      success: (res) => {
        if (res.confirm && res.content) {
          resolve({ confirmed: true, value: res.content });
        } else if (res.cancel) {
          resolve({ confirmed: false, cancel: true });
        } else {
          resolve({ confirmed: false });
        }
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
}

/**
 * 显示操作菜单
 * @param {Array<string>} items - 菜单项
 * @param {Object} options - 选项
 * @returns {Promise} 用户选择结果
 */
function showActionSheet(items, options = {}) {
  return new Promise((resolve, reject) => {
    const defaultOptions = {
      itemList: items,
      itemColor: '#4A7BFF'
    };

    wx.showActionSheet({
      ...defaultOptions,
      ...options,
      success: (res) => {
        resolve({ tappedIndex: res.tapIndex, tappedItem: items[res.tapIndex] });
      },
      fail: (err) => {
        if (err.errMsg && err.errMsg.includes('cancel')) {
          resolve({ tappedIndex: -1, cancel: true });
        } else {
          reject(err);
        }
      }
    });
  });
}

/**
 * 显示带导航的 Toast
 * @param {Object} options - 选项
 */
function showNavigateToast(options) {
  const defaultOptions = {
    title: options.title || '操作成功',
    icon: 'success',
    duration: 2000,
    url: null
  };

  const mergedOptions = { ...defaultOptions, ...options };

  wx.showToast({
    title: mergedOptions.title,
    icon: mergedOptions.icon,
    duration: mergedOptions.duration,
    mask: true,
    success: () => {
      if (mergedOptions.url) {
        setTimeout(() => {
          wx.navigateTo({ url: mergedOptions.url });
        }, mergedOptions.duration);
      }
    }
  });
}

/**
 * 格式化时间（秒 -> MM:SS）
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时间
 */
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * 格式化进度（小数 -> 百分比）
 * @param {number} progress - 进度（0-1）
 * @returns {string} 格式化后的进度
 */
function formatProgress(progress) {
  return `${Math.round(progress * 100)}%`;
}

/**
 * 显示进度 Toast
 * @param {string} status - 状态
 */
function showProgressToast(status) {
  let title = '';
  let icon = 'none';

  switch (status) {
    case 'pending':
      title = '等待开始...';
      icon = 'loading';
      break;
    case 'running':
      title = '正在处理...';
      icon = 'loading';
      break;
    case 'completed':
      title = '处理完成！';
      icon = 'success';
      break;
    case 'failed':
      title = '处理失败';
      icon = 'none';
      break;
    default:
      title = '处理中...';
      icon = 'loading';
  }

  wx.showToast({
    title,
    icon,
    duration: status === 'completed' ? 2000 : 60000,
    mask: true
  });
}

/**
 * 复制到剪贴板
 * @param {string} text - 要复制的文本
 */
function copyToClipboard(text) {
  return new Promise((resolve, reject) => {
    wx.setClipboardData({
      data: text,
      success: () => {
        wx.showToast({
          title: '已复制到剪贴板',
          icon: 'success',
          duration: 2000
        });
        resolve();
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
}

/**
 * 显示顶部提示
 * @param {Object} options - 选项
 */
function showTopTip(options) {
  const {
    title = '',
    duration = 2000,
    type = 'info' // info, success, warning, error
  } = options;

  const colors = {
    info: '#1890ff',
    success: '#52c41a',
    warning: '#faad14',
    error: '#f5222d'
  };

  // 使用页面 data 中的 topTip 组件
  const pages = getCurrentPages();
  if (pages.length > 0) {
    const currentPage = pages[pages.length - 1];
    if (currentPage.setData) {
      currentPage.setData({
        topTip: {
          show: true,
          title,
          type,
          color: colors[type]
        }
      });

      setTimeout(() => {
        currentPage.setData({
          'topTip.show': false
        });
      }, duration);
    }
  }
}

/**
 * 显示成功提示
 * @param {string} title - 提示文本
 */
function showSuccess(title = '操作成功') {
  wx.showToast({
    title,
    icon: 'success',
    duration: 2000
  });
}

/**
 * 显示网络错误
 */
function showNetworkError() {
  wx.showToast({
    title: '网络连接失败',
    icon: 'none',
    duration: 2500
  });
}

/**
 * 显示超时错误
 */
function showTimeoutError() {
  wx.showToast({
    title: '请求超时，请重试',
    icon: 'none',
    duration: 2500
  });
}

/**
 * 显示授权错误
 * @param {string} message - 错误消息
 */
function showAuthError(message) {
  wx.showModal({
    title: '需要授权',
    content: message || '请先登录',
    showCancel: false,
    confirmText: '去登录',
    success: (res) => {
      if (res.confirm) {
        wx.navigateTo({ url: '/pages/login/login' });
      }
    }
  });
}

// 导出（CommonJS 语法，兼容微信小程序）
module.exports = {
  showToast,
  showErrorToast,
  showWarningToast,
  showLoading,
  hideLoading,
  showModal,
  showInput,
  showActionSheet,
  showNavigateToast,
  formatTime,
  formatProgress,
  showProgressToast,
  copyToClipboard,
  showTopTip,
  showSuccess,
  showNetworkError,
  showTimeoutError,
  showAuthError
};
