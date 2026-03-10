# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxss', 'r') as f:
    content = f.read()

# Create the radar chart styles
radar_styles = '''
/* P2-2 雷达图样式 */
.radar-chart-container {
  margin: 20rpx 0;
  padding: 30rpx;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.radar-canvas-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.radar-chart-canvas {
  width: 300px;
  height: 300px;
}

.radar-placeholder {
  width: 300rpx;
  height: 300rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #8c8c8c;
  font-size: 26rpx;
}

/* 图例 */
.radar-legend {
  display: flex;
  justify-content: center;
  gap: 40rpx;
  margin-top: 20rpx;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.legend-color {
  width: 24rpx;
  height: 24rpx;
  border-radius: 4rpx;
}

.legend-color.my-brand {
  background: #00F5A0;
}

.legend-color.competitor {
  background: #00A9FF;
}

.legend-text {
  font-size: 24rpx;
  color: #FFFFFF;
}

'''

# Append the styles
new_content = content + radar_styles

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxss', 'w') as f:
    f.write(new_content)

print("Successfully appended radar chart styles!")
