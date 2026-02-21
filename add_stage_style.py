#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加阶段说明和解释文案样式
old_knowledge = '''/* 【P0 新增】诊断知识科普 */
.knowledge-section {'''

new_knowledge = '''/* 【P1-6 新增】阶段说明样式 */
.stage-description {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 15rpx 0;
  padding: 12rpx 24rpx;
  background: rgba(0, 242, 255, 0.05);
  border: 1rpx solid rgba(0, 242, 255, 0.2);
  border-radius: 12rpx;
  gap: 10rpx;
}

.stage-label {
  font-size: 24rpx;
  color: #00F2FF;
}

.stage-value {
  font-size: 26rpx;
  color: #FFFFFF;
  font-weight: 500;
}

/* 【P2-7 新增】进度解释文案样式 */
.progress-explanation {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 15rpx 0;
  padding: 16rpx 24rpx;
  background: rgba(103, 58, 183, 0.1);
  border: 1rpx solid rgba(103, 58, 183, 0.3);
  border-radius: 12rpx;
  gap: 10rpx;
}

.explanation-icon {
  font-size: 32rpx;
}

.explanation-text {
  font-size: 24rpx;
  color: #673AB7;
  font-weight: 500;
}

/* 【P0 新增】诊断知识科普 */
.knowledge-section {'''

content = content.replace(old_knowledge, new_knowledge)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加阶段说明和解释文案样式')
