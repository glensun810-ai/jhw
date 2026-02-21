#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 添加诊断完成入口样式

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在文件末尾添加样式
new_styles = '''

/* ========== 【P0 新增】诊断完成入口样式 ========== */
.completed-diagnosis-banner {
  margin: 24rpx 0;
  padding: 32rpx;
  background: linear-gradient(135deg, rgba(39, 174, 96, 0.15) 0%, rgba(52, 211, 153, 0.1) 100%);
  border-radius: 20rpx;
  border: 2rpx solid rgba(39, 174, 96, 0.4);
  box-shadow: 0 8rpx 32rpx rgba(39, 174, 96, 0.2);
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.completed-diagnosis-banner.hidden {
  display: none;
}

.banner-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.banner-icon {
  font-size: 56rpx;
  flex-shrink: 0;
}

.banner-title {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.title-main {
  font-size: 32rpx;
  font-weight: bold;
  color: #27ae60;
}

.title-sub {
  font-size: 24rpx;
  color: rgba(46, 204, 113, 0.8);
}

.banner-metrics {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 24rpx 0;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16rpx;
}

.banner-metrics .metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  flex: 1;
}

.banner-metrics .metric-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #2c3e50;
}

.banner-metrics .metric-value.excellent {
  color: #27ae60;
}

.banner-metrics .metric-value.good {
  color: #3498db;
}

.banner-metrics .metric-value.warning {
  color: #e74c3c;
}

.banner-metrics .metric-value.positive {
  color: #27ae60;
}

.banner-metrics .metric-value.negative {
  color: #e74c3c;
}

.banner-metrics .metric-value.neutral {
  color: #95a5a6;
}

.banner-metrics .metric-label {
  font-size: 22rpx;
  color: #7f8c8d;
}

.banner-metrics .metric-divider {
  width: 2rpx;
  height: 60rpx;
  background: rgba(0, 0, 0, 0.1);
}

.banner-actions {
  display: flex;
  gap: 16rpx;
}

.btn-view-report {
  flex: 2;
  height: 88rpx;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: 16rpx;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  box-shadow: 0 8rpx 24rpx rgba(52, 152, 219, 0.3);
}

.btn-view-report:active {
  opacity: 0.8;
  transform: scale(0.98);
}

.btn-view-report .btn-icon {
  font-size: 36rpx;
}

.btn-retry-diagnosis {
  flex: 1;
  height: 88rpx;
  background: rgba(255, 255, 255, 0.8);
  color: #2c3e50;
  font-size: 28rpx;
  font-weight: 500;
  border-radius: 16rpx;
  border: 2rpx solid rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
}

.btn-retry-diagnosis:active {
  background: rgba(255, 255, 255, 1);
  transform: scale(0.98);
}

.btn-retry-diagnosis .btn-icon {
  font-size: 32rpx;
}
'''

# 添加到文件末尾
content = content.rstrip() + new_styles

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加诊断完成入口样式')
