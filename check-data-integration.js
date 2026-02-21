/**
 * 前端数据对接全面检查脚本
 * 
 * 检查所有前端显示字段是否正确对接后台数据
 */

(function() {
  console.log('\n' + '='.repeat(80));
  console.log('🔍 前端数据对接全面检查');
  console.log('='.repeat(80) + '\n');

  const checks = {
    passed: 0,
    failed: 0,
    warnings: 0,
    details: []
  };

  // 读取存储数据
  const lastReport = wx.getStorageSync('last_diagnostic_report');
  
  if (!lastReport) {
    console.log('❌ 未找到诊断报告，请先执行诊断');
    return;
  }

  console.log('✅ 找到诊断报告');
  console.log(`   执行 ID: ${lastReport.executionId}`);
  console.log(`   品牌：${lastReport.brandName}`);
  console.log(`   保存时间：${new Date(lastReport.savedAt).toLocaleString()}`);
  console.log('');

  const dashboard = lastReport.dashboard;
  const rawResults = lastReport.rawResults || [];

  if (!dashboard) {
    console.log('❌ Dashboard 数据不存在');
    console.log('💡 数据格式可能不正确，请重新执行诊断');
    return;
  }

  // ========== 检查 1: Summary 数据 ==========
  console.log('📋 检查 1: Summary 数据（品牌健康度）\n');
  
  const summary = dashboard.summary || {};
  
  const summaryChecks = [
    { name: 'brandName', value: summary.brandName, required: true },
    { name: 'healthScore', value: summary.healthScore, required: true, min: 0 },
    { name: 'sov', value: summary.sov, required: true, min: 0 },
    { name: 'sov_value', value: summary.sov_value, required: false },
    { name: 'avgSentiment', value: summary.avgSentiment, required: true },
    { name: 'sentiment_value', value: summary.sentiment_value, required: false },
    { name: 'sovLabel', value: summary.sovLabel, required: true },
    { name: 'sovLabelClass', value: summary.sovLabelClass, required: true },
    { name: 'sentimentStatus', value: summary.sentimentStatus, required: true },
    { name: 'sentimentLabel', value: summary.sentimentLabel, required: true },
    { name: 'riskLevel', value: summary.riskLevel, required: true },
    { name: 'riskLevelText', value: summary.riskLevelText, required: true },
    { name: 'totalMentions', value: summary.totalMentions, required: true },
    { name: 'totalTests', value: summary.totalTests, required: true },
    { name: 'healthBreakdown', value: summary.healthBreakdown, required: false }
  ];

  summaryChecks.forEach(check => {
    const hasValue = check.value !== undefined && check.value !== null && check.value !== '';
    const isValid = hasValue && (check.min === undefined || check.value >= check.min);
    
    if (isValid || (!check.required && !hasValue)) {
      console.log(`✅ ${check.name}: ${check.value !== undefined ? check.value : '使用备选'}`);
      checks.passed++;
    } else {
      console.log(`❌ ${check.name}: ${hasValue ? `值无效 (${check.value})` : '缺失'}${check.required ? ' (必填)' : ' (可选)'}`);
      if (check.required) {
        checks.failed++;
      } else {
        checks.warnings++;
      }
    }
  });

  // ========== 检查 2: 问题卡片数据 ==========
  console.log('\n📋 检查 2: 问题卡片数据\n');
  
  const questionCards = dashboard.questionCards || [];
  
  if (questionCards.length === 0) {
    console.log('❌ 问题卡片数据为空');
    checks.failed++;
  } else {
    console.log(`✅ 问题数量：${questionCards.length}`);
    checks.passed++;
    
    questionCards.forEach((q, i) => {
      console.log(`\n   问题 ${i + 1}: ${q.text || q.question_text || '未知'}`);
      
      const qChecks = [
        { name: 'avgRank/avg_rank', value: q.avgRank || q.avg_rank },
        { name: 'mentionRate/mention_rate', value: q.mentionRate || q.mention_rate },
        { name: 'avgSentiment/avg_sentiment', value: q.avgSentiment || q.avg_sentiment },
        { name: 'riskLevel/risk_level', value: q.riskLevel || q.risk_level },
        { name: 'riskLevelText', value: q.riskLevelText },
        { name: 'mentionCount', value: q.mentionCount },
        { name: 'totalModels', value: q.totalModels },
        { name: 'key_competitor', value: q.key_competitor }
      ];
      
      qChecks.forEach(qc => {
        if (qc.value !== undefined && qc.value !== null && qc.value !== '') {
          console.log(`   ✅ ${qc.name}: ${qc.value}`);
        } else {
          console.log(`   ❌ ${qc.name}: 缺失`);
          checks.warnings++;
        }
      });
    });
  }

  // ========== 检查 3: 信源数据 ==========
  console.log('\n📋 检查 3: 信源数据\n');
  
  const allSources = dashboard.allSources || [];
  const toxicSources = dashboard.toxicSources || [];
  const questionSources = dashboard.questionSources || [];
  const sourceStats = dashboard.sourceStats || {};
  
  console.log('信源统计:');
  console.log(`   - 总信源：${sourceStats.total_sources || 0}`);
  console.log(`   - 正面信源：${sourceStats.positive_sources || 0}`);
  console.log(`   - 中性信源：${sourceStats.neutral_sources || 0}`);
  console.log(`   - 负面信源：${sourceStats.negative_sources || 0}`);
  
  if (sourceStats.total_sources > 0 || toxicSources.length > 0) {
    console.log('✅ 信源数据存在');
    checks.passed++;
  } else {
    console.log('⚠️  信源数据为空（可能是旧数据格式）');
    checks.warnings++;
  }
  
  if (allSources.length > 0) {
    console.log(`\n   信源影响力 TOP3:`);
    allSources.slice(0, 3).forEach((s, i) => {
      console.log(`   ${i + 1}. ${s.site_name || s.site || '未知'}`);
      console.log(`      影响力：${s.influence_score || s.influenceScore || 0}`);
      console.log(`      提及：${s.total_mentions || s.totalMentions || 0}次`);
      console.log(`      态度：${s.dominant_attitude || s.dominantAttitude || 'neutral'}`);
    });
    checks.passed++;
  } else {
    console.log('\n⚠️  完整信源列表为空');
    checks.warnings++;
  }

  // ========== 检查 4: 被拦截话题 ==========
  console.log('\n📋 检查 4: 被拦截话题\n');
  
  const interceptedTopics = dashboard.interceptedTopics || [];
  
  console.log(`话题数量：${interceptedTopics.length}`);
  
  if (interceptedTopics.length > 0) {
    console.log('✅ 被拦截话题数据存在');
    checks.passed++;
    
    interceptedTopics.forEach((t, i) => {
      console.log(`   ${i + 1}. ${t.topic || '未知'}`);
      console.log(`      频率：${t.frequency || 0}`);
      console.log(`      占比：${t.percentage || 0}%`);
      console.log(`      风险：${t.risk_level || t.riskLevel || '未知'}`);
    });
  } else {
    console.log('ℹ️  未被拦截话题（正常）');
    checks.passed++;
  }

  // ========== 检查 5: 原始数据完整性 ==========
  console.log('\n📋 检查 5: 原始数据完整性\n');
  
  console.log(`原始结果数：${rawResults.length}`);
  
  if (rawResults.length === 0) {
    console.log('❌ 原始结果数据为空');
    checks.failed++;
  } else {
    console.log('✅ 原始结果数据存在');
    checks.passed++;
    
    // 检查 geo_data 完整性
    let geoDataCount = 0;
    let sourcesCount = 0;
    let rankCount = 0;
    let sentimentCount = 0;
    
    rawResults.forEach(r => {
      if (r.geo_data) geoDataCount++;
      if (r.geo_data?.cited_sources && r.geo_data.cited_sources.length > 0) {
        sourcesCount += r.geo_data.cited_sources.length;
      }
      if (r.geo_data?.rank !== undefined && r.geo_data.rank !== null) {
        rankCount++;
      }
      if (r.geo_data?.sentiment !== undefined && r.geo_data.sentiment !== null) {
        sentimentCount++;
      }
    });
    
    console.log(`   - 有 geo_data 的记录：${geoDataCount}/${rawResults.length}`);
    console.log(`   - 有信源引用的记录：${sourcesCount}个信源`);
    console.log(`   - 有排名的记录：${rankCount}/${rawResults.length}`);
    console.log(`   - 有情感的记录：${sentimentCount}/${rawResults.length}`);
    
    if (geoDataCount === rawResults.length) {
      console.log('   ✅ geo_data 完整');
      checks.passed++;
    } else {
      console.log('   ⚠️  geo_data 不完整');
      checks.warnings++;
    }
  }

  // ========== 总结 ==========
  console.log('\n' + '='.repeat(80));
  console.log('📊 数据对接检查总结');
  console.log('='.repeat(80));
  
  console.log(`\n通过：${checks.passed}`);
  console.log(`失败：${checks.failed}`);
  console.log(`警告：${checks.warnings}`);
  
  const totalCritical = checks.passed + checks.failed;
  const passRate = totalCritical > 0 ? Math.round((checks.passed / totalCritical) * 100) : 0;
  
  console.log(`\n关键数据完整率：${passRate}%`);
  
  if (checks.failed === 0 && passRate >= 90) {
    console.log('\n✅ 所有关键数据完整！前端显示应该正常！');
  } else if (checks.failed === 0) {
    console.log('\n⚠️  部分可选数据缺失，但不影响核心功能');
    console.log('💡 建议：重新执行一次完整诊断以获取更完整数据');
  } else {
    console.log('\n❌ 关键数据缺失，前端显示会存在问题');
    console.log('💡 建议：');
    console.log('   1. 检查后端 API 返回数据格式');
    console.log('   2. 重新执行完整诊断');
    console.log('   3. 检查 pages/detail/index.js 中的数据计算逻辑');
  }
  
  console.log('\n' + '='.repeat(80) + '\n');
  
  // 保存检查结果
  window.dataIntegrationCheck = checks;

})();
