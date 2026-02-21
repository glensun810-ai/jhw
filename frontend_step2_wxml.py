#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 2: 修改 detail/index.wxml 添加实时统计 UI

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在进度条后添加实时统计显示
old_progress_section = '''      <!--【P0 新增】详细进度显示 -->
      <view class="progress-detail-container" wx:if="{{progressDetail}}">
        <text class="progress-detail">{{progressDetail}}</text>
      </view>'''

new_progress_section = '''      <!--【P0 新增】详细进度显示 -->
      <view class="progress-detail-container" wx:if="{{progressDetail}}">
        <text class="progress-detail">{{progressDetail}}</text>
      </view>
      
      <!--【阶段 1】实时统计显示 -->
      <view class="realtime-stats-container" wx:if="{{realtimeStats && realtimeStats.completed > 0}}">
        <view class="stats-header">
          <text class="stats-title">📊 实时统计</text>
          <text class="stats-subtitle">已处理 {{realtimeStats.completed}}/{{realtimeStats.total}}</text>
        </view>
        
        <view class="stats-grid">
          <view class="stat-item">
            <text class="stat-value highlight">{{realtimeSov}}%</text>
            <text class="stat-label">SOV</text>
          </view>
          <view class="stat-item">
            <text class="stat-value {{realtimeSentiment >= 0.5 ? 'positive' : realtimeSentiment >= 0.3 ? 'neutral' : 'negative'}}">{{realtimeSentiment}}</text>
            <text class="stat-label">情感</text>
          </view>
          <view class="stat-item">
            <text class="stat-value">{{brandRankings.length}}</text>
            <text class="stat-label">品牌已排名</text>
          </view>
        </view>
        
        <!-- 品牌实时排名 -->
        <view class="brand-rankings-container" wx:if="{{brandRankings.length > 0}}">
          <text class="rankings-title">🏆 品牌实时排名</text>
          <view class="rankings-list">
            <block wx:for="{{brandRankings}}" wx:key="brand">
              <view class="ranking-item {{item.is_main_brand ? 'main-brand' : ''}}">
                <view class="ranking-left">
                  <text class="ranking-rank">#{{item.rank}}</text>
                  <text class="ranking-brand">{{item.brand}}</text>
                  <text class="ranking-main" wx:if="{{item.is_main_brand}}">主品牌</text>
                </view>
                <view class="ranking-right">
                  <text class="ranking-responses">{{item.responses}}响应</text>
                  <text class="ranking-sentiment">情感{{item.avg_sentiment}}</text>
                </view>
              </view>
            </block>
          </view>
        </view>
      </view>
      
      <!--【阶段 2】聚合结果显示 -->
      <view class="aggregated-results-container" wx:if="{{aggregatedResults && aggregatedResults.summary}}">
        <view class="results-header">
          <text class="results-title">📈 聚合分析结果</text>
          <text class="results-subtitle">健康度：{{healthScore}}分</text>
        </view>
        
        <view class="results-grid">
          <view class="result-item">
            <view class="result-value {{healthScore >= 80 ? 'excellent' : healthScore >= 60 ? 'good' : 'warning'}}">{{healthScore}}</view>
            <text class="result-label">健康度</text>
          </view>
          <view class="result-item">
            <view class="result-value">{{aggregatedResults.summary.sov}}%</view>
            <text class="result-label">SOV</text>
          </view>
          <view class="result-item">
            <view class="result-value">{{aggregatedResults.summary.avgSentiment}}</view>
            <text class="result-label">情感</text>
          </view>
          <view class="result-item">
            <view class="result-value">{{aggregatedResults.summary.successRate}}%</view>
            <text class="result-label">成功率</text>
          </view>
        </view>
        
        <!-- 品牌排名详情 -->
        <view class="brand-rankings-detail" wx:if="{{aggregatedResults.brand_rankings && aggregatedResults.brand_rankings.length > 0}}">
          <text class="rankings-detail-title">🏆 品牌排名详情</text>
          <view class="rankings-detail-list">
            <block wx:for="{{aggregatedResults.brand_rankings}}" wx:key="brand">
              <view class="ranking-detail-item {{item.is_main_brand ? 'main-brand' : ''}}">
                <view class="ranking-detail-header">
                  <text class="ranking-detail-rank">#{{item.rank}}</text>
                  <text class="ranking-detail-brand">{{item.brand}}</text>
                  <text class="ranking-detail-main" wx:if="{{item.is_main_brand}}">主品牌</text>
                </view>
                <view class="ranking-detail-stats">
                  <view class="detail-stat">
                    <text class="detail-stat-label">响应数</text>
                    <text class="detail-stat-value">{{item.responses}}</text>
                  </view>
                  <view class="detail-stat">
                    <text class="detail-stat-label">SOV</text>
                    <text class="detail-stat-value">{{item.sov_share}}%</text>
                  </view>
                  <view class="detail-stat">
                    <text class="detail-stat-label">情感</text>
                    <text class="detail-stat-value">{{item.avg_sentiment}}</text>
                  </view>
                  <view class="detail-stat" wx:if="{{item.avg_rank > 0}}">
                    <text class="detail-stat-label">平均排名</text>
                    <text class="detail-stat-value">{{item.avg_rank}}</text>
                  </view>
                </view>
              </view>
            </block>
          </view>
        </view>
      </view>'''

content = content.replace(old_progress_section, new_progress_section)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 2 完成：实时统计 UI 已添加')
