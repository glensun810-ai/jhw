#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 3: UI 优化 - 添加进度百分比和任务进度显示

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修改进度条显示，添加百分比和任务进度
old_progress = '''      <!-- 进度条容器 -->
      <view class="progress-container">
        <view class="progress-inner" style="width: {{progress}}%; background: {{getProgressColor(progress)}};"></view>
      </view>

      <!-- 进度文本 -->
      <view class="progress-text-container">
        <text class="progress-text">{{progressText}}</text>
        <text class="progress-percentage number-font">{{Math.min(100, Math.round(progress))}}%</text>
      </view>'''

new_progress = '''      <!-- 进度条容器 -->
      <view class="progress-container">
        <view class="progress-inner" style="width: {{progress}}%; background: {{getProgressColor(progress)}};"></view>
      </view>

      <!-- 进度文本 -->
      <view class="progress-text-container">
        <text class="progress-text">{{progressText}}</text>
        <text class="progress-percentage number-font">{{progress}}%</text>
      </view>
      
      <!--【P0 新增】详细进度显示 -->
      <view class="progress-detail-container" wx:if="{{progressDetail}}">
        <text class="progress-detail">{{progressDetail}}</text>
      </view>'''

content = content.replace(old_progress, new_progress)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 3 完成：UI 已优化')
