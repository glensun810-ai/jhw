#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 3: 添加实时统计和聚合结果样式

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在文件末尾添加新样式
new_styles = '''

/* ========== 【阶段 1】实时统计样式 ========== */
.realtime-stats-container {
  margin: 24rpx 0;
  padding: 24rpx;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%);
  border-radius: 16rpx;
  border: 2rpx solid rgba(59, 130, 246, 0.3);
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #3b82f6;
}

.stats-subtitle {
  font-size: 24rpx;
  color: #6b7280;
}

.stats-grid {
  display: flex;
  justify-content: space-around;
  padding: 20rpx 0;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12rpx;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.stat-value {
  font-size: 36rpx;
  font-weight: bold;
  color: #2c3e50;
}

.stat-value.highlight {
  color: #3b82f6;
}

.stat-value.positive {
  color: #22c55e;
}

.stat-value.neutral {
  color: #f59e0b;
}

.stat-value.negative {
  color: #ef4444;
}

.stat-label {
  font-size: 22rpx;
  color: #6b7280;
}

/* 品牌实时排名 */
.brand-rankings-container {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.rankings-title {
  font-size: 26rpx;
  font-weight: bold;
  color: #2c3e50;
}

.rankings-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.ranking-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 20rpx;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12rpx;
  border-left: 4rpx solid #9ca3af;
}

.ranking-item.main-brand {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(147, 51, 234, 0.15) 100%);
  border-left-color: #3b82f6;
}

.ranking-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.ranking-rank {
  font-size: 28rpx;
  font-weight: bold;
  color: #6b7280;
}

.ranking-brand {
  font-size: 26rpx;
  font-weight: 600;
  color: #2c3e50;
}

.ranking-main {
  font-size: 20rpx;
  color: #3b82f6;
  padding: 4rpx 12rpx;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 8rpx;
}

.ranking-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4rpx;
}

.ranking-responses {
  font-size: 24rpx;
  color: #6b7280;
}

.ranking-sentiment {
  font-size: 22rpx;
  color: #22c55e;
}

/* ========== 【阶段 2】聚合结果样式 ========== */
.aggregated-results-container {
  margin: 24rpx 0;
  padding: 24rpx;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%);
  border-radius: 16rpx;
  border: 2rpx solid rgba(34, 197, 94, 0.3);
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.results-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #22c55e;
}

.results-subtitle {
  font-size: 24rpx;
  color: #6b7280;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  padding: 20rpx 0;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12rpx;
}

.result-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12rpx;
}

.result-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #2c3e50;
}

.result-value.excellent {
  color: #22c55e;
}

.result-value.good {
  color: #3b82f6;
}

.result-value.warning {
  color: #f59e0b;
}

.result-label {
  font-size: 22rpx;
  color: #6b7280;
}

/* 品牌排名详情 */
.brand-rankings-detail {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.rankings-detail-title {
  font-size: 26rpx;
  font-weight: bold;
  color: #2c3e50;
}

.rankings-detail-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.ranking-detail-item {
  padding: 20rpx;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12rpx;
  border-left: 4rpx solid #9ca3af;
}

.ranking-detail-item.main-brand {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(147, 51, 234, 0.15) 100%);
  border-left-color: #3b82f6;
}

.ranking-detail-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.ranking-detail-rank {
  font-size: 32rpx;
  font-weight: bold;
  color: #6b7280;
}

.ranking-detail-brand {
  font-size: 28rpx;
  font-weight: 600;
  color: #2c3e50;
}

.ranking-detail-main {
  font-size: 22rpx;
  color: #3b82f6;
  padding: 4rpx 12rpx;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 8rpx;
}

.ranking-detail-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12rpx;
}

.detail-stat {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding: 12rpx;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8rpx;
}

.detail-stat-label {
  font-size: 20rpx;
  color: #6b7280;
}

.detail-stat-value {
  font-size: 26rpx;
  font-weight: bold;
  color: #2c3e50;
}
'''

# 添加到文件末尾
content = content.rstrip() + new_styles

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 3 完成：实时统计样式已添加')
