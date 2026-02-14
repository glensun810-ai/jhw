// components/BattlefieldMatrix/BattlefieldMatrix.js
Component({
  /**
   * 组件的属性列表
   */
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
      value: 'standard' // 'standard', 'model', 'question'
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

  /**
   * 组件的初始数据
   */
  data: {
    // 滚动位置
    horizontalScrollLeft: 0,
    verticalScrollTop: 0,
    // 视图数据
    viewMatrixData: null,
    // 动画状态
    isAnimating: false
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 组件属性变化监听
     */
    handleViewChange: function() {
      // 当视图或选择的品牌/问题改变时，重新计算矩阵数据
      if (this.properties.matrixData) {
        this.updateViewMatrixData();
      }
    },

    /**
     * 更新视图矩阵数据
     */
    updateViewMatrixData: function() {
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
        case 'standard':
        default:
          viewMatrixData = this.properties.matrixData;
          break;
      }

      // 触发淡入淡出动画
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
    transformToModelView: function(matrixData, selectedBrand) {
      if (!matrixData || !selectedBrand) {
        return { headers: [], rows: [] };
      }

      // 获取所有唯一的问题
      const uniqueQuestions = [...new Set(matrixData.rows.map(row => row[0]))];

      // 获取所有模型（从结果中提取）
      const allModels = new Set();
      matrixData.rows.forEach(row => {
        for (let i = 1; i < row.length; i++) {
          if (row[i] && row[i].models) {
            row[i].models.forEach(model => allModels.add(model.name));
          }
        }
      });
      const modelsArray = Array.from(allModels);

      // 构建模型视图矩阵
      const headers = ['问题'].concat(modelsArray);
      const rows = [];

      uniqueQuestions.forEach(question => {
        const row = [question]; // 第一列是问题

        modelsArray.forEach(model => {
          // 查找特定品牌、问题和模型的分数
          const brandColIndex = matrixData.headers.indexOf(selectedBrand);
          if (brandColIndex > 0) {
            const questionRowIndex = matrixData.rows.findIndex(r => r[0] === question);
            if (questionRowIndex >= 0) {
              const cellData = matrixData.rows[questionRowIndex][brandColIndex];
              if (cellData && cellData.models) {
                const modelData = cellData.models.find(m => m.name === model);
                if (modelData) {
                  row.push({
                    score: modelData.score,
                    answer: modelData.answer,
                    model: model,
                    question: question
                  });
                } else {
                  row.push({
                    score: null,
                    answer: '无数据',
                    model: model,
                    question: question
                  });
                }
              } else {
                row.push({
                  score: null,
                  answer: '无数据',
                  model: model,
                  question: question
                });
              }
            } else {
              row.push({
                score: null,
                answer: '无数据',
                model: model,
                question: question
              });
            }
          } else {
            row.push({
              score: null,
              answer: '无数据',
              model: model,
              question: question
            });
          }
        });

        rows.push(row);
      });

      return {
        headers: headers,
        rows: rows
      };
    },

    /**
     * 转换为问题视图
     */
    transformToQuestionView: function(matrixData, selectedQuestion) {
      if (!matrixData || !selectedQuestion) {
        return { headers: [], rows: [] };
      }

      // 获取所有品牌
      const brands = matrixData.headers.slice(1);

      // 获取所有模型（从结果中提取）
      const allModels = new Set();
      matrixData.rows.forEach(row => {
        if (row[0] === selectedQuestion) {
          for (let i = 1; i < row.length; i++) {
            if (row[i] && row[i].models) {
              row[i].models.forEach(model => allModels.add(model.name));
            }
          }
        }
      });
      const modelsArray = Array.from(allModels);

      // 构建问题视图矩阵
      const headers = ['品牌'].concat(modelsArray);
      const rows = [];

      brands.forEach(brand => {
        const row = [brand]; // 第一列是品牌

        modelsArray.forEach(model => {
          // 查找特定品牌、问题和模型的分数
          const brandColIndex = matrixData.headers.indexOf(brand);
          const questionRowIndex = matrixData.rows.findIndex(r => r[0] === selectedQuestion);

          if (questionRowIndex >= 0 && brandColIndex > 0) {
            const cellData = matrixData.rows[questionRowIndex][brandColIndex];
            if (cellData && cellData.models) {
              const modelData = cellData.models.find(m => m.name === model);
              if (modelData) {
                row.push({
                  score: modelData.score,
                  answer: modelData.answer,
                  model: model,
                  brand: brand
                });
              } else {
                row.push({
                  score: null,
                  answer: '无数据',
                  model: model,
                  brand: brand
                });
              }
            } else {
              row.push({
                score: null,
                answer: '无数据',
                model: model,
                brand: brand
              });
            }
          } else {
            row.push({
              score: null,
              answer: '无数据',
              model: model,
              brand: brand
            });
          }
        });

        rows.push(row);
      });

      return {
        headers: headers,
        rows: rows
      };
    },

    /**
     * 水平滚动处理
     */
    onHorizontalScroll: function(e) {
      this.setData({
        horizontalScrollLeft: e.detail.scrollLeft
      });
    },

    /**
     * 垂直滚动处理
     */
    onVerticalScroll: function(e) {
      this.setData({
        verticalScrollTop: e.detail.scrollTop
      });
    },

    /**
     * 获取分数背景颜色
     */
    getScoreBgColor: function(score) {
      if (score === null) {
        // 无数据时使用灰色带斜纹
        return 'linear-gradient(135deg, transparent 25%, rgba(142, 142, 147, 0.2) 25%, rgba(142, 142, 147, 0.2) 50%, transparent 50%, transparent 75%, rgba(142, 142, 147, 0.2) 75%)';
      } else if (score >= 80) {
        // 80-100分使用绿色
        return 'linear-gradient(135deg, rgba(0, 200, 83, 0.2) 0%, rgba(0, 200, 83, 0.3) 100%)'; // #00C853 with gradient
      } else if (score >= 60) {
        // 60-79分使用黄色
        return 'linear-gradient(135deg, rgba(255, 214, 0, 0.2) 0%, rgba(255, 214, 0, 0.3) 100%)'; // #FFD600 with gradient
      } else {
        // <60分使用红色
        return 'linear-gradient(135deg, rgba(255, 23, 68, 0.2) 0%, rgba(255, 23, 68, 0.3) 100%)'; // #FF1744 with gradient
      }
    },

    /**
     * 显示详情弹窗
     */
    showDetailPopup: function(e) {
      const { brand, question, answer, score, model } = e.currentTarget.dataset;

      // 触发父组件事件
      this.triggerEvent('showDetail', {
        brand: brand,
        question: question,
        answer: answer,
        score: score,
        model: model
      });
    },

    /**
     * 显示情报抽屉
     */
    showIntelligenceDrawer: function(e) {
      const { brand, question, answer, score, model } = e.currentTarget.dataset;

      // 触发父组件事件
      this.triggerEvent('showIntelligence', {
        brand: brand,
        question: question,
        answer: answer,
        score: score,
        model: model
      });
    }
  },

  lifetimes: {
    attached() {
      // 组件实例进入页面节点树时执行
    },
    ready() {
      // 组件准备好后初始化视图数据
      if (this.properties.matrixData) {
        this.updateViewMatrixData();
      }
    },
    detached() {
      // 组件实例被从页面节点树移除时执行
    }
  },

  observers: {
    'matrixData, currentView, selectedBrand, selectedQuestion': function(matrixData, currentView, selectedBrand, selectedQuestion) {
      if (matrixData) {
        this.updateViewMatrixData();
      }
    }
  }
})