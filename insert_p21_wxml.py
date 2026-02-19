# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/history/history.wxml', 'r') as f:
    content = f.read()

# Find the position to insert (after page-header, before history-list)
insert_marker = '  <!-- 历史记录列表 -->'
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the trend chart section XML
trend_chart_xml = '''  <!-- P2-1 历史趋势图 -->
  <view class="trend-chart-section" wx:if="{{trendChartData && trendChartData.length > 0}}">
    <text class="section-title">📈 分数趋势</text>
    <view class="trend-chart-container">
      <!-- Y 轴标签 -->
      <view class="y-axis">
        <text class="y-label">100</text>
        <text class="y-label">80</text>
        <text class="y-label">60</text>
        <text class="y-label">40</text>
        <text class="y-label">20</text>
        <text class="y-label">0</text>
      </view>
      
      <!-- 图表区域 -->
      <view class="chart-area">
        <!-- 网格线 -->
        <view class="grid-line" wx:for="{{5}}" wx:key="index"></view>
        
        <!-- 数据点和连线 -->
        <view class="data-points-container">
          <view class="data-point" wx:for="{{trendChartData}}" wx:key="index" style="left: {{item.leftPercent}}%;">
            <view class="point {{item.score >= 80 ? 'good' : (item.score >= 60 ? 'medium' : 'bad')}}" style="top: {{item.topPercent}}%;"></view>
            <text class="point-score">{{item.score}}</text>
            <text class="point-date">{{item.shortDate}}</text>
          </view>
          
          <!-- 连线（使用 SVG 或简单 div） -->
          <svg class="trend-line" wx:if="{{trendChartData.length > 1}}">
            <polyline points="{{trendLinePoints}}" stroke="#00F5A0" stroke-width="3" fill="none"></polyline>
          </svg>
        </view>
      </view>
    </view>
    
    <!-- 趋势统计 -->
    <view class="trend-stats">
      <view class="stat-item">
        <text class="stat-label">平均分</text>
        <text class="stat-value">{{trendStats.averageScore}}</text>
      </view>
      <view class="stat-item">
        <text class="stat-label">最高分</text>
        <text class="stat-value high">{{trendStats.maxScore}}</text>
      </view>
      <view class="stat-item">
        <text class="stat-label">最低分</text>
        <text class="stat-value low">{{trendStats.minScore}}</text>
      </view>
      <view class="stat-item">
        <text class="stat-label">趋势</text>
        <text class="stat-value {{trendStats.trend === 'up' ? 'trend-up' : (trendStats.trend === 'down' ? 'trend-down' : 'trend-flat')}}">{{trendStats.trendText}}</text>
      </view>
    </view>
  </view>

'''

# Insert the trend chart section
new_content = content[:insert_pos] + trend_chart_xml + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/history/history.wxml', 'w') as f:
    f.write(new_content)

print("Successfully inserted trend chart section!")
