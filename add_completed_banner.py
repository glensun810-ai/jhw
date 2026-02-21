#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 添加诊断完成入口 UI

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在操作栏前添加诊断完成入口
old_action = '''  <!-- 【用户体验增强】操作栏 -->
  <view class="action-bar">'''

new_action = '''  <!-- 【P0 新增】诊断完成入口 -->
  <view class="completed-diagnosis-banner {{hasCompletedDiagnosis ? '' : 'hidden'}}" wx:if="{{hasCompletedDiagnosis}}">
    <view class="banner-header">
      <text class="banner-icon">✅</text>
      <view class="banner-title">
        <text class="title-main">诊断已完成！</text>
        <text class="title-sub">{{completedDiagnosisData.brandName}} · {{completedDiagnosisData.completedTime}}</text>
      </view>
    </view>
    
    <view class="banner-metrics">
      <view class="metric">
        <text class="metric-value {{completedDiagnosisData.healthScore >= 80 ? 'excellent' : completedDiagnosisData.healthScore >= 60 ? 'good' : 'warning'}}">{{completedDiagnosisData.healthScore}}</text>
        <text class="metric-label">健康度</text>
      </view>
      <view class="metric-divider"></view>
      <view class="metric">
        <text class="metric-value">{{completedDiagnosisData.sov}}%</text>
        <text class="metric-label">SOV</text>
      </view>
      <view class="metric-divider"></view>
      <view class="metric">
        <text class="metric-value {{completedDiagnosisData.avgSentiment >= 0.3 ? 'positive' : completedDiagnosisData.avgSentiment <= -0.3 ? 'negative' : 'neutral'}}">{{completedDiagnosisData.avgSentiment}}</text>
        <text class="metric-label">情感</text>
      </view>
    </view>
    
    <view class="banner-actions">
      <button class="btn-view-report" bindtap="viewCompletedReport">
        <text class="btn-icon">📊</text>
        <text class="btn-text">查看完整报告</text>
      </button>
      <button class="btn-retry-diagnosis" bindtap="retryDiagnosis">
        <text class="btn-icon">🔄</text>
        <text class="btn-text">重新诊断</text>
      </button>
    </view>
  </view>

  <!-- 【用户体验增强】操作栏 -->
  <view class="action-bar">'''

content = content.replace(old_action, new_action)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加诊断完成入口 UI')
