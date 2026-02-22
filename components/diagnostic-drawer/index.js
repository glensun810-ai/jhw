/**
 * 诊断抽屉主组件 - 重构简化版
 * 
 * 重构说明:
 * - 核心逻辑 → DrawerCore/index.js
 * - 内容渲染 → DrawerContent/index.js
 * 
 * 本文件保留:
 * - 组件协调
 * - 事件转发
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    showDrawer: {
      type: Boolean,
      value: false
    },
    currentQuestionData: {
      type: Object,
      value: null
    },
    brandName: {
      type: String,
      value: ''
    },
    competitors: {
      type: Array,
      value: []
    }
  },

  data: {
    // 简化后的数据
    responseText: ''
  },

  lifetimes: {
    attached() {
      console.log('[DiagnosticDrawer] 主组件已挂载');
    }
  },

  methods: {
    /**
     * 关闭抽屉
     */
    onClose() {
      this.triggerEvent('close');
    },

    /**
     * 数据准备就绪
     */
    onDataReady(e) {
      const { modelList, geoData, sourceList } = e.detail;
      
      // 提取响应文本
      const responseText = geoData.response || '';
      this.setData({ responseText });

      // 转发事件
      this.triggerEvent('dataready', { modelList, geoData, sourceList });
    },

    /**
     * 模型切换
     */
    onModelChange(e) {
      this.triggerEvent('modelchange', e.detail);
    },

    /**
     * 信源点击
     */
    onSourceTap(e) {
      this.triggerEvent('sourcetap', e.detail);
    },

    /**
     * 渲染完成
     */
    onRenderComplete() {
      this.triggerEvent('rendercomplete');
    }
  }
});
