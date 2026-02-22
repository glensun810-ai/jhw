/**
 * 趋势图工具函数
 * 
 * 功能：
 * - 折线图配置生成
 * - 柱状图配置生成
 * - 数据格式化
 * - 空状态处理
 */

const { getECharts, hexToRgba, createGradient, getDefaultColors } = require('./charts');

/**
 * 生成折线图配置
 * @param {Object} params - 参数
 * @param {Array} params.data - 数据数组
 * @param {Array} params.categories - 分类标签
 * @param {String} params.title - 标题
 * @param {String} params.color - 颜色
 * @param {Boolean} params.showArea - 是否显示面积
 */
function getLineChartConfig({ data, categories, title = '', color = '#667eea', showArea = true }) {
  const echarts = getECharts();
  if (!echarts) return null;

  const series = [{
    type: 'line',
    data: data || [],
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: {
      color: color
    },
    lineStyle: {
      width: 2,
      color: color
    }
  }];

  // 添加面积
  if (showArea) {
    series[0].areaStyle = {
      color: createGradient(color)
    };
  }

  return {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 14,
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c}'
    },
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories || [],
      axisLabel: {
        fontSize: 10,
        color: '#666'
      },
      axisLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0'
        }
      }
    },
    series
  };
}

/**
 * 生成柱状图配置
 * @param {Object} params - 参数
 * @param {Array} params.data - 数据数组
 * @param {Array} params.categories - 分类标签
 * @param {String} params.title - 标题
 * @param {String} params.color - 颜色
 */
function getBarChartConfig({ data, categories, title = '', color = '#667eea' }) {
  const echarts = getECharts();
  if (!echarts) return null;

  return {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 14,
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c}'
    },
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories || [],
      axisLabel: {
        fontSize: 10,
        color: '#666'
      },
      axisLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0'
        }
      }
    },
    series: [{
      type: 'bar',
      data: data || [],
      itemStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: hexToRgba(color, 1) },
            { offset: 1, color: hexToRgba(color, 0.6) }
          ]
        }
      },
      barWidth: '40%'
    }]
  };
}

/**
 * 生成趋势图配置（带预测）
 * @param {Object} params - 参数
 * @param {Array} params.dates - 日期数组
 * @param {Array} params.values - 实际值数组
 * @param {Array} params.predictions - 预测值数组
 * @param {String} params.title - 标题
 */
function getTrendChartConfig({ dates, values, predictions, title = '' }) {
  const echarts = getECharts();
  if (!echarts) return null;

  const colors = getDefaultColors();

  const series = [
    {
      name: '实际值',
      type: 'line',
      data: values || [],
      smooth: true,
      lineStyle: {
        color: colors.primary,
        width: 3
      },
      itemStyle: {
        color: colors.primary
      },
      areaStyle: {
        color: createGradient(colors.primary)
      }
    }
  ];

  // 添加预测数据
  if (predictions && predictions.length > 0) {
    series.push({
      name: '预测值',
      type: 'line',
      data: predictions,
      smooth: true,
      lineStyle: {
        color: colors.success,
        width: 3,
        type: 'dashed'
      },
      itemStyle: {
        color: colors.success
      }
    });
  }

  return {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 14,
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['实际值', '预测值'].filter((_, i) => i === 0 || predictions?.length > 0),
      bottom: '10%'
    },
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates || [],
      axisLabel: {
        rotate: 45,
        interval: 0,
        fontSize: 10,
        color: '#666'
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}'
      }
    },
    series
  };
}

/**
 * 生成空图表配置
 */
function getEmptyChartConfig(message = '暂无数据') {
  return {
    title: {
      text: message,
      left: 'center',
      top: 'center',
      textStyle: {
        color: '#8c8c8c',
        fontSize: 16
      }
    },
    backgroundColor: 'transparent'
  };
}

/**
 * 格式化趋势数据
 */
function formatTrendData(data) {
  if (!data) {
    return { dates: [], values: [], predictions: [] };
  }

  return {
    dates: data.dates || [],
    values: data.values || [],
    predictions: data.predictions || []
  };
}

module.exports = {
  getLineChartConfig,
  getBarChartConfig,
  getTrendChartConfig,
  getEmptyChartConfig,
  formatTrendData
};
