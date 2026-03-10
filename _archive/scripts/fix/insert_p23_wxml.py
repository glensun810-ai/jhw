# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml', 'r') as f:
    content = f.read()

# Find the position to insert (after semantic drift section, before source purity section)
insert_marker = "<!-- P1-2 信源纯净度展示 -->"
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the keyword cloud section XML
keyword_cloud_xml = '''  <!-- P2-3 关键词云 -->
  <view class="keyword-cloud-section" wx:if="{{keywordCloudData && keywordCloudData.length > 0}}">
    <text class="section-title">☁️ 品牌关键词云</text>
    
    <!-- 词云展示区 -->
    <view class="word-cloud-container">
      <view class="word-cloud-wrapper" wx:if="{{wordCloudRendered}}">
        <canvas 
          type="2d" 
          id="wordCloudCanvas"
          class="word-cloud-canvas"
          style="width: {{canvasWidth}}px; height: {{canvasHeight}}px;"
        ></canvas>
      </view>
      <view class="word-cloud-placeholder" wx:else>
        <text>正在生成词云...</text>
      </view>
    </view>
    
    <!-- 关键词统计 -->
    <view class="keyword-stats">
      <view class="stat-item">
        <text class="stat-number">{{keywordCloudData.length}}</text>
        <text class="stat-label">关键词数量</text>
      </view>
      <view class="stat-item">
        <text class="stat-number positive">{{keywordStats.positiveCount}}</text>
        <text class="stat-label">正面词</text>
      </view>
      <view class="stat-item">
        <text class="stat-number neutral">{{keywordStats.neutralCount}}</text>
        <text class="stat-label">中性词</text>
      </view>
      <view class="stat-item">
        <text class="stat-number negative">{{keywordStats.negativeCount}}</text>
        <text class="stat-label">负面词</text>
      </view>
    </view>
    
    <!-- 高频词列表 -->
    <view class="top-keywords-section" wx:if="{{topKeywords && topKeywords.length > 0}}">
      <text class="subsection-title">🔥 高频关键词</text>
      <view class="top-keywords-list">
        <view class="top-keyword-item" wx:for="{{topKeywords}}" wx:key="word">
          <text class="keyword-word {{item.sentiment}}">{{item.word}}</text>
          <text class="keyword-count">{{item.count}}</text>
        </view>
      </view>
    </view>
  </view>

'''

# Insert the keyword cloud section
new_content = content[:insert_pos] + keyword_cloud_xml + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml', 'w') as f:
    f.write(new_content)

print("Successfully inserted keyword cloud section!")
