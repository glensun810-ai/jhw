#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 WXSS 样式，支持新的提示格式
"""

with open('pages/index/index.wxss', 'r', encoding='utf-8') as f:
    content = f.read()

# 新的样式
new_styles = '''
/* 已选平台提示内容 */
.hint-content {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.hint-text {
  font-size: 26rpx;
  color: #00A9FF;
}

.hint-text .highlight {
  font-weight: 600;
  font-size: 30rpx;
}

.hint-sub {
  font-size: 22rpx;
  color: rgba(0, 169, 255, 0.7);
}
'''

# 查找插入位置
if '.hint-text {' in content:
    # 已存在，跳过
    print("ℹ️  样式已存在")
else:
    # 在 .selected-models-hint 后添加
    content = content.replace(
        '''.hint-text {
  font-size: 26rpx;
  color: #00A9FF;
}''',
        new_styles
    )
    print("✅ 已添加新样式")

with open('pages/index/index.wxss', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXSS 文件更新完成!")
