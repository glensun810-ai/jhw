/**
 * 导出格式选择器组件
 * 
 * 职责：
 * - 格式选择 (PDF/HTML/Excel)
 * - 报告级别选择
 * - 章节选择
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    // 当前格式
    format: {
      type: String,
      value: 'pdf'
    },
    // 当前级别
    level: {
      type: String,
      value: 'full'
    },
    // 选中章节
    selectedSections: {
      type: Object,
      value: {}
    },
    // 格式选项
    formatOptions: {
      type: Array,
      value: [
        { value: 'pdf', label: 'PDF', icon: '📄' },
        { value: 'html', label: 'HTML', icon: '🌐' },
        { value: 'excel', label: 'Excel', icon: '📊' }
      ]
    },
    // 级别选项
    levelOptions: {
      type: Array,
      value: [
        { value: 'basic', label: '基础版', desc: '执行摘要 + 健康度', icon: '📄' },
        { value: 'detailed', label: '详细版', desc: '基础版 + 平台 + 竞品', icon: '📊' },
        { value: 'full', label: '完整版', desc: '全部内容 + 行动计划', icon: '📑' }
      ]
    },
    // 章节选项
    sectionOptions: {
      type: Array,
      value: [
        { key: 'executiveSummary', label: '执行摘要', icon: '📊', required: true },
        { key: 'brandHealth', label: '品牌健康度', icon: '💚', required: true },
        { key: 'platformAnalysis', label: '平台表现', icon: '🤖', required: false },
        { key: 'competitiveAnalysis', label: '竞品对比', icon: '⚔️', required: false },
        { key: 'negativeSources', label: '负面信源', icon: '⚠️', required: false },
        { key: 'roiAnalysis', label: 'ROI 指标', icon: '💰', required: false },
        { key: 'actionPlan', label: '行动计划', icon: '📋', required: false }
      ]
    }
  },

  data: {
    // 本地状态
    expandedSection: false
  },

  lifetimes: {
    attached() {
      console.log('[ExportFormatSelector] 组件已挂载');
    }
  },

  methods: {
    /**
     * 选择格式
     */
    onSelectFormat(e) {
      const { format } = e.currentTarget.dataset;
      this.setData({ format });
      this.triggerEvent('formatchange', { format });
    },

    /**
     * 选择级别
     */
    onSelectLevel(e) {
      const { level } = e.currentTarget.dataset;
      this.setData({ level });
      this.triggerEvent('levelchange', { level });
    },

    /**
     * 切换章节选择
     */
    toggleSection(e) {
      const { key } = e.currentTarget.dataset;
      const selectedSections = { ...this.data.selectedSections };
      selectedSections[key] = !selectedSections[key];
      
      this.setData({ selectedSections });
      this.triggerEvent('sectionchange', { selectedSections });
    },

    /**
     * 全选章节
     */
    selectAllSections() {
      const selectedSections = {};
      this.data.sectionOptions.forEach(opt => {
        selectedSections[opt.key] = true;
      });
      
      this.setData({ selectedSections });
      this.triggerEvent('sectionchange', { selectedSections });
    },

    /**
     * 重置章节
     */
    resetSections() {
      const selectedSections = {};
      this.data.sectionOptions.forEach(opt => {
        selectedSections[opt.key] = opt.required;
      });
      
      this.setData({ selectedSections });
      this.triggerEvent('sectionchange', { selectedSections });
    },

    /**
     * 切换章节展开
     */
    toggleSectionExpand() {
      this.setData({
        expandedSection: !this.data.expandedSection
      });
    }
  }
});
