/**
 * 质量指示器组件
 * 
 * P2-4 优化：可复用组件 - 显示报告质量评分和等级
 * 
 * 使用示例:
 * <quality-indicator 
 *   quality-score="{{85}}" 
 *   quality-level="{{qualityLevel}}"
 *   onQualityClick="handleQualityClick"
 * />
 * 
 * @author 系统架构组
 * @date 2026-03-08
 * @version 1.0.0
 */

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    // 质量评分 (0-100)
    qualityScore: {
      type: Number,
      value: 0,
      observer: '_onQualityScoreChange'
    },
    
    // 质量等级信息
    qualityLevel: {
      type: Object,
      value: null,
      observer: '_onQualityLevelChange'
    },
    
    // 是否显示详细信息
    showDetail: {
      type: Boolean,
      value: false
    },
    
    // 是否可点击
    clickable: {
      type: Boolean,
      value: true
    },
    
    // 自定义样式类名
    customClass: {
      type: String,
      value: ''
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // 质量等级映射
    levelConfig: {
      excellent: {
        label: '优秀',
        color: '#28a745',
        bgColor: '#e8f5e9',
        icon: 'star'
      },
      good: {
        label: '良好',
        color: '#17a2b8',
        bgColor: '#e0f2f1',
        icon: 'thumb-up'
      },
      fair: {
        label: '一般',
        color: '#ffc107',
        bgColor: '#fff3e0',
        icon: 'info'
      },
      poor: {
        label: '较差',
        color: '#fd7e14',
        bgColor: '#fbe9e7',
        icon: 'warning'
      },
      critical: {
        label: '严重',
        color: '#dc3545',
        bgColor: '#ffebee',
        icon: 'error'
      }
    },
    
    // 当前等级配置
    currentLevel: null,
    
    // 是否显示提示
    showTip: false
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 质量评分变化监听
     */
    _onQualityScoreChange(newScore) {
      this._updateLevelConfig(newScore);
    },

    /**
     * 质量等级变化监听
     */
    _onQualityLevelChange(newLevel) {
      if (newLevel) {
        this.setData({ currentLevel: newLevel });
      }
    },

    /**
     * 根据评分更新等级配置
     */
    _updateLevelConfig(score) {
      let level = 'critical';
      
      if (score >= 80) {
        level = 'excellent';
      } else if (score >= 60) {
        level = 'good';
      } else if (score >= 40) {
        level = 'fair';
      } else if (score >= 20) {
        level = 'poor';
      }
      
      const levelConfig = this.data.levelConfig[level];
      
      this.setData({
        currentLevel: {
          ...levelConfig,
          level: level,
          score: score
        }
      });
    },

    /**
     * 点击处理
     */
    handleClick() {
      if (!this.properties.clickable) {
        return;
      }

      this.setData({ showTip: !this.data.showTip });

      // 触发点击事件
      this.triggerEvent('qualityClick', {
        score: this.properties.qualityScore,
        level: this.data.currentLevel
      });
    },

    /**
     * 关闭提示
     */
    closeTip() {
      this.setData({ showTip: false });
    },

    /**
     * 查看详情
     */
    viewDetail() {
      this.triggerEvent('viewDetail', {
        score: this.properties.qualityScore,
        level: this.data.currentLevel
      });
    }
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this._updateLevelConfig(this.properties.qualityScore);
    }
  }
});
