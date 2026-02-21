/**
 * ECharts for WeChat Mini Program
 * 简化版 ECharts 封装（生产环境请使用完整的 echarts-for-weixin 库）
 * 
 * 使用方式:
 * const echarts = require('../../lib/echarts');
 * const chart = echarts.init(canvas);
 * chart.setOption(option);
 */

class ECharts {
  constructor(canvas, theme, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.width = opts?.width || 300;
    this.height = opts?.height || 400;
    this.option = null;
    this.dpr = opts?.devicePixelRatio || 1;
  }

  setOption(option, notMerge = false) {
    this.option = option;
    this.render();
  }

  render() {
    if (!this.option || !this.ctx) return;

    const ctx = this.ctx;
    const option = this.option;

    // 清空画布
    ctx.clearRect(0, 0, this.width * this.dpr, this.height * this.dpr);

    // 绘制背景
    if (option.backgroundColor) {
      ctx.fillStyle = option.backgroundColor;
      ctx.fillRect(0, 0, this.width, this.height);
    }

    // 根据类型绘制图表
    if (option.series) {
      option.series.forEach(series => {
        this.renderSeries(series);
      });
    }
  }

  renderSeries(series) {
    const ctx = this.ctx;
    const type = series.type;

    if (type === 'line') {
      this.renderLineChart(series);
    } else if (type === 'bar') {
      this.renderBarChart(series);
    } else if (type === 'pie') {
      this.renderPieChart(series);
    }
  }

  renderLineChart(series) {
    const ctx = this.ctx;
    const data = series.data || [];
    const padding = { top: 40, right: 20, bottom: 40, left: 50 };
    const chartWidth = this.width - padding.left - padding.right;
    const chartHeight = this.height - padding.top - padding.bottom;

    // 计算最大值
    const maxValue = Math.max(...data.map(d => typeof d === 'object' ? d.value : d), 1);

    // 绘制坐标轴
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, this.height - padding.bottom);
    ctx.lineTo(this.width - padding.right, this.height - padding.bottom);
    ctx.stroke();

    // 绘制折线
    ctx.strokeStyle = series.itemStyle?.color || '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((item, index) => {
      const value = typeof item === 'object' ? item.value : item;
      const x = padding.left + (index / (data.length - 1)) * chartWidth;
      const y = padding.top + chartHeight - (value / maxValue) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // 绘制数据点
    data.forEach((item, index) => {
      const value = typeof item === 'object' ? item.value : item;
      const x = padding.left + (index / (data.length - 1)) * chartWidth;
      const y = padding.top + chartHeight - (value / maxValue) * chartHeight;

      ctx.fillStyle = series.itemStyle?.color || '#667eea';
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  renderBarChart(series) {
    const ctx = this.ctx;
    const data = series.data || [];
    const padding = { top: 40, right: 20, bottom: 40, left: 50 };
    const chartWidth = this.width - padding.left - padding.right;
    const chartHeight = this.height - padding.top - padding.bottom;
    const barWidth = chartWidth / data.length * 0.6;

    // 计算最大值
    const maxValue = Math.max(...data.map(d => typeof d === 'object' ? d.value : d), 1);

    // 绘制坐标轴
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, this.height - padding.bottom);
    ctx.lineTo(this.width - padding.right, this.height - padding.bottom);
    ctx.stroke();

    // 绘制柱状图
    data.forEach((item, index) => {
      const value = typeof item === 'object' ? item.value : item;
      const x = padding.left + index * (chartWidth / data.length) + (chartWidth / data.length - barWidth) / 2;
      const barHeight = (value / maxValue) * chartHeight;
      const y = this.height - padding.bottom - barHeight;

      // 渐变背景
      const gradient = ctx.createLinearGradient(0, y, 0, this.height - padding.bottom);
      gradient.addColorStop(0, series.itemStyle?.color || '#667eea');
      gradient.addColorStop(1, series.itemStyle?.color ? this.lightenColor(series.itemStyle.color, 40) : '#a0b4ff');

      ctx.fillStyle = gradient;
      ctx.fillRect(x, y, barWidth, barHeight);
    });
  }

  renderPieChart(series) {
    const ctx = this.ctx;
    const data = series.data || [];
    const centerX = this.width / 2;
    const centerY = this.height / 2;
    const radius = Math.min(centerX, centerY) - 40;

    let startAngle = -Math.PI / 2;

    // 计算总和
    const total = data.reduce((sum, item) => sum + (typeof item === 'object' ? item.value : item), 0);

    // 绘制扇形
    data.forEach(item => {
      const value = typeof item === 'object' ? item.value : item;
      const angle = (value / total) * Math.PI * 2;
      const endAngle = startAngle + angle;

      ctx.fillStyle = item.itemStyle?.color || this.getColorByIndex(data.indexOf(item));
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.closePath();
      ctx.fill();

      startAngle = endAngle;
    });
  }

  getColorByIndex(index) {
    const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'];
    return colors[index % colors.length];
  }

  lightenColor(color, percent) {
    // 简化版颜色变亮
    return color;
  }

  dispose() {
    this.ctx = null;
    this.option = null;
  }

  on(eventName, handler) {
    // 事件处理（简化版）
    console.log(`Event listener for '${eventName}' added.`);
  }
}

function init(canvas, theme, opts) {
  return new ECharts(canvas, theme, opts);
}

module.exports = {
  init,
  version: '5.0.0-mini'
};
