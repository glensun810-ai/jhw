// components/SourceCard/SourceCard.js
Component({
  options: {
    addGlobalClass: true
  },

  /**
   * 组件的属性列表
   */
  properties: {
    sources: {
      type: Array,
      value: []
    },
    title: {
      type: String,
      value: '信源列表'
    },
    loading: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {},

  /**
   * 组件的方法列表
   */
  methods: {
    // 点击信源卡片事件
    onSourceCardTap(e) {
      const index = e.currentTarget.dataset.index;
      const source = this.data.sources[index];

      if (source.url) {
        wx.setClipboardData({
          data: source.url,
          success: () => {
            wx.showToast({
              title: '链接已复制',
              icon: 'success'
            });
          },
          fail: () => {
            wx.showToast({
              title: '复制失败',
              icon: 'error'
            });
          }
        });
      }
    },

    // 获取域名
    getDomain(url) {
      try {
        const domain = new URL(url).hostname;
        return domain;
      } catch (e) {
        // 如果URL格式不正确，返回原始URL的前30个字符
        return url.length > 30 ? url.substring(0, 30) + '...' : url;
      }
    },

    // 获取favicon URL
    getFavicon(domain) {
      // 简单的favicon URL生成逻辑
      return `https://${domain}/favicon.ico`;
    }
  },

  lifetimes: {
    attached() {
      // 组件实例进入页面节点树时执行
    },
    detached() {
      // 组件实例被从页面节点树移除时执行
    }
  }
})