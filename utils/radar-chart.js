/**
 * 雷达图绘制工具
 * 使用 Canvas 2D API 绘制雷达图
 * 
 * 版本：v2.0
 * 日期：2026-02-21
 */

class RadarChart {
  constructor(canvas, ctx, config = {}) {
    this.canvas = canvas;
    this.ctx = ctx;
    this.config = {
      width: config.width || 400,
      height: config.height || 400,
      centerX: config.centerX || 200,
      centerY: config.centerY || 200,
      radius: config.radius || 150,
      levels: config.levels || 5,  // 网格层数
      scaleMax: config.scaleMax || 100,
      colors: {
        grid: '#e2e8f0',
        text: '#64748b',
        axis: '#cbd5e1'
      },
      ...config
    };
    
    this.data = config.data || null;
  }

  /**
   * 设置数据并绘制
   */
  setData(data) {
    this.data = data;
    this.draw();
  }

  /**
   * 绘制雷达图
   */
  draw() {
    if (!this.data) {
      console.warn('[RadarChart] No data to draw');
      return;
    }

    const { ctx, config } = this;
    const { width, height, centerX, centerY, radius, levels, scaleMax, colors } = config;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 绘制背景网格
    this._drawGrid(centerX, centerY, radius, levels, scaleMax, colors);

    // 绘制轴线
    this._drawAxes(centerX, centerY, radius, this.data.dimensions, colors);

    // 绘制数据区域
    if (this.data.datasets) {
      this.data.datasets.forEach((dataset, index) => {
        this._drawDataset(dataset, centerX, centerY, radius, this.data.dimensions, index);
      });
    }

    // 绘制数据点标签
    if (this.data.dimensions) {
      this._drawDimensionLabels(centerX, centerY, radius, this.data.dimensions);
    }
  }

  /**
   * 绘制背景网格
   */
  _drawGrid(centerX, centerY, radius, levels, scaleMax, colors) {
    const { ctx } = this;

    for (let i = 0; i < levels; i++) {
      const levelRadius = (radius / levels) * (i + 1);
      const angleStep = (Math.PI * 2) / (this.data.dimensions?.length || 5);

      ctx.beginPath();
      ctx.strokeStyle = colors.grid;
      ctx.lineWidth = 1;

      for (let j = 0; j <= (this.data.dimensions?.length || 5); j++) {
        const angle = j * angleStep - Math.PI / 2;
        const x = centerX + Math.cos(angle) * levelRadius;
        const y = centerY + Math.sin(angle) * levelRadius;

        if (j === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.closePath();
      ctx.stroke();

      // 绘制刻度值
      const value = Math.round((scaleMax / levels) * (i + 1));
      ctx.fillStyle = colors.text;
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(
        value.toString(),
        centerX + 4,
        centerY - levelRadius + 4
      );
    }
  }

  /**
   * 绘制轴线
   */
  _drawAxes(centerX, centerY, radius, dimensions, colors) {
    const { ctx } = this;
    const dimensionCount = dimensions?.length || 5;
    const angleStep = (Math.PI * 2) / dimensionCount;

    for (let i = 0; i < dimensionCount; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;

      ctx.beginPath();
      ctx.strokeStyle = colors.axis;
      ctx.lineWidth = 1;
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.stroke();
    }
  }

  /**
   * 绘制数据集
   */
  _drawDataset(dataset, centerX, centerY, radius, dimensions, index) {
    const { ctx } = this;
    const dimensionCount = dimensions?.length || 5;
    const angleStep = (Math.PI * 2) / dimensionCount;
    const data = dataset.data || [];

    // 计算数据点坐标
    const points = [];
    for (let i = 0; i < dimensionCount; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const value = data[i] || 0;
      const pointRadius = (value / 100) * radius;
      
      points.push({
        x: centerX + Math.cos(angle) * pointRadius,
        y: centerY + Math.sin(angle) * pointRadius
      });
    }

    // 绘制填充区域
    ctx.beginPath();
    ctx.fillStyle = dataset.backgroundColor || 'rgba(15, 52, 96, 0.2)';
    
    points.forEach((point, i) => {
      if (i === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    
    ctx.closePath();
    ctx.fill();

    // 绘制边框
    ctx.beginPath();
    ctx.strokeStyle = dataset.borderColor || '#0f3460';
    ctx.lineWidth = 2;
    
    points.forEach((point, i) => {
      if (i === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    
    ctx.closePath();
    ctx.stroke();

    // 绘制数据点
    points.forEach((point, i) => {
      ctx.beginPath();
      ctx.fillStyle = dataset.borderColor || '#0f3460';
      ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  /**
   * 绘制维度标签
   */
  _drawDimensionLabels(centerX, centerY, radius, dimensions) {
    const { ctx } = this;
    const dimensionCount = dimensions.length;
    const angleStep = (Math.PI * 2) / dimensionCount;
    const labelRadius = radius + 30;

    for (let i = 0; i < dimensionCount; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * labelRadius;
      const y = centerY + Math.sin(angle) * labelRadius;

      ctx.fillStyle = '#1a1a2e';
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      const dimension = dimensions[i];
      const label = typeof dimension === 'string' ? dimension : dimension.label;
      
      ctx.fillText(label, x, y);
    }
  }
}

/**
 * 创建雷达图实例
 */
function createRadarChart(canvasId, data, config = {}) {
  return new Promise((resolve, reject) => {
    const query = wx.createSelectorQuery();
    
    query.select(`#${canvasId}`)
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0]) {
          reject(new Error('Canvas not found'));
          return;
        }

        const { node, width, height } = res[0];
        const ctx = node.getContext('2d');
        
        // 设置 canvas 尺寸
        const dpr = wx.getSystemInfoSync().pixelRatio;
        node.width = width * dpr;
        node.height = height * dpr;
        ctx.scale(dpr, dpr);

        // 创建雷达图实例
        const radarChart = new RadarChart(node, ctx, {
          ...config,
          width,
          height,
          centerX: width / 2,
          centerY: height / 2,
          radius: Math.min(width, height) / 2 - 40,
          data
        });

        // 绘制
        radarChart.draw();

        resolve(radarChart);
      });
  });
}

module.exports = {
  RadarChart,
  createRadarChart
};
