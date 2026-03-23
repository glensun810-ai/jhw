/**
 * 战地矩阵主组件 - 重构简化版
 * 
 * 重构说明:
 * - 单元格渲染 → MatrixCell/index.js
 * - 图例显示 → MatrixLegend/index.js
 * 
 * 本文件保留:
 * - 组件协调
 * - 视图转换
 * - 事件转发
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    matrixData: {
      type: Object,
      value: null
    },
    loading: {
      type: Boolean,
      value: false
    },
    currentView: {
      type: String,
      value: 'standard'
    },
    selectedBrand: {
      type: String,
      value: ''
    },
    selectedQuestion: {
      type: String,
      value: ''
    }
  },

  data: {
    horizontalScrollLeft: 0,
    verticalScrollTop: 0,
    viewMatrixData: null,
    isAnimating: false
  },

  lifetimes: {
    attached() {
      console.log('[BattlefieldMatrix] 组件已挂载');
      this.updateViewMatrixData();
    }
  },

  methods: {
    /**
     * 属性变化监听
     */
    onPropertiesChange() {
      if (this.properties.matrixData) {
        this.updateViewMatrixData();
      }
    },

    /**
     * 更新视图矩阵数据
     */
    updateViewMatrixData() {
      let viewMatrixData = null;

      switch(this.properties.currentView) {
        case 'model':
          viewMatrixData = this.transformToModelView(
            this.properties.matrixData,
            this.properties.selectedBrand
          );
          break;
        case 'question':
          viewMatrixData = this.transformToQuestionView(
            this.properties.matrixData,
            this.properties.selectedQuestion
          );
          break;
        default:
          viewMatrixData = this.properties.matrixData;
          break;
      }

      // 触发动画
      this.setData({ isAnimating: true });

      setTimeout(() => {
        this.setData({
          viewMatrixData: viewMatrixData,
          isAnimating: false
        });
      }, 150);
    },

    /**
     * 转换为模型视图
     */
    transformToModelView(matrixData, selectedBrand) {
      if (!matrixData || !selectedBrand) {
        return { headers: [], rows: [] };
      }

      // 获取所有唯一模型
      const models = [...new Set(
        matrixData.rows?.flatMap(row => 
          row.cells?.filter(c => c.brand === selectedBrand).map(c => c.model) || []
        ) || []
      )];

      // 转换为模型视图数据
      return {
        headers: models.map(m => ({ label: m })),
        rows: matrixData.rows?.map(row => ({
          label: row.label,
          cells: models.map(model => 
            row.cells?.find(c => c.brand === selectedBrand && c.model === model) || { status: 'neutral' }
          )
        })) || []
      };
    },

    /**
     * 转换为问题视图
     */
    transformToQuestionView(matrixData, selectedQuestion) {
      if (!matrixData || !selectedQuestion) {
        return { headers: [], rows: [] };
      }

      // 过滤出问题相关数据
      const filteredRows = matrixData.rows?.filter(row => 
        row.label?.includes(selectedQuestion)
      ) || [];

      return {
        headers: matrixData.headers,
        rows: filteredRows
      };
    },

    /**
     * 视图切换
     */
    onViewChange(e) {
      const { view } = e.detail;
      this.setData({ currentView: view });
      this.triggerEvent('viewchange', { view });
    },

    /**
     * 单元格点击
     */
    onCellTap(e) {
      const { rowIndex, colIndex, cellData } = e.detail;
      this.triggerEvent('celltap', { rowIndex, colIndex, cellData });
    },

    /**
     * 滚动控制
     */
    onScrollLeft(e) {
      this.setData({ horizontalScrollLeft: e.detail.scrollLeft });
    },

    onScrollTop(e) {
      this.setData({ verticalScrollTop: e.detail.scrollTop });
    }
  },

  observers: {
    'matrixData,currentView,selectedBrand,selectedQuestion': function() {
      this.updateViewMatrixData();
    }
  }
});
