/**
 * 品牌分布组件
 *
 * 展示品牌在 AI 平台回答中的露出占比
 * 支持饼图和柱状图两种展示方式
 *
 * @author 系统架构组
 * @date 2026-02-27
 * @version 1.0.0
 */

Component({
  /**
   * 组件属性
   */
  properties: {
    // 品牌分布数据，格式：{ data: { brandName: percentage }, total_count: number, warning: string }
    distributionData: {
      type: Object,
      value: {
        data: {},
        total_count: 0,
        warning: null
      },
      observer: '_onDataChange'
    },
    // 图表类型：pie（饼图）或 bar（柱状图）
    chartType: {
      type: String,
      value: 'pie'
    },
    // 标题
    title: {
      type: String,
      value: '品牌分布'
    },
    // 是否显示图例
    showLegend: {
      type: Boolean,
      value: true
    },
    // 是否显示数值标签
    showLabels: {
      type: Boolean,
      value: true
    },
    // 颜色方案
    colorScheme: {
      type: String,
      value: 'default' // default, vibrant, pastel
    }
  },

  /**
   * 组件数据
   */
  data: {
    // 处理后的图表数据
    chartData: [],
    // 加载状态
    isLoading: false,
    // 错误信息
    errorMessage: '',
    // 是否有数据
    hasData: false,
    // 图表配置
    chartConfig: {
      width: 300,
      height: 300,
      pieRadius: 100,
      barWidth: 30
    }
  },

  /**
   * 生命周期方法
   */
  lifetimes: {
    attached() {
      console.log('[BrandDistribution] Component attached');
      this._processData();
    },
    detached() {
      console.log('[BrandDistribution] Component detached');
    }
  },

  /**
   * 页面生命周期方法
   */
  pageLifetimes: {
    show() {
      console.log('[BrandDistribution] Page show');
    },
    hide() {
      console.log('[BrandDistribution] Page hide');
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 数据变化监听
     * @private
     */
    _onDataChange(newVal) {
      console.log('[BrandDistribution] Data changed:', newVal);
      this._processData();
    },

    /**
     * 处理输入数据
     * @private
     */
    _processData() {
      const { distributionData } = this.properties;

      if (!distributionData || !distributionData.data) {
        this._setEmptyState('暂无数据');
        return;
      }

      const dataEntries = Object.entries(distributionData.data);

      if (dataEntries.length === 0) {
        this._setEmptyState(distributionData.warning || '暂无品牌数据');
        return;
      }

      // 处理数据为图表格式
      const chartData = dataEntries
        .map(([name, value]) => ({
          name: name,
          value: parseFloat(value) || 0
        }))
        .sort((a, b) => b.value - a.value);

      // 为每个品牌分配颜色
      const colors = this._getColors(chartData.length);
      chartData.forEach((item, index) => {
        item.color = colors[index % colors.length];
      });

      this.setData({
        chartData: chartData,
        hasData: true,
        errorMessage: ''
      });

      console.log('[BrandDistribution] Data processed:', chartData);
    },

    /**
     * 设置空状态
     * @private
     * @param {string} message - 提示信息
     */
    _setEmptyState(message) {
      this.setData({
        chartData: [],
        hasData: false,
        errorMessage: message
      });
    },

    /**
     * 获取颜色方案
     * @private
     * @param {number} count - 需要的颜色数量
     * @returns {Array<string>} 颜色数组
     */
    _getColors(count) {
      const colorSchemes = {
        default: [
          '#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0',
          '#00BCD4', '#FFEB3B', '#795548', '#607D8B', '#3F51B5'
        ],
        vibrant: [
          '#FF5252', '#FF4081', '#E040FB', '#7C4DFF', '#536DFE',
          '#448AFF', '#40C4FF', '#18FFFF', '#64FFDA', '#69F0AE'
        ],
        pastel: [
          '#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF',
          '#E2F0CB', '#FFDAC1', '#E0BBE4', '#957DAD', '#D291BC'
        ]
      };

      const scheme = colorSchemes[this.properties.colorScheme] || colorSchemes.default;

      // 如果颜色不够，生成额外颜色
      if (scheme.length < count) {
        const additionalColors = this._generateAdditionalColors(count - scheme.length);
        return [...scheme, ...additionalColors];
      }

      return scheme.slice(0, count);
    },

    /**
     * 生成额外颜色
     * @private
     * @param {number} count - 需要生成的颜色数量
     * @returns {Array<string>} 颜色数组
     */
    _generateAdditionalColors(count) {
      const colors = [];
      for (let i = 0; i < count; i++) {
        const hue = (i * 137.508) % 360; // 黄金角度
        colors.push(`hsl(${hue}, 70%, 60%)`);
      }
      return colors;
    },

    /**
     * 切换图表类型
     * @param {Object} event - 事件对象
     */
    onToggleChartType(event) {
      const newType = this.properties.chartType === 'pie' ? 'bar' : 'pie';
      this.setData({ chartType: newType });
      this.triggerEvent('chartTypeChange', { type: newType });
    },

    /**
     * 点击品牌项
     * @param {Object} event - 事件对象
     */
    onBrandTap(event) {
      const { index } = event.currentTarget.dataset;
      const brand = this.data.chartData[index];

      console.log('[BrandDistribution] Brand tapped:', brand);

      this.triggerEvent('brandTap', {
        brand: brand.name,
        value: brand.value,
        index: index
      });
    },

    /**
     * 长按品牌项
     * @param {Object} event - 事件对象
     */
    onBrandLongPress(event) {
      const { index } = event.currentTarget.dataset;
      const brand = this.data.chartData[index];

      this.triggerEvent('brandLongPress', {
        brand: brand.name,
        value: brand.value,
        index: index
      });
    },

    /**
     * 刷新数据
     */
    refresh() {
      console.log('[BrandDistribution] Refreshing data');
      this._processData();
    },

    /**
     * 导出图片
     */
    exportImage() {
      console.log('[BrandDistribution] Export image requested');
      this.triggerEvent('exportImage', {
        chartType: this.properties.chartType,
        data: this.data.chartData
      });
    }
  }
});
