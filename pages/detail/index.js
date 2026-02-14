// pages/detail/index.js
const { getMatrixData, getColorByScore } = require('./utils/matrixHelper');
const { getTaskStatusApi } = require('../../api/home');
const { parseTaskStatus } = require('../../services/DiagnosisService');

Page({
  data: {
    matrixData: null,
    isLoading: true,
    currentView: 'panorama', // 'panorama', 'model'
    selectedBrandIndex: 0,
    selectedQuestionIndex: 0,
    brandNames: [],
    questionList: [],
    modelList: [], // AI 模型列表
    showIntelligenceDrawer: false,
    intelligenceData: null,
    gridData: null, // 用于矩阵显示的数据
    isGridLoading: false,
    customQuestion: '品牌GEO战略对阵中心',
    // 视图切换选项
    viewOptions: [
      { id: 'standard', label: '全景透视' },
      { id: 'model', label: '模型对比' },
      { id: 'question', label: '问题诊断' }
    ],
    // 时间预估相关
    estimatedTime: 0,
    currentTime: 0,
    progress: 0,
    progressText: '正在启动AI认知诊断...',
    isCountdownActive: false,
    showSurpriseMessage: false,
    surpriseMessage: ''
  },

  onLoad: function(options) {
    // 检查是否传入了 executionId，如果有则启动轮询
    if (options.executionId) {
      // 从URL参数解析数据
      this.executionId = decodeURIComponent(options.executionId);
      this.brandList = JSON.parse(decodeURIComponent(options.brand_list || '[]'));
      this.modelNames = JSON.parse(decodeURIComponent(options.models || '[]'));
      this.customQuestion = decodeURIComponent(options.question || '');

      // 计算预估时间：基础8秒 + (品牌数 * 模型数 * 1.5秒) * 1.3倍安全系数
      const estimatedTime = Math.ceil((8 + (this.brandList.length * this.modelNames.length * 1.5)) * 1.3);

      // 更新标题显示当前诊断问题
      this.setData({
        isLoading: true,
        showSkeleton: true,
        customQuestion: this.customQuestion,
        estimatedTime: estimatedTime,
        currentTime: estimatedTime,
        progress: 0,
        progressText: `📊 深度研判启动：预计耗时 ${estimatedTime}s`
      });

      // 启动进度条动画（10秒内平滑滑到80%）
      this.startProgressAnimation(estimatedTime);

      // 启动轮询
      this.startPolling();
    } else {
      // 如果没有executionId，使用原来的结果数据模式
      this.loadFromResults(options);
    }
  },

  /**
   * 从结果数据加载（原有逻辑）
   */
  loadFromResults: function(options) {
    try {
      // 获取传入的诊断结果数据
      const results = JSON.parse(decodeURIComponent(options.results || '[]'));
      const brandNames = JSON.parse(decodeURIComponent(options.brands || '[]'));

      // 如果没有数据，生成模拟数据
      let normalizedResults;
      if (!results || results.length === 0) {
        normalizedResults = this.generateMockData(brandNames);
      } else {
        // 标准化数据结构，确保与matrixHelper期望的格式匹配
        normalizedResults = this.normalizeResults(results, brandNames);
      }

      // 转换数据为矩阵格式
      const matrixData = this.transformToMatrix(normalizedResults, brandNames);

      // 获取问题列表
      const questionList = [...new Set(normalizedResults.map(item => item.question))];

      // 获取模型列表
      const modelList = [...new Set(normalizedResults.map(item => item.model || 'Unknown Model'))];

      // 初始化网格数据
      const gridData = getMatrixData('panorama', { results: normalizedResults }, '');

      // 模拟AI研判过程，增加用户体验
      setTimeout(() => {
        this.setData({
          matrixData: matrixData,
          brandNames: brandNames,
          questionList: questionList,
          modelList: modelList,
          gridData: gridData,
          isLoading: false
        });
      }, 500); // 短暂延迟模拟AI处理过程
    } catch (error) {
      console.error('Error processing data in detail page:', error);
      // 使用模拟数据作为后备
      const brandNames = JSON.parse(decodeURIComponent(options.brands || '[]'));
      const mockResults = this.generateMockData(brandNames);
      const matrixData = this.transformToMatrix(mockResults, brandNames);
      const gridData = getMatrixData('panorama', { results: mockResults }, '');
      const questionList = [...new Set(mockResults.map(item => item.question))];
      const modelList = [...new Set(mockResults.map(item => item.model || 'Unknown Model'))];

      this.setData({
        matrixData: matrixData,
        brandNames: brandNames,
        questionList: questionList,
        modelList: modelList,
        gridData: gridData,
        isLoading: false
      });

      wx.showToast({
        title: '使用模拟数据',
        icon: 'none'
      });
    }
  },

  /**
   * 启动进度条动画（10秒内平滑滑到80%）
   */
  startProgressAnimation: function(estimatedTime) {
    // 设置初始进度
    this.setData({
      progress: 0,
      progressText: 'AI 正在连接全网大模型...'
    });

    // 计算每秒应该增长的进度（10秒内达到80%）
    const totalSteps = 10; // 10秒
    const stepSize = 80 / totalSteps; // 每秒增长8%
    let currentStep = 0;

    this.progressInterval = setInterval(() => {
      currentStep++;
      const newProgress = Math.min(80, Math.round(currentStep * stepSize));

      // 根据进度更新文案
      let progressText = '';
      if (newProgress <= 30) {
        progressText = 'AI 正在连接全网大模型...';
      } else if (newProgress <= 60) {
        progressText = 'AI 正在进行深度语义研判...';
      } else {
        progressText = 'AI 正在聚合战略对阵矩阵...';
      }

      this.setData({
        progress: newProgress,
        progressText: progressText
      });

      // 10秒后停止，等待真实数据返回
      if (currentStep >= totalSteps) {
        clearInterval(this.progressInterval);
      }
    }, 1000);
  },

  /**
   * 启动轮询
   */
  startPolling: function() {
    // 初始化矩阵框架，显示加载状态
    this.initializeMatrixFramework();

    // 记录开始时间
    this.startTime = Date.now();

    // 添加进度停滞检测相关变量
    this.stagnantProgressCounter = 0; // 进度停滞计数器
    this.lastProgressValue = 0; // 上一次的进度值

    // 开始轮询
    this.pollInterval = setInterval(async () => {
      try {
        const statusData = await this.fetchTaskStatus(this.executionId);

        if (statusData) {
          // 使用服务层解析任务状态数据
          const parsedStatus = parseTaskStatus(statusData);

          // 检查任务是否完成
          const isCompleted = statusData.is_completed ||
                             parsedStatus.stage === 'completed';

          if (isCompleted && statusData.results && statusData.results.length > 0) {
            clearInterval(this.pollInterval);

            // 计算实际耗时
            const actualTime = Math.round((Date.now() - this.startTime) / 1000);

            // 处理完成的数据
            this.handleTaskCompletion(statusData, actualTime);
          } else {
            // 更新进度信息
            this.updateProgress(statusData);

            // 检测进度停滞
            this.checkProgressStagnation(statusData.progress);
          }
        }
      } catch (error) {
        console.error('轮询错误:', error);
        clearInterval(this.pollInterval);

        // 出错时显示模拟数据
        this.setData({
          isLoading: false,
          showSkeleton: false
        });
        wx.showToast({
          title: '数据加载失败，显示模拟数据',
          icon: 'none'
        });
      }
    }, 2000); // 每2秒轮询一次
  },

  /**
   * 检测进度停滞
   * @param {number} currentProgress - 当前进度值
   */
  checkProgressStagnation: function(currentProgress) {
    // 如果当前进度等于上次记录的进度，计数器加1
    if (currentProgress === this.lastProgressValue) {
      this.stagnantProgressCounter++;

      // 如果连续10次轮询进度没有变化（约20秒）
      if (this.stagnantProgressCounter >= 10) {
        // 更新UI提示用户
        this.setData({
          progressText: '后端计算量较大，正在为您协调额外算力...'
        });

        // 重置计数器，避免重复提示
        this.stagnantProgressCounter = 0;

        // 触发一次增量请求校验
        this.verifyTaskStatus();
      }
    } else {
      // 如果进度有变化，重置计数器
      this.stagnantProgressCounter = 0;
    }

    // 更新上次进度值
    this.lastProgressValue = currentProgress;
  },

  /**
   * 触发增量请求校验
   */
  verifyTaskStatus: function() {
    // 重新获取任务状态以确认实际情况
    if (this.executionId) {
      this.fetchTaskStatus(this.executionId)
        .then(statusData => {
          if (statusData) {
            // 使用服务层解析任务状态数据
            const parsedStatus = parseTaskStatus(statusData);

            // 更新进度信息
            this.setData({
              progress: parsedStatus.progress,
              progressText: parsedStatus.statusText
            });
          }
        })
        .catch(error => {
          console.error('校验任务状态失败:', error);
        });
    }
  },

  /**
   * 处理任务完成
   */
  handleTaskCompletion: function(statusData, actualTime) {
    // 检查是否为惊喜完成（实际时间小于预估时间）
    const isSurprise = actualTime < this.data.estimatedTime;

    if (isSurprise) {
      // 更新为惊喜文案
      this.setData({
        progressText: '⚡ 算力调度成功，研判提前完成！'
      });

      // 触发1.5秒的极速冲刺动画直达100%
      this.rapidFinishAnimation();
    } else {
      // 正常完成
      this.setData({
        progress: 100,
        progressText: '研判完成，正在生成报告...'
      });
    }

    // 处理完成的数据
    this.processCompletedResults(statusData);

    // 清除进度动画
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }
  },

  /**
   * 进度条极速冲刺动画（1.5秒冲刺到100%）
   */
  rapidFinishAnimation: function() {
    // 创建快速完成动画，1.5秒内冲刺到100%
    const startProgress = this.data.progress;
    const targetProgress = 100;
    const duration = 1500; // 1.5秒
    const steps = 30; // 动画步数
    const intervalTime = duration / steps; // 每步间隔时间

    let step = 0;
    const stepSize = (targetProgress - startProgress) / steps;

    // 保存定时器引用以便后续清理
    this.rapidFinishInterval = setInterval(() => {
      step++;
      const currentProgress = Math.min(targetProgress, startProgress + (step * stepSize));

      if (step >= steps) {
        // 动画结束，直接设置到100%
        this.setData({
          progress: targetProgress,
          progressText: '✅ 战略报告生成完毕'
        });
        if (this.rapidFinishInterval) {
          clearInterval(this.rapidFinishInterval);
          this.rapidFinishInterval = null;
        }
      } else {
        this.setData({
          progress: currentProgress,
          progressText: '🚀 极速冲刺中...'
        });
      }
    }, intervalTime);
  },

  /**
   * 初始化矩阵框架
   */
  initializeMatrixFramework: function() {
    // 创建初始矩阵框架，显示加载状态
    const brandNames = this.brandList || [];
    const questionList = [this.customQuestion || '品牌认知分析']; // 使用传入的问题

    // 创建初始矩阵数据结构
    const headers = ['问题', ...brandNames];
    const rows = [];

    // 为每个问题创建行（暂时只有一行）
    questionList.forEach(question => {
      const row = [question];
      brandNames.forEach(brand => {
        row.push({
          score: null, // 显示加载状态
          answer: 'AI 正在分析中...',
          brand: brand,
          question: question
        });
      });
      rows.push(row);
    });

    // 更新数据
    this.setData({
      isLoading: true,
      showSkeleton: true,
      gridData: {
        headers: headers,
        rows: rows
      }
    });
  },

  /**
   * 获取任务状态
   */
  fetchTaskStatus: async function(executionId) {
    try {
      return await getTaskStatusApi(executionId);
    } catch (error) {
      console.error('获取任务状态失败:', error);
      throw error; // 重新抛出错误，让调用方处理
    }
  },

  /**
   * 处理完成的结果
   */
  processCompletedResults: function(statusData) {
    try {
      // 标准化数据结构
      const normalizedResults = this.normalizeResults(statusData.results || [], this.brandList);

      // 转换数据为矩阵格式
      const matrixData = this.transformToMatrix(normalizedResults, this.brandList);

      // 获取问题列表
      const questionList = [...new Set(normalizedResults.map(item => item.question))];

      // 获取模型列表
      const modelList = [...new Set(normalizedResults.map(item => item.model || 'Unknown Model'))];

      // 初始化网格数据
      const gridData = getMatrixData('panorama', { results: normalizedResults }, '');

      // 完成进度条
      this.setData({
        matrixData: matrixData,
        brandNames: this.brandList,
        questionList: questionList,
        modelList: modelList,
        gridData: gridData,
        isLoading: false,
        showSkeleton: false,
        progress: 100,
        progressText: '战略大盘生成完毕',
        // 如果还有倒计时，清除它
        currentTime: 0
      });

      // 如果还有倒计时，清除它
      if (this.countdownInterval) {
        clearInterval(this.countdownInterval);
      }
    } catch (error) {
      console.error('处理完成结果时出错:', error);
      this.setData({
        isLoading: false,
        showSkeleton: false
      });
      wx.showToast({
        title: '数据处理失败',
        icon: 'none'
      });
    }
  },

  /**
   * 更新进度
   */
  updateProgress: function(statusData) {
    // 这里可以更新进度条或其他进度指示器
    console.log('任务进度:', statusData);

    // 使用服务层解析任务状态数据
    const parsedStatus = parseTaskStatus(statusData);

    console.log('解析后的状态文本:', parsedStatus.statusText);
    console.log('解析后的阶段:', parsedStatus.stage);

    // 更新进度文本
    this.setData({
      progressText: parsedStatus.statusText
    });

    console.log('当前进度:', parsedStatus.statusText);

    // 同时更新进度条数值
    if (statusData.progress !== undefined) {
      this.setData({
        progress: statusData.progress
      });
    }
  },

  onUnload: function() {
    // 清除轮询定时器
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }

    // 清除进度动画定时器
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }

    // 清除冲刺动画定时器
    if (this.rapidFinishInterval) {
      clearInterval(this.rapidFinishInterval);
    }

    // 清除倒计时定时器
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
  },

  /**
   * 生成模拟数据
   * @param {Array} brandNames - 品牌名称数组
   * @returns {Array} 模拟结果数组
   */
  generateMockData: function(brandNames) {
    if (!brandNames || brandNames.length === 0) {
      brandNames = ['元若曦', '养生堂', '固生堂'];
    }

    const questions = [
      '养生茶哪家好',
      '养生茶品牌推荐',
      '哪个品牌的养生茶最有效',
      '养生茶如何选择',
      '养生茶的功效与作用'
    ];

    const models = ['DeepSeek', '豆包', '通义千问'];

    const mockResults = [];

    for (const brand of brandNames) {
      for (const question of questions) {
        for (const model of models) {
          mockResults.push({
            brand: brand,
            question: question,
            model: model,
            answer: `${brand}在${question}方面表现出色，具有显著优势。`,
            scores: {
              accuracy: Math.floor(Math.random() * 20) + 80, // 80-100
              completeness: Math.floor(Math.random() * 20) + 75, // 75-95
              relevance: Math.floor(Math.random() * 25) + 75, // 75-100
              security: Math.floor(Math.random() * 30) + 70, // 70-100
              sentiment: Math.floor(Math.random() * 20) + 80 // 80-100
            },
            source: ['https://example.com/source1', 'https://example.com/source2']
          });
        }
      }
    }

    return mockResults;
  },

  /**
   * 标准化结果数据结构
   * @param {Array} results - 原始结果数组
   * @param {Array} brandNames - 品牌名称数组
   * @returns {Array} 标准化后的结果数组
   */
  normalizeResults: function(results, brandNames) {
    if (!results || !Array.isArray(results)) {
      return [];
    }

    // 检查数据结构，如果是嵌套结构则展平
    let normalized = [];

    for (const result of results) {
      if (result.brand && result.question) {
        // 如果已经是标准格式
        normalized.push({
          brand: result.brand,
          question: result.question,
          model: result.model || result.provider || 'Unknown Model',
          answer: result.answer || result.response || result.content || '',
          scores: result.scores || result.score || {},
          source: result.source || result.sources || []
        });
      } else if (result.results && Array.isArray(result.results)) {
        // 如果是嵌套结构，展平它
        for (const subResult of result.results) {
          normalized.push({
            brand: subResult.brand || result.brand || brandNames[0] || 'Unknown Brand',
            question: subResult.question || result.question || 'Unknown Question',
            model: subResult.model || subResult.provider || result.model || result.provider || 'Unknown Model',
            answer: subResult.answer || subResult.response || subResult.content || result.answer || '',
            scores: subResult.scores || subResult.score || result.scores || result.score || {},
            source: subResult.source || subResult.sources || result.source || result.sources || []
          });
        }
      } else {
        // 尝试从其他可能的字段结构中提取
        const brand = result.brand || result.brandName || brandNames[0] || 'Unknown Brand';
        const question = result.question || result.query || 'Unknown Question';
        const model = result.model || result.provider || result.ai_model || 'Unknown Model';

        normalized.push({
          brand: brand,
          question: question,
          model: model,
          answer: result.answer || result.response || result.content || result.prediction || '',
          scores: result.scores || result.score || result.prediction_scores || {},
          source: result.source || result.sources || result.references || []
        });
      }
    }

    return normalized;
  },

  /**
   * 将后端 results 数组转换为矩阵格式
   * @param {Array} results - 后端返回的结果数组
   * @param {Array} brandNames - 品牌名称数组
   * @returns {Object} 矩阵数据结构
   */
  transformToMatrix: function(results, brandNames) {
    if (!results || !Array.isArray(results) || results.length === 0) {
      return {
        headers: [],
        rows: []
      };
    }

    // 获取所有唯一的问题
    const uniqueQuestions = [...new Set(results.map(item => item.question))];

    // 构建矩阵数据
    const headers = ['问题'].concat(brandNames); // 第一列为问题，其余为品牌
    const rows = [];

    uniqueQuestions.forEach(question => {
      const row = [question]; // 第一列是问题

      brandNames.forEach(brandName => {
        // 找到该品牌和问题对应的答案
        const brandResults = results.filter(item =>
          item.question === question && item.brand === brandName
        );

        if (brandResults.length > 0) {
          // 计算该品牌在该问题下的平均分
          const avgScore = this.calculateAverageScore(brandResults);

          // 获取该品牌在该问题下的回答摘要
          const answerSummary = this.getAnswerSummary(brandResults);

          // 获取模型详细数据
          const modelsData = brandResults.map(result => ({
            name: result.model || 'Unknown Model',
            score: this.getItemScore(result),
            answer: result.answer || result.response || ''
          }));

          row.push({
            score: avgScore,
            answer: answerSummary,
            brand: brandName,
            question: question,
            models: modelsData
          });
        } else {
          // 如果没有数据，标记为无数据
          row.push({
            score: null,
            answer: '无数据',
            brand: brandName,
            question: question,
            models: []
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
   * 计算平均分
   * @param {Array} results - 特定品牌和问题的结果数组
   * @returns {Number} 平均分
   */
  calculateAverageScore: function(results) {
    if (!results || results.length === 0) {
      return 0;
    }

    const totalScore = results.reduce((sum, item) => {
      // 计算单个结果的综合得分
      const itemScore = this.getItemScore(item);
      return sum + itemScore;
    }, 0);

    return Math.round(totalScore / results.length);
  },

  /**
   * 获取单个项目的综合得分
   * @param {Object} item - 单个结果项
   * @returns {Number} 综合得分
   */
  getItemScore: function(item) {
    // 从评分对象中提取各项分数
    const scores = item.scores || {};
    const accuracy = scores.accuracy || scores.Accuracy || 0;
    const completeness = scores.completeness || scores.Completeness || 0;
    const relevance = scores.relevance || scores.Relevance || 0;
    const security = scores.security || scores.Security || 0;
    const sentiment = scores.sentiment || scores.Sentiment || 0;

    // 计算平均分
    const total = accuracy + completeness + relevance + security + sentiment;
    return Math.round(total / 5);
  },

  /**
   * 获取回答摘要
   * @param {Array} results - 特定品牌和问题的结果数组
   * @returns {String} 回答摘要
   */
  getAnswerSummary: function(results) {
    if (!results || results.length === 0) {
      return '无数据';
    }

    // 获取第一个结果的回答作为摘要
    const firstAnswer = results[0].answer || results[0].response || '';
    
    // 限制长度并添加省略号
    return firstAnswer.length > 50 ? firstAnswer.substring(0, 50) + '...' : firstAnswer;
  },


  /**
   * 显示详情弹窗
   * @param {Object} e - 事件对象
   */
  showDetailPopup: function(e) {
    const { brand, question, answer } = e.currentTarget.dataset;

    wx.showModal({
      title: `${brand} - ${question}`,
      content: answer,
      showCancel: false,
      confirmText: '关闭'
    });
  },

  /**
   * 获取矩阵数据密度
   */
  getMatrixDensity: function() {
    if (!this.data.matrixData || !this.data.matrixData.rows) {
      return 0;
    }

    const rows = this.data.matrixData.rows;
    const headers = this.data.matrixData.headers;

    if (rows.length === 0 || headers.length <= 1) {
      return 0;
    }

    let filledCells = 0;
    let totalCells = 0;

    rows.forEach(row => {
      // 跳过第一个元素（问题描述）
      for (let i = 1; i < row.length; i++) {
        totalCells++;
        if (row[i] && row[i].score !== null) {
          filledCells++;
        }
      }
    });

    return totalCells > 0 ? Math.round((filledCells / totalCells) * 100) : 0;
  },

  /**
   * 处理详情弹窗显示
   */
  onShowDetail: function(e) {
    const { brand, question, answer, score } = e.detail;

    wx.showModal({
      title: `${brand} - ${question} (得分: ${score || '-'})`,
      content: answer,
      showCancel: false,
      confirmText: '关闭'
    });
  },

  /**
   * 处理视图切换
   */
  onViewChange: function(e) {
    const view = e.detail.view;

    this.setData({
      currentView: view,
      // 重置滚动位置
      scrollTop: 0
    });
  },

  /**
   * 处理品牌/问题选择
   */
  onSelectionChange: function(e) {
    const value = parseInt(e.detail.value);

    if (this.data.currentView === 'model') {
      this.setData({
        selectedBrandIndex: value
      });
    } else if (this.data.currentView === 'question') {
      this.setData({
        selectedQuestionIndex: value
      });
    }
  },

  /**
   * 显示情报抽屉
   */
  onShowIntelligence: function(e) {
    const { brand, question, answer, score, model } = e.detail;

    // 获取详细指标数据
    const detailedScores = this.getDetailedScores(brand, question);

    this.setData({
      showIntelligenceDrawer: true,
      intelligenceData: {
        brand: brand,
        question: question,
        answer: answer,
        score: score,
        model: model || '未知模型',
        sources: this.getSources(brand, question), // 获取信源数据
        detailedScores: detailedScores
      }
    });
  },

  /**
   * 获取详细指标数据
   */
  getDetailedScores: function(brand, question) {
    // 这里应该根据实际数据结构获取详细指标
    // 模拟数据
    return [
      { name: '准确性', value: Math.floor(Math.random() * 40) + 60 }, // 60-100
      { name: '完整性', value: Math.floor(Math.random() * 40) + 60 },
      { name: '相关性', value: Math.floor(Math.random() * 40) + 60 },
      { name: '安全性', value: Math.floor(Math.random() * 40) + 60 },
      { name: '情感倾向', value: Math.floor(Math.random() * 40) + 60 }
    ];
  },

  /**
   * 获取信源数据
   */
  getSources: function(brand, question) {
    // 这里应该根据实际数据结构获取信源
    // 模拟数据
    return [
      { url: 'https://example.com/source1', title: '参考来源 1' },
      { url: 'https://example.com/source2', title: '参考来源 2' },
      { url: 'https://example.com/source3', title: '参考来源 3' }
    ];
  },

  /**
   * 关闭情报抽屉
   */
  onCloseIntelligenceDrawer: function() {
    this.setData({
      showIntelligenceDrawer: false,
      intelligenceData: null
    });
  },

  /**
   * 切换视图
   */
  onSwitchView: function(e) {
    const viewType = e.detail.view;
    let gridData;

    if (viewType === 'model') {
      // 获取当前选中的品牌
      const selectedBrand = this.data.brandNames[this.data.selectedBrandIndex] || '';
      gridData = getMatrixData('model', { results: this.data.matrixData.results || [] }, selectedBrand);
    } else {
      gridData = getMatrixData('panorama', { results: this.data.matrixData.results || [] }, '');
    }

    this.setData({
      currentView: viewType,
      gridData: gridData,
      isGridLoading: false
    });
  },

  /**
   * 选择品牌
   */
  onBrandSelect: function(e) {
    const value = parseInt(e.detail.value);
    this.setData({
      selectedBrandIndex: value
    });

    // 如果当前是模型视图，需要重新加载数据
    if (this.data.currentView === 'model') {
      const selectedBrand = this.data.brandNames[value] || '';
      const gridData = getMatrixData('model', { results: this.data.matrixData.results || [] }, selectedBrand);
      this.setData({
        gridData: gridData
      });
    }
  },

  /**
   * 显示分数提示
   */
  showScoreTip: function(e) {
    const { brand, question, model, score } = e.currentTarget.dataset;
    wx.showToast({
      title: `点击查看 ${brand} 在 ${model} 下的详细归因`,
      icon: 'none',
      duration: 2000
    });
  },

  /**
   * 获取分数背景颜色（供WXML使用）
   */
  getScoreBgColor: function(score) {
    return getColorByScore(score);  // 使用从 utils/matrixHelper 导入的函数
  },

  /**
   * 根据视图更新矩阵数据
   */
  updateMatrixForView: function(view) {
    // 这里可以根据不同的视图模式重新计算矩阵数据
    // 例如：标准视图、模型对比视图、问题诊断视图
    console.log('切换到视图:', view);
  },

  /**
   * 获取进度条颜色
   */
  getProgressColor: function(progress) {
    // 从深蓝 (#0066FF) 随百分比向科技青 (#00F2FF) 渐变
    const ratio = progress / 100;
    const r = Math.round(0 * (1 - ratio) + 0 * ratio);
    const g = Math.round(102 * (1 - ratio) + 242 * ratio);
    const b = Math.round(255 * (1 - ratio) + 255 * ratio);

    return `rgb(${r}, ${g}, ${b})`;
  },

  /**
   * 获取进度文案
   */
  getProgressText: function(progress) {
    if (progress <= 30) {
      return 'AI 正在连接全网大模型...';
    } else if (progress <= 60) {
      return 'AI 正在进行深度语义研判...';
    } else if (progress <= 80) {
      return 'AI 正在聚合战略对阵矩阵...';
    } else if (progress < 100) {
      return 'AI 正在生成最终报告...';
    } else {
      return '战略报告生成完毕';
    }
  }
})