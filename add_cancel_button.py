#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在进度页顶部添加取消按钮
old_progress_section = '''    <!-- 时间预估与进度显示 -->
    <view class="time-estimation-section" wx:if="{{isLoading}}">'''

new_progress_section = '''    <!-- 时间预估与进度显示 -->
    <view class="time-estimation-section" wx:if="{{isLoading}}">
      <!-- 【P2-8 新增】取消诊断按钮 -->
      <view class="cancel-diagnosis-btn" bindtap="cancelDiagnosis">
        <text class="cancel-icon">❌</text>
        <text class="cancel-text">取消诊断</text>
      </view>'''

content = content.replace(old_progress_section, new_progress_section)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加取消诊断按钮')
