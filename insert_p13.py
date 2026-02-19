# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml', 'r') as f:
    content = f.read()

# Find the position to insert (before P1-2 source purity section)
insert_marker = "<!-- P1-2 信源纯净度展示 -->"
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the recommendation section XML
recommendation_xml = '''  <!-- P1-3 优化建议列表 -->
  <view class="recommendation-section" wx:if="{{recommendationData && recommendationData.recommendations && recommendationData.recommendations.length > 0}}">
    <text class="section-title">💡 优化建议</text>
    
    <!-- 建议概览 -->
    <view class="recommendation-overview">
      <view class="overview-item">
        <text class="overview-number">{{recommendationData.totalCount}}</text>
        <text class="overview-label">建议总数</text>
      </view>
      <view class="overview-item">
        <text class="overview-number high">{{recommendationData.highPriorityCount}}</text>
        <text class="overview-label">高优先级</text>
      </view>
      <view class="overview-item">
        <text class="overview-number medium">{{recommendationData.mediumPriorityCount}}</text>
        <text class="overview-label">中优先级</text>
      </view>
      <view class="overview-item">
        <text class="overview-number low">{{recommendationData.lowPriorityCount}}</text>
        <text class="overview-label">低优先级</text>
      </view>
    </view>

    <!-- 建议列表 -->
    <view class="recommendation-list">
      <view class="recommendation-card" wx:for="{{recommendationData.recommendations}}" wx:key="index">
        <view class="card-header {{item.priority}}">
          <text class="priority-tag {{item.priority}}">{{item.priorityText}}</text>
          <text class="type-tag {{item.type}}">{{item.typeText}}</text>
          <text class="urgency-score">紧急度：{{item.urgency}}/10</text>
        </view>
        <view class="card-body">
          <text class="card-title">{{item.title}}</text>
          <text class="card-description">{{item.description}}</text>
          
          <!-- 行动步骤 -->
          <view class="action-steps" wx:if="{{item.actionSteps && item.actionSteps.length > 0}}">
            <text class="steps-title">📋 行动步骤：</text>
            <view class="step-item" wx:for="{{item.actionSteps}}" wx:key="index">
              <text class="step-number">{{index + 1}}</text>
              <text class="step-text">{{item}}</text>
            </view>
          </view>
          
          <!-- 目标对象 -->
          <view class="target-info" wx:if="{{item.target}}">
            <text class="target-label">🎯 目标对象：</text>
            <text class="target-value">{{item.target}}</text>
          </view>
          
          <!-- 预估影响 -->
          <view class="impact-info">
            <text class="impact-label">📊 预估影响：</text>
            <text class="impact-value {{item.estimatedImpact}}">{{item.estimatedImpactText}}</text>
          </view>
        </view>
      </view>
    </view>
  </view>

'''

# Insert the recommendation section
new_content = content[:insert_pos] + recommendation_xml + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml', 'w') as f:
    f.write(new_content)

print("Successfully inserted recommendation section!")
