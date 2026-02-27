/**
 * 关键词云组件
 *
 * 展示从 AI 回答中提取的高频关键词
 * 支持词云展示和列表展示两种模式
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
    // 关键词数据，格式：[{ word: string, count: number, sentiment: number, sentiment_label: string }]
    keywordsData: {
      type: Array,
      value: [],
      observer: '_onDataChange'
    },
    // 展示模式：cloud（词云）或 list（列表）
    displayMode: {
      type: String,
      value: 'cloud'
    },
    // 标题
    title: {
      type: String,
      value: '关键词云'
    },
    // 最大显示关键词数量
    maxKeywords: {
      type: Number,
      value: 50
    },
    // 最小词频过滤
    minCount: {
      type: Number,
      value: 1
    },
    // 是否显示情感颜色
    showSentimentColor: {
      type: Boolean,
      value: true
    },
    // 是否显示词频
    showCount: {
      type: Boolean,
      value: true
    }
  },

  /**
   * 组件数据
   */
  data: {
    // 处理后的关键词数据
    processedKeywords: [],
    // 加载状态
    isLoading: false,
    // 错误信息
    errorMessage: '',
    // 是否有数据
    hasData: false,
    // 词云布局数据
    cloudLayout: [],
    // 当前选中的关键词
    selectedKeyword: null,
    // 关键词统计
    stats: {
      totalKeywords: 0,
      positiveCount: 0,
      neutralCount: 0,
      negativeCount: 0,
      avgSentiment: 0
    }
  },

  /**
   * 情感颜色配置
   */
  sentimentColors: {
    positive: '#28a745',
    neutral: '#6c757d',
    negative: '#dc3545'
  },

  /**
   * 生命周期方法
   */
  lifetimes: {
    attached() {
      console.log('[KeywordCloud] Component attached');
      this._processData();
    },
    detached() {
      console.log('[KeywordCloud] Component detached');
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
      console.log('[KeywordCloud] Data changed, count:', newVal?.length);
      this._processData();
    },

    /**
     * 处理输入数据
     * @private
     */
    _processData() {
      const { keywordsData, maxKeywords, minCount } = this.properties;

      if (!keywordsData || keywordsData.length === 0) {
        this._setEmptyState('暂无关键词数据');
        return;
      }

      // 过滤和排序关键词
      const filtered = keywordsData
        .filter(kw => (kw.count || 0) >= minCount)
        .sort((a, b) => (b.count || 0) - (a.count || 0))
        .slice(0, maxKeywords);

      if (filtered.length === 0) {
        this._setEmptyState('没有符合过滤条件的关键词');
        return;
      }

      // 计算统计数据
      const stats = this._calculateStats(filtered);

      // 处理词云布局
      const cloudLayout = this._calculateCloudLayout(filtered);

      this.setData({
        processedKeywords: filtered,
        cloudLayout: cloudLayout,
        stats: stats,
        hasData: true,
        errorMessage: ''
      });

      console.log('[KeywordCloud] Data processed, keywords:', filtered.length);
    },

    /**
     * 计算统计数据
     * @private
     * @param {Array} keywords - 关键词列表
     * @returns {Object} 统计数据
     */
    _calculateStats(keywords) {
      const totalKeywords = keywords.length;
      let positiveCount = 0;
      let neutralCount = 0;
      let negativeCount = 0;
      let totalSentiment = 0;

      keywords.forEach(kw => {
        const sentiment = kw.sentiment || 0;
        totalSentiment += sentiment;

        if (sentiment > 0.3) {
          positiveCount++;
        } else if (sentiment < -0.3) {
          negativeCount++;
        } else {
          neutralCount++;
        }
      });

      return {
        totalKeywords: totalKeywords,
        positiveCount: positiveCount,
        neutralCount: neutralCount,
        negativeCount: negativeCount,
        avgSentiment: totalKeywords > 0 ? (totalSentiment / totalKeywords).toFixed(3) : 0
      };
    },

    /**
     * 计算词云布局
     * @private
     * @param {Array} keywords - 关键词列表
     * @returns {Array} 布局数据
     */
    _calculateCloudLayout(keywords) {
      if (!keywords || keywords.length === 0) {
        return [];
      }

      // 计算最大最小词频用于归一化
      const counts = keywords.map(kw => kw.count || 0);
      const maxCount = Math.max(...counts, 1);
      const minCount = Math.min(...counts, 1);

      // 词云配置
      const minFontSize = 24; // 最小字体大小（rpx）
      const maxFontSize = 64; // 最大字体大小（rpx）

      // 简单的螺旋布局算法
      const layout = [];
      const centerX = 150; // 画布中心 X
      const centerY = 150; // 画布中心 Y
      let angle = 0;
      let radius = 0;
      const angleStep = 0.5; // 角度增量
      const radiusStep = 3;  // 半径增量

      keywords.forEach((kw, index) => {
        // 计算字体大小
        const normalized = maxCount === minCount ? 0.5 : (kw.count - minCount) / (maxCount - minCount);
        const fontSize = Math.round(minFontSize + normalized * (maxFontSize - minFontSize));

        // 估算词宽度（简化）
        const wordWidth = kw.word.length * fontSize * 0.6;
        const wordHeight = fontSize * 1.2;

        // 计算位置（螺旋）
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);

        // 获取颜色
        const color = this._getKeywordColor(kw);

        layout.push({
          word: kw.word,
          x: x - wordWidth / 2,
          y: y - wordHeight / 2,
          fontSize: fontSize,
          color: color,
          count: kw.count,
          sentiment: kw.sentiment,
          rotation: 0 // 可以添加旋转效果
        });

        // 更新螺旋参数
        angle += angleStep;
        radius += radiusStep;
      });

      return layout;
    },

    /**
     * 获取关键词颜色
     * @private
     * @param {Object} keyword - 关键词数据
     * @returns {string} 颜色值
     */
    _getKeywordColor(keyword) {
      if (!this.properties.showSentimentColor) {
        return '#333333';
      }

      const sentiment = keyword.sentiment || 0;
      if (sentiment > 0.3) {
        return this.sentimentColors.positive;
      } else if (sentiment < -0.3) {
        return this.sentimentColors.negative;
      } else {
        return this.sentimentColors.neutral;
      }
    },

    /**
     * 设置空状态
     * @private
     * @param {string} message - 提示信息
     */
    _setEmptyState(message) {
      this.setData({
        processedKeywords: [],
        cloudLayout: [],
        stats: {
          totalKeywords: 0,
          positiveCount: 0,
          neutralCount: 0,
          negativeCount: 0,
          avgSentiment: 0
        },
        hasData: false,
        errorMessage: message
      });
    },

    /**
     * 获取情感标签
     * @param {number} sentiment - 情感得分
     * @returns {string} 情感标签
     */
    getSentimentLabel(sentiment) {
      if (sentiment > 0.3) {
        return '正面';
      } else if (sentiment < -0.3) {
        return '负面';
      } else {
        return '中性';
      }
    },

    /**
     * 获取情感颜色类
     * @param {number} sentiment - 情感得分
     * @returns {string} 颜色类名
     */
    getSentimentClass(sentiment) {
      if (sentiment > 0.3) {
        return 'positive';
      } else if (sentiment < -0.3) {
        return 'negative';
      } else {
        return 'neutral';
      }
    },

    /**
     * 点击关键词
     * @param {Object} event - 事件对象
     */
    onKeywordTap(event) {
      const { index } = event.currentTarget.dataset;
      const keyword = this.data.processedKeywords[index];

      console.log('[KeywordCloud] Keyword tapped:', keyword);

      this.setData({ selectedKeyword: keyword });

      this.triggerEvent('keywordTap', {
        keyword: keyword.word,
        count: keyword.count,
        sentiment: keyword.sentiment,
        index: index
      });
    },

    /**
     * 长按关键词
     * @param {Object} event - 事件对象
     */
    onKeywordLongPress(event) {
      const { index } = event.currentTarget.dataset;
      const keyword = this.data.processedKeywords[index];

      this.triggerEvent('keywordLongPress', {
        keyword: keyword.word,
        count: keyword.count,
        sentiment: keyword.sentiment,
        index: index
      });
    },

    /**
     * 切换展示模式
     * @param {Object} event - 事件对象
     */
    onToggleDisplayMode(event) {
      const newMode = this.properties.displayMode === 'cloud' ? 'list' : 'cloud';
      this.setData({ displayMode: newMode });
      this.triggerEvent('displayModeChange', { mode: newMode });
    },

    /**
     * 刷新数据
     */
    refresh() {
      console.log('[KeywordCloud] Refreshing data');
      this._processData();
    },

    /**
     * 导出词云图片
     */
    exportImage() {
      console.log('[KeywordCloud] Export image requested');
      this.triggerEvent('exportImage', {
        keywords: this.data.processedKeywords,
        stats: this.data.stats
      });
    },

    /**
     * 关闭选中状态
     */
    closeSelected() {
      this.setData({ selectedKeyword: null });
    }
  }
});
