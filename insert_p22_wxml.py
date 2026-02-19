# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml', 'r') as f:
    content = f.read()

# Find the radar placeholder section
old_radar_section = '''      <view class="radar-chart-container">
        <!-- 雷达图占位 -->
        <view class="radar-placeholder">
          <text>雷达图展示平台认知对比</text>
        </view>
      </view>'''

# Create the new radar chart section
new_radar_section = '''      <view class="radar-chart-container">
        <!-- P2-2 雷达图组件 -->
        <view class="radar-canvas-wrapper" wx:if="{{radarChartData && radarChartData.length > 0}}">
          <canvas 
            type="2d" 
            id="radarChartCanvas"
            class="radar-chart-canvas"
            style="width: {{canvasWidth}}px; height: {{canvasHeight}}px;"
          ></canvas>
        </view>
        <view class="radar-placeholder" wx:else>
          <text>暂无雷达图数据</text>
        </view>
      </view>
      
      <!-- 维度说明 -->
      <view class="radar-legend" wx:if="{{radarChartData && radarChartData.length > 0}}">
        <view class="legend-item">
          <view class="legend-color my-brand"></view>
          <text class="legend-text">{{targetBrand}}</text>
        </view>
        <view class="legend-item">
          <view class="legend-color competitor"></view>
          <text class="legend-text">竞品平均</text>
        </view>
      </view>'''

# Replace the old section with the new one
new_content = content.replace(old_radar_section, new_radar_section)

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml', 'w') as f:
    f.write(new_content)

print("Successfully replaced radar chart placeholder with real component!")
