# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/history/history.wxss', 'r') as f:
    content = f.read()

# Create the trend chart styles
trend_styles = '''
/* P2-1 历史趋势图样式 */
.trend-chart-section {
  margin-bottom: 40rpx;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  padding: 30rpx;
}

.trend-chart-section .section-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #FFFFFF;
  display: block;
  margin-bottom: 20rpx;
}

/* 趋势图容器 */
.trend-chart-container {
  display: flex;
  gap: 20rpx;
  margin-bottom: 30rpx;
  height: 240rpx;
}

/* Y 轴 */
.y-axis {
  width: 60rpx;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
}

.y-label {
  font-size: 20rpx;
  color: #8c8c8c;
}

/* 图表区域 */
.chart-area {
  flex: 1;
  position: relative;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8rpx;
  overflow: hidden;
}

/* 网格线 */
.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1rpx;
  background: rgba(255, 255, 255, 0.1);
}

.grid-line:nth-child(1) {
  top: 0%;
}

.grid-line:nth-child(2) {
  top: 20%;
}

.grid-line:nth-child(3) {
  top: 40%;
}

.grid-line:nth-child(4) {
  top: 60%;
}

.grid-line:nth-child(5) {
  top: 80%;
}

/* 数据点容器 */
.data-points-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

/* 数据点 */
.data-point {
  position: absolute;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.point {
  width: 24rpx;
  height: 24rpx;
  border-radius: 50%;
  border: 3rpx solid #FFFFFF;
  transform: translateY(-50%);
}

.point.good {
  background: #00F5A0;
}

.point.medium {
  background: #FF9800;
}

.point.bad {
  background: #F44336;
}

.point-score {
  font-size: 20rpx;
  color: #FFFFFF;
  margin-top: 8rpx;
  font-weight: bold;
}

.point-date {
  font-size: 18rpx;
  color: #8c8c8c;
  margin-top: 4rpx;
}

/* SVG 连线 */
.trend-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 300rpx;
  height: 200rpx;
  pointer-events: none;
}

/* 趋势统计 */
.trend-stats {
  display: flex;
  justify-content: space-around;
  gap: 20rpx;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.stat-label {
  font-size: 22rpx;
  color: #8c8c8c;
}

.stat-value {
  font-size: 28rpx;
  font-weight: bold;
  color: #FFFFFF;
}

.stat-value.high {
  color: #00F5A0;
}

.stat-value.low {
  color: #F44336;
}

.stat-value.trend-up {
  color: #00F5A0;
}

.stat-value.trend-down {
  color: #F44336;
}

.stat-value.trend-flat {
  color: #FF9800;
}

'''

# Append the styles
new_content = content + trend_styles

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/history/history.wxss', 'w') as f:
    f.write(new_content)

print("Successfully appended trend chart styles!")
