/**
 * 综合评分仪表盘组件
 * 
 * 属性:
 * - score: 综合评分 (0-100)
 * - grade: 等级文字 (如"优秀")
 * - showDetails: 是否显示详情
 * - sovShare: 声量份额
 * - sentimentScore: 情感得分
 * - physicalRank: 物理排名
 * - influenceScore: 影响力评分
 */

Component({
  properties: {
    score: {
      type: Number,
      value: 0,
      observer: 'onScoreChange'
    },
    grade: {
      type: String,
      value: '待评估'
    },
    showDetails: {
      type: Boolean,
      value: false
    },
    sovShare: {
      type: Number,
      value: 0
    },
    sentimentScore: {
      type: Number,
      value: 0
    },
    physicalRank: {
      type: Number,
      value: 0
    },
    influenceScore: {
      type: Number,
      value: 0
    }
  },

  data: {
    bgRotate: -90,
    pointerRotate: -90,
    gradeClass: 'grade-pending'
  },

  lifetimes: {
    attached: function() {
      this.updateGauge(this.data.score);
    }
  },

  methods: {
    /**
     * 分数变化时更新仪表盘
     */
    onScoreChange: function(newScore) {
      this.updateGauge(newScore);
    },

    /**
     * 更新仪表盘状态
     */
    updateGauge: function(score) {
      // 限制分数范围
      score = Math.max(0, Math.min(100, score));
      
      // 计算指针旋转角度 (-90 到 90 度)
      const pointerRotate = -90 + (score / 100) * 180;
      
      // 确定等级样式
      let gradeClass = 'grade-pending';
      if (score >= 80) {
        gradeClass = 'grade-excellent';
      } else if (score >= 60) {
        gradeClass = 'grade-good';
      } else if (score >= 40) {
        gradeClass = 'grade-fair';
      } else {
        gradeClass = 'grade-poor';
      }
      
      this.setData({
        pointerRotate,
        gradeClass
      });
    }
  }
});
