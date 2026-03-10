# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r') as f:
    content = f.read()

# Find the position to insert (before processRecommendationData function)
insert_marker = "  /**\n   * P1-3 修复：处理优化建议数据\n   */\n  processRecommendationData: function(competitiveAnalysis, results) {"
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the radar chart functions
radar_functions = '''  /**
   * P2-2 修复：准备雷达图数据
   */
  prepareRadarChartData: function(competitiveAnalysis, targetBrand, competitorBrands) {
    try {
      if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
        return [];
      }
      
      const brandScores = competitiveAnalysis.brandScores;
      const targetScores = brandScores[targetBrand] || {};
      
      // 计算竞品平均分
      let competitorScores = {};
      let competitorCount = 0;
      
      competitorBrands.forEach(brand => {
        if (brandScores[brand]) {
          competitorCount++;
          const scores = brandScores[brand];
          Object.keys(scores).forEach(key => {
            if (key.startsWith('overall') && key !== 'overallScore' && key !== 'overallGrade' && key !== 'overallSummary') {
              competitorScores[key] = (competitorScores[key] || 0) + (scores[key] || 0);
            }
          });
        }
      });
      
      // 计算平均值
      if (competitorCount > 0) {
        Object.keys(competitorScores).forEach(key => {
          competitorScores[key] = Math.round(competitorScores[key] / competitorCount);
        });
      }
      
      // 构建雷达图数据（5 个维度）
      const dimensionMap = {
        'overallAuthority': '权威度',
        'overallVisibility': '可见度',
        'overallSentiment': '好感度',
        'overallPurity': '纯净度',
        'overallConsistency': '一致性'
      };
      
      const radarData = [];
      Object.keys(dimensionMap).forEach(key => {
        radarData.push({
          dimension: dimensionMap[key],
          myBrand: targetScores[key] || 0,
          competitor: competitorScores[key] || 0
        });
      });
      
      return radarData;
    } catch (e) {
      logger.error('准备雷达图数据失败:', e);
      return [];
    }
  },

  /**
   * P2-2 修复：渲染雷达图
   */
  renderRadarChart: function() {
    try {
      const query = wx.createSelectorQuery();
      query.select('#radarChartCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0] || !res[0].node) {
            logger.error('Canvas not found');
            return;
          }
          
          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;
          
          // 设置 Canvas 尺寸
          const width = this.data.canvasWidth;
          const height = this.data.canvasHeight;
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          ctx.scale(dpr, dpr);
          
          const centerX = width / 2;
          const centerY = height / 2;
          const radius = Math.min(width, height) / 2 - 40;
          const data = this.data.radarChartData;
          
          // 清空画布
          ctx.clearRect(0, 0, width, height);
          
          // 绘制背景网格（5 边形）
          this.drawRadarGrid(ctx, centerX, centerY, radius);
          
          // 绘制数据区域
          this.drawRadarData(ctx, centerX, centerY, radius, data);
          
          this.setData({ radarChartRendered: true });
        });
    } catch (e) {
      logger.error('渲染雷达图失败:', e);
    }
  },

  /**
   * 绘制雷达图网格
   */
  drawRadarGrid: function(ctx, centerX, centerY, radius) {
    const levels = 5;
    const angleStep = (Math.PI * 2) / 5;
    
    for (let level = 1; level <= levels; level++) {
      const levelRadius = (radius / levels) * level;
      ctx.beginPath();
      
      for (let i = 0; i <= 5; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const x = centerX + Math.cos(angle) * levelRadius;
        const y = centerY + Math.sin(angle) * levelRadius;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    
    // 绘制维度轴线
    for (let i = 0; i < 5; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
      
      // 绘制维度标签
      const labelAngle = i * angleStep - Math.PI / 2;
      const labelRadius = radius + 20;
      const labelX = centerX + Math.cos(labelAngle) * labelRadius;
      const labelY = centerY + Math.sin(labelAngle) * labelRadius;
      
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(this.data.radarChartData[i].dimension, labelX, labelY);
    }
  },

  /**
   * 绘制雷达图数据
   */
  drawRadarData: function(ctx, centerX, centerY, radius, data) {
    const angleStep = (Math.PI * 2) / 5;
    
    // 绘制目标品牌区域（绿色）
    ctx.beginPath();
    for (let i = 0; i <= 5; i++) {
      const dataIndex = i % 5;
      const angle = i * angleStep - Math.PI / 2;
      const value = data[dataIndex].myBrand;
      const pointRadius = (value / 100) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 245, 160, 0.3)';
    ctx.fill();
    ctx.strokeStyle = '#00F5A0';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制竞品平均区域（蓝色）
    ctx.beginPath();
    for (let i = 0; i <= 5; i++) {
      const dataIndex = i % 5;
      const angle = i * angleStep - Math.PI / 2;
      const value = data[dataIndex].competitor;
      const pointRadius = (value / 100) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 169, 255, 0.3)';
    ctx.fill();
    ctx.strokeStyle = '#00A9FF';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制数据点
    for (let i = 0; i < 5; i++) {
      const angle = i * angleStep - Math.PI / 2;
      
      // 目标品牌数据点
      const myBrandRadius = (data[i].myBrand / 100) * radius;
      const myBrandX = centerX + Math.cos(angle) * myBrandRadius;
      const myBrandY = centerY + Math.sin(angle) * myBrandRadius;
      
      ctx.beginPath();
      ctx.arc(myBrandX, myBrandY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00F5A0';
      ctx.fill();
      
      // 竞品平均数据点
      const competitorRadius = (data[i].competitor / 100) * radius;
      const competitorX = centerX + Math.cos(angle) * competitorRadius;
      const competitorY = centerY + Math.sin(angle) * competitorRadius;
      
      ctx.beginPath();
      ctx.arc(competitorX, competitorY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00A9FF';
      ctx.fill();
    }
  },

'''

# Insert the functions
new_content = content[:insert_pos] + radar_functions + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'w') as f:
    f.write(new_content)

print("Successfully inserted radar chart functions!")
