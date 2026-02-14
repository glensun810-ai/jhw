/**
 * 矩阵数据转换器 - 实现不同视图的数据转换逻辑
 * 
 * @param {string} viewType - 视图类型 ('panorama' | 'model')
 * @param {Object} rawData - 原始数据
 * @param {string} selectedBrand - 选中的品牌（仅在 model 视图中使用）
 * @returns {Object} 转换后的矩阵数据
 */
function getMatrixData(viewType, rawData, selectedBrand = '') {
  if (!rawData || !rawData.results || !Array.isArray(rawData.results)) {
    return { headers: [], rows: [] };
  }

  const results = rawData.results;

  switch (viewType) {
    case 'panorama': // 战略全景视图
      return getPanoramaViewData(results);
    
    case 'model': // 模型对阵视图
      return getModelViewData(results, selectedBrand);
    
    default:
      return { headers: [], rows: [] };
  }
}

/**
 * 获取战略全景视图数据
 * 横轴: 所有参与诊断的品牌列表
 * 纵轴: 用户定义的问题列表
 * 数值: 该品牌在各模型下的平均分
 */
function getPanoramaViewData(results) {
  // 获取所有唯一的问题
  const uniqueQuestions = [...new Set(results.map(item => item.question))];
  
  // 获取所有唯一的品牌
  const uniqueBrands = [...new Set(results.map(item => item.brand))];
  
  // 构建矩阵数据
  const headers = ['问题', ...uniqueBrands]; // 第一列为问题，其余为品牌
  const rows = [];

  uniqueQuestions.forEach(question => {
    const row = [question]; // 第一列是问题
    
    uniqueBrands.forEach(brandName => {
      // 找到该品牌和问题对应的答案
      const brandResults = results.filter(item => 
        item.question === question && item.brand === brandName
      );
      
      if (brandResults.length > 0) {
        // 计算该品牌在该问题下的平均分
        const avgScore = calculateAverageScore(brandResults);
        row.push(avgScore);
      } else {
        // 如果没有数据，标记为无数据
        row.push(null);
      }
    });
    
    rows.push(row);
  });

  return {
    headers: headers,
    rows: rows
  };
}

/**
 * 获取模型对阵视图数据
 * 横轴: AI 模型列表
 * 纵轴: 用户定义的问题列表
 * 数值: 特定 AI 对选定品牌 (selectedBrand) 的评分
 */
function getModelViewData(results, selectedBrand) {
  if (!selectedBrand) {
    return { headers: [], rows: [] };
  }

  // 获取所有唯一的问题（对于选定品牌）
  const uniqueQuestions = [...new Set(
    results
      .filter(item => item.brand === selectedBrand)
      .map(item => item.question)
  )];
  
  // 获取所有唯一的模型
  const uniqueModels = [...new Set(results.map(item => item.model || 'Unknown Model'))];
  
  // 构建矩阵数据
  const headers = ['问题', ...uniqueModels]; // 第一列为问题，其余为模型
  const rows = [];

  uniqueQuestions.forEach(question => {
    const row = [question]; // 第一列是问题
    
    uniqueModels.forEach(modelName => {
      // 找到该品牌、问题和模型对应的答案
      const modelResults = results.filter(item => 
        item.question === question && 
        item.brand === selectedBrand && 
        (item.model === modelName || (modelName === 'Unknown Model' && !item.model))
      );
      
      if (modelResults.length > 0) {
        // 计算该模型在该问题下的平均分
        const avgScore = calculateAverageScore(modelResults);
        row.push(avgScore);
      } else {
        // 如果没有数据，标记为无数据
        row.push(null);
      }
    });
    
    rows.push(row);
  });

  return {
    headers: headers,
    rows: rows
  };
}

/**
 * 计算平均分
 */
function calculateAverageScore(results) {
  if (!results || results.length === 0) {
    return 0;
  }

  const totalScore = results.reduce((sum, item) => {
    // 计算单个结果的综合得分
    const itemScore = getItemScore(item);
    return sum + itemScore;
  }, 0);

  return Math.round(totalScore / results.length);
}

/**
 * 获取单个项目的综合得分
 */
function getItemScore(item) {
  // 从评分对象中提取各项分数
  const scores = item.scores || {};
  const accuracy = scores.accuracy || scores.Accuracy || 0;
  const completeness = scores.completeness || scores.Completeness || 0;
  const relevance = scores.relevance || scores.Relevance || 0;
  const security = scores.security || scores.Security || 0;
  const sentiment = scores.sentiment || scores.Sentiment || 0;

  // 计算平均分
  const total = accuracy + completeness + relevance + security + sentiment;
  return Math.round(total / 5);
}

/**
 * 根据分值获取颜色代码
 * >80: #00F2FF (科技青), 60-79: #FFD600 (琥珀黄), <60: #FF1744 (警示红)
 */
function getColorByScore(score) {
  if (score === null || score === undefined) {
    // 无数据时使用灰色
    return 'rgba(142, 142, 147, 0.2)';
  } else if (score > 80) {
    // >80: 科技青
    return 'rgba(0, 242, 255, 0.2)';
  } else if (score >= 60) {
    // 60-79: 琥珀黄
    return 'rgba(255, 214, 0, 0.2)';
  } else {
    // <60: 警示红
    return 'rgba(255, 23, 68, 0.2)';
  }
}

module.exports = {
  getMatrixData,
  getPanoramaViewData,
  getModelViewData,
  calculateAverageScore,
  getColorByScore
};