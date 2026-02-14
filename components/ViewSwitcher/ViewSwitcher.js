// components/ViewSwitcher/ViewSwitcher.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    currentView: {
      type: String,
      value: 'standard'
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    views: [
      { id: 'standard', label: '全景透视' },
      { id: 'model', label: '模型对比' },
      { id: 'question', label: '问题诊断' }
    ]
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 切换视图
     */
    switchView: function(e) {
      const viewId = e.currentTarget.dataset.view;

      this.setData({
        currentView: viewId
      });

      // 触发视图切换事件
      this.triggerEvent('viewChange', {
        view: viewId
      });
    }
  }
})