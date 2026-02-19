# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxss', 'r') as f:
    content = f.read()

# Create the keyword cloud styles
keyword_cloud_styles = '''
/* P2-3 关键词云样式 */
.keyword-cloud-section {
  margin-bottom: 60rpx;
}

.keyword-cloud-section .section-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #FFFFFF;
  display: block;
  margin-bottom: 30rpx;
}

/* 词云容器 */
.word-cloud-container {
  margin-bottom: 30rpx;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  padding: 30rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400rpx;
}

.word-cloud-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.word-cloud-canvas {
  width: 350px;
  height: 350px;
}

.word-cloud-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  color: #8c8c8c;
  font-size: 26rpx;
}

/* 关键词统计 */
.keyword-stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 30rpx;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  padding: 30rpx;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10rpx;
}

.stat-number {
  font-size: 36rpx;
  font-weight: bold;
  color: #FFFFFF;
}

.stat-number.positive {
  color: #00F5A0;
}

.stat-number.neutral {
  color: #00A9FF;
}

.stat-number.negative {
  color: #F44336;
}

.stat-label {
  font-size: 24rpx;
  color: #8c8c8c;
}

/* 高频词列表 */
.top-keywords-section {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  padding: 30rpx;
}

.top-keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 15rpx;
  margin-top: 20rpx;
}

.top-keyword-item {
  display: flex;
  align-items: center;
  gap: 10rpx;
  background: rgba(255, 255, 255, 0.1);
  padding: 10rpx 20rpx;
  border-radius: 8rpx;
}

.keyword-word {
  font-size: 26rpx;
  font-weight: bold;
}

.keyword-word.positive {
  color: #00F5A0;
}

.keyword-word.neutral {
  color: #00A9FF;
}

.keyword-word.negative {
  color: #F44336;
}

.keyword-count {
  font-size: 22rpx;
  color: #8c8c8c;
  background: rgba(0, 0, 0, 0.3);
  padding: 4rpx 10rpx;
  border-radius: 4rpx;
}

'''

# Append the styles
new_content = content + keyword_cloud_styles

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxss', 'w') as f:
    f.write(new_content)

print("Successfully appended keyword cloud styles!")
