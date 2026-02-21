#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 添加输入恢复提示样式

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在文件末尾添加新样式
new_styles = '''

/* ========== 【P1 新增】输入恢复提示样式 ========== */
.input-restore-banner {
  margin: 24rpx 0;
  padding: 24rpx;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%);
  border-radius: 16rpx;
  border: 2rpx solid rgba(59, 130, 246, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s ease;
}

.input-restore-banner.hidden {
  display: none;
}

.banner-content {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
}

.banner-icon {
  font-size: 48rpx;
  flex-shrink: 0;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.banner-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #2c3e50);
}

.banner-summary {
  font-size: 24rpx;
  color: var(--text-secondary, #7f8c8d);
}

.banner-time {
  font-size: 22rpx;
  color: rgba(127, 140, 145, 0.8);
}

.banner-actions {
  display: flex;
  gap: 12rpx;
  flex-shrink: 0;
}

.btn-use-last {
  padding: 12rpx 24rpx;
  background: linear-gradient(135deg, #3b82f6 0%, #9333ea 100%);
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 12rpx;
  border: none;
}

.btn-use-last:active {
  opacity: 0.8;
  transform: scale(0.95);
}

.btn-clear-input {
  padding: 12rpx 24rpx;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  font-size: 26rpx;
  font-weight: 500;
  border-radius: 12rpx;
  border: 2rpx solid rgba(239, 68, 68, 0.3);
}

.btn-clear-input:active {
  background: rgba(239, 68, 68, 0.2);
}
'''

# 添加到文件末尾
content = content.rstrip() + new_styles

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 添加输入恢复提示样式')
