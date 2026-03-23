// components/WorkflowFindings/WorkflowFindings.js
/**
 * P0 级空缺修复：工作流发现列表组件
 *
 * 属性:
 * - title: 组件标题
 * - subtitle: 副标题
 * - workflowStages: 工作流阶段数据
 * - summary: 汇总统计
 * - expandAll: 是否全部展开
 * - expandedStage: 当前展开的阶段
 * 
 * P1 修复：
 * - 添加数据兜底，确保所有嵌套属性都有默认值
 * - 预处理 metrics 分数，避免 WXML 中复杂表达式
 */
Component({
  properties: {
    title: {
      type: String,
      value: '工作流分析发现'
    },
    subtitle: {
      type: String,
      value: ''
    },
    workflowStages: {
      type: Object,
      value: {
        intelligence_evaluating: { status: 'pending', findings: [], metrics: {} },
        intelligence_analyzing: { status: 'pending', findings: [], key_discoveries: [] },
        competition_analyzing: { status: 'pending', findings: [], market_position: {} },
        source_tracing: { status: 'pending', findings: [], credibility_analysis: {} }
      },
      observer: 'onWorkflowStagesChange'
    },
    summary: {
      type: Object,
      value: null
    },
    expandAll: {
      type: Boolean,
      value: false
    },
    expandedStage: {
      type: String,
      value: '' // 'evaluating', 'analyzing', 'competition', 'source'
    }
  },

  data: {
    // 预处理后的数据，用于 WXML 绑定
    safeStages: {
      intelligence_evaluating: {
        status: 'pending',
        findings: [],
        metrics: {
          authority_score: 0,
          completeness_score: 0,
          timeliness_score: 0
        }
      },
      intelligence_analyzing: {
        status: 'pending',
        findings: [],
        key_discoveries: []
      },
      competition_analyzing: {
        status: 'pending',
        findings: [],
        market_position: {
          market_leader: '',
          challenger: ''
        }
      },
      source_tracing: {
        status: 'pending',
        findings: [],
        credibility_analysis: {
          high_credibility: 0,
          medium_credibility: 0,
          low_credibility: 0
        }
      }
    }
  },

  methods: {
    /**
     * P1 修复：workflowStages 变化时的处理
     * 确保所有嵌套属性都有默认值
     */
    onWorkflowStagesChange(newVal) {
      if (!newVal) {
        return;
      }

      const safeStages = {
        // 评估阶段
        intelligence_evaluating: {
          status: (newVal.intelligence_evaluating && newVal.intelligence_evaluating.status) || 'pending',
          findings: (newVal.intelligence_evaluating && newVal.intelligence_evaluating.findings) || [],
          metrics: {
            authority_score: this._safeGetNumber(newVal, 'intelligence_evaluating.metrics.authority_score', 0),
            completeness_score: this._safeGetNumber(newVal, 'intelligence_evaluating.metrics.completeness_score', 0),
            timeliness_score: this._safeGetNumber(newVal, 'intelligence_evaluating.metrics.timeliness_score', 0)
          }
        },
        // 分析阶段
        intelligence_analyzing: {
          status: (newVal.intelligence_analyzing && newVal.intelligence_analyzing.status) || 'pending',
          findings: (newVal.intelligence_analyzing && newVal.intelligence_analyzing.findings) || [],
          key_discoveries: (newVal.intelligence_analyzing && newVal.intelligence_analyzing.key_discoveries) || []
        },
        // 竞争分析阶段
        competition_analyzing: {
          status: (newVal.competition_analyzing && newVal.competition_analyzing.status) || 'pending',
          findings: (newVal.competition_analyzing && newVal.competition_analyzing.findings) || [],
          market_position: {
            market_leader: (newVal.competition_analyzing && newVal.competition_analyzing.market_position && newVal.competition_analyzing.market_position.market_leader) || '',
            challenger: (newVal.competition_analyzing && newVal.competition_analyzing.market_position && newVal.competition_analyzing.market_position.challenger) || ''
          }
        },
        // 信源追溯阶段
        source_tracing: {
          status: (newVal.source_tracing && newVal.source_tracing.status) || 'pending',
          findings: (newVal.source_tracing && newVal.source_tracing.findings) || [],
          credibility_analysis: {
            high_credibility: this._safeGetNumber(newVal, 'source_tracing.credibility_analysis.high_credibility', 0),
            medium_credibility: this._safeGetNumber(newVal, 'source_tracing.credibility_analysis.medium_credibility', 0),
            low_credibility: this._safeGetNumber(newVal, 'source_tracing.credibility_analysis.low_credibility', 0)
          }
        }
      };

      this.setData({ safeStages });
    },

    /**
     * P1 修复：安全获取数字值
     * @param {Object} obj - 源对象
     * @param {String} path - 属性路径（如 'intelligence_evaluating.metrics.authority_score'）
     * @param {Number} defaultValue - 默认值
     * @returns {Number} 安全的数字值
     */
    _safeGetNumber(obj, path, defaultValue = 0) {
      try {
        const keys = path.split('.');
        let value = obj;
        
        for (const key of keys) {
          if (value === null || value === undefined) {
            return defaultValue;
          }
          value = value[key];
        }
        
        // 确保返回的是数字
        const numValue = Number(value);
        return isNaN(numValue) ? defaultValue : numValue;
      } catch (error) {
        return defaultValue;
      }
    },

    /**
     * 获取分数样式类
     */
    getScoreClass(score) {
      const numScore = Number(score) || 0;
      if (numScore >= 80) return 'workflow-findings__metric-value--high';
      if (numScore >= 60) return 'workflow-findings__metric-value--medium';
      return 'workflow-findings__metric-value--low';
    },

    /**
     * 切换阶段展开状态
     */
    toggleStage(stage) {
      const currentExpanded = this.data.expandedStage;
      this.triggerEvent('stagetoggle', {
        stage: currentExpanded === stage ? '' : stage
      });
    }
  },

  lifetimes: {
    attached() {
      console.log('[WorkflowFindings] attached');
      // 初始化时处理数据
      if (this.data.workflowStages) {
        this.onWorkflowStagesChange(this.data.workflowStages);
      }
    },
    detached() {
      console.log('[WorkflowFindings] detached');
    }
  }
});
