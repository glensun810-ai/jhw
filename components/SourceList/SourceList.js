// components/SourceList/SourceList.js
Component({
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
    // 点击信源项事件
    onSourceTap(e) {
      const index = e.currentTarget.dataset.index;
      const source = this.data.sources[index];

      this.triggerEvent('sourceTap', {
        source: source,
        index: index
      });
    },

    // 复制链接事件
    onCopyLink(e) {
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