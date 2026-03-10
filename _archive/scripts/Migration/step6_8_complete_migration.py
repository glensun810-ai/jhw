# -*- coding: utf-8 -*-
"""Step 6-8 完整迁移脚本"""
import re

# ============== WXML 迁移 ==============
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxml', 'r', encoding='utf-8') as f:
    wxml = f.read()

# 按钮区域完全使用 appState
old_btn = """      <!-- 状态 2: 诊断按钮（始终显示，根据状态改变文字） -->
      <button class="scan-button {{hasLastReport ? 'hidden' : ''}}"
              bindtap="startBrandTest"
              disabled="{{isTesting}}">
        <text class="button-content">
          <text class="loading-spinner" wx:if="{{isTesting}}"></text>
          <text class="button-text">{{isTesting ? '诊断中... ' + testProgress + '%' : 'AI 品牌战略诊断'}}</text>
        </text>
      </button>"""

new_btn = """      <!-- 状态 2: 诊断按钮（完全使用 appState） -->
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
      </button>"""

wxml = wxml.replace(old_btn, new_btn)
print('✅ WXML: 按钮区域已更新')

# 完成状态区域
old_complete = """      <!-- 状态 3: 诊断完成（当次）- 始终显示查看按钮 -->
      <view class="completed-actions {{testCompleted && !hasLastReport ? '' : 'hidden'}}">"""

new_complete = """      <!-- 状态 3: 诊断完成（当次）- 完全使用 appState -->
      <view class="completed-actions {{appState === 'completed' ? '' : 'hidden'}}">"""

wxml = wxml.replace(old_complete, new_complete)
print('✅ WXML: 完成状态区域已更新')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(wxml)

# ============== JS 迁移 ==============
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 简化 startBrandTest setData
old_start = """    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null,
      appState: 'testing'
    });"""

new_start = """    // Step 7: 主要使用 appState
    this.setData({
      appState: 'testing',
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...'
    });"""

js = js.replace(old_start, new_start)
print('✅ JS: startBrandTest 已简化')

# 简化 handleDiagnosisComplete setData
old_complete_js = """      // 【Step 3 新增】同步设置 appState
      this.setData({
        isTesting: false,
        testCompleted: true,
        hasLastReport: true,
        completedTime: this.getCompletedTimeText(),
        appState: 'completed'  // 与 testCompleted: true 对应
      });"""

new_complete_js = """      // Step 7: 主要使用 appState
      this.setData({
        appState: 'completed',
        hasLastReport: true,
        completedTime: this.getCompletedTimeText()
      });"""

js = js.replace(old_complete_js, new_complete_js)
print('✅ JS: handleDiagnosisComplete 已简化')

# 简化错误处理 setData
old_error_js = """      // 【Step 3 新增】同步设置 appState
      this.setData({
        isTesting: false,
        testCompleted: false,
        appState: 'error'  // 标记为错误状态
      });"""

new_error_js = """      // Step 7: 主要使用 appState
      this.setData({
        appState: 'error'
      });"""

js = js.replace(old_error_js, new_error_js)
print('✅ JS: 错误处理已简化')

# 更新 data 注释
old_data = """    // 测试状态
    isTesting: false,
    testProgress: 0,
    progressText: '准备启动 AI 认知诊断...',
    testCompleted: false,

    // 【Step 1 新增】统一状态管理（与现有变量并存，双轨运行）
    // 状态枚举：'idle' | 'checking' | 'testing' | 'completed' | 'error'
    appState: 'idle',"""

new_data = """    // 测试状态
    // 【Step 8 已弃用】appState 是唯一状态源，旧变量保留用于向后兼容
    isTesting: false,        // @deprecated 使用 appState 代替
    testProgress: 0,         // 保留：进度百分比
    progressText: '准备启动 AI 认知诊断...',  // 保留：进度文本
    testCompleted: false,    // @deprecated 使用 appState 代替

    // 【Step 1 新增】统一状态管理
    appState: 'idle',  // 状态枚举：'idle' | 'testing' | 'completed' | 'error'"""

js = js.replace(old_data, new_data)
print('✅ JS: data 注释已更新')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(js)

print('\n✅ Step 6-8 完整迁移完成！')
