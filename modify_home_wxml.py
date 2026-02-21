#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 首页 WXML 修改 - 添加输入恢复提示

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在标题区域后添加输入恢复提示
old_title = '''    <!-- 标题 -->
    <view class="title-section">
      <text class="main-title">AI 搜索品牌影响力监测</text>
      <text class="subtitle">驾驭 AI，重塑品牌影响力</text>
    </view>'''

new_title = '''    <!-- 标题 -->
    <view class="title-section">
      <text class="main-title">AI 搜索品牌影响力监测</text>
      <text class="subtitle">驾驭 AI，重塑品牌影响力</text>
    </view>

    <!--【P1 新增】输入恢复提示 -->
    <view class="input-restore-banner {{hasLastInput ? '' : 'hidden'}}" wx:if="{{hasLastInput}}">
      <view class="banner-content">
        <text class="banner-icon">💡</text>
        <view class="banner-text">
          <text class="banner-title">发现上次的诊断输入</text>
          <text class="banner-summary">{{lastInputSummary}}</text>
          <text class="banner-time">{{lastInputTime}}</text>
        </view>
      </view>
      <view class="banner-actions">
        <button class="btn-use-last" bindtap="useLastInput">使用</button>
        <button class="btn-clear-input" bindtap="clearInput">清空</button>
      </view>
    </view>'''

content = content.replace(old_title, new_title)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 首页 WXML 修改完成')
