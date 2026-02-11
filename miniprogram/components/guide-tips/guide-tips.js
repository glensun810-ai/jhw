// components/guide-tips/guide-tips.js
Component({
  properties: {
    // 提示类型
    type: {
      type: String,
      value: 'info' // info, warning, success, error
    },
    // 提示文本
    text: {
      type: String,
      value: ''
    },
    // 是否显示
    show: {
      type: Boolean,
      value: true
    },
    // 是否可关闭
    closable: {
      type: Boolean,
      value: true
    },
    // 自动隐藏时间（毫秒）
    autoHideDuration: {
      type: Number,
      value: 0 // 0 表示不自动隐藏
    }
  },

  data: {
    isVisible: true
  },

  observers: {
    'show': function(newVal) {
      this.setData({
        isVisible: newVal
      });
    }
  },

  lifetimes: {
    attached() {
      if (this.data.autoHideDuration > 0) {
        setTimeout(() => {
          this.setData({
            isVisible: false
          });
        }, this.data.autoHideDuration);
      }
    }
  },

  methods: {
    // 关闭提示
    closeTip() {
      if (this.data.closable) {
        this.setData({
          isVisible: false
        });
        
        // 触发关闭事件
        this.triggerEvent('close');
      }
    },

    // 重新显示提示
    showTip() {
      this.setData({
        isVisible: true
      });
    }
  }
});