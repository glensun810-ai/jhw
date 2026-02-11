const serverUrl = 'http://127.0.0.1:5001';

Page({
  data: {
    isLoading: true,
    // 以下数据结构与 results 页面保持一致
    results: [],
    targetBrand: '',
    competitiveAnalysis: null,
    executiveSummary: {
      mainThreat: null,
      mainOpportunity: null,
    },
    scoreMatrix: [],
    matrixHeaders: [],
    activeTab: 'byPlatform',
    dataByPlatform: {},
    dataByBrand: {},
    problemList: [],
    radarChartOption: null
  },

  onLoad: function (options) {
    const recordId = options.id;
    if (recordId) {
      this.loadRecordDetail(recordId);
    } else {
      wx.showToast({ title: '缺少报告ID', icon: 'error' });
      setTimeout(() => { wx.navigateBack(); }, 1500);
    }
  },

  // 加载历史记录详情
  loadRecordDetail: function (recordId) {
    this.setData({ isLoading: true });
    wx.request({
      url: `${serverUrl}/api/test-record/${recordId}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success' && res.data.record) {
          const record = res.data.record;
          const detailedResults = record.detailed_results;
          const targetBrand = record.brand_name;
          const competitiveAnalysis = record.results_summary.competitiveAnalysis || {}; // 从summary中获取或构建

          // 重新构建 competitiveAnalysis.brandScores
          const brandScores = {};
          // 主品牌分数
          brandScores[targetBrand] = {
            overallScore: record.overall_score,
            overallAuthority: record.results_summary.overall_authority,
            overallVisibility: record.results_summary.overall_visibility,
            overallSentiment: record.results_summary.overall_sentiment,
            overallPurity: record.results_summary.overall_purity,
            overallConsistency: record.results_summary.overall_consistency,
            overallGrade: record.results_summary.overall_grade,
            overallSummary: record.results_summary.overall_summary,
          };
          // 竞品分数 (如果detailedResults中有其他品牌，需要从detailedResults中聚合)
          const allBrandsInResults = new Set(detailedResults.map(item => item.brand));
          allBrandsInResults.forEach(brand => {
            if (brand !== targetBrand) {
              const brandItems = detailedResults.filter(item => item.brand === brand);
              if (brandItems.length > 0) {
                // 简单聚合竞品分数，实际应调用ScoringEngine
                const avgAuthority = brandItems.reduce((sum, item) => sum + item.authority_score, 0) / brandItems.length;
                const avgVisibility = brandItems.reduce((sum, item) => sum + item.visibility_score, 0) / brandItems.length;
                const avgSentiment = brandItems.reduce((sum, item) => sum + item.sentiment_score, 0) / brandItems.length;
                const avgPurity = brandItems.reduce((sum, item) => sum + item.purity_score, 0) / brandItems.length;
                const avgConsistency = brandItems.reduce((sum, item) => sum + item.consistency_score, 0) / brandItems.length;
                const avgScore = brandItems.reduce((sum, item) => sum + item.score, 0) / brandItems.length;

                brandScores[brand] = {
                  overallScore: Math.round(avgScore),
                  overallAuthority: Math.round(avgAuthority),
                  overallVisibility: Math.round(avgVisibility),
                  overallSentiment: Math.round(avgSentiment),
                  overallPurity: Math.round(avgPurity),
                  overallConsistency: Math.round(avgConsistency),
                  overallGrade: this.calculateGrade(Math.round(avgScore)),
                  overallSummary: `AI对${brand}的平均认知`,
                };
              }
            }
          });
          competitiveAnalysis.brandScores = brandScores;


          // 调用 results 页面的数据处理逻辑
          this.processAndStructureData(detailedResults, targetBrand, competitiveAnalysis);
          this.setData({ isLoading: false });

        } else {
          this.setData({ isLoading: false });
          wx.showToast({ title: '加载报告失败', icon: 'error' });
          setTimeout(() => { wx.navigateBack(); }, 1500);
        }
      },
      fail: (err) => {
        this.setData({ isLoading: false });
        console.error('请求报告详情失败:', err);
        wx.showToast({ title: '网络请求失败', icon: 'error' });
        setTimeout(() => { wx.navigateBack(); }, 1500);
      }
    });
  },

  // 以下方法与 results 页面完全相同，直接复制
  // 核心数据处理与组织
  processAndStructureData: function(results, targetBrand, competitiveAnalysis) {
    const dataByPlatform = {};
    const dataByBrand = {};
    const problemList = [];
    const scoreMatrix = [];
    const matrixHeaders = new Set();

    results.forEach(item => {
      item.expanded = false;
      if (!dataByPlatform[item.aiModel]) { dataByPlatform[item.aiModel] = []; }
      dataByPlatform[item.aiModel].push(item);
      matrixHeaders.add(item.aiModel);

      if (!dataByBrand[item.brand]) { dataByBrand[item.brand] = []; }
      dataByBrand[item.brand].push(item);

      if (item.authority_score < 60 && item.visibility_score > 60) { problemList.push({ type: '语义偏移', item: item }); }
      if (item.sentiment_score < 50) { problemList.push({ type: '负面情感', item: item }); }
      if (item.purity_score < 70) { problemList.push({ type: '竞品干扰', item: item }); }
    });

    for (const brand in dataByBrand) {
      const brandRow = { brand: brand, scores: {} };
      dataByBrand[brand].forEach(item => {
        brandRow.scores[item.aiModel] = item.score;
      });
      scoreMatrix.push(brandRow);
    }
    
    let executiveSummary = { mainThreat: null, mainOpportunity: null };
    if (problemList.length > 0) {
      const firstProblem = problemList[0];
      executiveSummary.mainThreat = `在 ${firstProblem.item.aiModel} 上存在 ${firstProblem.type} 风险`;
    }
    if (competitiveAnalysis && competitiveAnalysis.brandScores && competitiveAnalysis.brandScores[targetBrand]) {
        const myScore = competitiveAnalysis.brandScores[targetBrand].overallScore;
        if (myScore > 75) {
            executiveSummary.mainOpportunity = `在全网平均分达到 ${myScore}，表现良好，可继续扩大优势`;
        }
    }

    const mainBrandScores = competitiveAnalysis.brandScores[targetBrand] || {};
    const radarOption = this.generateRadarChartOption(
      mainBrandScores.overallAuthority,
      mainBrandScores.overallVisibility,
      mainBrandScores.overallSentiment,
      mainBrandScores.overallPurity,
      mainBrandScores.overallConsistency,
      competitiveAnalysis,
      targetBrand
    );

    this.setData({
      results,
      targetBrand,
      competitiveAnalysis,
      dataByPlatform,
      dataByBrand,
      problemList,
      scoreMatrix,
      matrixHeaders: Array.from(matrixHeaders),
      executiveSummary,
      radarChartOption
    });
  },

  switchTab: function(e) {
    const tab = e.currentTarget.dataset.tab;
    if (tab !== this.data.activeTab) {
      this.setData({ activeTab: tab });
    }
  },

  toggleExpand: function(e) {
    const { type, platform, index } = e.currentTarget.dataset;
    let key;

    if (type === 'platform') {
      key = `dataByPlatform.${platform}[${index}].expanded`;
      this.setData({ [key]: !this.data.dataByPlatform[platform][index].expanded });
    } else if (type === 'brand') {
      const brand = e.currentTarget.dataset.brand;
      key = `dataByBrand.${brand}[${index}].expanded`;
      this.setData({ [key]: !this.data.dataByBrand[brand][index].expanded });
    } else if (type === 'problem') {
      key = `problemList[${index}].item.expanded`;
      this.setData({ [key]: !this.data.problemList[index].item.expanded });
    }
  },

  getHeatmapColor: function(score) {
    if (score === undefined || score === null) return 'rgba(255, 255, 255, 0.05)';
    if (score >= 85) return 'rgba(0, 245, 160, 0.8)';
    if (score >= 70) return 'rgba(0, 245, 160, 0.5)';
    if (score >= 50) return 'rgba(255, 140, 0, 0.6)';
    return 'rgba(255, 77, 79, 0.6)';
  },

  generateRadarChartOption: function(authority, visibility, sentiment, purity, consistency, competitiveAnalysis, targetBrand) {
    let benchmarkData = [60, 60, 60, 60, 60];
    let benchmarkName = '行业基准';

    if (competitiveAnalysis && competitiveAnalysis.brandScores) {
      let compScores = { authority: 0, visibility: 0, sentiment: 0, purity: 0, consistency: 0 };
      let count = 0;
      
      for (const [brand, scores] of Object.entries(competitiveAnalysis.brandScores)) {
        if (brand !== targetBrand) {
          compScores.authority += scores.overallAuthority || 0;
          compScores.visibility += scores.overallVisibility || 0;
          compScores.sentiment += scores.overallSentiment || 0;
          compScores.purity += scores.overallPurity || 0;
          compScores.consistency += scores.overallConsistency || 0;
          count++;
        }
      }
      
      if (count > 0) {
        benchmarkData = [
          Math.round(compScores.authority / count),
          Math.round(compScores.visibility / count),
          Math.round(compScores.sentiment / count),
          Math.round(compScores.purity / count),
          Math.round(compScores.consistency / count)
        ];
        benchmarkName = '竞品平均';
      }
    }

    return {
      backgroundColor: 'transparent',
      textStyle: { color: '#e8e8e8' },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(0,0,0,0.7)',
        borderColor: '#333',
        textStyle: { color: '#fff' }
      },
      legend: {
        data: ['本品牌', benchmarkName],
        bottom: 5,
        textStyle: { color: '#ccc' }
      },
      radar: {
        indicator: [
          { name: '权威度', max: 100 },
          { name: '可见度', max: 100 },
          { name: '好感度', max: 100 },
          { name: '纯净度', max: 100 },
          { name: '一致性', max: 100 }
        ],
        center: ['50%', '50%'],
        radius: '60%',
        name: { textStyle: { color: '#ccc', fontSize: 12 } },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } },
        splitArea: { show: false }
      },
      series: [{
        name: 'AI 生存指数对比',
        type: 'radar',
        data: [
          {
            value: [authority, visibility, sentiment, purity, consistency],
            name: '本品牌',
            itemStyle: { color: '#00F5A0' },
            areaStyle: { color: 'rgba(0, 245, 160, 0.4)' }
          },
          {
            value: benchmarkData,
            name: benchmarkName,
            itemStyle: { color: '#00A9FF' },
            areaStyle: { color: 'rgba(0, 169, 255, 0.4)' },
            lineStyle: { type: 'dashed' }
          }
        ]
      }]
    };
  },

  calculateGrade: function(score) {
    if (score >= 85) return 'A';
    if (score >= 70) return 'B';
    if (score >= 50) return 'C';
    return 'D';
  },

  goHome: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  generateReport: function() {
    wx.showToast({ title: '报告生成功能开发中', icon: 'none' });
  }
})