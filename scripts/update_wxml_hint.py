#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 WXML 中的已选平台提示
"""

with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

# 更新已选平台提示，显示更详细的信息
old_hint = '''        <!-- 已选平台提示 -->
        <view class="selected-models-hint" wx:if="{{selectedModelCount > 0}}">
          <text class="hint-icon">✓</text>
          <text class="hint-text">已选择 {{selectedModelCount}} 个 AI 平台</text>
        </view>'''

new_hint = '''        <!-- 已选平台提示 -->
        <view class="selected-models-hint" wx:if="{{selectedModelCount > 0}}">
          <text class="hint-icon">✓</text>
          <view class="hint-content">
            <text class="hint-text">当前市场已选择 <text class="highlight">{{selectedModelCount}}</text> 个 AI 平台</text>
            <text class="hint-sub" wx:if="{{totalSelectedCount > selectedModelCount}}">（另一个市场还选择了 {{totalSelectedCount - selectedModelCount}} 个，切换后可见）</text>
          </view>
        </view>'''

if old_hint in content:
    content = content.replace(old_hint, new_hint)
    print("✅ 已更新已选平台提示（显示详细信息）")
else:
    print("❌ 未找到旧提示")

with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 文件更新完成!")
