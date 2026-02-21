#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换剩余时间显示
old_time_display = '''      <!-- 【P0 新增】预计剩余时间 -->
      <view class="remaining-time" wx:if="{{remainingTime > 0}}">
        <text class="remaining-label">⏱️ 预计剩余：</text>
        <text class="remaining-value number-font">{{formatTime(remainingTime)}}</text>
      </view>'''

new_time_display = '''      <!-- 【P0 新增】预计剩余时间 -->
      <view class="remaining-time" wx:if="{{remainingTime > 0 || smoothedRemainingTime}}">
        <text class="remaining-label">⏱️ 预计剩余：</text>
        <text class="remaining-value number-font">{{smoothedRemainingTime || formatTime(remainingTime)}}</text>
      </view>'''

content = content.replace(old_time_display, new_time_display)

# 添加进度警告显示
old_task_section = '''      <!-- 【P0 新增】任务状态详情 -->
      <view class="task-status-section">'''

new_task_section = '''      <!-- 【P1-4 新增】进度警告 -->
      <view class="progress-warning" wx:if="{{progressWarnings.length > 0}}">
        <text class="warning-icon">⚠️</text>
        <text class="warning-text" wx:for="{{progressWarnings}}" wx:key="*this">{{item}}</text>
      </view>

      <!-- 【P0 新增】任务状态详情 -->
      <view class="task-status-section">'''

content = content.replace(old_task_section, new_task_section)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已更新 WXML 显示')
