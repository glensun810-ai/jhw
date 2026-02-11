Component({
  properties: {
    myBrandData: {
      type: Object,
      value: null
    },
    competitorData: {
      type: Object,
      value: null
    },
    isPremium: {
      type: Boolean,
      value: false
    }
  },

  data: {
    myBrand: {},
    competitor: {},
    radarChartOption: null,
    metricsDelta: []
  },

  observers: {
    'myBrandData, competitorData': function(myBrandData, competitorData) {
      if (myBrandData && competitorData) {
        this.processData();
      }
    }
  },

  methods: {
    processData() {
      const myBrand = {
        name: this.properties.myBrandData.brand,
        score: this.properties.myBrandData.overallScore,
        isWinner: this.properties.myBrandData.overallScore >= this.properties.competitorData.overallScore,
        scores: [
          this.properties.myBrandData.overallAuthority,
          this.properties.myBrandData.overallVisibility,
          this.properties.myBrandData.overallSentiment,
          this.properties.myBrandData.overallPurity,
          this.properties.myBrandData.overallConsistency
        ]
      };

      const competitor = {
        name: this.properties.competitorData.brand,
        score: this.properties.competitorData.overallScore,
        isWinner: this.properties.competitorData.overallScore > this.properties.myBrandData.overallScore,
        scores: [
          this.properties.competitorData.overallAuthority,
          this.properties.competitorData.overallVisibility,
          this.properties.competitorData.overallSentiment,
          this.properties.competitorData.overallPurity,
          this.properties.competitorData.overallConsistency
        ]
      };

      const metricsDelta = [
        { name: '权威度', myScore: myBrand.scores[0], compScore: competitor.scores[0] },
        { name: '可见度', myScore: myBrand.scores[1], compScore: competitor.scores[1] },
        { name: '好感度', myScore: myBrand.scores[2], compScore: competitor.scores[2] },
        { name: '纯净度', myScore: myBrand.scores[3], compScore: competitor.scores[3] },
        { name: '一致性', myScore: myBrand.scores[4], compScore: competitor.scores[4] },
      ].map(item => {
        const total = item.myScore + item.compScore;
        return {
          ...item,
          delta: Math.round(item.myScore - item.compScore),
          myBrandPercentage: total > 0 ? (item.myScore / total) * 100 : 50,
          competitorPercentage: total > 0 ? (item.compScore / total) * 100 : 50,
        }
      });

      const radarChartOption = this.generateRadarChartOption(myBrand, competitor);

      this.setData({
        myBrand,
        competitor,
        metricsDelta,
        radarChartOption
      });
    },

    generateRadarChartOption(myBrand, competitor) {
      return {
        backgroundColor: 'transparent',
        color: ['#00F5A0', '#00A9FF'],
        legend: {
          data: [myBrand.name, competitor.name],
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
          type: 'radar',
          data: [
            { value: myBrand.scores, name: myBrand.name, areaStyle: { color: 'rgba(0, 245, 160, 0.4)' } },
            { value: competitor.scores, name: competitor.name, areaStyle: { color: 'rgba(0, 169, 255, 0.4)' } }
          ]
        }]
      };
    },

    onUnlockTap() {
      wx.showModal({
        title: '解锁专业版',
        content: '升级到专业版，查看详细的竞品拦截路径和深度指标分析。',
        confirmText: '立即升级',
        success: (res) => {
          if (res.confirm) {
            wx.showToast({ title: '正在跳转支付...', icon: 'loading' });
          }
        }
      });
    }
  }
});