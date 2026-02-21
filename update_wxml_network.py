#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在顶部添加网络质量显示
old_header = '''    <!-- 时间预估与进度显示 -->
    <view class="time-estimation-section" wx:if="{{isLoading}}">'''

new_header = '''    <!-- 时间预估与进度显示 -->
    <view class="time-estimation-section" wx:if="{{isLoading}}">
      <!-- 【P2-9 新增】网络质量显示 -->
      <view class="network-quality-display" wx:if="{{networkQuality}}">
        <text class="quality-label">📶 网络质量：</text>
        <text class="quality-value {{networkQuality}}">{{networkQualityText}}</text>
      </view>'''

content = content.replace(old_header, new_header)

# 在取消按钮旁边添加订阅按钮
old_cancel = '''      <!-- 【P2-8 新增】取消诊断按钮 -->
      <view class="cancel-diagnosis-btn" bindtap="cancelDiagnosis">
        <text class="cancel-icon">❌</text>
        <text class="cancel-text">取消诊断</text>
      </view>'''

new_cancel = '''      <!-- 【P2-8 新增】取消诊断按钮 -->
      <view class="cancel-diagnosis-btn" bindtap="cancelDiagnosis">
        <text class="cancel-icon">❌</text>
        <text class="cancel-text">取消诊断</text>
      </view>

      <!-- 【P2-10 新增】订阅消息按钮 -->
      <view class="subscribe-btn {{isSubscribed ? 'subscribed' : ''}}" bindtap="requestMessageSubscription" wx:if="{{!isSubscribed}}">
        <text class="subscribe-icon">🔔</text>
        <text class="subscribe-text">订阅完成通知</text>
      </view>'''

content = content.replace(old_cancel, new_cancel)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已更新 WXML 添加网络质量和订阅显示')
