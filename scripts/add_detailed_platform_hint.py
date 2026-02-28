#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 WXML 中添加详细的已选平台提示信息（第 37 行位置）
"""

with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

# 在第 37 行位置（我方品牌区域后）添加详细提示
# 找到"敌方阵营"的注释位置，在它前面插入
old_vs_icon = '''      </view>

      <view class="vs-icon">VS</view>'''

new_content = '''      </view>

      <!-- 已选平台详细提示 -->
      <view class="selected-platforms-summary" wx:if="{{selectedModelCount > 0 || totalSelectedCount > 0}}">
        <view class="summary-header">
          <text class="summary-icon">🎯</text>
          <text class="summary-title">已选 AI 平台</text>
        </view>
        <view class="summary-content">
          <view class="platform-group" wx:if="{{domesticSelectedNames.length > 0}}">
            <text class="group-label">国内：</text>
            <text class="platform-names">{{domesticSelectedNames}}</text>
            <text class="platform-count">（{{domesticSelectedNames.length}}个）</text>
          </view>
          <view class="platform-group" wx:if="{{overseasSelectedNames.length > 0}}">
            <text class="group-label">海外：</text>
            <text class="platform-names">{{overseasSelectedNames}}</text>
            <text class="platform-count">（{{overseasSelectedNames.length}}个）</text>
          </view>
          <view class="summary-tip" wx:if="{{totalSelectedCount > 0}}">
            <text class="tip-icon">💡</text>
            <text class="tip-text">当前激活：{{selectedMarketTab === 'domestic' ? '国内' : '海外'}}市场，提交时只包含当前市场的 {{selectedModelCount}} 个平台</text>
          </view>
        </view>
      </view>

      <view class="vs-icon">VS</view>'''

if old_vs_icon in content:
    content = content.replace(old_vs_icon, new_content)
    print("✅ 已添加详细的已选平台提示信息")
else:
    print("❌ 未找到插入位置")

with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 文件更新完成!")
print("\n📋 新增功能:")
print("  1. ✅ 显示国内平台选择列表和数量")
print("  2. ✅ 显示海外平台选择列表和数量")
print("  3. ✅ 提示当前激活的市场和提交时的平台数量")
print("  4. ✅ 只在有选中平台时显示")
