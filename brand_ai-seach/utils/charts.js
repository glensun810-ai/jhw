/**
 * 基础图表工具函数
 * 
 * 功能：
 * - 通用图表配置
 * - 颜色工具
 * - 数据格式化
 */

// ECharts 延迟加载
let echarts = null;

/**
 * 获取 ECharts 实例
 */
function getECharts() {
  if (!echarts) {
    try {
      echarts = require('../components/ec-canvas/echarts');
    } catch (e) {
      console.warn('ECharts 加载失败:', e);
    }
  }
  return echarts;
}

/**
 * Hex 颜色转 RGBA
 */
function hexToRgba(hex, alpha = 1) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * 获取默认颜色主题
 */
function getDefaultColors() {
  return {
    primary: '#667eea',
    success: '#52c41a',
    warning: '#fa8c16',
    error: '#ff4d4f',
    info: '#1890ff'
  };
}

/**
 * 生成渐变配置
 */
function createGradient(color, startAlpha = 0.3, endAlpha = 0.05) {
  const echarts = getECharts();
  if (!echarts) return null;

  return {
    type: 'linear',
    x: 0,
    y: 0,
    x2: 0,
    y2: 1,
    colorStops: [
      { offset: 0, color: hexToRgba(color, startAlpha) },
      { offset: 1, color: hexToRgba(color, endAlpha) }
    ]
  };
}

/**
 * 格式化数据
 */
function formatData(data, formatter) {
  if (!Array.isArray(data)) return [];
  return data.map(item => {
    if (typeof formatter === 'function') {
      return formatter(item);
    }
    return item;
  });
}

/**
 * 获取默认网格配置
 */
function getDefaultGrid() {
  return {
    left: '10%',
    right: '5%',
    top: '15%',
    bottom: '10%',
    containLabel: true
  };
}

/**
 * 获取默认 Tooltip 配置
 */
function getDefaultTooltip() {
  return {
    trigger: 'axis',
    formatter: '{b}: {c}'
  };
}

/**
 * 获取默认 Axis 配置
 */
function getDefaultAxis(type = 'category') {
  return {
    type,
    axisLabel: {
      fontSize: 10,
      color: '#666'
    },
    axisLine: {
      lineStyle: {
        color: '#e0e0e0'
      }
    }
  };
}

module.exports = {
  getECharts,
  hexToRgba,
  getDefaultColors,
  createGradient,
  formatData,
  getDefaultGrid,
  getDefaultTooltip,
  getDefaultAxis
};
