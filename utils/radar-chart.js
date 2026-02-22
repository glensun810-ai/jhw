/**
 * 雷达图工具函数
 * 
 * 功能：
 * - 雷达图配置生成
 * - 数据格式化
 * - 空状态处理
 */

const { getECharts, hexToRgba, createGradient, getDefaultColors } = require('./charts');

/**
 * 生成雷达图配置
 * @param {Object} params - 参数
 * @param {Array} params.indicators - 指标数组 [{name, max}]
 * @param {Array} params.series - 系列数据 [{name, value, color}]
 * @param {String} params.title - 标题
 */
function getRadarChartConfig({ indicators, series, title = '' }) {
  const echarts = getECharts();
  if (!echarts) return null;

  const colors = getDefaultColors();

  // 格式化指标
  const formattedIndicators = (indicators || []).map(item => ({
    name: item.name,
    max: item.max || 100
  }));

  // 格式化系列
  const formattedSeries = (series || []).map(item => ({
    name: item.name,
    value: item.value,
    areaStyle: {
      color: createGradient(item.color || colors.primary)
    },
    lineStyle: {
      width: 2,
      color: item.color || colors.primary
    },
    itemStyle: {
      color: item.color || colors.primary
    }
  }));

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
      trigger: 'item'
    },
    legend: {
      data: series?.map(s => s.name) || [],
      bottom: '10%'
    },
    radar: {
      indicator: formattedIndicators,
      radius: '65%',
      center: ['50%', '45%'],
      axisName: {
        fontSize: 11,
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['#f8f8f8', '#fff']
        }
      }
    },
    series: [{
      type: 'radar',
      data: formattedSeries,
      emphasis: {
        lineStyle: {
          width: 4
        }
      }
    }]
  };
}

/**
 * 生成空雷达图配置
 */
function getEmptyRadarChartConfig(message = '暂无数据') {
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
 * 格式化雷达图数据
 */
function formatRadarData(data) {
  if (!data || !Array.isArray(data)) {
    return { indicators: [], series: [] };
  }

  const indicators = data.map(item => ({
    name: item.name,
    max: item.max || 100
  }));

  const series = data.map(item => ({
    name: item.name,
    value: item.value || [],
    color: item.color
  }));

  return { indicators, series };
}

module.exports = {
  getRadarChartConfig,
  getEmptyRadarChartConfig,
  formatRadarData
};
