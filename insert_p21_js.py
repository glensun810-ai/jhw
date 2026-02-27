# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/history/history.js', 'r') as f:
    content = f.read()

# Find the position to insert (before the closing "})")
insert_marker = "  }\n})"
insert_pos = content.rfind(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the processTrendData function
process_trend_function = '''
  /**
   * P2-1 修复：处理趋势图数据
   */
  processTrendData: function(historyList) {
    try {
      if (!historyList || historyList.length === 0) {
        return {
          trendChartData: [],
          trendLinePoints: '',
          trendStats: {
            averageScore: 0,
            maxScore: 0,
            minScore: 0,
            trend: 'flat',
            trendText: '平稳'
          }
        };
      }
      
      // 按时间排序
      const sortedList = [...historyList].sort((a, b) => {
        return new Date(a.created_at) - new Date(b.created_at);
      });
      
      // 计算趋势图数据点
      const chartData = sortedList.map((item, index) => {
        const score = item.overall_score || 0;
        const totalPoints = sortedList.length;
        
        // 计算位置百分比
        const leftPercent = totalPoints > 1 ? (index / (totalPoints - 1)) * 100 : 50;
        const topPercent = 100 - (score / 100) * 100; // Y 轴翻转，分数越高位置越靠上
        
        // 格式化日期
        const date = new Date(item.created_at);
        const shortDate = `${date.getMonth() + 1}/${date.getDate()}`;
        
        return {
          id: item.id,
          score: Math.round(score),
          leftPercent: leftPercent,
          topPercent: topPercent,
          shortDate: shortDate,
          fullDate: item.created_at
        };
      });
      
      // 计算 SVG 连线坐标
      let linePoints = '';
      if (chartData.length > 1) {
        linePoints = chartData.map(point => {
          const x = (point.leftPercent / 100) * 300; // 假设图表宽度 300
          const y = (point.topPercent / 100) * 200;  // 假设图表高度 200
          return `${x},${y}`;
        }).join(' ');
      }
      
      // 计算趋势统计
      const scores = sortedList.map(item => item.overall_score || 0);
      const averageScore = Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
      const maxScore = Math.round(Math.max(...scores));
      const minScore = Math.round(Math.min(...scores));
      
      // 计算趋势方向
      let trend = 'flat';
      let trendText = '平稳';
      if (sortedList.length >= 2) {
        const firstScore = sortedList[0].overall_score || 0;
        const lastScore = sortedList[sortedList.length - 1].overall_score || 0;
        const diff = lastScore - firstScore;
        
        if (diff > 5) {
          trend = 'up';
          trendText = '上升 ↑';
        } else if (diff < -5) {
          trend = 'down';
          trendText = '下降 ↓';
        }
      }
      
      return {
        trendChartData: chartData,
        trendLinePoints: linePoints,
        trendStats: {
          averageScore: averageScore,
          maxScore: maxScore,
          minScore: minScore,
          trend: trend,
          trendText: trendText
        }
      };
    } catch (e) {
      logger.error('处理趋势图数据失败:', e);
      return {
        trendChartData: [],
        trendLinePoints: '',
        trendStats: {
          averageScore: 0,
          maxScore: 0,
          minScore: 0,
          trend: 'flat',
          trendText: '平稳'
        }
      };
    }
  }
'''

# Insert the function
new_content = content[:insert_pos] + process_trend_function + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/history/history.js', 'w') as f:
    f.write(new_content)

print("Successfully inserted processTrendData function!")
