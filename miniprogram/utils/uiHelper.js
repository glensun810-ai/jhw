/**
 * UI 辅助工具
 *
 * 提供常用的 UI 交互辅助函数
 */

import { handleApiError, ErrorCodes, ErrorMessages } from './errorHandler';

/**
 * 显示成功提示
 * @param {Object} options - 选项
 */
export function showToast(options) {
  const defaultOptions = {
    icon: 'success',
    duration: 2000,
    mask: true
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
export function showErrorToast(error, options = {}) {
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
export function showWarningToast(options) {
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
 * 显示加载提示
 * @param {string} title - 加载提示文本
 * @param {Object} options - 选项
 */
export function showLoading(title = '加载中...', options = {}) {
  const defaultOptions = {
    title,
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
export function hideLoading() {
  wx.hideLoading();
}

/**
 * 显示模态对话框
 * @param {Object} options - 选项
 * @returns {Promise<boolean>} 用户是否确认
 */
export function showModal(options) {
  const defaultOptions = {
    title: '提示',
    showCancel: true,
    confirmText: '确定',
    cancelText: '取消',
    confirmColor: '#1890ff',
    cancelColor: '#999999'
  };

  return new Promise((resolve, reject) => {
    wx.showModal({
      ...defaultOptions,
      ...options,
      success: (res) => {
        resolve(res.confirm);
      },
      fail: reject
    });
  });
}

/**
 * 显示错误模态框
 * @param {Object} error - 错误对象
 * @param {Object} options - 选项
 * @returns {Promise<boolean>} 用户是否确认重试
 */
export async function showErrorModal(error, options = {}) {
  const handled = handleApiError(error);
  
  const result = await showModal({
    title: handled.title || '发生错误',
    content: handled.message,
    confirmText: options.retryText || '重试',
    cancelText: options.cancelText || '取消',
    showCancel: options.showRetry !== false,
    confirmColor: options.showRetry !== false ? '#1890ff' : '#f44336'
  });
  
  return result;
}

/**
 * 显示确认对话框
 * @param {Object} options - 选项
 * @returns {Promise<boolean>} 用户是否确认
 */
export async function showConfirm(options) {
  return showModal({
    ...options,
    showCancel: true
  });
}

/**
 * 显示输入框
 * @param {Object} options - 选项
 * @returns {Promise<string>} 用户输入的内容
 */
export function showInput(options = {}) {
  const defaultOptions = {
    title: '请输入',
    placeholder: '',
    editable: true
  };

  return new Promise((resolve, reject) => {
    wx.showModal({
      ...defaultOptions,
      ...options,
      success: (res) => {
        if (res.confirm && res.content) {
          resolve(res.content);
        } else {
          resolve(null);
        }
      },
      fail: reject
    });
  });
}

/**
 * 显示动作面板
 * @param {Array} items - 选项列表
 * @param {Object} options - 选项
 * @returns {Promise<number>} 选中的索引
 */
export function showActionSheet(items, options = {}) {
  const defaultOptions = {
    itemList: items,
    itemColor: '#333333'
  };

  return new Promise((resolve, reject) => {
    wx.showActionSheet({
      ...defaultOptions,
      ...options,
      success: (res) => {
        resolve(res.tapIndex);
      },
      fail: (err) => {
        // 用户取消不视为错误
        if (err.errMsg && err.errMsg.includes('cancel')) {
          resolve(-1);
        } else {
          reject(err);
        }
      }
    });
  });
}

/**
 * 显示导航提示
 * @param {Object} options - 选项
 */
export function showNavigateToast(options) {
  const defaultOptions = {
    title: '跳转中...',
    icon: 'loading',
    duration: 1500
  };

  wx.showToast({
    ...defaultOptions,
    ...options
  });
}

/**
 * 格式化时间
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时间文本
 */
export function formatTime(seconds) {
  if (seconds < 60) {
    return `${seconds}秒`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return `${minutes}分${remainingSeconds}秒`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}小时${remainingMinutes}分`;
}

/**
 * 格式化进度百分比
 * @param {number} progress - 进度值（0-100）
 * @returns {string} 格式化后的进度文本
 */
export function formatProgress(progress) {
  const value = Math.min(100, Math.max(0, progress));
  return `${value.toFixed(0)}%`;
}

/**
 * 显示进度提示
 * @param {Object} status - 状态对象
 */
export function showProgressToast(status) {
  const progress = status?.progress || 0;
  const stage = status?.stage || status?.status_text || '处理中';

  wx.showToast({
    title: `${stage} ${progress}%`,
    icon: 'none',
    duration: 1500
  });
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} 是否成功
 */
export function copyToClipboard(text) {
  return new Promise((resolve, reject) => {
    wx.setClipboardData({
      data: text,
      success: () => {
        showToast({
          title: '已复制到剪贴板',
          icon: 'success'
        });
        resolve(true);
      },
      fail: reject
    });
  });
}

/**
 * 显示顶部提示条
 * @param {Object} options - 选项
 */
export function showTopTip(options) {
  const {
    title = '',
    duration = 2000,
    type = 'info' // info, success, warning, error
  } = options;

  // 创建提示元素
  const tipId = 'toptip_' + Date.now();
  const pages = getCurrentPages();
  const currentPage = pages[pages.length - 1];
  
  if (currentPage) {
    const pageData = currentPage.data || {};
    const topTips = pageData.topTips || [];
    
    topTips.push({
      id: tipId,
      title,
      type,
      show: true
    });
    
    currentPage.setData({ topTips });
    
    // 自动消失
    setTimeout(() => {
      const newTips = topTips.filter(tip => tip.id !== tipId);
      currentPage.setData({ topTips: newTips });
    }, duration);
  }
}

/**
 * 显示成功提示（快捷方法）
 * @param {string} title - 提示文本
 */
export function showSuccess(title = '操作成功') {
  showToast({
    title,
    icon: 'success',
    duration: 2000
  });
}

/**
 * 显示网络错误提示
 */
export function showNetworkError() {
  showErrorToast({
    code: ErrorCodes.NETWORK_ERROR,
    message: ErrorMessages[ErrorCodes.NETWORK_ERROR]
  });
}

/**
 * 显示超时错误提示
 */
export function showTimeoutError() {
  showErrorToast({
    code: ErrorCodes.TIMEOUT,
    message: ErrorMessages[ErrorCodes.TIMEOUT]
  });
}

/**
 * 显示权限错误提示
 */
export function showAuthError(message) {
  showErrorToast({
    code: ErrorCodes.UNAUTHORIZED,
    message: message || ErrorMessages[ErrorCodes.UNAUTHORIZED]
  });
}
