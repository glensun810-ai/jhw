/**
 * 图表工具函数
 * 提供常用图表配置生成函数
 */

// 防御性导入 ECharts - 使用相对路径
let echarts = null;
try {
  echarts = require('../components/ec-canvas/echarts');
} catch (e) {
  console.warn('ECharts 加载失败，图表功能将不可用:', e);
}

/**
 * 生成折线图配置
 * @param {Object} params - 参数
 * @param {Array} params.data - 数据数组
 * @param {Array} params.categories - 分类标签
 * @param {String} params.title - 标题
 * @param {String} params.color - 颜色
 */
function getLineChartConfig({ data, categories, title = '', color = '#667eea' }) {
  // 防御性检查
  if (!echarts) {
    console.warn('ECharts 未加载，返回空配置');
    return null;
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
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: {
        color: color
      },
      lineStyle: {
        width: 2,
        color: color
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: hexToRgba(color, 0.3) },
            { offset: 1, color: hexToRgba(color, 0.05) }
          ]
        }
      }
    }]
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
        color: '#666',
        rotate: categories && categories.length > 5 ? 45 : 0
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
      data: data,
      barWidth: '60%',
      itemStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: color },
            { offset: 1, color: hexToRgba(color, 0.5) }
          ]
        },
        borderRadius: [4, 4, 0, 0]
      }
    }]
  };
}

/**
 * 生成饼图配置
 * @param {Object} params - 参数
 * @param {Array} params.data - 数据数组 [{name, value}]
 * @param {String} params.title - 标题
 */
function getPieChartConfig({ data, title = '' }) {
  // 防御性检查
  if (!echarts) {
    console.warn('ECharts 未加载，返回空配置');
    return null;
  }
  
  const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'];

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
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      data: data.map(item => item.name),
      textStyle: {
        fontSize: 10,
        color: '#666'
      }
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      data: data.map((item, index) => ({
        name: item.name,
        value: item.value,
        itemStyle: {
          color: colors[index % colors.length]
        }
      }))
    }]
  };
}

/**
 * 生成雷达图配置
 * @param {Object} params - 参数
 * @param {Array} params.indicators - 指示器数组 [{name, max}]
 * @param {Array} params.data - 数据数组
 * @param {String} params.title - 标题
 */
function getRadarChartConfig({ indicators, data, title = '' }) {
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
    radar: {
      indicator: indicators,
      center: ['50%', '55%'],
      radius: '65%',
      axisName: {
        color: '#666',
        fontSize: 10
      },
      splitLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      },
      splitArea: {
        show: false
      }
    },
    series: [{
      type: 'radar',
      data: data,
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: {
        color: '#667eea'
      },
      lineStyle: {
        width: 2,
        color: '#667eea'
      },
      areaStyle: {
        color: hexToRgba('#667eea', 0.3)
      }
    }]
  };
}

/**
 * HEX 颜色转 RGBA
 */
function hexToRgba(hex, alpha = 1) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

module.exports = {
  getLineChartConfig,
  getBarChartConfig,
  getPieChartConfig,
  getRadarChartConfig,
  hexToRgba,
  echarts
};
