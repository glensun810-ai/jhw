#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加已选平台详细提示的样式
"""

with open('pages/index/index.wxss', 'r', encoding='utf-8') as f:
    content = f.read()

# 新样式
new_styles = '''
/* ==================== 已选平台详细提示 ==================== */
.selected-platforms-summary {
  margin: 24rpx 0;
  padding: 24rpx;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%);
  border-radius: 16rpx;
  border: 2rpx solid rgba(59, 130, 246, 0.3);
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.summary-icon {
  font-size: 32rpx;
}

.summary-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #00A9FF;
}

.summary-content {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.platform-group {
  display: flex;
  align-items: flex-start;
  gap: 8rpx;
  flex-wrap: wrap;
}

.group-label {
  font-size: 26rpx;
  font-weight: 600;
  color: #00A9FF;
  flex-shrink: 0;
}

.platform-names {
  font-size: 26rpx;
  color: #e8e8e8;
  flex: 1;
}

.platform-count {
  font-size: 24rpx;
  color: rgba(0, 169, 255, 0.8);
  flex-shrink: 0;
}

.summary-tip {
  margin-top: 8rpx;
  padding: 12rpx;
  background-color: rgba(0, 169, 255, 0.08);
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.tip-icon {
  font-size: 28rpx;
  flex-shrink: 0;
}

.tip-text {
  font-size: 24rpx;
  color: rgba(0, 169, 255, 0.9);
  line-height: 1.5;
}
'''

# 查找插入位置 - 在 .hint-sub 之后
if '.hint-sub {' in content:
    # 在.hint-sub 块结束后插入
    marker = '''.hint-sub {
  font-size: 26rpx;
  color: #00A9FF;
}'''
    if marker in content:
        content = content.replace(marker, marker + '\n' + new_styles)
        print("✅ 已添加已选平台详细提示样式")
    else:
        print("❌ 未找到.hint-sub 样式块")
else:
    print("❌ 未找到插入位置")

with open('pages/index/index.wxss', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXSS 文件更新完成!")
