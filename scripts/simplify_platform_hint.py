#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改已选平台提示：只显示当前激活市场的已选平台
"""

with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的提示代码
old_hint = '''  <!-- 已选平台详细提示 -->
  <view class="selected-platforms-summary" wx:if="{{selectedModelCount > 0 || totalSelectedCount > 0}}">
    <view class="summary-header">
      <text class="summary-title">已选 AI</text>
    </view>
    <view class="summary-content">
      <view class="platform-group" wx:if="{{domesticSelectedNames.length > 0}}">
        <text class="group-label">国内：</text>
        <text class="platform-names">{{domesticSelectedNames}}</text>
        <text class="platform-count">（{{selectedModelCount}}个）</text>
      </view>
      <view class="platform-group" wx:if="{{overseasSelectedNames.length > 0}}">
        <text class="group-label">海外：</text>
        <text class="platform-names">{{overseasSelectedNames}}</text>
        <text class="platform-count">（{{totalSelectedCount - selectedModelCount}}个）</text>
      </view>
      <view class="summary-tip" wx:if="{{totalSelectedCount > 0}}">
        <text class="tip-text">已激活：{{selectedMarketTab === 'domestic' ? '国内' : '海外'}}</text>
      </view>
    </view>
  </view>'''

# 新的提示代码 - 只显示当前激活市场的已选平台
new_hint = '''  <!-- 已选平台详细提示 - 只显示当前激活市场的已选平台 -->
  <view class="selected-platforms-summary" wx:if="{{selectedModelCount > 0}}">
    <view class="summary-header">
      <text class="summary-icon">🎯</text>
      <text class="summary-title">已选 AI 平台</text>
    </view>
    <view class="summary-content">
      <!-- 国内市场 -->
      <view class="platform-group" wx:if="{{selectedMarketTab === 'domestic' && domesticSelectedNames.length > 0}}">
        <text class="group-label">国内：</text>
        <text class="platform-names">{{domesticSelectedNames}}</text>
        <text class="platform-count">（{{selectedModelCount}}个）</text>
      </view>
      <!-- 海外市场 -->
      <view class="platform-group" wx:if="{{selectedMarketTab === 'overseas' && overseasSelectedNames.length > 0}}">
        <text class="group-label">海外：</text>
        <text class="platform-names">{{overseasSelectedNames}}</text>
        <text class="platform-count">（{{selectedModelCount}}个）</text>
      </view>
    </view>
  </view>'''

if old_hint in content:
    content = content.replace(old_hint, new_hint)
    print("✅ 已更新已选平台提示（只显示当前激活市场）")
else:
    print("❌ 未找到旧提示代码")

with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 文件更新完成!")
print("\n📋 修改内容:")
print("  1. ✅ 移除 totalSelectedCount 条件判断")
print("  2. ✅ 只显示当前激活市场的已选平台")
print("  3. ✅ 国内市场激活时只显示国内已选平台")
print("  4. ✅ 海外市场激活时只显示海外已选平台")
print("  5. ✅ 移除干扰信息")
