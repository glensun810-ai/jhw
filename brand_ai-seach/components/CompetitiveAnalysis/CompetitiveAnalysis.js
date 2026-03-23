/**
 * 竞品分析组件
 * 展示竞品对比数据和雷达图
 * 
 * 版本：v2.0
 * 日期：2026-02-21
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  /**
   * 组件属性
   */
  properties: {
    // 竞品数据
    competitiveData: {
      type: Object,
      value: null
    },
    // 我方品牌数据
    myBrandData: {
      type: Object,
      value: null
    },
    // 是否显示
    visible: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件数据
   */
  data: {
    // 雷达图数据
    radarData: null,
    
    // 对比摘要
    comparisonSummary: null,
    
    // 竞品列表
    competitors: [],
    
    // 当前选中的竞品
    selectedCompetitor: null,
    
    // 维度映射
    dimensions: [
      { key: 'authority', label: '权威性', icon: '🏆' },
      { key: 'visibility', label: '可见性', icon: '👁️' },
      { key: 'purity', label: '纯净度', icon: '✨' },
      { key: 'consistency', label: '一致性', icon: '⚖️' },
      { key: 'overall', label: '综合', icon: '📊' }
    ],
    
    // 对比模式
    compareMode: 'radar',  // radar, table, card
  },

  /**
   * 数据监听器
   */
  observers: {
    competitiveData: function(newData) {
      if (newData) {
        this._processData(newData);
      }
    },
    myBrandData: function(newData) {
      if (newData) {
        this._processMyBrand(newData);
      }
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 处理竞品数据
     */
    _processData(data) {
      const competitors = data.competitors || [];
      const comparison = data.comparison_summary || {};
      const radar = data.radar_data || null;

      this.setData({
        competitors,
        comparisonSummary: comparison,
        radarData: radar
      });

      // 默认选中第一个竞品
      if (competitors.length > 0 && !this.data.selectedCompetitor) {
        this.setData({
          selectedCompetitor: competitors[0]
        });
      }
    },

    /**
     * 处理我方品牌数据
     */
    _processMyBrand(data) {
      const brandName = data.brand_name || '我方品牌';
      const scores = data.dimension_scores || {};
      
      // 更新雷达图数据
      const { radarData } = this.data;
      if (radarData && radarData.datasets) {
        // 确保我方品牌在第一个 dataset
        const myDataset = {
          label: brandName,
          data: [
            scores.authority || 75,
            scores.visibility || 75,
            scores.purity || 75,
            scores.consistency || 75,
            data.overall_score || 75
          ],
          borderColor: 'rgb(233, 69, 96)',
          backgroundColor: 'rgba(233, 69, 96, 0.2)',
          borderWidth: 3
        };

        radarData.datasets.unshift(myDataset);
        
        this.setData({ radarData });
      }
    },

    /**
     * 切换竞品
     */
    onSelectCompetitor(e) {
      const { competitor } = e.currentTarget.dataset;
      this.setData({ selectedCompetitor: competitor });
      
      this.triggerEvent('competitorSelect', { competitor });
    },

    /**
     * 切换对比模式
     */
    onModeChange(e) {
      const { mode } = e.currentTarget.dataset;
      this.setData({ compareMode: mode });
    },

    /**
     * 分享竞品分析
     */
    onShare() {
      this.triggerEvent('share', {
        type: 'competitive_analysis',
        data: this.data.competitiveData
      });
    },

    /**
     * 获取排名描述
     */
    _getRankDescription(rank, total) {
      if (rank === 1) {
        return '🥇 领先';
      } else if (rank === 2) {
        return '🥈 紧随其后';
      } else if (rank === 3) {
        return '🥉 中游';
      } else {
        return '📈 需努力';
      }
    },

    /**
     * 获取分数等级
     */
    _getScoreGrade(score) {
      if (score >= 90) return { grade: 'A+', color: '#10b981' };
      if (score >= 80) return { grade: 'A', color: '#10b981' };
      if (score >= 70) return { grade: 'B', color: '#3b82f6' };
      if (score >= 60) return { grade: 'C', color: '#f59e0b' };
      return { grade: 'D', color: '#ef4444' };
    }
  }
});
