/**
 * Storage 数据检查脚本 - 步骤 1
 * 
 * 使用方法:
 * 1. 微信开发者工具 → 打开小程序
 * 2. 执行一次诊断
 * 3. 在控制台执行此脚本
 * 
 * 作者：系统首席架构师
 * 日期：2026-03-11
 */

console.log('========================================');
console.log('📊 Storage 数据检查 - 步骤 1');
console.log('========================================\n');

// 1. 获取所有 storage keys
console.log('【1】获取所有 Storage Keys');
const info = wx.getStorageInfoSync();
console.log('所有 keys 数量:', info.keys.length);
console.log('所有 keys:', info.keys);
console.log('Storage 使用量:', info.currentSize, 'KB /', info.limitSize, 'KB\n');

// 2. 查找诊断相关的 key
console.log('【2】查找诊断相关 Keys');
const diagnosisKeys = info.keys.filter(k => k.startsWith('diagnosis_result_'));
console.log('diagnosis_result_ 开头的 keys:', diagnosisKeys);
console.log('数量:', diagnosisKeys.length, '\n');

// 3. 检查诊断历史列表
console.log('【3】检查诊断历史列表');
const historyList = wx.getStorageSync('diagnosis_history_list') || [];
console.log('历史记录数量:', historyList.length);
if (historyList.length > 0) {
  console.log('最新记录:', historyList[0]);
}
console.log('');

// 4. 查看最新的诊断数据
console.log('【4】查看最新诊断数据');
if (diagnosisKeys.length > 0) {
  const latestKey = diagnosisKeys[0];
  const data = wx.getStorageSync(latestKey);
  
  console.log('=== 诊断数据详情 ===');
  console.log('Key:', latestKey);
  console.log('Version:', data.version);
  console.log('ExecutionId:', data.executionId);
  console.log('BrandName:', data.brandName);
  console.log('Timestamp:', new Date(data.timestamp).toLocaleString());
  console.log('');
  
  console.log('=== data 字段 ===');
  console.log('data 字段 keys:', Object.keys(data.data || {}));
  console.log('');
  
  console.log('=== 核心数据检查 ===');
  console.log('brandDistribution:', data.data?.brandDistribution);
  console.log('brandScores:', data.data?.brandScores);
  console.log('detailedResults 数量:', data.data?.detailedResults?.length || 0);
  console.log('competitiveAnalysis:', data.data?.competitiveAnalysis);
  console.log('qualityScore:', data.data?.qualityScore);
  console.log('overallScore:', data.data?.overallScore);
  console.log('');
  
  console.log('=== 问题诊断 ===');
  
  // 检查 brandDistribution
  if (!data.data?.brandDistribution && !data.data?.brandScores) {
    console.error('❌ 问题发现：brandDistribution 和 brandScores 均为空！');
    console.log('   可能原因：后端未生成品牌分布数据');
    console.log('   下一步：检查后端诊断编排器');
  } else {
    console.log('✅ 品牌分布数据：存在');
    const brandDist = data.data?.brandDistribution || data.data?.brandScores;
    console.log('   total_count:', brandDist?.total_count);
    console.log('   data keys:', Object.keys(brandDist?.data || {}));
  }
  
  // 检查 detailedResults
  if (!data.data?.detailedResults || data.data.detailedResults.length === 0) {
    console.error('❌ 问题发现：detailedResults 为空！');
    console.log('   可能原因：诊断结果为空或保存失败');
  } else {
    console.log('✅ 详细结果：存在，数量 =', data.data.detailedResults.length);
  }
  
  // 检查数据结构
  console.log('');
  console.log('=== 数据结构验证 ===');
  const expectedFields = [
    'brandDistribution',
    'brandScores',
    'detailedResults',
    'competitiveAnalysis',
    'qualityScore',
    'overallScore'
  ];
  
  expectedFields.forEach(field => {
    const exists = !!data.data?.[field];
    const icon = exists ? '✅' : '❌';
    console.log(`${icon} ${field}:`, exists ? '存在' : '不存在');
  });
  
  console.log('');
  console.log('=== 下一步建议 ===');
  if (!data.data?.brandDistribution && !data.data?.brandScores) {
    console.log('➡️  跳转到步骤 4: 检查后端数据生成');
  } else if (!data.data?.detailedResults || data.data.detailedResults.length === 0) {
    console.log('➡️  跳转到步骤 5: 检查诊断执行流程');
  } else {
    console.log('➡️  继续步骤 2: 检查页面加载逻辑');
  }
  
} else {
  console.error('❌ 未找到诊断数据！');
  console.log('可能原因:');
  console.log('  1. 未执行诊断');
  console.log('  2. 诊断完成后未保存到 storage');
  console.log('  3. storage key 命名不一致');
  console.log('');
  console.log('=== 下一步 ===');
  console.log('➡️  检查 pages/index/index.js 的 handleDiagnosisComplete 函数');
  console.log('➡️  确认 saveDiagnosisResult 是否被调用');
}

console.log('');
console.log('========================================');
console.log('📊 Storage 数据检查 - 完成');
console.log('========================================\n');
