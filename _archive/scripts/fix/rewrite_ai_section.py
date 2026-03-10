#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完全重写 AI 模型选择部分
"""

with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换
old_start = '''      <!-- AI 模型选择 -->
      <view class="setting-block">
        <view class="setting-title">
          <text>AI 平台矩阵</text>
          <text class="setting-subtitle">选择您想诊断的 AI 平台</text>
        </view>
        <view class="ai-model-selection">
        <!-- 市场分段选择器 -->'''

new_start = '''      <!-- AI 模型选择 -->
      <view class="setting-block">
        <view class="setting-title">
          <text>AI 平台矩阵</text>
          <text class="setting-subtitle">请选择目标分析市场，系统将自动匹配该区域最具代表性的 AI 搜索引擎</text>
        </view>
        
        <!-- 市场分段选择器 -->'''

if old_start in content:
    content = content.replace(old_start, new_start)
    print("✅ 已修复开头部分")
else:
    print("❌ 未找到开头")

# 修复国内标题
content = content.replace(
    '<text class="category-title">国内 AI 平台</text>',
    '<text class="category-title">国内主流 AI 平台</text>'
)
print("✅ 已修复国内标题")

# 修复海外标题
content = content.replace(
    '<text class="category-title">海外 AI 平台</text>',
    '<text class="category-title">海外主流 AI 平台</text>'
)
print("✅ 已修复海外标题")

# 修复结构 - 移除 ai-model-selection 内的分段选择器
content = content.replace(
    '''<view class="ai-model-selection">
        <!-- 市场分段选择器 -->''',
    '''<view class="ai-model-selection">'''
)
print("✅ 已修复结构")

# 添加已选平台提示
old_end = '''        </view>
      </view>
    </view>

    <!-- 保存配置模态框 -->'''

new_end = '''        </view>
        
        <!-- 已选平台提示 -->
        <view class="selected-models-hint" wx:if="{{selectedModelCount > 0}}">
          <text class="hint-icon">✓</text>
          <text class="hint-text">已选择 {{selectedModelCount}} 个 AI 平台</text>
        </view>
      </view>
    </view>

    <!-- 保存配置模态框 -->'''

if old_end in content:
    content = content.replace(old_end, new_end)
    print("✅ 已添加已选平台提示")
else:
    print("❌ 未找到结束位置")

with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 文件修复完成!")
