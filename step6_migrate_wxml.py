# -*- coding: utf-8 -*-
"""Step 6: WXML 迁移到 appState"""

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

# Step 6: 完全使用 appState 的主操作按钮区域
old_button_section = """    <!-- 主操作按钮 -->
    <view class="main-action-section">
      <!-- 状态 1: 有上次诊断报告 -->
      <view class="completed-actions {{hasLastReport && !isTesting ? '' : 'hidden'}}">
        <view class="completed-badge">
          <text class="badge-icon">✅</text>
          <text class="badge-text">已有诊断报告</text>
          <text class="badge-time" wx:if="{{completedTime}}">{{completedTime}}</text>
        </view>

        <view class="completed-buttons">
          <button class="btn-primary-view" bindtap="viewReport">
            <text class="btn-icon">📊</text>
            <text class="btn-text">查看上次诊断报告</text>
          </button>

          <button class="btn-secondary-retry" bindtap="retryDiagnosis">
            <text class="btn-icon">🔄</text>
            <text class="btn-text">重新诊断</text>
          </button>
        </view>
      </view>

      <!-- 状态 2: 诊断按钮（始终显示，根据状态改变文字） -->
      <button class="scan-button {{hasLastReport ? 'hidden' : ''}}"
              bindtap="startBrandTest"
              disabled="{{isTesting}}">
        <text class="button-content">
          <text class="loading-spinner" wx:if="{{isTesting}}"></text>
          <text class="button-text">{{isTesting ? '诊断中... ' + testProgress + '%' : 'AI 品牌战略诊断'}}</text>
        </text>
      </button>

      <!-- 状态 3: 诊断完成（当次）- 始终显示查看按钮 -->
      <view class="completed-actions {{testCompleted && !hasLastReport ? '' : 'hidden'}}">
        <view class="completed-badge">
          <text class="badge-icon">✅</text>
          <text class="badge-text">诊断已完成</text>
          <text class="badge-time" wx:if="{{completedTime}}">{{completedTime}}</text>
        </view>

        <view class="completed-buttons">
          <button class="btn-primary-view" bindtap="viewReport">
            <text class="btn-icon">📊</text>
            <text class="btn-text">查看诊断报告</text>
          </button>

          <button class="btn-secondary-retry" bindtap="retryDiagnosis">
            <text class="btn-icon">🔄</text>
            <text class="btn-text">重新诊断</text>
          </button>
        </view>
      </view>
    </view>"""

new_button_section = """    <!-- 主操作按钮 - Step 6: 完全使用 appState -->
    <view class="main-action-section">
      <!-- 状态 1: 有上次诊断报告（保留，这是独立状态） -->
      <view class="completed-actions {{hasLastReport && appState !== 'testing' ? '' : 'hidden'}}">
        <view class="completed-badge">
          <text class="badge-icon">✅</text>
          <text class="badge-text">已有诊断报告</text>
          <text class="badge-time" wx:if="{{completedTime}}">{{completedTime}}</text>
        </view>

        <view class="completed-buttons">
          <button class="btn-primary-view" bindtap="viewReport">
            <text class="btn-icon">📊</text>
            <text class="btn-text">查看上次诊断报告</text>
          </button>

          <button class="btn-secondary-retry" bindtap="retryDiagnosis">
            <text class="btn-icon">🔄</text>
            <text class="btn-text">重新诊断</text>
          </button>
        </view>
      </view>

      <!-- 状态 2: 诊断按钮（完全使用 appState） -->
      <button class="scan-button {{hasLastReport ? 'hidden' : ''}}"
              bindtap="startBrandTest"
              disabled="{{appState === 'testing'}}">
        <text class="button-content">
          <text class="loading-spinner" wx:if="{{appState === 'testing'}}"></text>
          <text class="button-text">
            <block wx:if="{{appState === 'testing'}}">
              诊断中... {{testProgress}}%
            </block>
            <block wx:elif="{{appState === 'completed'}}">
              重新诊断
            </block>
            <block wx:elif="{{appState === 'error'}}">
              AI 品牌战略诊断
            </block>
            <block wx:else>
              AI 品牌战略诊断
            </block>
          </text>
        </text>
      </button>

      <!-- 状态 3: 诊断完成（当次）- 完全使用 appState -->
      <view class="completed-actions {{appState === 'completed' ? '' : 'hidden'}}">
        <view class="completed-badge">
          <text class="badge-icon">✅</text>
          <text class="badge-text">诊断已完成</text>
          <text class="badge-time" wx:if="{{completedTime}}">{{completedTime}}</text>
        </view>

        <view class="completed-buttons">
          <button class="btn-primary-view" bindtap="viewReport">
            <text class="btn-icon">📊</text>
            <text class="btn-text">查看诊断报告</text>
          </button>

          <button class="btn-secondary-retry" bindtap="retryDiagnosis">
            <text class="btn-icon">🔄</text>
            <text class="btn-text">重新诊断</text>
          </button>
        </view>
      </view>
    </view>"""

if old_button_section in content:
    content = content.replace(old_button_section, new_button_section)
    print('✅ Step 6: WXML 按钮区域已更新为使用 appState')
else:
    print('❌ 未找到原始按钮区域代码')

# 更新 analysis-card 的 loading 属性
old_analysis_card = """    <analysis-card
      title="AI 品牌认知诊断"
      subtitle="实时监控 AI 对品牌的认知状态"
      status="{{currentStage}}"
      progress="{{testProgress}}"
      data="{{reportData}}"
      loading="{{isTesting}}"
      wx:if="{{isTesting || reportData}}">
    </analysis-card>"""

new_analysis_card = """    <!-- Step 6: 使用 appState 控制 loading -->
    <analysis-card
      title="AI 品牌认知诊断"
      subtitle="实时监控 AI 对品牌的认知状态"
      status="{{currentStage}}"
      progress="{{testProgress}}"
      data="{{reportData}}"
      loading="{{appState === 'testing'}}"
      wx:if="{{appState === 'testing' || appState === 'completed' || reportData}}">
    </analysis-card>"""

if old_analysis_card in content:
    content = content.replace(old_analysis_card, new_analysis_card)
    print('✅ Step 6: analysis-card 已更新为使用 appState')
else:
    print('❌ 未找到 analysis-card 代码')

# 更新 analysis-charts 的 loading 属性
old_analysis_charts = """    <analysis-charts
      radar-data="{{scoreData}}"
      trend-data="{{trendChartData}}"
      loading="{{isTesting}}"
      wx:if="{{reportData}}">
    </analysis-charts>"""

new_analysis_charts = """    <!-- Step 6: 使用 appState 控制 loading -->
    <analysis-charts
      radar-data="{{scoreData}}"
      trend-data="{{trendChartData}}"
      loading="{{appState === 'testing'}}"
      wx:if="{{reportData}}">
    </analysis-charts>"""

if old_analysis_charts in content:
    content = content.replace(old_analysis_charts, new_analysis_charts)
    print('✅ Step 6: analysis-charts 已更新为使用 appState')
else:
    print('❌ 未找到 analysis-charts 代码')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ Step 6 完成！WXML 已完全迁移到 appState')
