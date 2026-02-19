# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r') as f:
    content = f.read()

# Find the position to insert (before prepareRadarChartData function)
insert_marker = "  /**\n   * P2-2 修复：准备雷达图数据\n   */\n  prepareRadarChartData: function(competitiveAnalysis, targetBrand, competitorBrands) {"
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the keyword cloud functions
keyword_functions = '''  /**
   * P2-3 修复：准备关键词云数据
   */
  prepareKeywordCloudData: function(semanticDriftData, results, targetBrand) {
    try {
      let allKeywords = [];
      
      // 从语义偏移数据中提取关键词
      if (semanticDriftData) {
        // 添加正面术语
        if (semanticDriftData.positiveTerms) {
          semanticDriftData.positiveTerms.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'positive' });
          });
        }
        
        // 添加负面术语
        if (semanticDriftData.negativeTerms) {
          semanticDriftData.negativeTerms.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'negative' });
          });
        }
        
        // 添加意外关键词（中性）
        if (semanticDriftData.unexpectedKeywords) {
          semanticDriftData.unexpectedKeywords.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'neutral' });
          });
        }
      }
      
      // 从 AI 响应中提取更多关键词
      const targetResults = results.filter(r => r.brand === targetBrand);
      const allResponses = targetResults.map(r => r.response || '').join(' ');
      
      // 简单分词和统计
      const words = allResponses.split(/[\\s,.。！？!？]+/);
      const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等', '一个', '这个', '这些'];
      
      const wordCount = {};
      words.forEach(word => {
        if (word.length > 1 && !stopWords.includes(word)) {
          wordCount[word] = (wordCount[word] || 0) + 1;
        }
      });
      
      // 合并词频数据
      const keywordMap = {};
      allKeywords.forEach(item => {
        keywordMap[item.word] = {
          word: item.word,
          count: wordCount[item.word] || 1,
          sentiment: item.sentiment
        };
      });
      
      // 转换为数组并排序
      const keywordData = Object.values(keywordMap)
        .sort((a, b) => b.count - a.count)
        .slice(0, 50);  // 限制最多 50 个词
      
      // 计算权重（用于字体大小）
      const maxCount = keywordData.length > 0 ? keywordData[0].count : 1;
      keywordData.forEach(item => {
        item.weight = item.count / maxCount;
      });
      
      // 统计情感分布
      const stats = {
        positiveCount: keywordData.filter(k => k.sentiment === 'positive').length,
        neutralCount: keywordData.filter(k => k.sentiment === 'neutral').length,
        negativeCount: keywordData.filter(k => k.sentiment === 'negative').length
      };
      
      // 高频词（Top 10）
      const topKeywords = keywordData.slice(0, 10);
      
      return {
        keywordCloudData: keywordData,
        topKeywords: topKeywords,
        keywordStats: stats
      };
    } catch (e) {
      console.error('准备关键词云数据失败:', e);
      return {
        keywordCloudData: [],
        topKeywords: [],
        keywordStats: {
          positiveCount: 0,
          neutralCount: 0,
          negativeCount: 0
        }
      };
    }
  },

  /**
   * P2-3 修复：渲染关键词云
   */
  renderWordCloud: function() {
    try {
      const query = wx.createSelectorQuery();
      query.select('#wordCloudCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0] || !res[0].node) {
            console.error('Canvas not found');
            return;
          }
          
          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;
          
          // 设置 Canvas 尺寸
          const width = this.data.wordCloudCanvasWidth;
          const height = this.data.wordCloudCanvasHeight;
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          ctx.scale(dpr, dpr);
          
          const data = this.data.keywordCloudData;
          const centerX = width / 2;
          const centerY = height / 2;
          
          // 清空画布
          ctx.clearRect(0, 0, width, height);
          
          // 绘制词云
          this.drawWordCloud(ctx, centerX, centerY, data);
          
          this.setData({ wordCloudRendered: true });
        });
    } catch (e) {
      console.error('渲染词云失败:', e);
    }
  },

  /**
   * 绘制关键词云
   */
  drawWordCloud: function(ctx, centerX, centerY, data) {
    const placedWords = [];
    const maxRadius = Math.min(centerX, centerY) - 40;
    
    // 情感颜色映射
    const sentimentColors = {
      'positive': '#00F5A0',  // 绿色
      'neutral': '#00A9FF',   // 蓝色
      'negative': '#F44336'   // 红色
    };
    
    data.forEach((item, index) => {
      // 计算字体大小（12-28px）
      const fontSize = Math.round(12 + item.weight * 16);
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = sentimentColors[item.sentiment] || '#FFFFFF';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // 计算位置（螺旋布局）
      const angle = index * 0.5;  // 黄金角度
      const radius = (index / data.length) * maxRadius;
      let x = centerX + Math.cos(angle) * radius;
      let y = centerY + Math.sin(angle) * radius;
      
      // 简单的碰撞检测
      let overlap = false;
      const wordWidth = ctx.measureText(item.word).width;
      const wordHeight = fontSize;
      
      for (let placed of placedWords) {
        const dx = x - placed.x;
        const dy = y - placed.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < (wordWidth + placed.width) / 2) {
          overlap = true;
          break;
        }
      }
      
      // 如果不重叠，绘制并记录
      if (!overlap || index < 5) {  // 前 5 个词强制显示
        ctx.fillText(item.word, x, y);
        placedWords.push({
          x: x,
          y: y,
          width: wordWidth,
          height: wordHeight
        });
      }
    });
  },

'''

# Insert the functions
new_content = content[:insert_pos] + keyword_functions + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'w') as f:
    f.write(new_content)

print("Successfully inserted keyword cloud functions!")
