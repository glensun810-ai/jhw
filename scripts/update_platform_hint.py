#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改已选平台提示：只显示当前激活市场的已选平台
"""

with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换主条件判断
content = content.replace(
    'wx:if="{{selectedModelCount > 0 || totalSelectedCount > 0}}"',
    'wx:if="{{selectedModelCount > 0}}"'
)
print("✅ 已更新主条件判断")

# 2. 替换国内平台显示条件
old_domestic = 'wx:if="{{domesticSelectedNames.length > 0}}"'
new_domestic = 'wx:if="{{selectedMarketTab == \'domestic\' && domesticSelectedNames.length > 0}}"'
content = content.replace(old_domestic, new_domestic)
print("✅ 已更新国内平台显示条件")

# 3. 替换海外平台显示条件
old_overseas = 'wx:if="{{overseasSelectedNames.length > 0}}"'
new_overseas = 'wx:if="{{selectedMarketTab == \'overseas\' && overseasSelectedNames.length > 0}}"'
content = content.replace(old_overseas, new_overseas)
print("✅ 已更新海外平台显示条件")

# 4. 移除 summary-tip
old_tip = '''            <view class="summary-tip" wx:if="{{totalSelectedCount > 0}}">
              <text class="tip-text">已激活：{{selectedMarketTab === 'domestic' ? '国内' : '海外'}}</text>
            </view>'''
content = content.replace(old_tip, '')
print("✅ 已移除提示行")

# 5. 更新海外平台计数
content = content.replace(
    '（{{totalSelectedCount - selectedModelCount}}个）',
    '（{{selectedModelCount}}个）'
)
print("✅ 已统一计数显示")

with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 文件更新完成!")
print("\n📋 修改内容:")
print("  1. ✅ 主条件改为 selectedModelCount > 0")
print("  2. ✅ 国内平台显示添加 selectedMarketTab == 'domestic' 条件")
print("  3. ✅ 海外平台显示添加 selectedMarketTab == 'overseas' 条件")
print("  4. ✅ 移除已激活提示行")
print("  5. ✅ 统一计数显示为 selectedModelCount")
