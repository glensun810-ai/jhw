#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换进度条样式
old_progress = '''/* 进度条容器 */
.progress-container {
  width: 100%;
  height: 12rpx;
  background: rgba(255, 255, 255, 0.1); /* 玻璃拟态背景 */
  border-radius: 6rpx;
  margin-bottom: 15rpx;
  overflow: hidden;
  position: relative;
}

.progress-inner {
  height: 100%;
  background: linear-gradient(90deg, #0066FF 0%, #00F2FF 100%); /* 从深蓝到科技青渐变 */
  border-radius: 6rpx;
  transition: width 0.3s ease;
  position: relative;
}'''

new_progress = '''/* 进度条容器 */
.progress-container {
  width: 100%;
  height: 12rpx;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6rpx;
  margin-bottom: 15rpx;
  overflow: hidden;
  position: relative;
}

/* 【P1-5 优化】进度条平滑过渡 */
.progress-inner {
  height: 100%;
  background: linear-gradient(90deg, #0066FF 0%, #00F2FF 100%);
  border-radius: 6rpx;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

/* 【P1-5 新增】进度条光泽效果 */
.progress-inner::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255,255,255,0.3),
    transparent
  );
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  100% {
    left: 100%;
  }
}

/* 【P1-5 新增】进度条脉冲效果 (接近完成时) */
.progress-inner.near-complete {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 10rpx rgba(0, 242, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 20rpx rgba(0, 242, 255, 0.8);
  }
}'''

content = content.replace(old_progress, new_progress)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已优化进度条动画')
