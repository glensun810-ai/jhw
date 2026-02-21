/**
 * 品牌排名统计准确性检查
 * 
 * 检查品牌在不同 AI 搜索中的排名是否被准确统计和展示
 */

(function() {
  console.log('\n' + '='.repeat(80));
  console.log('🏆 品牌排名统计准确性检查');
  console.log('='.repeat(80) + '\n');

  // 读取存储数据
  const lastReport = wx.getStorageSync('last_diagnostic_report');
  
  if (!lastReport) {
    console.log('❌ 未找到诊断报告，请先执行诊断');
    return;
  }

  const dashboard = lastReport.dashboard || {};
  const rawResults = lastReport.rawResults || [];
  const summary = dashboard.summary || {};
  const questionCards = dashboard.questionCards || [];

  console.log('📊 基础信息');
  console.log('='.repeat(80));
  console.log(`品牌名称：${summary.brandName || lastReport.brandName || '未知'}`);
  console.log(`原始结果数：${rawResults.length}`);
  console.log('');

  // ========== 检查 1: 原始数据中的排名统计 ==========
  console.log('📋 检查 1: 原始数据中的品牌排名\n');

  const rankStats = {
    total: rawResults.length,
    mentioned: 0,
    notMentioned: 0,
    ranks: [],
    byModel: {},
    byQuestion: {}
  };

  rawResults.forEach((result, i) => {
    const modelName = result.model || '未知模型';
    const questionId = result.question_id !== undefined ? result.question_id : 'unknown';
    const geoData = result.geo_data;

    // 按模型统计
    if (!rankStats.byModel[modelName]) {
      rankStats.byModel[modelName] = {
        total: 0,
        mentioned: 0,
        ranks: [],
        avgRank: 0
      };
    }
    rankStats.byModel[modelName].total++;

    // 按问题统计
    if (!rankStats.byQuestion[questionId]) {
      rankStats.byQuestion[questionId] = {
        total: 0,
        mentioned: 0,
        ranks: [],
        avgRank: 0,
        questionText: result.question_text || '问题 ' + (questionId + 1)
      };
    }
    rankStats.byQuestion[questionId].total++;

    if (geoData) {
      if (geoData.brand_mentioned === true) {
        rankStats.mentioned++;
        rankStats.byModel[modelName].mentioned++;
        rankStats.byQuestion[questionId].mentioned++;

        if (geoData.rank !== undefined && geoData.rank !== null && geoData.rank > 0) {
          rankStats.ranks.push(geoData.rank);
          rankStats.byModel[modelName].ranks.push(geoData.rank);
          rankStats.byQuestion[questionId].ranks.push(geoData.rank);

          console.log(`✅ 结果 ${i + 1}:`);
          console.log(`   模型：${modelName}`);
          console.log(`   问题：${result.question_text || questionId}`);
          console.log(`   排名：第 ${geoData.rank} 名`);
          console.log(`   情感：${geoData.sentiment}`);
          console.log(`   拦截：${geoData.interception || '无'}`);
        } else {
          console.log(`⚠️  结果 ${i + 1}: 提及但排名缺失 (${modelName})`);
        }
      } else {
        rankStats.notMentioned++;
        console.log(`❌ 结果 ${i + 1}: 未提及品牌 (${modelName})`);
      }
    } else {
      console.log(`❌ 结果 ${i + 1}: geo_data 缺失 (${modelName})`);
    }
  });

  // 计算平均排名
  console.log('\n📊 排名统计汇总');
  console.log('='.repeat(80));

  const overallAvgRank = rankStats.ranks.length > 0
    ? (rankStats.ranks.reduce((sum, r) => sum + r, 0) / rankStats.ranks.length).toFixed(2)
    : 'N/A';

  console.log(`\n总体统计:`);
  console.log(`  - 总结果数：${rankStats.total}`);
  console.log(`  - 提及品牌：${rankStats.mentioned} (${rankStats.total > 0 ? ((rankStats.mentioned / rankStats.total) * 100).toFixed(1) : 0}%)`);
  console.log(`  - 未提及：${rankStats.notMentioned} (${rankStats.total > 0 ? ((rankStats.notMentioned / rankStats.total) * 100).toFixed(1) : 0}%)`);
  console.log(`  - 平均排名：${overallAvgRank}`);

  console.log(`\n按模型统计:`);
  Object.keys(rankStats.byModel).forEach(model => {
    const modelStats = rankStats.byModel[model];
    const modelAvgRank = modelStats.ranks.length > 0
      ? (modelStats.ranks.reduce((sum, r) => sum + r, 0) / modelStats.ranks.length).toFixed(2)
      : 'N/A';

    console.log(`\n  ${model}:`);
    console.log(`    - 提及：${modelStats.mentioned}/${modelStats.total}`);
    console.log(`    - 平均排名：${modelAvgRank}`);
    if (modelStats.ranks.length > 0) {
      console.log(`    - 排名分布：${modelStats.ranks.join(', ')}`);
    }
  });

  console.log(`\n按问题统计:`);
  Object.keys(rankStats.byQuestion).forEach(qId => {
    const qStats = rankStats.byQuestion[qId];
    const qAvgRank = qStats.ranks.length > 0
      ? (qStats.ranks.reduce((sum, r) => sum + r, 0) / qStats.ranks.length).toFixed(2)
      : 'N/A';

    console.log(`\n  问题 ${parseInt(qId) + 1}: ${qStats.questionText}`);
    console.log(`    - 提及：${qStats.mentioned}/${qStats.total}`);
    console.log(`    - 平均排名：${qAvgRank}`);
  });

  // ========== 检查 2: Dashboard 展示准确性 ==========
  console.log('\n\n📋 检查 2: Dashboard 展示准确性\n');

  console.log('Dashboard 数据:');
  console.log('='.repeat(80));

  if (questionCards.length > 0) {
    console.log(`\n问题卡片数量：${questionCards.length}`);

    questionCards.forEach((card, i) => {
      console.log(`\n问题 ${i + 1}:`);
      console.log(`  - 文本：${card.text || card.question_text || '未知'}`);
      console.log(`  - 平均排名：${card.avgRank || card.avg_rank || '缺失'}`);
      console.log(`  - 提及率：${card.mentionRate || card.mention_rate || 0}%`);
      console.log(`  - 提及数：${card.mentionCount || 0}`);
      console.log(`  - 总模型数：${card.totalModels || 0}`);

      // 验证计算是否正确
      const expectedMentionRate = card.totalModels > 0
        ? ((card.mentionCount || 0) / card.totalModels * 100).toFixed(1)
        : 0;

      if (Math.abs((card.mentionRate || card.mention_rate || 0) - parseFloat(expectedMentionRate)) > 0.1) {
        console.log(`  ⚠️  提及率计算可能有误 (显示：${card.mentionRate || card.mention_rate}, 期望：${expectedMentionRate})`);
      } else {
        console.log(`  ✅ 提及率计算正确 (${expectedMentionRate}%)`);
      }
    });
  } else {
    console.log('❌ 问题卡片数据为空');
  }

  // ========== 检查 3: SOV 计算准确性 ==========
  console.log('\n\n📋 检查 3: SOV 计算准确性\n');

  const sov = summary.sov || summary.sov_value || 0;
  const totalMentions = summary.totalMentions || 0;
  const totalTests = summary.totalTests || 0;

  console.log(`Dashboard 显示:`);
  console.log(`  - SOV: ${sov}%`);
  console.log(`  - 提及数：${totalMentions}`);
  console.log(`  - 总测试数：${totalTests}`);

  // 验证 SOV 计算
  const expectedSov = totalTests > 0
    ? ((totalMentions / totalTests) * 100).toFixed(2)
    : 0;

  console.log(`\nSOV 验证:`);
  console.log(`  - 计算值：${expectedSov}%`);
  console.log(`  - 显示值：${sov}%`);

  if (Math.abs(sov - parseFloat(expectedSov)) > 1) {
    console.log(`  ⚠️  SOV 计算可能有误`);
  } else {
    console.log(`  ✅ SOV 计算正确`);
  }

  // ========== 总结 ==========
  console.log('\n' + '='.repeat(80));
  console.log('📊 检查总结');
  console.log('='.repeat(80));

  const issues = [];

  if (rankStats.mentioned === 0) {
    issues.push('❌ 品牌在所有 AI 搜索中都未被提及');
  }

  if (rankStats.ranks.length === 0) {
    issues.push('❌ 没有有效的排名数据');
  }

  if (questionCards.length === 0) {
    issues.push('❌ Dashboard 问题卡片数据缺失');
  }

  if (issues.length > 0) {
    console.log('\n发现的问题:');
    issues.forEach(issue => console.log(`  ${issue}`));
    console.log('\n💡 建议:');
    console.log('  1. 检查后端 API 返回的 geo_data 是否完整');
    console.log('  2. 确认品牌名称在 AI 提示中是否正确');
    console.log('  3. 检查 pages/detail/index.js 中的数据计算逻辑');
  } else {
    console.log('\n✅ 品牌排名统计准确，展示清晰！');
    console.log(`\n关键指标:`);
    console.log(`  - 品牌提及率：${rankStats.total > 0 ? ((rankStats.mentioned / rankStats.total) * 100).toFixed(1) : 0}%`);
    console.log(`  - 平均排名：${overallAvgRank}`);
    console.log(`  - SOV: ${sov}%`);
  }

  console.log('\n' + '='.repeat(80) + '\n');

  window.rankCheckResults = {
    rawStats: rankStats,
    dashboard: {
      sov,
      totalMentions,
      totalTests,
      questionCards
    },
    issues
  };

})();
