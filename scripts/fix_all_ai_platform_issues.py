#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面修复 AI 平台矩阵选择模块
按优先级修复所有测试发现的问题
"""

with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 开始修复 AI 平台矩阵选择模块...")

# P0-1: 修复 WXML 结构 - 将分段选择器移到 ai-model-selection 外部
old_structure = '''      <!-- AI 模型选择 -->
      <view class="setting-block">
        <view class="setting-title">
          <text>AI 平台矩阵</text>
          <text class="setting-subtitle">选择您想诊断的 AI 平台</text>
        </view>
        <view class="ai-model-selection">
        <!-- 市场分段选择器 -->
        <view class="market-segmented-control">'''

new_structure = '''      <!-- AI 模型选择 -->
      <view class="setting-block">
        <view class="setting-title">
          <text>AI 平台矩阵</text>
          <text class="setting-subtitle">请选择目标分析市场，系统将自动匹配该区域最具代表性的 AI 搜索引擎</text>
        </view>
        
        <!-- 市场分段选择器 -->
        <view class="market-segmented-control">'''

if old_structure in content:
    content = content.replace(old_structure, new_structure)
    print("✅ P0-1: 已修复 WXML 结构，更新 subtitle 文案")
else:
    print("❌ P0-1: 未找到旧结构，可能已部分修改")
    # 尝试只修复 subtitle
    content = content.replace('选择您想诊断的 AI 平台', '请选择目标分析市场，系统将自动匹配该区域最具代表性的 AI 搜索引擎')
    print("   已尝试只修复 subtitle")

# P0-3: 确保 .hidden 类在 WXSS 中定义（稍后处理 app.wxss）

# P1-4: 更新国内 AI 平台标题
content = content.replace(
    '<text class="category-title">国内 AI 平台</text>',
    '<text class="category-title">国内主流 AI 平台</text>'
)
print("✅ P1-4: 已更新国内 AI 平台标题")

# P1-5: 更新海外 AI 平台标题
content = content.replace(
    '<text class="category-title">海外 AI 平台</text>',
    '<text class="category-title">海外主流 AI 平台</text>'
)
print("✅ P1-5: 已更新海外 AI 平台标题")

# P1-6: 添加"已选平台提示"区域 - 在 ai-model-selection 结束标签前
old_close = '''        </view>
      </view>
    </view>

    <!-- 保存配置模态框 -->'''

new_close = '''        </view>
        
        <!-- 已选平台提示 -->
        <view class="selected-models-hint" wx:if="{{selectedModelCount > 0}}">
          <text class="hint-icon">✓</text>
          <text class="hint-text">已选择 {{selectedModelCount}} 个 AI 平台</text>
        </view>
      </view>
    </view>

    <!-- 保存配置模态框 -->'''

if old_close in content:
    content = content.replace(old_close, new_close)
    print("✅ P1-6: 已添加已选平台提示")
else:
    print("❌ P1-6: 未找到插入位置")

with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 修复完成!")

# 修复 app.wxss - 添加 .hidden 类定义
with open('app.wxss', 'r', encoding='utf-8') as f:
    app_wxss = f.read()

# 检查是否已有 .hidden 类
if '.hidden {' not in app_wxss and '.hidden {' not in open('pages/index/index.wxss', 'r', encoding='utf-8').read():
    # 在文件末尾添加
    hidden_style = '''
/* ==================== 显示控制 ==================== */
.hidden {
  display: none !important;
}
'''
    app_wxss += hidden_style
    with open('app.wxss', 'w', encoding='utf-8') as f:
        f.write(app_wxss)
    print("✅ P0-3: 已在 app.wxss 添加 .hidden 类定义")
else:
    print("ℹ️  P0-3: .hidden 类已存在")

print("\n✅ 所有修复完成!")
