#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加网络质量和订阅按钮样式
old_cancel = '''/* 【P2-8 新增】取消诊断按钮样式 */
.cancel-diagnosis-btn {'''

new_cancel = '''/* 【P2-9 新增】网络质量显示样式 */
.network-quality-display {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 15rpx;
  padding: 10rpx 20rpx;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8rpx;
  gap: 10rpx;
}

.quality-label {
  font-size: 22rpx;
  color: #8c8c8c;
}

.quality-value {
  font-size: 24rpx;
  font-weight: 500;
}

.quality-value.excellent {
  color: #22c55e;
}

.quality-value.good {
  color: #3b82f6;
}

.quality-value.fair {
  color: #f59e0b;
}

.quality-value.poor,
.quality-value.bad {
  color: #ef4444;
}

/* 【P2-10 新增】订阅消息按钮样式 */
.subscribe-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 15rpx;
  padding: 12rpx 24rpx;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%);
  border: 1rpx solid rgba(147, 51, 234, 0.3);
  border-radius: 12rpx;
  gap: 10rpx;
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
  transition: all 0.3s ease;
}

.subscribe-btn:active {
  transform: scale(0.98);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(147, 51, 234, 0.3) 100%);
}

.subscribe-btn.subscribed {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
}

.subscribe-icon {
  font-size: 28rpx;
}

.subscribe-text {
  font-size: 24rpx;
  color: #9333EA;
  font-weight: 500;
}

.subscribe-btn.subscribed .subscribe-text {
  color: #22c55e;
}

/* 【P2-8 新增】取消诊断按钮样式 */
.cancel-diagnosis-btn {'''

content = content.replace(old_cancel, new_cancel)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加网络质量和订阅按钮样式')
