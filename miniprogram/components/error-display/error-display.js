/**
 * 错误显示组件
 * 
 * P2-4 优化：可复用组件 - 显示错误信息和操作建议
 * 
 * 使用示例:
 * <error-display 
 *   error-type="{{errorType}}"
 *   error-message="{{errorMessage}}"
 *   fallback-info="{{fallbackInfo}}"
 *   onRetry="handleRetry"
 *   onNavigate="handleNavigate"
 * />
 * 
 * @author 系统架构组
 * @date 2026-03-08
 * @version 1.0.0
 */

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    // 错误类型
    errorType: {
      type: String,
      value: 'error',
      observer: '_onErrorTypeChange'
    },
    
    // 错误消息
    errorMessage: {
      type: String,
      value: '发生未知错误'
    },
    
    // 降级信息（包含标题、描述、图标、操作）
    fallbackInfo: {
      type: Object,
      value: null,
      observer: '_onFallbackInfoChange'
    },
    
    // 是否显示重试按钮
    showRetry: {
      type: Boolean,
      value: true
    },
    
    // 自定义样式类名
    customClass: {
      type: String,
      value: ''
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // 默认错误配置
    defaultConfig: {
      error: {
        title: '发生错误',
        description: '系统遇到意外错误',
        icon: 'error',
        iconColor: '#dc3545'
      },
      not_found: {
        title: '未找到',
        description: '请求的内容不存在',
        icon: 'search',
        iconColor: '#ffc107'
      },
      timeout: {
        title: '请求超时',
        description: '请求处理时间过长',
        icon: 'time',
        iconColor: '#fd7e14'
      },
      no_results: {
        title: '无结果',
        description: '未找到相关结果',
        icon: 'inbox',
        iconColor: '#6c757d'
      }
    },
    
    // 当前配置
    currentConfig: null
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 错误类型变化监听
     */
    _onErrorTypeChange(newType) {
      this._updateConfig(newType);
    },

    /**
     * 降级信息变化监听
     */
    _onFallbackInfoChange(newInfo) {
      if (newInfo) {
        this.setData({ currentConfig: newInfo });
      }
    },

    /**
     * 根据错误类型更新配置
     */
    _updateConfig(type) {
      const defaultConfig = this.data.defaultConfig[type] || this.data.defaultConfig.error;
      
      this.setData({
        currentConfig: {
          ...defaultConfig,
          type: type
        }
      });
    },

    /**
     * 点击重试
     */
    handleRetry() {
      this.triggerEvent('retry');
    },

    /**
     * 点击操作按钮
     */
    handleAction(e) {
      const { action } = e.currentTarget.dataset;
      
      if (action.type === 'navigate') {
        wx.navigateTo({
          url: action.url,
          fail: () => {
            // 如果 navigateTo 失败，尝试 switchTab
            wx.switchTab({
              url: action.url
            });
          }
        });
      } else if (action.type === 'retry') {
        this.handleRetry();
      } else if (action.type === 'contact') {
        this.handleContact();
      }
      
      this.triggerEvent('action', { action });
    },

    /**
     * 联系客服
     */
    handleContact() {
      wx.showModal({
        title: '联系客服',
        content: '请添加客服微信：xxx 或拨打客服电话：xxx',
        showCancel: false
      });
    },

    /**
     * 返回首页
     */
    goHome() {
      wx.switchTab({
        url: '/pages/index/index'
      });
    }
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this._updateConfig(this.properties.errorType);
    }
  }
});
