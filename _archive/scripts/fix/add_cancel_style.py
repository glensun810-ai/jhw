#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加取消按钮样式
old_section = '''/* 进度条容器 */
.progress-container {'''

new_section = '''/* 【P2-8 新增】取消诊断按钮样式 */
.cancel-diagnosis-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
  padding: 12rpx 24rpx;
  background: rgba(244, 67, 54, 0.1);
  border: 1rpx solid rgba(244, 67, 54, 0.3);
  border-radius: 12rpx;
  gap: 10rpx;
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
}

.cancel-diagnosis-btn:active {
  background: rgba(244, 67, 54, 0.2);
  transform: scale(0.98);
}

.cancel-icon {
  font-size: 28rpx;
}

.cancel-text {
  font-size: 24rpx;
  color: #F44336;
  font-weight: 500;
}

/* 进度条容器 */
.progress-container {'''

content = content.replace(old_section, new_section)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加取消按钮样式')
