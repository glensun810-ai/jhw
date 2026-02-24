#!/usr/bin/env python3
"""修复信源情报展示空状态"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换信源情报展示部分
old_text = '''  <!-- 信源情报展示 -->
  <view class="source-intelligence-section" wx:if="{{showSourceIntelligence}}">
    <text class="section-title">🔍 信源情报分析</text>
    <view class="intelligence-graph">
      <view class="graph-node" wx:for="{{sourceIntelligenceMap.nodes}}" wx:key="id" bindtap="viewSourceDetails" data-id="{{item.id}}">
        <view class="node-content {{item.category}}">
          <text class="node-name">{{item.name}}</text>
          <text class="node-weight" wx:if="{{item.value}}">权重：{{item.value}}</text>
          <text class="node-sentiment" wx:if="{{item.sentiment}}">情感：{{item.sentiment}}</text>
        </view>
      </view>
    </view>
  </view>'''

new_text = '''  <!-- 信源情报展示 -->
  <view class="source-intelligence-section">
    <text class="section-title">🔍 信源情报分析</text>
    
    <!-- 有数据时展示 -->
    <block wx:if="{{sourceIntelligenceMap && sourceIntelligenceMap.nodes && sourceIntelligenceMap.nodes.length > 0}}">
      <view class="intelligence-graph">
        <view class="graph-node" wx:for="{{sourceIntelligenceMap.nodes}}" wx:key="id" bindtap="viewSourceDetails" data-id="{{item.id}}">
          <view class="node-content {{item.category}}">
            <text class="node-name">{{item.name}}</text>
            <text class="node-weight" wx:if="{{item.value}}">权重：{{item.value}}</text>
            <text class="node-sentiment" wx:if="{{item.sentiment}}">情感：{{item.sentiment}}</text>
          </view>
        </view>
      </view>
    </block>

    <!-- 无数据时展示空状态 -->
    <view wx:else class="empty-state">
      <text class="empty-icon">🔍</text>
      <text class="empty-text">信源情报图谱数据生成中</text>
      <text class="empty-hint">后端正在构建信源关系图谱，请稍后查看</text>
    </view>
  </view>'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 信源情报展示空状态修复完成")
else:
    print("⚠️ 未找到目标文本，可能已修复或格式不同")
    # 尝试查找类似内容
    if 'source-intelligence-section' in content:
        print("✅ 信源情报展示部分已存在")
