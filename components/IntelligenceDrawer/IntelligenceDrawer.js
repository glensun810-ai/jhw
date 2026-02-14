// components/IntelligenceDrawer/IntelligenceDrawer.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    visible: {
      type: Boolean,
      value: false
    },
    data: {
      type: Object,
      value: null
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    drawerHeight: '80%',
    animation: null,
    showDrawer: false
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 显示抽屉
     */
    show: function() {
      this.setData({
        showDrawer: true
      });
      
      // 创建动画
      const animation = wx.createAnimation({
        duration: 300,
        timingFunction: 'ease-out'
      });
      
      animation.translateY(0).step();
      this.setData({
        animation: animation.export()
      });
    },

    /**
     * 隐藏抽屉
     */
    hide: function() {
      // 创建关闭动画
      const animation = wx.createAnimation({
        duration: 300,
        timingFunction: 'ease-out'
      });
      
      animation.translateY('100%').step();
      this.setData({
        animation: animation.export()
      });
      
      // 动画结束后隐藏组件
      setTimeout(() => {
        this.setData({
          showDrawer: false
        });
        this.triggerEvent('close');
      }, 300);
    },

    /**
     * 阻止背景滚动
     */
    preventTouchMove: function() {
      // 空函数，阻止触摸移动
    },

    /**
     * 复制全文
     */
    copyFullText: function() {
      const { answer } = this.properties.data || {};
      if (answer) {
        wx.setClipboardData({
          data: answer,
          success: () => {
            wx.showToast({
              title: '已复制',
              icon: 'success'
            });
          }
        });
      }
    },

    /**
     * 生成分析海报
     */
    generateAnalysisPoster: function() {
      wx.showToast({
        title: '生成海报中...',
        icon: 'loading'
      });
      
      // 这里可以集成海报生成功能
      setTimeout(() => {
        wx.hideToast();
        wx.showToast({
          title: '海报生成完成',
          icon: 'success'
        });
      }, 1500);
    }
  },

  lifetimes: {
    attached() {
      // 组件实例进入页面节点树时执行
    },
    ready() {
      // 组件在视图层布局完成后执行
    },
    detached() {
      // 组件实例被从页面节点树移除时执行
    }
  },

  observers: {
    'visible': function(newVal) {
      if (newVal) {
        this.show();
      } else {
        this.hide();
      }
    }
  }
})