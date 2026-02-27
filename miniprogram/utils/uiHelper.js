/**
 * UI 辅助工具
 * 
 * 提供常用的 UI 交互辅助函数
 */

/**
 * 显示成功提示
 * @param {Object} options - 选项
 */
export function showToast(options) {
  const defaultOptions = {
    icon: 'success',
    duration: 2000
  };

  wx.showToast({
    ...defaultOptions,
    ...options
  });
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
    cancelText: '取消'
  };

  return new Promise((resolve, reject) => {
    wx.showModal({
      ...defaultOptions,
      ...options,
      success: (res) => {
        if (res.confirm) {
          resolve(true);
        } else {
          resolve(false);
        }
      },
      fail: reject
    });
  });
}

/**
 * 显示加载中
 * @param {string} title - 加载提示文本
 */
export function showLoading(title = '加载中...') {
  wx.showLoading({
    title,
    mask: true
  });
}

/**
 * 隐藏加载中
 */
export function hideLoading() {
  wx.hideLoading();
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
 * 显示诊断进度提示
 * @param {Object} status - 状态对象
 */
export function showProgressToast(status) {
  const progress = status?.progress || 0;
  const stage = status?.stage || '处理中';
  
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
 * 显示确认对话框（带倒计时）
 * @param {Object} options - 选项
 * @param {number} options.countdown - 倒计时秒数
 * @returns {Promise<boolean>} 用户是否确认
 */
export function showConfirmWithCountdown(options) {
  const { countdown = 3, ...modalOptions } = options;
  let remaining = countdown;
  
  return new Promise((resolve) => {
    const timer = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        clearInterval(timer);
        wx.hideModal();
        resolve(false);
      }
    }, 1000);
    
    showModal({
      ...modalOptions,
      confirmText: `确定 (${remaining}s)`,
      success: (res) => {
        clearInterval(timer);
        resolve(res.confirm);
      }
    });
  });
}
