#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 3b: 添加详细进度显示样式

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在进度条样式后添加详细进度样式
old_progress_style = '''/* 进度文本容器 */
.progress-text-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15rpx;
}

.progress-text {
  font-size: 24rpx;
  color: #8c8c8d;
  flex: 1;
}

.progress-percentage {
  font-size: 28rpx;
  color: #00F2FF; /* 高亮科技青 */
  font-weight: bold;
  font-family: 'Courier New', 'DIN', monospace; /* 等宽字体 */
}'''

new_progress_style = '''/* 进度文本容器 */
.progress-text-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}

.progress-text {
  font-size: 24rpx;
  color: #8c8c8d;
  flex: 1;
}

.progress-percentage {
  font-size: 28rpx;
  color: #00F2FF;
  font-weight: bold;
  font-family: 'Courier New', 'DIN', monospace;
}

/* 【P0 新增】详细进度显示 */
.progress-detail-container {
  text-align: center;
  margin-bottom: 15rpx;
  padding: 8rpx 16rpx;
  background: rgba(0, 242, 255, 0.05);
  border-radius: 8rpx;
  border: 1rpx solid rgba(0, 242, 255, 0.2);
}

.progress-detail {
  font-size: 22rpx;
  color: #00F2FF;
  font-weight: 500;
}'''

content = content.replace(old_progress_style, new_progress_style)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 3b 完成：详细进度样式已添加')
