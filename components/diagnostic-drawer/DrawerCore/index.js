/**
 * 诊断抽屉核心组件
 * 
 * 职责：
 * - 抽屉基础交互
 * - 数据加载
 * - 状态管理
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    showDrawer: {
      type: Boolean,
      value: false,
      observer: 'onShowDrawerChange'
    },
    currentQuestionData: {
      type: Object,
      value: null,
      observer: 'onQuestionDataChange'
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
    // 加载状态
    isLoading: true,
    hasError: false,
    errorMessage: '',

    // 当前模型
    currentModelId: '',
    currentModelName: '',
    modelList: [],

    // 指标数据
    avgRank: '-',
    sentimentValue: '-',
    sentimentStatus: 'neutral',
    riskLevel: 'safe',
    riskLevelText: '低风险',

    // 信源列表
    sourceList: [],

    // 手势控制
    touchStartY: 0,
    touchCurrentY: 0,
    drawerOffset: 100
  },

  lifetimes: {
    attached() {
      console.log('[DrawerCore] 组件已挂载');
    },
    detached() {
      this.cleanup();
    }
  },

  methods: {
    /**
     * 显示抽屉变化监听
     */
    onShowDrawerChange(newVal) {
      if (newVal) {
        this.loadDrawerData();
      }
    },

    /**
     * 问题数据变化监听
     */
    onQuestionDataChange(newVal) {
      if (newVal && this.data.showDrawer) {
        this.loadDrawerData();
      }
    },

    /**
     * 加载抽屉数据
     */
    loadDrawerData() {
      const questionData = this.data.currentQuestionData;
      
      if (!questionData) {
        this.setData({
          isLoading: false,
          hasError: true,
          errorMessage: '无数据'
        });
        return;
      }

      // 提取模型列表
      const modelList = questionData.models || [];
      const currentModel = modelList[0] || {};

      // 提取指标数据
      const geoData = questionData.geo_data || {};
      const avgRank = geoData.rank || '-';
      const sentiment = geoData.sentiment || 0;

      // 计算情感状态
      let sentimentStatus = 'neutral';
      let sentimentValue = sentiment;
      if (sentiment > 0.5) {
        sentimentStatus = 'positive';
      } else if (sentiment < -0.5) {
        sentimentStatus = 'negative';
      }

      // 计算风险等级
      let riskLevel = 'safe';
      let riskLevelText = '低风险';
      if (geoData.interception) {
        riskLevel = 'high';
        riskLevelText = '高风险';
      }

      // 提取信源列表
      const sourceList = geoData.cited_sources || [];

      this.setData({
        isLoading: false,
        hasError: false,
        currentModelId: currentModel.id || '',
        currentModelName: currentModel.name || '',
        modelList,
        avgRank,
        sentimentValue,
        sentimentStatus,
        riskLevel,
        riskLevelText,
        sourceList
      });

      // 触发数据加载完成事件
      this.triggerEvent('dataready', {
        modelList,
        geoData,
        sourceList
      });
    },

    /**
     * 关闭抽屉
     */
    closeDrawer() {
      this.triggerEvent('close');
    },

    /**
     * 模型切换
     */
    onModelChange(e) {
      const { modelId, modelName } = e.detail;
      this.setData({
        currentModelId: modelId,
        currentModelName: modelName
      });
      this.triggerEvent('modelchange', { modelId, modelName });
    },

    /**
     * 手势开始
     */
    onTouchStart(e) {
      this.data.touchStartY = e.touches[0].clientY;
    },

    /**
     * 手势移动
     */
    onTouchMove(e) {
      this.data.touchCurrentY = e.touches[0].clientY;
      const deltaY = this.data.touchCurrentY - this.data.touchStartY;
      
      if (deltaY > 50) {
        this.closeDrawer();
      }
    },

    /**
     * 信源点击
     */
    onSourceTap(e) {
      const { source } = e.detail;
      this.triggerEvent('sourcetap', { source });
    },

    /**
     * 清理资源
     */
    cleanup() {
      console.log('[DrawerCore] 组件已清理');
    }
  }
});
