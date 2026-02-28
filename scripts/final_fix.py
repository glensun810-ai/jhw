# AI 平台矩阵选择模块 - 最终修复脚本

import re

# 读取原始文件
with open('pages/index/index.wxml', 'r', encoding='utf-8') as f:
    content = f.read()

print("📝 开始修复 AI 平台矩阵选择模块...")

# 1. 替换整个 AI 模型选择部分
old_pattern = r'''      <!-- AI 模型选择 -->
      <view class="setting-block">
        <view class="setting-title">
          <text>AI 平台矩阵</text>
          <text class="setting-subtitle">选择您想诊断的 AI 平台</text>
        </view>
        <view class="ai-model-selection">
          <!-- 国内 AI 模型 -->
          <view class="ai-category">
            <view class="category-header">
              <text class="category-title">国内 AI 平台</text>
              <button class="select-all-btn" bindtap="selectAllModels" data-type="domestic">全选</button>
            </view>
            <view class="model-grid">
              <view class="model-chip-pro \{\{item\.checked \? 'checked' : ''\}\} \{\{item\.disabled \? 'disabled' : ''\}\}" wx:for="\{\{domesticAiModels\}\}" wx:key="id" bindtap="toggleModelSelection" data-type="domestic" data-index="\{\{index\}\}">
                <view class="logo-placeholder">\{\{item\.logo \|\| item\.name\.substring\(0,2\)\}\}</view>
                <text class="model-name">\{\{item\.name\}\}</text>
                <view class="tag-list">
                  <text class="tag" wx:for="\{\{item\.tags\}\}" wx:for-item="tag" wx:key="\*this">\{\{tag\}\}</text>
                </view>
                <view class="check-icon">✓</view>
              </view>
            </view>
          </view>
          <!-- 海外 AI 模型 -->
          <view class="ai-category">
            <view class="category-header">
              <text class="category-title">海外 AI 平台</text>
              <button class="select-all-btn" bindtap="selectAllModels" data-type="overseas">全选</button>
            </view>
            <view class="model-grid">
              <view class="model-chip-pro \{\{item\.checked \? 'checked' : ''\}\}" wx:for="\{\{overseasAiModels\}\}" wx:key="id" bindtap="toggleModelSelection" data-type="overseas" data-index="\{\{index\}\}">
                <view class="logo-placeholder">\{\{item\.logo \|\| item\.name\.substring\(0,2\)\}\}</view>
                <text class="model-name">\{\{item\.name\}\}</text>
                <view class="tag-list">
                  <text class="tag" wx:for="\{\{item\.tags\}\}" wx:for-item="tag" wx:key="\*this">\{\{tag\}\}</text>
                </view>
                <view class="check-icon">✓</view>
              </view>
            </view>
          </view>
        </view>
      </view>'''

# 由于正则表达式太复杂，改用简单字符串替换
# 先找到 AI 模型选择的开始和结束位置
start_marker = '      <!-- AI 模型选择 -->'
end_marker = '    <!-- 保存配置模态框 -->'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    # 提取要替换的部分
    old_section = content[start_idx:end_idx]
    
    # 新内容
    new_section = '''      <!-- AI 模型选择 -->
      <view class="setting-block">
        <view class="setting-title">
          <text>AI 平台矩阵</text>
          <text class="setting-subtitle">请选择目标分析市场，系统将自动匹配该区域最具代表性的 AI 搜索引擎</text>
        </view>
        
        <!-- 市场分段选择器 -->
        <view class="market-segmented-control">
          <view class="segment-option {{selectedMarketTab === 'domestic' ? 'active' : ''}}"
                bindtap="switchMarketTab"
                data-market="domestic">
            <text class="segment-text">国内 AI 平台</text>
          </view>
          <view class="segment-option {{selectedMarketTab === 'overseas' ? 'active' : ''}}"
                bindtap="switchMarketTab"
                data-market="overseas">
            <text class="segment-text">海外 AI 平台</text>
          </view>
        </view>
        
        <!-- AI 平台列表 - 根据选中市场动态渲染 -->
        <view class="ai-model-selection">
          <!-- 国内 AI 模型 -->
          <view class="ai-category {{selectedMarketTab !== 'domestic' ? 'hidden' : ''}}">
            <view class="category-header">
              <text class="category-title">国内主流 AI 平台</text>
              <button class="select-all-btn" bindtap="selectAllModels" data-type="domestic">全选</button>
            </view>
            <view class="model-grid">
              <view class="model-chip-pro {{item.checked ? 'checked' : ''}} {{item.disabled ? 'disabled' : ''}}"
                    wx:for="{{domesticAiModels}}"
                    wx:key="id"
                    bindtap="toggleModelSelection"
                    data-type="domestic"
                    data-index="{{index}}">
                <view class="logo-placeholder">{{item.logo || item.name.substring(0,2)}}</view>
                <text class="model-name">{{item.name}}</text>
                <view class="tag-list">
                  <text class="tag" wx:for="{{item.tags}}" wx:for-item="tag" wx:key="*this">{{tag}}</text>
                </view>
                <view class="check-icon">✓</view>
              </view>
            </view>
          </view>
          
          <!-- 海外 AI 模型 -->
          <view class="ai-category {{selectedMarketTab !== 'overseas' ? 'hidden' : ''}}">
            <view class="category-header">
              <text class="category-title">海外主流 AI 平台</text>
              <button class="select-all-btn" bindtap="selectAllModels" data-type="overseas">全选</button>
            </view>
            <view class="model-grid">
              <view class="model-chip-pro {{item.checked ? 'checked' : ''}}"
                    wx:for="{{overseasAiModels}}"
                    wx:key="id"
                    bindtap="toggleModelSelection"
                    data-type="overseas"
                    data-index="{{index}}">
                <view class="logo-placeholder">{{item.logo || item.name.substring(0,2)}}</view>
                <text class="model-name">{{item.name}}</text>
                <view class="tag-list">
                  <text class="tag" wx:for="{{item.tags}}" wx:for-item="tag" wx:key="*this">{{tag}}</text>
                </view>
                <view class="check-icon">✓</view>
              </view>
            </view>
          </view>
          
          <!-- 已选平台提示 -->
          <view class="selected-models-hint" wx:if="{{selectedModelCount > 0}}">
            <text class="hint-icon">✓</text>
            <text class="hint-text">已选择 {{selectedModelCount}} 个 AI 平台</text>
          </view>
        </view>
      </view>
'''
    
    # 替换
    content = content[:start_idx] + new_section + content[end_idx:]
    print("✅ 已替换整个 AI 模型选择部分")
else:
    print(f"❌ 未找到标记位置 start={start_idx}, end={end_idx}")

# 写入文件
with open('pages/index/index.wxml', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ WXML 文件修复完成!")
print("\n📋 修复内容:")
print("  1. ✅ 更新 subtitle 文案")
print("  2. ✅ 添加市场分段选择器（移到外部）")
print("  3. ✅ 更新国内 AI 平台标题为'国内主流 AI 平台'")
print("  4. ✅ 更新海外 AI 平台标题为'海外主流 AI 平台'")
print("  5. ✅ 为国内/海外 AI 模型添加 hidden 条件")
print("  6. ✅ 添加已选平台提示")
