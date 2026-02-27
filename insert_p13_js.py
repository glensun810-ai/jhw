# Read the file
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r') as f:
    content = f.read()

# Find the position to insert (before processSourcePurityData function)
insert_marker = "  /**\n   * P1-2 修复：处理信源纯净度数据\n   */\n  processSourcePurityData: function(competitiveAnalysis, results) {"
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("Marker not found!")
    exit(1)

# Create the processRecommendationData function
recommendation_function = '''  /**
   * P1-3 修复：处理优化建议数据
   */
  processRecommendationData: function(competitiveAnalysis, results) {
    try {
      // 从 backend 获取建议数据
      const recommendations = competitiveAnalysis.recommendations || [];
      
      if (!recommendations || recommendations.length === 0) {
        return { recommendationData: null };
      }
      
      // 统计各优先级数量
      let highPriorityCount = 0;
      let mediumPriorityCount = 0;
      let lowPriorityCount = 0;
      
      // 处理每条建议
      const processedRecommendations = recommendations.map(rec => {
        // 统计优先级
        if (rec.priority === 'high') highPriorityCount++;
        else if (rec.priority === 'medium') mediumPriorityCount++;
        else if (rec.priority === 'low') lowPriorityCount++;
        
        // 转换优先级文本
        const priorityTextMap = {
          'high': '高优先级',
          'medium': '中优先级',
          'low': '低优先级'
        };
        
        // 转换类型文本
        const typeTextMap = {
          'content_correction': '内容纠偏',
          'brand_strengthening': '品牌强化',
          'source_attack': '信源攻坚',
          'risk_mitigation': '风险缓解'
        };
        
        // 转换预估影响文本
        const impactTextMap = {
          'high': '高影响',
          'medium': '中影响',
          'low': '低影响'
        };
        
        return {
          priority: rec.priority || 'medium',
          priorityText: priorityTextMap[rec.priority] || '中优先级',
          type: rec.type || 'content_correction',
          typeText: typeTextMap[rec.type] || '内容纠偏',
          title: rec.title || '优化建议',
          description: rec.description || '',
          target: rec.target || '',
          estimatedImpact: rec.estimated_impact || 'medium',
          estimatedImpactText: impactTextMap[rec.estimated_impact] || '中影响',
          actionSteps: rec.action_steps || [],
          urgency: rec.urgency || 5
        };
      });
      
      return {
        recommendationData: {
          totalCount: recommendations.length,
          highPriorityCount: highPriorityCount,
          mediumPriorityCount: mediumPriorityCount,
          lowPriorityCount: lowPriorityCount,
          recommendations: processedRecommendations
        }
      };
    } catch (e) {
      logger.error('处理优化建议数据失败:', e);
      return {
        recommendationData: null
      };
    }
  },

'''

# Insert the function
new_content = content[:insert_pos] + recommendation_function + content[insert_pos:]

# Write back
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'w') as f:
    f.write(new_content)

print("Successfully inserted processRecommendationData function!")
