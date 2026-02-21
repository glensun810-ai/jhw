#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxss'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加警告样式
old_knowledge = '''/* 【P0 新增】诊断知识科普 */
.knowledge-section {'''

new_knowledge = '''/* 【P1-4 新增】进度警告样式 */
.progress-warning {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 15rpx 0;
  padding: 16rpx 24rpx;
  background: rgba(255, 152, 0, 0.1);
  border: 1rpx solid rgba(255, 152, 0, 0.3);
  border-radius: 12rpx;
  gap: 10rpx;
}

.warning-icon {
  font-size: 32rpx;
}

.warning-text {
  font-size: 24rpx;
  color: #FF9800;
  font-weight: 500;
}

/* 【P0 新增】诊断知识科普 */
.knowledge-section {'''

content = content.replace(old_knowledge, new_knowledge)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加警告样式')
