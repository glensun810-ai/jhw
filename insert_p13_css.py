# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxss', 'r') as f:
    content = f.read()

# Find the position to append (at the end of file)
# Create the recommendation styles
recommendation_styles = '''
/* P1-3 优化建议列表样式 */
.recommendation-section {
  margin-bottom: 60rpx;
}

.recommendation-section .section-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #FFFFFF;
  display: block;
  margin-bottom: 30rpx;
}

/* 建议概览 */
.recommendation-overview {
  margin-bottom: 40rpx;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  padding: 30rpx;
  display: flex;
  justify-content: space-around;
  gap: 20rpx;
}

.overview-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10rpx;
}

.overview-number {
  font-size: 40rpx;
  font-weight: bold;
  color: #FFFFFF;
}

.overview-number.high {
  color: #F44336;
}

.overview-number.medium {
  color: #FF9800;
}

.overview-number.low {
  color: #00F5A0;
}

.overview-label {
  font-size: 24rpx;
  color: #8c8c8c;
}

/* 建议列表 */
.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.recommendation-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16rpx;
  overflow: hidden;
}

.card-header {
  padding: 20rpx 30rpx;
  display: flex;
  align-items: center;
  gap: 15rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.1);
}

.card-header.high {
  background: rgba(244, 67, 54, 0.2);
}

.card-header.medium {
  background: rgba(255, 152, 0, 0.2);
}

.card-header.low {
  background: rgba(0, 245, 160, 0.2);
}

.priority-tag {
  padding: 8rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
  font-weight: bold;
}

.priority-tag.high {
  background: #F44336;
  color: #FFFFFF;
}

.priority-tag.medium {
  background: #FF9800;
  color: #FFFFFF;
}

.priority-tag.low {
  background: #00F5A0;
  color: #141414;
}

.type-tag {
  padding: 8rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.type-tag.content_correction {
  background: #2196F3;
  color: #FFFFFF;
}

.type-tag.brand_strengthening {
  background: #9C27B0;
  color: #FFFFFF;
}

.type-tag.source_attack {
  background: #F44336;
  color: #FFFFFF;
}

.type-tag.risk_mitigation {
  background: #FF9800;
  color: #FFFFFF;
}

.urgency-score {
  margin-left: auto;
  font-size: 24rpx;
  color: #8c8c8c;
}

/* 卡片内容 */
.card-body {
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #FFFFFF;
}

.card-description {
  font-size: 26rpx;
  color: #CCCCCC;
  line-height: 1.6;
}

/* 行动步骤 */
.action-steps {
  display: flex;
  flex-direction: column;
  gap: 15rpx;
}

.steps-title {
  font-size: 26rpx;
  color: #FFFFFF;
  font-weight: bold;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 15rpx;
}

.step-number {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #00A9FF, #00F5A0);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  font-weight: bold;
  color: #FFFFFF;
  flex-shrink: 0;
}

.step-text {
  flex: 1;
  font-size: 26rpx;
  color: #CCCCCC;
  line-height: 1.5;
}

/* 目标对象 */
.target-info {
  display: flex;
  gap: 15rpx;
  align-items: center;
}

.target-label {
  font-size: 26rpx;
  color: #8c8c8c;
}

.target-value {
  font-size: 26rpx;
  color: #00A9FF;
}

/* 预估影响 */
.impact-info {
  display: flex;
  gap: 15rpx;
  align-items: center;
}

.impact-label {
  font-size: 26rpx;
  color: #8c8c8c;
}

.impact-value {
  font-size: 26rpx;
  font-weight: bold;
}

.impact-value.high {
  color: #F44336;
}

.impact-value.medium {
  color: #FF9800;
}

.impact-value.low {
  color: #00F5A0;
}

'''

# Append the styles
new_content = content + recommendation_styles

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxss', 'w') as f:
    f.write(new_content)

print("Successfully appended recommendation styles!")
