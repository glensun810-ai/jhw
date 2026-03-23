/**
 * 统一错误提示组件逻辑
 * 
 * 提供友好的错误提示展示和交互
 */

import { ErrorCodes, ErrorMessages } from '../../utils/errorHandler';

Component({
  /**
   * 组件属性
   */
  properties: {
    // 是否显示
    visible: {
      type: Boolean,
      value: false
    },
    // 错误类型：network | server | business | auth | timeout | default
    errorType: {
      type: String,
      value: 'default'
    },
    // 错误标题
    title: {
      type: String,
      value: ''
    },
    // 错误消息
    message: {
      type: String,
      value: ''
    },
    // 错误详情
    detail: {
      type: String,
      value: ''
    },
    // 错误代码
    errorCode: {
      type: String,
      value: ''
    },
    // 是否显示详情按钮
    showDetail: {
      type: Boolean,
      value: false
    },
    // 是否显示取消按钮
    showCancel: {
      type: Boolean,
      value: false
    },
    // 是否显示重试按钮
    showRetry: {
      type: Boolean,
      value: false
    },
    // 是否显示确认按钮
    showConfirm: {
      type: Boolean,
      value: false
    },
    // 取消按钮文本
    cancelText: {
      type: String,
      value: '取消'
    },
    // 重试按钮文本
    retryText: {
      type: String,
      value: '重试'
    },
    // 确认按钮文本
    confirmText: {
      type: String,
      value: '确定'
    },
    // 关闭按钮文本
    closeText: {
      type: String,
      value: '知道了'
    },
    // 是否自动关闭
    autoClose: {
      type: Boolean,
      value: false
    },
    // 自动关闭倒计时（秒）
    countdown: {
      type: Number,
      value: 5
    },
    // 是否为开发模式（显示错误代码）
    isDevMode: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件数据
   */
  data: {
    expanded: false, // 是否展开详情
    currentCountdown: 5, // 当前倒计时
    iconText: '❌', // 图标文本
    timer: null // 倒计时定时器
  },

  /**
   * 错误类型与图标映射
   */
  errorIcons: {
    network: '📡',
    server: '⚠️',
    business: '💼',
    auth: '🔒',
    timeout: '⏱️',
    default: '❌'
  },

  /**
   * 错误类型与标题映射
   */
  errorTitles: {
    network: '网络连接失败',
    server: '服务器错误',
    business: '业务错误',
    auth: '权限错误',
    timeout: '请求超时',
    default: '发生错误'
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      console.log('[ErrorToast] Component attached');
      this.updateIcon();
    },

    detached() {
      console.log('[ErrorToast] Component detached');
      this.clearTimer();
    }
  },

  /**
   * 属性观察器
   */
  observers: {
    visible(newVal) {
      if (newVal) {
        this.updateIcon();
        if (this.data.autoClose) {
          this.startCountdown();
        }
      } else {
        this.clearTimer();
      }
    },
    errorType() {
      this.updateIcon();
    },
    countdown(newVal) {
      this.setData({ currentCountdown: newVal });
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 更新图标
     */
    updateIcon() {
      const errorType = this.data.errorType;
      const icon = this.errorIcons[errorType] || this.errorIcons.default;
      this.setData({ iconText: icon });
    },

    /**
     * 获取错误标题
     * @param {string} type - 错误类型
     * @returns {string} 错误标题
     */
    getTitleByType(type) {
      return this.errorTitles[type] || this.errorTitles.default;
    },

    /**
     * 开始倒计时
     */
    startCountdown() {
      this.clearTimer();
      
      this.setData({ currentCountdown: this.data.countdown });
      
      this.data.timer = setInterval(() => {
        const remaining = this.data.currentCountdown - 1;
        
        if (remaining <= 0) {
          this.clearTimer();
          this.onClose();
        } else {
          this.setData({ currentCountdown: remaining });
        }
      }, 1000);
    },

    /**
     * 清除定时器
     */
    clearTimer() {
      if (this.data.timer) {
        clearInterval(this.data.timer);
        this.data.timer = null;
      }
    },

    /**
     * 切换详情展开/收起
     */
    toggleExpand() {
      this.setData({
        expanded: !this.data.expanded
      });
    },

    /**
     * 关闭错误提示
     */
    onClose() {
      this.clearTimer();
      this.triggerEvent('close');
      this.triggerEvent('change', { visible: false });
    },

    /**
     * 取消操作
     */
    onCancel() {
      this.clearTimer();
      this.triggerEvent('cancel');
      this.triggerEvent('close');
    },

    /**
     * 重试操作
     */
    onRetry() {
      this.clearTimer();
      this.triggerEvent('retry');
    },

    /**
     * 确认操作
     */
    onConfirm() {
      this.clearTimer();
      this.triggerEvent('confirm');
      this.triggerEvent('close');
    },

    /**
     * 显示错误提示（便捷方法）
     * @param {Object} options - 错误选项
     */
    show(options = {}) {
      const {
        errorType = 'default',
        message = '',
        title = '',
        detail = '',
        errorCode = '',
        showRetry = false,
        showCancel = false,
        showConfirm = true,
        autoClose = true,
        countdown = 5
      } = options;

      this.setData({
        visible: true,
        errorType,
        message,
        title: title || this.getTitleByType(errorType),
        detail,
        errorCode,
        showRetry,
        showCancel,
        showConfirm,
        autoClose,
        countdown
      });
    },

    /**
     * 隐藏错误提示
     */
    hide() {
      this.setData({ visible: false });
      this.clearTimer();
    },

    /**
     * 根据错误对象显示提示
     * @param {Object} error - 错误对象
     * @param {Object} options - 额外选项
     */
    showError(error, options = {}) {
      const handled = this.handleError(error);
      
      this.setData({
        visible: true,
        errorType: handled.type,
        message: handled.message,
        title: handled.title,
        detail: handled.detail || '',
        errorCode: handled.code || '',
        showRetry: options.showRetry !== undefined ? options.showRetry : handled.retryable,
        showCancel: options.showCancel || false,
        showConfirm: options.showConfirm !== undefined ? options.showConfirm : true,
        autoClose: options.autoClose !== undefined ? options.autoClose : false,
        countdown: options.countdown || 5
      });
    },

    /**
     * 处理错误对象
     * @param {Object} error - 错误对象
     * @returns {Object} 处理后的错误信息
     */
    handleError(error) {
      if (!error) {
        return {
          type: 'default',
          title: '发生错误',
          message: '未知错误，请稍后重试',
          code: '',
          detail: '',
          retryable: true
        };
      }

      // 根据错误代码判断类型
      const code = error.code || error.errorCode || '';
      const message = error.message || error.errMsg || '未知错误';
      
      let type = 'default';
      let title = '发生错误';
      let retryable = true;

      // 网络错误
      if (code === ErrorCodes.NETWORK_ERROR || message.includes('网络') || message.includes('fail')) {
        type = 'network';
        title = '网络连接失败';
        retryable = true;
      }
      // 超时错误
      else if (code === ErrorCodes.TIMEOUT || message.includes('超时') || message.includes('timeout')) {
        type = 'timeout';
        title = '请求超时';
        retryable = true;
      }
      // 权限错误
      else if (code === ErrorCodes.UNAUTHORIZED || message.includes('登录') || message.includes('授权')) {
        type = 'auth';
        title = '权限错误';
        retryable = false;
      }
      // 任务不存在
      else if (code === ErrorCodes.TASK_NOT_FOUND || message.includes('不存在')) {
        type = 'business';
        title = '资源不存在';
        retryable = false;
      }
      // 服务器错误
      else if (code === ErrorCodes.SERVER_ERROR || code === ErrorCodes.INTERNAL_ERROR || 
               (error.statusCode && error.statusCode >= 500)) {
        type = 'server';
        title = '服务器错误';
        retryable = true;
      }

      return {
        type,
        title,
        message,
        code,
        detail: error.detail || '',
        retryable
      };
    }
  }
});
