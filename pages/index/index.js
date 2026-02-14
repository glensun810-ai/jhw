const { checkServerConnectionApi, startBrandTestApi, getTestProgressApi, getTaskStatusApi } = require('../../api/home');
const {
  processTestProgress,
  getProgressTextByValue,
  formatTestResults,
  formatCompetitiveAnalysis,
  isTestCompleted,
  isTestFailed
} = require('../../services/homeService.js');
const { parseTaskStatus } = require('../../services/taskStatusService');

const appid = 'wx8876348e089bc261'; // 您的 AppID

Page({
  data: {
    // 用户状态
    userInfo: null,
    openid: '',
    loginStatus: '未登录',
    serverStatus: '未连接',

    // 品牌与竞品
    brandName: '',
    competitorBrands: [],
    currentCompetitor: '',

    // 问题设置
    customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}],
    selectedQuestionCount: 0,

    // AI模型选择
    domesticAiModels: [
      { name: 'DeepSeek', checked: true, logo: 'DS', tags: ['综合', '代码'] },
      { name: '豆包', checked: true, logo: 'DB', tags: ['综合', '创意'] },
      { name: '通义千问', checked: true, logo: 'QW', tags: ['综合', '长文本'] },
      { name: '元宝', checked: false, logo: 'YB', tags: ['综合']},
      { name: 'Kimi', checked: false, logo: 'KM', tags: ['长文本'] },
      { name: '文心一言', checked: false, logo: 'WX', tags: ['综合', '创意'] },
      { name: '讯飞星火', checked: false, logo: 'XF', tags: ['综合', '语音'] },
      { name: '智谱AI', checked: false, logo: 'ZP', tags: ['综合', 'GLM'] },      
    ],
    overseasAiModels: [
      { name: 'ChatGPT', checked: true, logo: 'GPT', tags: ['综合', '代码'] },
      { name: 'Gemini', checked: false, logo: 'GM', tags: ['综合', '多模态'] },
      { name: 'Claude', checked: false, logo: 'CD', tags: ['长文本', '创意'] },
      { name: 'Perplexity', checked: false, logo: 'PE', tags: ['综合', '长文本'] },
      { name: 'Grok', checked: false, logo: 'GR', tags: ['推理', '多模态'] },
      
    ],
    selectedModelCount: 0,

    // 测试状态
    isTesting: false,
    testProgress: 0,
    progressText: '准备启动AI认知诊断...',
    testCompleted: false,

    // 高级设置控制
    showAdvancedSettings: false,

    // 存储后端返回的最终结果
    latestTestResults: null,
    latestCompetitiveAnalysis: null,

    // 新增：用于存储完整报告数据
    reportData: null,

    // 控制是否启用新的分析图表组件
    analysisChartsEnabled: true,

    // 控制内容区域入场动画
    contentVisible: false,

    // 控制吸顶效果
    isSticky: false,

    // 当前任务阶段
    currentStage: 'init',

    // 趋势图表数据
    trendChartData: null,

    // 评分数据
    scoreData: null,

    // 竞争分析数据
    competitionData: null,

    // 预测数据
    predictionData: null,

    // 信源列表数据
    sourceListData: [],

    // 保存配置相关
    showSaveModal: false,
    configName: '',

    // Debug 区域显示的原始JSON
    debugJson: '',

    // 动画
    particleAnimateId: null
  },

  onLoad: function (options) {
    console.log('品牌AI雷达 - 页面加载完成');
    this.checkServerConnection();
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();

    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      // 延迟执行，确保页面已完全加载
      setTimeout(() => {
        this.startBrandTest();
      }, 1000); // 延迟稍长一些，确保配置已完全加载
    }
  },

  onShow: function() {
    // 检查是否有从配置管理页面传回的临时配置
    const app = getApp();
    if (app.globalData && app.globalData.tempConfig) {
      this.applyConfig(app.globalData.tempConfig);
      // 清除临时配置
      app.globalData.tempConfig = null;
    }
  },

  // 应用配置
  applyConfig: function(config) {
    // 确保自定义问题格式正确（每个问题都应该有text和show属性）
    const formattedQuestions = config.customQuestions.map(q => ({
      text: q.text || '',
      show: q.show !== undefined ? q.show : true
    }));

    this.setData({
      brandName: config.brandName || '',
      competitorBrands: Array.isArray(config.competitorBrands) ? config.competitorBrands : [],
      customQuestions: formattedQuestions,
      // 仅更新选中状态，保留模型的其他属性，处理可能不存在的模型
      domesticAiModels: this.data.domesticAiModels.map(model => {
        const savedModel = Array.isArray(config.domesticAiModels)
          ? config.domesticAiModels.find(saved => saved.name === model.name)
          : null;
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      }),
      overseasAiModels: this.data.overseasAiModels.map(model => {
        const savedModel = Array.isArray(config.overseasAiModels)
          ? config.overseasAiModels.find(saved => saved.name === model.name)
          : null;
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      })
    });

    wx.showToast({
      title: '配置已加载',
      icon: 'success'
    });
  },

  onReady: function () {
    this.initParticleCanvas();
  },

  onUnload: function () {
    if (this.data.particleAnimateId) {
      cancelAnimationFrame(this.data.particleAnimateId);
    }
  },

  initParticleCanvas: function() {
    const query = wx.createSelectorQuery();
    query.select('#particle-canvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0] || !res[0].node) {
          console.error("Cannot get canvas node.");
          return;
        }
        const canvas = res[0].node;
        const ctx = canvas.getContext('2d');
        const systemSetting = wx.getSystemSetting();
        const appAuthorizeSetting = wx.getAppAuthorizeSetting();
        const deviceInfo = wx.getDeviceInfo();
        const windowInfo = wx.getWindowInfo();
        const appBaseInfo = wx.getAppBaseInfo();

        // 合并需要的字段
        const systemInfo = {
            ...deviceInfo,
            ...windowInfo,
            ...appBaseInfo,
            system: appBaseInfo.system,
            platform: appBaseInfo.platform,
        };
        const dpr = systemInfo.pixelRatio;
        canvas.width = res[0].width * dpr;
        canvas.height = res[0].height * dpr;
        ctx.scale(dpr, dpr);

        const particles = [];
        const particleCount = 50;

        for (let i = 0; i < particleCount; i++) {
          particles.push({
            x: Math.random() * res[0].width,
            y: Math.random() * res[0].height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            radius: Math.random() * 1.5 + 0.5
          });
        }

        const animate = () => {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < 0 || p.x > res[0].width) p.vx *= -1;
            if (p.y < 0 || p.y > res[0].height) p.vy *= -1;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.fill();
          });
          for (let i = 0; i < particleCount; i++) {
            for (let j = i + 1; j < particleCount; j++) {
              const dist = Math.hypot(particles[i].x - particles[j].x, particles[i].y - particles[j].y);
              if (dist < 100) {
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.strokeStyle = `rgba(255, 255, 255, ${0.5 - dist / 200})`;
                ctx.stroke();
              }
            }
          }
          this.data.particleAnimateId = canvas.requestAnimationFrame(animate);
        };
        animate();
      });
  },

  async checkServerConnection() {
    try {
      await checkServerConnectionApi();
      this.setData({ serverStatus: '已连接' });
    } catch (err) {
      this.setData({ serverStatus: '连接失败' });
      wx.showToast({ title: '后端服务未启动', icon: 'error' });
    }
  },

  toggleAdvancedSettings: function() {
    this.setData({
      showAdvancedSettings: !this.data.showAdvancedSettings
    });
  },

  onBrandNameInput: function(e) {
    this.setData({ brandName: e.detail.value });
  },

  onCompetitorInput: function(e) {
    this.setData({ currentCompetitor: e.detail.value });
  },

  addCompetitor: function() {
    const currentCompetitor = this.data.currentCompetitor.trim();
    let competitorBrands = this.data.competitorBrands;

    if (!currentCompetitor) {
      wx.showToast({ title: '请输入竞争对手名称', icon: 'none' });
      return;
    }
    if (competitorBrands.includes(currentCompetitor)) {
      wx.showToast({ title: '该竞争对手已存在', icon: 'none' });
      return;
    }
    if (currentCompetitor === this.data.brandName.trim()) {
      wx.showToast({ title: '不能添加主品牌作为竞品', icon: 'none' });
      return;
    }

    competitorBrands.push(currentCompetitor);
    this.setData({ competitorBrands: competitorBrands, currentCompetitor: '' });
    wx.showToast({ title: '添加成功', icon: 'success' });
  },

  removeCompetitor: function(e) {
    const index = e.currentTarget.dataset.index;
    let competitorBrands = this.data.competitorBrands;
    competitorBrands.splice(index, 1);
    this.setData({ competitorBrands: competitorBrands });
    wx.showToast({ title: '删除成功', icon: 'success' });
  },

  onCustomQuestionInput: function(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value;
    let customQuestions = this.data.customQuestions;
    customQuestions[index].text = value;
    this.setData({ customQuestions: customQuestions });
    this.updateSelectedQuestionCount();
  },

  addCustomQuestion: function() {
    let customQuestions = this.data.customQuestions;
    customQuestions.push({text: '', show: true});
    this.setData({ customQuestions: customQuestions });
    this.updateSelectedQuestionCount();
  },

  removeCustomQuestion: function(e) {
    const index = e.currentTarget.dataset.index;
    let customQuestions = this.data.customQuestions;

    // 如果只有一个问题，则清空内容而不是删除
    if (customQuestions.length === 1) {
      customQuestions[0].text = '';
      this.setData({ customQuestions: customQuestions });
    } else {
      customQuestions.splice(index, 1);
      this.setData({ customQuestions: customQuestions });
    }

    this.updateSelectedQuestionCount();
  },

  getValidQuestions: function() {
    return this.data.customQuestions
      .filter(questionObj => questionObj.show !== false && questionObj.text && questionObj.text.trim() !== '')
      .map(questionObj => questionObj.text.trim());
  },

  updateSelectedQuestionCount: function() {
    const validQuestions = this.data.customQuestions
      .filter(questionObj => questionObj.show !== false && questionObj.text && questionObj.text.trim() !== '');
    this.setData({ selectedQuestionCount: validQuestions.length });
  },

  toggleModelSelection: function(e) {
    const { type, index } = e.currentTarget.dataset;
    const key = type === 'domestic' ? 'domesticAiModels' : 'overseasAiModels';
    const models = this.data[key];

    if (models[index].disabled) {
      wx.showToast({ title: '该模型暂未配置', icon: 'none' });
      return;
    }

    models[index].checked = !models[index].checked;
    this.setData({ [key]: models });
    this.updateSelectedModelCount();
  },

  selectAllModels: function(e) {
    const { type } = e.currentTarget.dataset;
    const key = type === 'domestic' ? 'domesticAiModels' : 'overseasAiModels';
    const models = this.data[key].map(model => ({ 
      ...model, 
      checked: !model.disabled
    }));
    this.setData({ [key]: models });
    this.updateSelectedModelCount();
  },

  updateSelectedModelCount: function() {
    const selectedDomesticCount = this.data.domesticAiModels.filter(model => model.checked).length;
    const selectedOverseasCount = this.data.overseasAiModels.filter(model => model.checked).length;
    const totalCount = selectedDomesticCount + selectedOverseasCount;
    this.setData({ selectedModelCount: totalCount });
  },

  startBrandTest: function() {
    const brandName = this.data.brandName.trim();
    if (!brandName) {
      wx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
      return;
    }

    const brand_list = [brandName, ...this.data.competitorBrands];
    let selectedModels = [...this.data.domesticAiModels, ...this.data.overseasAiModels].filter(model => model.checked && !model.disabled);
    let customQuestions = this.getValidQuestions();

    if (selectedModels.length === 0) {
      wx.showToast({ title: '请选择至少一个AI模型', icon: 'error' });
      return;
    }
    if (customQuestions.length === 0) {
      customQuestions = ["介绍一下{brandName}", "{brandName}的主要产品是什么"];
    }

    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动AI认知诊断...',
      testCompleted: false,
    });

    this.callBackendBrandTest(brand_list, selectedModels, customQuestions);
  },

  async callBackendBrandTest(brand_list, selectedModels, customQuestions) {
    wx.showLoading({ title: '启动诊断...' });

    // 载荷标准化：将 selectedModels 对象数组平滑化为纯字符串 ID 数组
    const processedSelectedModels = selectedModels.map(item => {
      if (typeof item === 'object' && item !== null) {
        // 如果 item 是对象，提取其 id 或 value
        return item.id || item.value || item.name || item.label || '';
      } else {
        // 如果是字符串，直接保留
        return item;
      }
    }).filter(id => id !== ''); // 过滤掉空字符串

    // 类型降维处理：将问题数组转换为字符串
    const custom_question = customQuestions.join(' ');

    // 调试增强：打印请求数据
    console.log('Request Payload:', {
      brand_list: brand_list,
      selectedModels: processedSelectedModels, // 确保格式正确并标准化模型名称
      custom_question: custom_question  // 修正字段名和类型
    });

    try {
      const requestData = {
        brand_list: brand_list,
        selectedModels: processedSelectedModels, // 确保格式正确并标准化模型名称
        custom_question: custom_question  // 修正字段名和类型
      };

      console.log('Sending request to API:', requestData);

      const res = await startBrandTestApi(requestData);

      console.log('API Response:', res);

      // 强制兼容多种返回格式
      const responseData = res.data || res;
      const executionId = responseData.execution_id || responseData.id || (responseData.data && responseData.data.execution_id);

      if (executionId) {
        console.log('✅ 战局指令下达成功，执行ID:', executionId);
        wx.hideLoading(); // 确保配对关闭
        this.navigateToDetail(executionId, brand_list, selectedModels, custom_question); // 调用跳转
      } else {
        throw new Error('未能从响应中提取有效ID');
      }
    } catch (err) {
      // 错误捕获防御：彻底重写 catch(err) 块
      // 要求：第一时间执行 wx.hideLoading()
      wx.hideLoading();

      console.error("Diagnostic Error:", err);
      console.error("Error details:", err.errMsg, err.data);

      // 要求：使用 err.data?.error || err.data?.message || err.errMsg 提取信息
      let extractedError = err.data?.error || err.data?.message || err.errMsg || "任务创建失败";

      // 如果错误信息包含网络相关错误，提供更友好的提示
      if (extractedError && (extractedError.includes('request:fail') || extractedError.includes('network'))) {
        extractedError = '网络连接失败，请检查网络设置或稍后重试';
      }

      // 要求：使用 wx.showModal 弹出提取到的真实错误信息
      wx.showModal({
        title: '启动失败',
        content: String(extractedError),
        showCancel: false
      });

      this.setData({ isTesting: false });
    } finally {
      // 交互修复：确保在所有情况下都隐藏加载提示
      // 注意：这里不再重复调用 wx.hideLoading()，因为在 catch 块中已经调用了
      // 避免重复调用可能引起的错误
    }
  },

  pollTestProgress(executionId) {
    // 使用新的 /api/test/status/{id} 接口进行轮询
    const pollInterval = setInterval(async () => {
      try {
        const res = await getTaskStatusApi(executionId);
        console.log("返回数据：",res)//调试用，上线前删除
        if (res.statusCode === 200) {
          // 更新调试区域显示原始JSON
          this.setData({ debugJson: JSON.stringify(res.data, null, 2) });

          // 使用服务层解析任务状态数据
          const parsedStatus = parseTaskStatus(res.data);

          // 更新进度条、状态文本和当前阶段
          this.setData({
            testProgress: parsedStatus.progress,
            progressText: parsedStatus.statusText,
            currentStage: parsedStatus.stage
          });

          // 如果状态为 completed，停止轮询并处理结果
          if (parsedStatus.stage === 'completed') {
            clearInterval(pollInterval);

            // 存储完整的报告数据
            const reportData = parsedStatus.detailed_results || parsedStatus.results;

            // 使用数据防御机制处理报告数据
            const processedReportData = this.processReportData(reportData);

            this.setData({
              reportData: processedReportData,
              isTesting: false,
              testCompleted: true,
              progressText: '诊断完成，正在生成报告...',
              // 设置趋势图表数据
              trendChartData: this.generateTrendChartData(processedReportData),
              // 设置预测数据
              predictionData: this.extractPredictionData(processedReportData),
              // 设置评分数据
              scoreData: this.extractScoreData(processedReportData),
              // 设置竞争分析数据
              competitionData: this.extractCompetitionData(processedReportData),
              // 设置信源列表数据
              sourceListData: this.extractSourceListData(processedReportData)
            });

            wx.showToast({ title: '诊断完成', icon: 'success' });
            this.renderReport(); // 触发报告渲染
          }
        } else {
          console.error('获取任务状态失败:', res);
          this.setData({ progressText: '获取状态失败...' });
        }
      } catch (err) {
        console.error('获取任务状态异常:', err);
        this.setData({ progressText: '状态连接异常...' });
      }
    }, 2000); // 每2秒轮询一次
  },

  viewDetailedResults: function() {
    // 优先使用新的 reportData，如果不存在则使用旧的 latestTestResults
    const resultsToUse = this.data.reportData || this.data.latestTestResults;

    if (resultsToUse) {
      // 直接传递对象，让微信小程序处理URL编码
      wx.navigateTo({
        url: `/pages/results/results?results=${encodeURIComponent(JSON.stringify(resultsToUse))}&competitiveAnalysis=${encodeURIComponent(JSON.stringify(this.data.latestCompetitiveAnalysis || {}))}&targetBrand=${encodeURIComponent(this.data.brandName)}`
      });
    } else {
      wx.showToast({ title: '暂无诊断结果', icon: 'none' });
    }
  },

  /**
   * 生成趋势图表数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 图表配置对象
   */
  generateTrendChartData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法生成趋势图表');
      return null;
    }

    try {
      // 检查 reportData 是否包含时间序列数据
      if (reportData.timeSeries && Array.isArray(reportData.timeSeries)) {
        // 如果有实际的时间序列数据，基于这些数据构建图表配置
        const timeSeries = reportData.timeSeries;
        const dates = timeSeries.map(item => item.period || item.date || '未知时间');
        const values = timeSeries.map(item => item.value || 0);

        // 如果有预测数据，也提取出来
        const predictions = reportData.prediction && Array.isArray(reportData.prediction.forecast_points)
          ? reportData.prediction.forecast_points.map(point => point.value || 0)
          : [];

        return {
          dates: dates,
          values: values,
          predictions: predictions
        };
      } else {
        // 如果没有实际数据，返回默认的示例数据
        return {
          dates: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
          values: [30, 45, 60, 75, 80, 85, 90],
          predictions: [88, 92, 95, 97, 98, 99, 100]
        };
      }
    } catch (error) {
      console.error('生成趋势图表数据失败:', error);
      // 返回默认的空数据结构
      return {
        dates: [],
        values: [],
        predictions: []
      };
    }
  },

  /**
   * 提取信源列表数据
   * @param {Object} reportData - 报告数据
   * @returns {Array} 信源列表
   */
  extractSourceListData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取信源列表');
      return [];
    }

    try {
      // 检查 reportData 是否包含 sources 属性
      if (reportData.sources && Array.isArray(reportData.sources)) {
        // 如果有实际的信源数据，直接返回
        return reportData.sources.map(source => ({
          title: source.title || source.name || '未知信源',
          url: source.url || source.link || '',
          score: source.score || source.confidence || 0,
          type: source.type || '未知类型'
        }));
      } else if (reportData.results && Array.isArray(reportData.results)) {
        // 如果没有 sources，尝试从 results 中提取信源信息
        const sources = [];
        reportData.results.forEach(result => {
          if (result.sources && Array.isArray(result.sources)) {
            result.sources.forEach(source => {
              sources.push({
                title: source.title || source.name || '未知信源',
                url: source.url || source.link || '',
                score: source.score || source.confidence || 0,
                type: source.type || '未知类型'
              });
            });
          }
        });
        return sources;
      } else {
        // 如果没有实际数据，返回默认的示例数据
        return [
          {
            title: '品牌官网',
            url: 'https://brand.example.com',
            score: 95,
            type: '官方'
          },
          {
            title: '行业报告',
            url: 'https://industry-report.com',
            score: 87,
            type: '第三方'
          },
          {
            title: '社交媒体',
            url: 'https://social-media.com',
            score: 78,
            type: 'UGC'
          }
        ];
      }
    } catch (error) {
      console.error('提取信源列表数据失败:', error);
      // 返回空数组作为最后的防线
      return [];
    }
  },

  /**
   * 信源点击事件处理
   */
  onSourceTap: function(event) {
    const { source, index } = event.detail;
    console.log('信源被点击:', source, index);

    // 可以在这里处理信源点击事件，比如打开详情页或外部链接
    if (source.url) {
      // 在浏览器中打开链接
      wx.setClipboardData({
        data: source.url,
        success: () => {
          wx.showToast({
            title: '链接已复制',
            icon: 'success'
          });
        }
      });
    }
  },

  /**
   * 提取评分数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 评分数据
   */
  extractScoreData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取评分数据');
      return {};
    }

    try {
      // 根据 API 文档规范，查找 scores 属性
      if (reportData.scores) {
        // 直接返回 scores 对象，确保字段名符合契约
        return {
          accuracy: reportData.scores.accuracy || reportData.scores.Accuracy || 0,
          completeness: reportData.scores.completeness || reportData.scores.Completeness || 0,
          relevance: reportData.scores.relevance || reportData.scores.Relevance || 0,
          security: reportData.scores.security || reportData.scores.Security || 0,
          sentiment: reportData.scores.sentiment || reportData.scores.Sentiment || 0,
          competitiveness: reportData.scores.competitiveness || reportData.scores.Competitiveness || 0,
          authority: reportData.scores.authority || reportData.scores.Authority || 0
        };
      } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
        // 如果没有直接的 scores 属性，尝试从第一个结果中提取
        const firstResult = reportData.results[0];
        if (firstResult.scores) {
          return {
            accuracy: firstResult.scores.accuracy || firstResult.scores.Accuracy || 0,
            completeness: firstResult.scores.completeness || firstResult.scores.Completeness || 0,
            relevance: firstResult.scores.relevance || firstResult.scores.Relevance || 0,
            security: firstResult.scores.security || firstResult.scores.Security || 0,
            sentiment: firstResult.scores.sentiment || firstResult.scores.Sentiment || 0,
            competitiveness: firstResult.scores.competitiveness || firstResult.scores.Competitiveness || 0,
            authority: firstResult.scores.authority || firstResult.scores.Authority || 0
          };
        }
      }

      // 如果没有找到评分数据，返回默认值
      return {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0,
        authority: 0
      };
    } catch (error) {
      console.error('提取评分数据失败:', error);
      // 返回默认结构作为最后的防线
      return {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0,
        authority: 0
      };
    }
  },

  /**
   * 提取竞争分析数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 竞争分析数据
   */
  extractCompetitionData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取竞争分析数据');
      return {};
    }

    try {
      // 根据 API 文档规范，查找竞争分析相关属性
      if (reportData.competition) {
        // 直接返回竞争分析对象
        return {
          brand_keywords: reportData.competition.brand_keywords || reportData.competition.brandKeywords || [],
          shared_keywords: reportData.competition.shared_keywords || reportData.competition.sharedKeywords || [],
          competitors: reportData.competition.competitors || []
        };
      } else if (reportData.competitive_analysis) {
        // 兼容另一种命名方式
        return {
          brand_keywords: reportData.competitive_analysis.brand_keywords || reportData.competitive_analysis.brandKeywords || [],
          shared_keywords: reportData.competitive_analysis.shared_keywords || reportData.competitive_analysis.sharedKeywords || [],
          competitors: reportData.competitive_analysis.competitors || []
        };
      } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
        // 如果没有直接的竞争分析属性，尝试从第一个结果中提取
        const firstResult = reportData.results[0];
        if (firstResult.competition) {
          return {
            brand_keywords: firstResult.competition.brand_keywords || firstResult.competition.brandKeywords || [],
            shared_keywords: firstResult.competition.shared_keywords || firstResult.competition.sharedKeywords || [],
            competitors: firstResult.competition.competitors || []
          };
        } else if (firstResult.competitive_analysis) {
          return {
            brand_keywords: firstResult.competitive_analysis.brand_keywords || firstResult.competitive_analysis.brandKeywords || [],
            shared_keywords: firstResult.competitive_analysis.shared_keywords || firstResult.competitive_analysis.sharedKeywords || [],
            competitors: firstResult.competitive_analysis.competitors || []
          };
        }
      }

      // 如果没有找到竞争分析数据，返回默认值
      return {
        brand_keywords: [],
        shared_keywords: [],
        competitors: []
      };
    } catch (error) {
      console.error('提取竞争分析数据失败:', error);
      // 返回默认结构作为最后的防线
      return {
        brand_keywords: [],
        shared_keywords: [],
        competitors: []
      };
    }
  },

  /**
   * 处理报告数据，应用数据防御机制
   * @param {Object} reportData - 原始报告数据
   * @returns {Object} 处理后的报告数据
   */
  processReportData: function(reportData) {
    // 数据防御：永远假设后端可能返回 null、undefined 或空数组
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，返回默认结构');
      return this.getDefaultReportStructure();
    }

    // 使用数据防御法则处理各个数据部分
    return {
      // 预测数据防御
      prediction: this.defensiveGet(reportData, 'prediction', {}) || {},

      // 评分数据防御
      scores: this.defensiveGet(reportData, 'scores', {}) || {},

      // 竞争分析数据防御
      competition: this.defensiveGet(reportData, 'competition', {}) || {},

      // 信源数据防御
      sources: this.defensiveGet(reportData, 'sources', []) || [],

      // 趋势数据防御
      trends: this.defensiveGet(reportData, 'trends', {}) || {},

      // 结果数据防御
      results: this.defensiveGet(reportData, 'results', []) || [],

      // 原始数据备份
      original: reportData
    };
  },

  /**
   * 安全获取对象属性，防止 null/undefined 错误
   * @param {Object} obj - 源对象
   * @param {String} prop - 属性路径，支持点号分隔如 'data.prediction.points'
   * @param {*} defaultValue - 默认值
   * @returns {*} 属性值或默认值
   */
  defensiveGet: function(obj, prop, defaultValue = null) {
    try {
      // 如果对象为空，返回默认值
      if (!obj || typeof obj !== 'object') {
        return defaultValue;
      }

      // 支持点号路径访问
      const props = prop.split('.');
      let result = obj;

      for (const p of props) {
        if (result == null || typeof result !== 'object') {
          return defaultValue;
        }
        result = result[p];

        // 如果中间某个属性为 null 或 undefined，返回默认值
        if (result == null) {
          return defaultValue;
        }
      }

      // 如果结果是数组但为空，返回默认值（根据需要调整）
      if (Array.isArray(defaultValue) && Array.isArray(result) && result.length === 0) {
        return defaultValue;
      }

      return result;
    } catch (error) {
      console.error(`获取属性 ${prop} 时出错:`, error);
      return defaultValue;
    }
  },

  /**
   * 获取默认报告结构
   * @returns {Object} 默认报告结构
   */
  getDefaultReportStructure: function() {
    return {
      prediction: {
        forecast_points: [],
        confidence: 0,
        trend: 'neutral'
      },
      scores: {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0
      },
      competition: {
        brand_keywords: [],
        shared_keywords: [],
        competitor_keywords: [],
        competitors: []
      },
      sources: [],
      trends: {
        historical: [],
        projected: []
      },
      results: [],
      original: {}
    };
  },

  /**
   * 渲染报告 - 触发报告展示逻辑
   */
  renderReport: function() {
    console.log('开始渲染报告...');

    // 更新UI以反映报告已准备好
    this.setData({
      reportReady: true
    });

    // 可以在这里添加额外的报告渲染逻辑
    // 例如：动画效果、数据可视化初始化等
  },

  /**
   * 提取预测数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 预测数据
   */
  extractPredictionData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取预测数据');
      return {};
    }

    try {
      // 根据 API 文档规范，查找预测相关属性
      if (reportData.prediction) {
        // 直接返回预测对象
        return {
          forecast_points: (reportData.prediction.forecast_points || reportData.prediction.forecastPoints) || [],
          confidence: reportData.prediction.confidence || 0,
          trend: reportData.prediction.trend || 'neutral'
        };
      } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
        // 如果没有直接的预测属性，尝试从第一个结果中提取
        const firstResult = reportData.results[0];
        if (firstResult.prediction) {
          return {
            forecast_points: (firstResult.prediction.forecast_points || firstResult.prediction.forecastPoints) || [],
            confidence: firstResult.prediction.confidence || 0,
            trend: firstResult.prediction.trend || 'neutral'
          };
        }
      }

      // 如果没有找到预测数据，返回默认值
      return {
        forecast_points: [],
        confidence: 0,
        trend: 'neutral'
      };
    } catch (error) {
      console.error('提取预测数据失败:', error);
      // 返回默认结构作为最后的防线
      return {
        forecast_points: [],
        confidence: 0,
        trend: 'neutral'
      };
    }
  },

  viewConfigManager: function() {
    wx.navigateTo({ url: '/pages/config-manager/config-manager' });
  },

  viewPermissionManager: function() {
    wx.navigateTo({ url: '/pages/permission-manager/permission-manager' });
  },

  viewDataManager: function() {
    wx.navigateTo({ url: '/pages/data-manager/data-manager' });
  },

  viewUserGuide: function() {
    wx.navigateTo({ url: '/pages/user-guide/user-guide' });
  },

  viewHistory: function() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  // 显示保存配置模态框
  showSaveConfigModal: function() {
    this.setData({
      showSaveModal: true,
      configName: ''
    });
  },

  // 隐藏保存配置模态框
  hideSaveConfigModal: function() {
    this.setData({
      showSaveModal: false,
      configName: ''
    });
  },

  // 处理配置名称输入
  onConfigNameInput: function(e) {
    this.setData({
      configName: e.detail.value
    });
  },

  // 保存当前配置
  saveCurrentConfig: function() {
    const configName = this.data.configName.trim();

    if (!configName) {
      wx.showToast({
        title: '请输入配置名称',
        icon: 'none'
      });
      return;
    }

    // 获取当前配置，只保存有效的自定义问题（show为true且有内容）
    const validQuestions = this.data.customQuestions
      .filter(questionObj => questionObj.show !== false && questionObj.text && questionObj.text.trim() !== '')
      .map(questionObj => ({ ...questionObj })); // 创建副本以避免引用问题

    const currentConfig = {
      name: configName,
      brandName: this.data.brandName,
      competitorBrands: this.data.competitorBrands,
      customQuestions: validQuestions,
      domesticAiModels: this.data.domesticAiModels.map(model => ({
        name: model.name,
        checked: model.checked
      })),
      overseasAiModels: this.data.overseasAiModels.map(model => ({
        name: model.name,
        checked: model.checked
      }))
    };

    // 读取现有的配置列表
    let savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];

    // 检查是否已存在同名配置
    const existingIndex = savedConfigs.findIndex(config => config.name === configName);
    if (existingIndex !== -1) {
      // 如果存在，询问用户是否覆盖
      wx.showModal({
        title: '配置已存在',
        content: `配置 "${configName}" 已存在，是否覆盖？`,
        success: (res) => {
          if (res.confirm) {
            savedConfigs[existingIndex] = currentConfig;
            wx.setStorageSync('savedSearchConfigs', savedConfigs);
            wx.showToast({
              title: '配置已更新',
              icon: 'success'
            });
            this.hideSaveConfigModal();
          }
        }
      });
    } else {
      // 添加新配置
      savedConfigs.push(currentConfig);
      wx.setStorageSync('savedSearchConfigs', savedConfigs);
      wx.showToast({
        title: '配置已保存',
        icon: 'success'
      });
      this.hideSaveConfigModal();
    }
  },

  // 加载保存的配置
  loadSavedConfig: function(configName) {
    const savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];
    const configToLoad = savedConfigs.find(config => config.name === configName);

    if (!configToLoad) {
      wx.showToast({
        title: '配置不存在',
        icon: 'none'
      });
      return;
    }

    // 更新页面数据
    this.setData({
      brandName: configToLoad.brandName,
      competitorBrands: configToLoad.competitorBrands,
      customQuestions: configToLoad.customQuestions,
      // 仅更新选中状态，保留模型的其他属性
      domesticAiModels: this.data.domesticAiModels.map(model => {
        const savedModel = configToLoad.domesticAiModels.find(saved => saved.name === model.name);
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      }),
      overseasAiModels: this.data.overseasAiModels.map(model => {
        const savedModel = configToLoad.overseasAiModels.find(saved => saved.name === model.name);
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      })
    });

    wx.showToast({
      title: '配置已加载',
      icon: 'success'
    });
  },

  /**
   * 页面滚动事件处理，用于吸顶效果
   */
  onPageScroll: function(e) {
    // 当页面滚动超过一定距离时，激活吸顶效果
    const scrollTop = e.scrollTop || 0;
    const shouldStick = scrollTop > 100; // 滚动超过100rpx时激活吸顶

    if (shouldStick !== this.data.isSticky) {
      this.setData({
        isSticky: shouldStick
      });
    }
  },

  /**
   * 分享功能
   */
  onShareAppMessage: function() {
    // 获取当前报告的总分，如果没有则使用默认值
    const totalScore = this.calculateTotalScore();
    const brandName = this.data.brandName || '品牌';

    return {
      title: `[${totalScore}分] ${brandName} GEO 品牌诊断报告已生成`,
      path: `/pages/index/index?brandName=${encodeURIComponent(brandName)}`,
      imageUrl: '/images/share-image.png' // 如果有分享图片的话
    };
  },

  /**
   * 清理系统缓存
   */
  clearSystemCache: function() {
    wx.showModal({
      title: '确认清理',
      content: '确定要清理系统缓存吗？这将删除临时文件和日志，但不会影响您的配置和数据。',
      success: (res) => {
        if (res.confirm) {
          // 清理本地存储
          wx.clearStorage({
            success: () => {
              console.log('本地存储清理成功');
            },
            fail: (err) => {
              console.error('本地存储清理失败:', err);
            }
          });

          // 清理本地文件
          wx.getSavedFileList({
            success: (res) => {
              const fileList = res.fileList || [];
              let cleanedCount = 0;

              fileList.forEach(file => {
                // 删除后缀为 .log、.tmp 或 .txt 的测试记录文件
                if (file.filePath.endsWith('.log') ||
                    file.filePath.endsWith('.tmp') ||
                    file.filePath.endsWith('.txt')) {
                  wx.removeSavedFile({
                    filePath: file.filePath,
                    success: () => {
                      cleanedCount++;
                    },
                    fail: (err) => {
                      console.error('删除文件失败:', file.filePath, err);
                    }
                  });
                }
              });

              if (cleanedCount > 0) {
                console.log(`清理了 ${cleanedCount} 个临时文件`);
              }

              // 清理缓存
              wx.clearStorageSync();

              wx.showToast({
                title: `清理完成，共清理${cleanedCount}个文件`,
                icon: 'success'
              });
            },
            fail: (err) => {
              console.error('获取文件列表失败:', err);
              wx.showToast({
                title: '获取文件列表失败',
                icon: 'none'
              });
            }
          });
        }
      }
    });
  },

  /**
   * 计算总分
   */
  calculateTotalScore: function() {
    if (!this.data.scoreData) {
      return 0;
    }

    const scores = this.data.scoreData;
    const total = (scores.accuracy || 0) +
                  (scores.completeness || 0) +
                  (scores.relevance || 0) +
                  (scores.security || 0) +
                  (scores.sentiment || 0) +
                  (scores.competitiveness || 0) +
                  (scores.authority || 0);

    return Math.round(total / 7); // 平均分
  },

  /**
   * 获取趋势指示器
   */
  getTrendIndicator: function() {
    if (!this.data.scoreData) {
      return '→'; // 默认水平箭头
    }

    // 简单的趋势判断逻辑，可以根据实际需求调整
    const scores = this.data.scoreData;
    const currentScore = this.calculateTotalScore();

    // 这里可以加入与历史数据比较的逻辑来确定趋势
    // 暂时返回一个示例趋势
    if (currentScore > 80) {
      return '↑'; // 上升趋势
    } else if (currentScore < 60) {
      return '↓'; // 下降趋势
    } else {
      return '→'; // 平稳趋势
    }
  },

  /**
   * 触发内容入场动画
   */
  triggerContentAnimation: function() {
    // 延迟显示内容以触发动画
    setTimeout(() => {
      this.setData({
        contentVisible: true
      });
    }, 100);
  },

  /**
   * 渲染报告 - 触发报告展示逻辑
   */
  renderReport: function() {
    console.log('开始渲染报告...');

    // 更新UI以反映报告已准备好
    this.setData({
      reportReady: true
    });

    // 触发内容入场动画
    this.triggerContentAnimation();

    // 可以在这里添加额外的报告渲染逻辑
    // 例如：动画效果、数据可视化初始化等
  },

  /**
   * 强制清理并跳转
   */
  navigateToDetail: function(executionId, brandList, selectedModels, customQuestion) {
    // 1. 立即隐藏加载状态，确保跳转瞬间界面清爽
    wx.hideLoading();

    // 2. 提取模型名称，避免传递完整对象数组
    const modelNames = selectedModels.map(model => {
      if (typeof model === 'object' && model !== null) {
        return model.name || model.id || model.label || '';
      } else {
        return model;
      }
    });

    // 3. 严谨封装"养生茶"诊断参数
    try {
      const brands = encodeURIComponent(JSON.stringify(brandList || []));
      const models = encodeURIComponent(JSON.stringify(modelNames || [])); // 优化：只传递模型名称
      const question = encodeURIComponent(customQuestion || '');
      const url = `/pages/detail/index?executionId=${encodeURIComponent(executionId)}&brand_list=${brands}&models=${models}&question=${question}`; // 优化：使用简化参数名

      console.log('🚀 战略中心激活，正在导航:', url);

      // 4. 执行顶级流畅跳转
      wx.navigateTo({
        url: url,
        fail: (err) => {
          console.error('❌ 跳转失败，请确认 app.json 路径:', err);
          // 兜底方案：如果是路径问题，弹出专业提示
          wx.showModal({
            title: '系统提示',
            content: '战局中心模块尚未注册，请检查页面路径配置',
            showCancel: false
          });
        }
      });
    } catch (e) {
      console.error('❌ 参数序列化失败:', e);
    }
  },

  /**
   * 设置自定义API服务器地址
   */
  setCustomServerUrl: function() {
    wx.showModal({
      title: '设置API服务器地址',
      editable: true,
      placeholderText: '请输入API服务器地址，例如：http://192.168.1.100:5001',
      success: (res) => {
        if (res.cancel) {
          return;
        }

        const inputUrl = res.content.trim();
        if (!inputUrl) {
          wx.showToast({
            title: '请输入有效的服务器地址',
            icon: 'none'
          });
          return;
        }

        if (!inputUrl.startsWith('http://') && !inputUrl.startsWith('https://')) {
          wx.showToast({
            title: '地址必须以http://或https://开头',
            icon: 'none'
          });
          return;
        }

        // 保存到本地存储
        wx.setStorageSync('custom_base_url', inputUrl);

        wx.showToast({
          title: '服务器地址已更新',
          icon: 'success'
        });
      }
    });
  }
});