/**
 * 全面检查所有界面的真实数据对接
 * 
 * 检查所有页面是否使用真实数据而非预设值
 */

(function() {
  console.log('\n' + '='.repeat(80));
  console.log('🔍 全面检查真实数据对接');
  console.log('='.repeat(80) + '\n');

  const issues = {
    hardCoded: [],  // 硬编码数据
    missing: [],    // 缺失数据
    incorrect: []   // 错误数据
  };

  // 读取存储数据
  const lastReport = wx.getStorageSync('last_diagnostic_report');
  
  if (!lastReport) {
    console.log('❌ 未找到诊断报告，请先执行诊断');
    return;
  }

  const dashboard = lastReport.dashboard || {};
  const rawResults = lastReport.rawResults || [];

  console.log('📊 数据源检查');
  console.log('='.repeat(80));
  console.log(`✅ 诊断报告存在`);
  console.log(`   执行 ID: ${lastReport.executionId}`);
  console.log(`   原始结果数：${rawResults.length}`);
  console.log('');

  // ========== 检查 Dashboard 数据 ==========
  console.log('📋 检查 Dashboard 数据真实性\n');

  const summary = dashboard.summary || {};
  
  // 检查硬编码值
  console.log('1. 品牌健康度数据:');
  if (summary.healthScore === 75 && summary.healthScore !== 0) {
    console.log('   ⚠️  healthScore = 75 (可能是预设值)');
    issues.hardCoded.push({
      field: 'summary.healthScore',
      value: summary.healthScore,
      expected: '真实计算值'
    });
  } else if (summary.healthScore > 0 && summary.healthScore <= 100) {
    console.log(`   ✅ healthScore = ${summary.healthScore} (真实值)`);
  } else {
    console.log(`   ❌ healthScore = ${summary.healthScore} (无效值)`);
    issues.missing.push({
      field: 'summary.healthScore',
      value: summary.healthScore
    });
  }

  if (summary.sov === 50 && summary.sov !== 0) {
    console.log('   ⚠️  sov = 50 (可能是预设值)');
    issues.hardCoded.push({
      field: 'summary.sov',
      value: summary.sov,
      expected: '真实计算值'
    });
  } else if (summary.sov >= 0 && summary.sov <= 100) {
    console.log(`   ✅ sov = ${summary.sov}% (真实值)`);
  } else {
    console.log(`   ❌ sov = ${summary.sov} (无效值)`);
    issues.missing.push({
      field: 'summary.sov',
      value: summary.sov
    });
  }

  if (summary.avgSentiment === 0.3 && summary.avgSentiment !== 0) {
    console.log('   ⚠️  avgSentiment = 0.3 (可能是预设值)');
    issues.hardCoded.push({
      field: 'summary.avgSentiment',
      value: summary.avgSentiment,
      expected: '真实计算值'
    });
  } else if (summary.avgSentiment >= -1 && summary.avgSentiment <= 1) {
    console.log(`   ✅ avgSentiment = ${summary.avgSentiment} (真实值)`);
  } else {
    console.log(`   ❌ avgSentiment = ${summary.avgSentiment} (无效值)`);
    issues.missing.push({
      field: 'summary.avgSentiment',
      value: summary.avgSentiment
    });
  }

  console.log('\n2. 检查健康度细分:');
  const breakdown = summary.healthBreakdown;
  if (breakdown) {
    if (breakdown.sovScore === 33.33 || breakdown.sovScore === 25) {
      console.log(`   ⚠️  sovScore = ${breakdown.sovScore} (可能是预设值)`);
      issues.hardCoded.push({
        field: 'summary.healthBreakdown.sovScore',
        value: breakdown.sovScore
      });
    } else {
      console.log(`   ✅ sovScore = ${breakdown.sovScore} (真实值)`);
    }
  } else {
    console.log('   ❌ healthBreakdown 数据缺失');
    issues.missing.push({
      field: 'summary.healthBreakdown',
      value: null
    });
  }

  console.log('\n3. 检查问题卡片数据:');
  const questionCards = dashboard.questionCards || [];
  
  if (questionCards.length === 0) {
    console.log('   ❌ 问题卡片数据为空');
    issues.missing.push({
      field: 'dashboard.questionCards',
      value: []
    });
  } else {
    console.log(`   ✅ 问题数量：${questionCards.length}`);
    
    questionCards.forEach((q, i) => {
      console.log(`\n   问题 ${i + 1}:`);
      
      if (q.avgRank === 1 || q.avg_rank === 1) {
        console.log(`   ⚠️  avgRank = 1 (可能是预设值)`);
        issues.hardCoded.push({
          field: `questionCards[${i}].avgRank`,
          value: q.avgRank || q.avg_rank
        });
      } else if ((q.avgRank || q.avg_rank) !== undefined) {
        console.log(`   ✅ avgRank = ${q.avgRank || q.avg_rank} (真实值)`);
      } else {
        console.log(`   ❌ avgRank 缺失`);
        issues.missing.push({
          field: `questionCards[${i}].avgRank`,
          value: undefined
        });
      }
      
      if (q.mentionRate === 100 || q.mention_rate === 100) {
        console.log(`   ⚠️  mentionRate = 100% (可能是预设值)`);
        issues.hardCoded.push({
          field: `questionCards[${i}].mentionRate`,
          value: q.mentionRate || q.mention_rate
        });
      } else if ((q.mentionRate || q.mention_rate) !== undefined) {
        console.log(`   ✅ mentionRate = ${q.mentionRate || q.mention_rate}% (真实值)`);
      } else {
        console.log(`   ❌ mentionRate 缺失`);
        issues.missing.push({
          field: `questionCards[${i}].mentionRate`,
          value: undefined
        });
      }
    });
  }

  console.log('\n4. 检查信源数据:');
  const allSources = dashboard.allSources || [];
  
  if (allSources.length === 0) {
    console.log('   ⚠️  完整信源列表为空（可能是旧数据）');
    issues.missing.push({
      field: 'dashboard.allSources',
      value: []
    });
  } else {
    console.log(`   ✅ 信源数量：${allSources.length}`);
    
    // 检查信源数据是否完整
    const firstSource = allSources[0];
    if (firstSource.influence_score === 15.5 || firstSource.influenceScore === 15.5) {
      console.log(`   ⚠️  influenceScore = 15.5 (可能是预设值)`);
      issues.hardCoded.push({
        field: 'allSources[0].influenceScore',
        value: firstSource.influence_score || firstSource.influenceScore
      });
    } else if ((firstSource.influence_score || firstSource.influenceScore) !== undefined) {
      console.log(`   ✅ influenceScore = ${firstSource.influence_score || firstSource.influenceScore} (真实值)`);
    }
  }

  console.log('\n5. 检查原始数据:');
  console.log(`   原始结果数：${rawResults.length}`);
  
  if (rawResults.length === 0) {
    console.log('   ❌ 原始结果数据为空');
    issues.missing.push({
      field: 'rawResults',
      value: []
    });
  } else {
    console.log('   ✅ 原始结果数据存在');
    
    // 检查 geo_data 完整性
    let validGeoData = 0;
    rawResults.forEach((r, i) => {
      if (r.geo_data && 
          r.geo_data.rank !== undefined && 
          r.geo_data.sentiment !== undefined &&
          r.geo_data.brand_mentioned !== undefined) {
        validGeoData++;
      }
    });
    
    console.log(`   - 有效 geo_data: ${validGeoData}/${rawResults.length}`);
    
    if (validGeoData < rawResults.length) {
      issues.missing.push({
        field: 'rawResults.geo_data',
        value: `${validGeoData}/${rawResults.length}`
      });
    }
  }

  // ========== 总结 ==========
  console.log('\n' + '='.repeat(80));
  console.log('📊 检查总结');
  console.log('='.repeat(80));
  
  console.log(`\n硬编码数据：${issues.hardCoded.length} 处`);
  console.log(`缺失数据：${issues.missing.length} 处`);
  console.log(`错误数据：${issues.incorrect.length} 处`);
  
  if (issues.hardCoded.length > 0) {
    console.log('\n⚠️  发现硬编码预设值，需要替换为真实计算:');
    issues.hardCoded.forEach((issue, i) => {
      console.log(`   ${i + 1}. ${issue.field} = ${issue.value}`);
    });
  }
  
  if (issues.missing.length > 0) {
    console.log('\n❌ 发现数据缺失:');
    issues.missing.forEach((issue, i) => {
      console.log(`   ${i + 1}. ${issue.field}`);
    });
  }
  
  if (issues.hardCoded.length === 0 && issues.missing.length === 0) {
    console.log('\n✅ 所有数据都是真实的！没有发现硬编码预设值！');
  } else {
    console.log('\n💡 建议:');
    console.log('   1. 检查 pages/detail/index.js 中的数据计算逻辑');
    console.log('   2. 确保 SOV、情感、健康度都是真实计算');
    console.log('   3. 移除所有硬编码的预设值');
  }
  
  console.log('\n' + '='.repeat(80) + '\n');
  
  window.realDataCheck = issues;

})();
