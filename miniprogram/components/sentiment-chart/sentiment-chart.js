/**
 * 情感分布组件
 *
 * 展示 AI 回答中对品牌的情感倾向分布
 * 支持饼图和环形图两种展示方式
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
    // 情感分布数据，格式：{ data: { positive: number, neutral: number, negative: number }, total_count: number, warning: string }
    distributionData: {
      type: Object,
      value: {
        data: {
          positive: 0,
          neutral: 0,
          negative: 0
        },
        total_count: 0,
        warning: null
      },
      observer: '_onDataChange'
    },
    // 图表类型：pie（饼图）或 donut（环形图）
    chartType: {
      type: String,
      value: 'donut'
    },
    // 标题
    title: {
      type: String,
      value: '情感分布'
    },
    // 是否显示中心统计（仅环形图）
    showCenterStat: {
      type: Boolean,
      value: true
    },
    // 是否显示详细数据
    showDetails: {
      type: Boolean,
      value: true
    }
  },

  /**
   * 组件数据
   */
  data: {
    // 处理后的图表数据
    chartData: [],
    // 情感得分
    sentimentScore: 0,
    // 情感等级
    sentimentLevel: 'neutral',
    // 加载状态
    isLoading: false,
    // 错误信息
    errorMessage: '',
    // 是否有数据
    hasData: false,
    // 正面情感比例
    positiveRate: 0,
    // 负面情感比例
    negativeRate: 0,
    // 中性情感比例
    neutralRate: 0
  },

  /**
   * 情感配置
   */
  sentimentConfig: {
    positive: {
      label: '正面',
      color: '#28a745',
      icon: '😊',
      description: '积极评价'
    },
    neutral: {
      label: '中性',
      color: '#6c757d',
      icon: '😐',
      description: '中性评价'
    },
    negative: {
      label: '负面',
      color: '#dc3545',
      icon: '😟',
      description: '消极评价'
    }
  },

  /**
   * 生命周期方法
   */
  lifetimes: {
    attached() {
      console.log('[SentimentChart] Component attached');
      this._processData();
    },
    detached() {
      console.log('[SentimentChart] Component detached');
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
      console.log('[SentimentChart] Data changed:', newVal);
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

      const data = distributionData.data;
      const positive = parseFloat(data.positive) || 0;
      const neutral = parseFloat(data.neutral) || 0;
      const negative = parseFloat(data.negative) || 0;

      // 检查是否有有效数据
      if (positive === 0 && neutral === 0 && negative === 0) {
        this._setEmptyState(distributionData.warning || '暂无情感数据');
        return;
      }

      // 计算情感得分（正面 - 负面）
      const sentimentScore = positive - negative;

      // 确定情感等级
      let sentimentLevel = 'neutral';
      if (sentimentScore > 20) {
        sentimentLevel = 'positive';
      } else if (sentimentScore < -20) {
        sentimentLevel = 'negative';
      }

      // 构建图表数据
      const chartData = [
        {
          key: 'positive',
          name: '正面',
          value: positive,
          color: this.sentimentConfig.positive.color,
          icon: this.sentimentConfig.positive.icon
        },
        {
          key: 'neutral',
          name: '中性',
          value: neutral,
          color: this.sentimentConfig.neutral.color,
          icon: this.sentimentConfig.neutral.icon
        },
        {
          key: 'negative',
          name: '负面',
          value: negative,
          color: this.sentimentConfig.negative.color,
          icon: this.sentimentConfig.negative.icon
        }
      ];

      this.setData({
        chartData: chartData,
        sentimentScore: sentimentScore,
        sentimentLevel: sentimentLevel,
        positiveRate: positive,
        negativeRate: negative,
        neutralRate: neutral,
        hasData: true,
        errorMessage: ''
      });

      console.log('[SentimentChart] Data processed:', chartData);
    },

    /**
     * 设置空状态
     * @private
     * @param {string} message - 提示信息
     */
    _setEmptyState(message) {
      this.setData({
        chartData: [],
        sentimentScore: 0,
        sentimentLevel: 'neutral',
        hasData: false,
        errorMessage: message
      });
    },

    /**
     * 获取情感等级描述
     * @returns {string} 情感描述
     */
    getSentimentDescription() {
      const { sentimentLevel } = this.data;
      const descriptions = {
        positive: '整体评价积极，品牌口碑良好',
        neutral: '评价较为中性，品牌认知度有待提升',
        negative: '负面评价较多，需要关注品牌形象'
      };
      return descriptions[sentimentLevel] || descriptions.neutral;
    },

    /**
     * 获取情感等级颜色
     * @returns {string} 颜色值
     */
    getSentimentColor() {
      const { sentimentLevel } = this.data;
      const colors = {
        positive: '#28a745',
        neutral: '#6c757d',
        negative: '#dc3545'
      };
      return colors[sentimentLevel] || colors.neutral;
    },

    /**
     * 点击情感项
     * @param {Object} event - 事件对象
     */
    onSentimentTap(event) {
      const { index } = event.currentTarget.dataset;
      const sentiment = this.data.chartData[index];

      console.log('[SentimentChart] Sentiment tapped:', sentiment);

      this.triggerEvent('sentimentTap', {
        sentiment: sentiment.key,
        name: sentiment.name,
        value: sentiment.value,
        index: index
      });
    },

    /**
     * 切换图表类型
     * @param {Object} event - 事件对象
     */
    onToggleChartType(event) {
      const newType = this.properties.chartType === 'pie' ? 'donut' : 'pie';
      this.setData({ chartType: newType });
      this.triggerEvent('chartTypeChange', { type: newType });
    },

    /**
     * 刷新数据
     */
    refresh() {
      console.log('[SentimentChart] Refreshing data');
      this._processData();
    },

    /**
     * 获取积极评价率
     * @returns {number} 积极评价率
     */
    getPositiveRate() {
      const { positiveRate } = this.data;
      return positiveRate;
    },

    /**
     * 获取净推荐值（NPS 风格）
     * @returns {number} 净情感值
     */
    getNetSentimentScore() {
      const { sentimentScore } = this.data;
      return sentimentScore;
    }
  }
});
