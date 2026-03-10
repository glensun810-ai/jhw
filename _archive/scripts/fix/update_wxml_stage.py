#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加阶段说明和解释文案显示
old_task_section = '''      <!-- 【P0 新增】任务状态详情 -->
      <view class="task-status-section">
        <view class="status-row completed" wx:if="{{completedTasks > 0}}">
          <text class="status-icon">✅</text>
          <text class="status-label">已完成：</text>
          <text class="status-value">{{completedTasks}}/{{totalTasks}}</text>
        </view>
        <view class="status-row current" wx:if="{{currentTask}}">
          <text class="status-icon">🔄</text>
          <text class="status-label">进行中：</text>
          <text class="status-value">{{currentTask}}</text>
        </view>
        <view class="status-row pending" wx:if="{{pendingTasks > 0}}">
          <text class="status-icon">⏳</text>
          <text class="status-label">待执行：</text>
          <text class="status-value">{{pendingTasks}} 任务</text>
        </view>
      </view>'''

new_task_section = '''      <!-- 【P1-6 新增】阶段说明 -->
      <view class="stage-description" wx:if="{{stageDescription}}">
        <text class="stage-label">📍 当前阶段：</text>
        <text class="stage-value">{{stageDescription}}</text>
      </view>

      <!-- 【P0 新增】任务状态详情 -->
      <view class="task-status-section">
        <view class="status-row completed" wx:if="{{completedTasks > 0}}">
          <text class="status-icon">✅</text>
          <text class="status-label">已完成：</text>
          <text class="status-value">{{completedTasks}}/{{totalTasks}}</text>
        </view>
        <view class="status-row current" wx:if="{{currentTask}}">
          <text class="status-icon">🔄</text>
          <text class="status-label">进行中：</text>
          <text class="status-value">{{currentTask}}</text>
        </view>
        <view class="status-row pending" wx:if="{{pendingTasks > 0}}">
          <text class="status-icon">⏳</text>
          <text class="status-label">待执行：</text>
          <text class="status-value">{{pendingTasks}} 任务</text>
        </view>
      </view>

      <!-- 【P2-7 新增】进度解释文案 -->
      <view class="progress-explanation" wx:if="{{progressExplanation}}">
        <text class="explanation-icon">💡</text>
        <text class="explanation-text">{{progressExplanation}}</text>
      </view>'''

content = content.replace(old_task_section, new_task_section)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已更新 WXML 显示阶段说明和解释文案')
