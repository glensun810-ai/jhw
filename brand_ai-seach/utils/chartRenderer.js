/**
 * 图表渲染工具
 * 负责 ECharts 图表的渲染、重试、清理
 */

/**
 * 渲染雷达图（带重试机制）
 * @param {Object} pageContext - 页面上下文（this）
 * @param {number} retryCount - 当前重试次数
 * @returns {Promise}
 */
const renderRadarChart = (pageContext, retryCount = 0) => {
  return new Promise((resolve, reject) => {
    try {
      const query = wx.createSelectorQuery();

      query.select('#radarCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          // 节点未找到，重试
          if (!res[0] || !res[0].node) {
            console.error('[Chart] 雷达图 Canvas 未找到');

            if (retryCount < 3) {
              console.log(`[Chart] 重试 ${retryCount + 1}/3`);
              setTimeout(() => {
                renderRadarChart(pageContext, retryCount + 1)
                  .then(resolve)
                  .catch(reject);
              }, 300);
              return;
            }

            reject(new Error('Canvas 节点未找到'));
            return;
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;

          // 设置 Canvas 尺寸
          canvas.width = res[0].width * dpr;
          canvas.height = res[0].height * dpr;
          ctx.scale(dpr, dpr);

          // 初始化 ECharts
          const chart = echarts.init(canvas, null, {
            renderer: 'canvas',
            devicePixelRatio: dpr
          });

          // 配置项
          const radarData = pageContext.data.radarChartData || [];
          const indicator = radarData.map(item => ({
            name: item.name,
            max: item.max || 100
          }));

          const option = {
            radar: {
              indicator: indicator,
              radius: '65%'
            },
            series: [{
              type: 'radar',
              data: [{
                value: radarData.map(item => item.value),
                name: pageContext.data.targetBrand || '品牌'
              }]
            }]
          };

          chart.setOption(option);

          // 保存实例
          pageContext.setData({ radarChartInstance: chart });

          console.log('[Chart] 雷达图渲染成功');
          resolve(chart);
        });
    } catch (error) {
      console.error('[Chart] 雷达图渲染失败:', error);
      reject(error);
    }
  });
};

/**
 * 渲染词云图（带重试机制）
 * @param {Object} pageContext - 页面上下文（this）
 * @param {number} retryCount - 当前重试次数
 * @returns {Promise}
 */
const renderWordCloud = (pageContext, retryCount = 0) => {
  return new Promise((resolve, reject) => {
    try {
      const query = wx.createSelectorQuery();

      query.select('#wordCloudCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          // 节点未找到，重试
          if (!res[0] || !res[0].node) {
            console.error('[Chart] 词云 Canvas 未找到');

            if (retryCount < 3) {
              console.log(`[Chart] 重试 ${retryCount + 1}/3`);
              setTimeout(() => {
                renderWordCloud(pageContext, retryCount + 1)
                  .then(resolve)
                  .catch(reject);
              }, 300);
              return;
            }

            reject(new Error('Canvas 节点未找到'));
            return;
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;

          canvas.width = res[0].width * dpr;
          canvas.height = res[0].height * dpr;
          ctx.scale(dpr, dpr);

          const chart = echarts.init(canvas, null, {
            renderer: 'canvas',
            devicePixelRatio: dpr
          });

          // 词云配置
          const keywordCloudData = pageContext.data.keywordCloudData || [];

          const option = {
            series: [{
              type: 'wordCloud',
              shape: 'circle',
              left: 'center',
              top: 'center',
              width: '70%',
              height: '80%',
              data: keywordCloudData.map(item => ({
                name: item.word,
                value: item.count,
                textStyle: {
                  color: getSentimentColor(item.sentiment)
                }
              }))
            }]
          };

          chart.setOption(option);
          pageContext.setData({ wordCloudInstance: chart });

          console.log('[Chart] 词云渲染成功');
          resolve(chart);
        });
    } catch (error) {
      console.error('[Chart] 词云渲染失败:', error);
      reject(error);
    }
  });
};

/**
 * 获取情感颜色
 * @param {string} sentiment - 情感类型
 * @returns {string} 颜色值
 */
const getSentimentColor = (sentiment) => {
  switch (sentiment) {
    case 'positive': return '#52c41a';
    case 'negative': return '#ff4d4f';
    default: return '#1890ff';
  }
};

/**
 * 渲染所有图表
 * @param {Object} pageContext - 页面上下文
 * @returns {Promise}
 */
const renderAllCharts = (pageContext) => {
  console.log('[Chart] 开始渲染所有图表');

  return Promise.all([
    renderRadarChart(pageContext),
    renderWordCloud(pageContext)
  ]).then(() => {
    pageContext.setData({ chartsReady: true });
    console.log('[Chart] 所有图表渲染完成');
  }).catch(error => {
    console.error('[Chart] 图表渲染失败:', error);
    throw error;
  });
};

/**
 * 清理图表实例
 * @param {Object} pageContext - 页面上下文
 */
const disposeCharts = (pageContext) => {
  if (pageContext.data.radarChartInstance) {
    pageContext.data.radarChartInstance.dispose();
  }
  if (pageContext.data.wordCloudInstance) {
    pageContext.data.wordCloudInstance.dispose();
  }
  console.log('[Chart] 图表实例已清理');
};

module.exports = {
  renderRadarChart,
  renderWordCloud,
  renderAllCharts,
  disposeCharts,
  getSentimentColor
};
