/**
 * PDF 报告导出工具
 * 生成完整的品牌洞察报告
 */

/**
 * 生成完整的品牌洞察报告
 * @param {Object} pageInstance - 页面实例
 * @returns {Promise<void>}
 */
const generateFullReport = async (pageInstance) => {
  try {
    const data = pageInstance.data;
    const competitiveAnalysis = data.competitiveAnalysis;
    const targetBrand = data.targetBrand;

    if (!competitiveAnalysis || !targetBrand) {
      throw new Error('数据不完整，无法生成报告');
    }

    // 构建报告内容
    const reportContent = buildReportContent(pageInstance);

    // 显示生成中提示
    wx.showLoading({
      title: '正在生成报告...',
      mask: true
    });

    // 使用 Canvas 生成图片
    const imagePath = await renderReportToCanvas(reportContent, pageInstance);

    wx.hideLoading();

    // 保存图片到相册
    if (imagePath) {
      wx.saveImageToPhotosAlbum({
        filePath: imagePath,
        success: () => {
          wx.showModal({
            title: '保存成功',
            content: '报告已保存到相册，您可以分享或打印',
            showCancel: false,
            confirmText: '知道了'
          });
        },
        fail: (err) => {
          console.error('保存失败:', err);
          // 如果保存失败，显示预览
          wx.previewImage({
            urls: [imagePath],
            current: imagePath
          });
        }
      });
    } else {
      wx.showModal({
        title: '生成失败',
        content: '无法生成报告图片，请重试',
        showCancel: false
      });
    }

  } catch (error) {
    console.error('生成报告失败:', error);
    wx.hideLoading();
    wx.showModal({
      title: '生成失败',
      content: error.message || '报告生成失败，请重试',
      showCancel: false
    });
  }
};

/**
 * 构建报告内容数据结构
 * @param {Object} pageInstance - 页面实例
 * @returns {Object} 报告内容
 */
const buildReportContent = (pageInstance) => {
  const data = pageInstance.data;
  const competitiveAnalysis = data.competitiveAnalysis;
  const targetBrand = data.targetBrand;
  const brandScores = competitiveAnalysis.brandScores[targetBrand] || {};

  return {
    // 报告头部
    header: {
      title: '品牌洞察报告',
      subtitle: `"${targetBrand}"：AI 认知与市场格局分析`,
      generatedAt: formatDate(new Date())
    },

    // 品牌概览
    overview: {
      brandName: targetBrand,
      overallScore: brandScores.overallScore || 0,
      overallGrade: brandScores.overallGrade || 'D',
      overallSummary: brandScores.overallSummary || '暂无评价',
      dimensions: {
        authority: brandScores.overallAuthority || 0,
        visibility: brandScores.overallVisibility || 0,
        purity: brandScores.overallPurity || 0,
        consistency: brandScores.overallConsistency || 0
      }
    },

    // 核心洞察
    insights: {
      advantage: pageInstance.data.advantageInsight || '暂无',
      risk: pageInstance.data.riskInsight || '暂无',
      opportunity: pageInstance.data.opportunityInsight || '暂无'
    },

    // AI 平台对比
    platformComparison: {
      platforms: data.platforms || [],
      pkDataByPlatform: data.pkDataByPlatform || {},
      platformDisplayNames: data.platformDisplayNames || {}
    },

    // 品牌排名
    brandRanking: competitiveAnalysis.brandRanking || [],

    // 竞品分析
    competitorAnalysis: competitiveAnalysis.competitorAnalysis || [],

    // 详细结果
    detailedResults: data.latestTestResults || [],

    // 语义偏移分析
    semanticDrift: data.semanticDriftData || null,

    // 信源纯净度
    sourcePurity: data.sourcePurityData || null,

    // 优化建议
    recommendations: data.recommendationData || null
  };
};

/**
 * 渲染报告到 Canvas
 * @param {Object} content - 报告内容
 * @param {Object} pageInstance - 页面实例
 * @returns {Promise<string>} 图片路径
 */
const renderReportToCanvas = (content, pageInstance) => {
  return new Promise((resolve, reject) => {
    try {
      // 创建离屏 Canvas
      const query = wx.createSelectorQuery().in(pageInstance);
      query.select('#report-canvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0]) {
            console.error('未找到 Canvas 元素');
            resolve(null);
            return;
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');

          const dpr = wx.getSystemInfoSync().pixelRatio;
          const canvasWidth = 750;
          const canvasHeight = 2000; // 增加高度以容纳更多内容

          canvas.width = canvasWidth * dpr;
          canvas.height = canvasHeight * dpr;
          ctx.scale(dpr, dpr);

          // 绘制白色背景
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, canvasWidth, canvasHeight);

          // 绘制内容
          const totalHeight = drawReportContent(ctx, content, canvasWidth);

          // 如果需要更长的图片，调整高度
          if (totalHeight > canvasHeight) {
            canvas.height = totalHeight * dpr;
            ctx.scale(dpr, dpr);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvasWidth, totalHeight);
            drawReportContent(ctx, content, canvasWidth);
          }

          // 导出图片
          wx.canvasToTempFilePath({
            canvas: canvas,
            success: (res) => {
              console.log('Canvas 导出成功:', res.tempFilePath);
              resolve(res.tempFilePath);
            },
            fail: (err) => {
              console.error('Canvas 导出失败:', err);
              resolve(null);
            }
          }, pageInstance);
        });
    } catch (error) {
      console.error('Canvas 渲染失败:', error);
      resolve(null);
    }
  });
};

/**
 * 绘制报告内容
 * @param {CanvasContext} ctx - Canvas 上下文
 * @param {Object} content - 报告内容
 * @param {number} width - Canvas 宽度
 * @returns {number} 使用的总高度
 */
const drawReportContent = (ctx, content, width) => {
  let y = 40;
  const padding = 30;
  const contentWidth = width - padding * 2;

  // 标题部分
  y = drawHeader(ctx, content.header, padding, y, contentWidth);
  y += 30;

  // 品牌概览卡片
  y = drawOverviewCard(ctx, content.overview, padding, y, contentWidth);
  y += 30;

  // 核心洞察
  y = drawInsights(ctx, content.insights, padding, y, contentWidth);
  y += 30;

  // 多维度分析
  y = drawDimensions(ctx, content.overview.dimensions, padding, y, contentWidth);
  y += 30;

  // 品牌排名
  if (content.brandRanking && content.brandRanking.length > 0) {
    y = drawBrandRanking(ctx, content.brandRanking, padding, y, contentWidth);
    y += 30;
  }

  // 竞品分析
  if (content.competitorAnalysis && content.competitorAnalysis.length > 0) {
    y = drawCompetitorAnalysis(ctx, content.competitorAnalysis, padding, y, contentWidth);
    y += 30;
  }

  // 详细结果（限制显示前 20 条）
  if (content.detailedResults && content.detailedResults.length > 0) {
    const limitedResults = content.detailedResults.slice(0, 20);
    y = drawDetailedResults(ctx, limitedResults, content.overview.brandName, padding, y, contentWidth);
  }

  // 页脚
  y += 30;
  y = drawFooter(ctx, content.header.generatedAt, padding, y, contentWidth);

  return y;
};

/**
 * 绘制报告头部
 */
const drawHeader = (ctx, header, x, y, width) => {
  const startY = y;

  // 装饰线
  ctx.fillStyle = '#007AFF';
  ctx.fillRect(x, y, 8, 60);

  // 标题
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 48px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(header.title, x + 20, y + 45);

  // 副标题
  ctx.fillStyle = '#666666';
  ctx.font = '28px sans-serif';
  wrapText(ctx, header.subtitle, x + 20, y + 85, width - 20, 32);

  // 生成时间
  ctx.fillStyle = '#999999';
  ctx.font = '24px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(`生成时间：${header.generatedAt}`, x + width, y + 45);

  return y + 100;
};

/**
 * 绘制品牌概览卡片
 */
const drawOverviewCard = (ctx, overview, x, y, width) => {
  const startY = y;
  const cardHeight = 220;

  // 卡片背景渐变
  const gradient = ctx.createLinearGradient(x, y, x + width, y + cardHeight);
  gradient.addColorStop(0, '#f0f7ff');
  gradient.addColorStop(1, '#e8f5e9');
  ctx.fillStyle = gradient;
  ctx.fillRect(x, y, width, cardHeight);

  // 边框
  ctx.strokeStyle = '#007AFF';
  ctx.lineWidth = 2;
  ctx.strokeRect(x, y, width, cardHeight);

  // 品牌名称
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 36px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(overview.brandName, x + 30, y + 55);

  // 总分
  ctx.fillStyle = '#007AFF';
  ctx.font = 'bold 72px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(overview.overallScore.toString(), x + width - 30, y + 65);

  // 等级
  ctx.fillStyle = getGradeColor(overview.overallGrade);
  ctx.font = 'bold 48px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(`等级：${overview.overallGrade}`, x + width - 30, y + 120);

  // 评价
  ctx.fillStyle = '#666666';
  ctx.font = '26px sans-serif';
  ctx.textAlign = 'left';
  wrapText(ctx, overview.overallSummary, x + 30, y + 160, width - 200, 32);

  return y + cardHeight;
};

/**
 * 绘制核心洞察
 */
const drawInsights = (ctx, insights, x, y, width) => {
  let currentY = y;

  // 标题
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('🎯 核心洞察', x, currentY);
  currentY += 50;

  // 洞察卡片
  const insightItems = [
    { icon: '🏆', label: '优势领域', content: insights.advantage, color: '#00C853', bgColor: '#e8f5e9' },
    { icon: '⚠️', label: '风险提示', content: insights.risk, color: '#FF5252', bgColor: '#ffebee' },
    { icon: '💡', label: '机会点', content: insights.opportunity, color: '#FFC107', bgColor: '#fff8e1' }
  ];

  insightItems.forEach((item) => {
    // 卡片背景
    ctx.fillStyle = item.bgColor;
    ctx.fillRect(x, currentY, width, 110);

    // 左侧色条
    ctx.fillStyle = item.color;
    ctx.fillRect(x, currentY, 6, 110);

    // 图标和标签
    ctx.fillStyle = item.color;
    ctx.font = 'bold 28px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`${item.icon} ${item.label}`, x + 20, currentY + 40);

    // 内容
    ctx.fillStyle = '#333333';
    ctx.font = '24px sans-serif';
    wrapText(ctx, item.content || '暂无', x + 20, currentY + 75, width - 40, 30);

    currentY += 125;
  });

  return currentY;
};

/**
 * 绘制多维度分析
 */
const drawDimensions = (ctx, dimensions, x, y, width) => {
  let currentY = y;

  // 标题
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('📊 多维度分析', x, currentY);
  currentY += 50;

  const dimensionItems = [
    { key: 'authority', label: '🏆 权威度', color: '#007AFF' },
    { key: 'visibility', label: '👁️ 可见度', color: '#5856D6' },
    { key: 'purity', label: '✨ 纯净度', color: '#FF9500' },
    { key: 'consistency', label: '🔗 一致性', color: '#34C759' }
  ];

  dimensionItems.forEach((item) => {
    const score = dimensions[item.key] || 0;

    // 维度名称和分数
    ctx.fillStyle = '#333333';
    ctx.font = '26px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(item.label, x, currentY + 28);

    ctx.fillStyle = item.color;
    ctx.font = 'bold 26px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${score}分`, x + width, currentY + 28);

    // 进度条背景
    ctx.fillStyle = '#e0e0e0';
    ctx.fillRect(x, currentY + 38, width, 20);

    // 进度条填充（渐变）
    const gradient = ctx.createLinearGradient(x, currentY + 38, x + width * (score / 100), currentY + 38);
    gradient.addColorStop(0, item.color);
    gradient.addColorStop(1, lightenColor(item.color, 30));
    ctx.fillStyle = gradient;
    ctx.fillRect(x, currentY + 38, width * (score / 100), 20);

    currentY += 75;
  });

  return currentY;
};

/**
 * 绘制品牌排名
 */
const drawBrandRanking = (ctx, brandRanking, x, y, width) => {
  if (!brandRanking || brandRanking.length === 0) {
    return y;
  }

  let currentY = y;

  // 标题
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('🏅 品牌排名', x, currentY);
  currentY += 50;

  // 表头
  ctx.fillStyle = '#999999';
  ctx.font = '24px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('排名', x, currentY + 25);
  ctx.fillText('品牌', x + 80, currentY + 25);
  ctx.textAlign = 'right';
  ctx.fillText('总分', x + width - 100, currentY + 25);

  // 分隔线
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x, currentY + 35);
  ctx.lineTo(x + width, currentY + 35);
  ctx.stroke();

  currentY += 50;

  // 排名列表（限制显示前 10 名）
  const topBrands = brandRanking.slice(0, 10);
  topBrands.forEach((brand, index) => {
    const rank = index + 1;

    // 排名
    if (rank <= 3) {
      ctx.fillStyle = rank === 1 ? '#FFD700' : rank === 2 ? '#C0C0C0' : rank === 3 ? '#CD7F32' : '#666666';
      ctx.font = 'bold 28px sans-serif';
      ctx.fillText(`#${rank}`, x, currentY + 28);
    } else {
      ctx.fillStyle = '#666666';
      ctx.font = '26px sans-serif';
      ctx.fillText(`#${rank}`, x, currentY + 28);
    }

    // 品牌名称
    ctx.fillStyle = '#333333';
    ctx.font = '26px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(brand.brand, x + 80, currentY + 28);

    // 分数
    ctx.fillStyle = '#007AFF';
    ctx.font = 'bold 26px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${brand.overallScore}分`, x + width - 100, currentY + 28);

    currentY += 45;
  });

  return currentY;
};

/**
 * 绘制竞品分析
 */
const drawCompetitorAnalysis = (ctx, competitorAnalysis, x, y, width) => {
  if (!competitorAnalysis || competitorAnalysis.length === 0) {
    return y;
  }

  let currentY = y;

  // 标题
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('🚗 竞品分析', x, currentY);
  currentY += 50;

  // 竞品列表（限制显示前 5 个）
  const topCompetitors = competitorAnalysis.slice(0, 5);
  topCompetitors.forEach((competitor) => {
    // 卡片背景
    ctx.fillStyle = '#fafafa';
    ctx.fillRect(x, currentY, width, 140);

    // 品牌名称
    ctx.fillStyle = '#333333';
    ctx.font = 'bold 28px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(competitor.brand, x + 20, currentY + 40);

    // 分数
    ctx.fillStyle = '#5856D6';
    ctx.font = 'bold 28px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${competitor.overallScore}分`, x + width - 20, currentY + 40);

    // 评价
    ctx.fillStyle = '#666666';
    ctx.font = '24px sans-serif';
    wrapText(ctx, competitor.overallSummary || '暂无评价', x + 20, currentY + 75, width - 40, 28);

    currentY += 150;
  });

  return currentY;
};

/**
 * 绘制详细结果
 */
const drawDetailedResults = (ctx, results, targetBrand, x, y, width) => {
  if (!results || results.length === 0) {
    return y;
  }

  let currentY = y;

  // 标题
  ctx.fillStyle = '#1a1a1a';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(`📋 详细问答（前${results.length}条）`, x, currentY);
  currentY += 50;

  results.forEach((result, index) => {
    const isTargetBrand = result.brand === targetBrand;

    // 序号和背景
    ctx.fillStyle = isTargetBrand ? '#e3f2fd' : '#fafafa';
    ctx.fillRect(x, currentY, width, 130);

    // 左侧色条
    ctx.fillStyle = isTargetBrand ? '#007AFF' : '#999999';
    ctx.fillRect(x, currentY, 4, 130);

    // 序号和品牌
    ctx.fillStyle = isTargetBrand ? '#007AFF' : '#666666';
    ctx.font = isTargetBrand ? 'bold 24px sans-serif' : '24px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`${index + 1}. ${result.brand}`, x + 15, currentY + 30);

    // 问题
    ctx.fillStyle = '#333333';
    ctx.font = '22px sans-serif';
    wrapText(ctx, `Q: ${result.question}`, x + 15, currentY + 60, width - 30, 26);

    // 回答
    ctx.fillStyle = '#666666';
    ctx.font = '20px sans-serif';
    wrapText(ctx, `A: ${result.response}`, x + 15, currentY + 90, width - 30, 24);

    currentY += 145;
  });

  return currentY;
};

/**
 * 绘制页脚
 */
const drawFooter = (ctx, generatedAt, x, y, width) => {
  // 分隔线
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + width, y);
  ctx.stroke();

  y += 30;

  // 页脚文字
  ctx.fillStyle = '#999999';
  ctx.font = '22px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(`本报告由 AI 生成 · 生成时间：${generatedAt}`, x + width / 2, y);

  return y + 40;
};

/**
 * 获取等级颜色
 * @param {string} grade - 等级
 * @returns {string} 颜色值
 */
const getGradeColor = (grade) => {
  const colors = {
    'A': '#00C853',
    'B': '#64DD17',
    'C': '#FFC107',
    'D': '#FF9800',
    'E': '#FF5252',
    'F': '#F44336'
  };
  return colors[grade] || '#666666';
};

/**
 * 颜色变亮
 * @param {string} color - 颜色值
 * @param {number} percent - 变亮百分比
 * @returns {string} 变亮后的颜色
 */
const lightenColor = (color, percent) => {
  // 简化的颜色变亮逻辑
  return color;
};

/**
 * 格式化日期
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的日期字符串
 */
const formatDate = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

/**
 * 在 Canvas 上绘制换行文本
 * @param {CanvasContext} ctx - Canvas 上下文
 * @param {string} text - 文本内容
 * @param {number} x - X 坐标
 * @param {number} y - Y 坐标
 * @param {number} maxWidth - 最大宽度
 * @param {number} lineHeight - 行高
 */
const wrapText = (ctx, text, x, y, maxWidth, lineHeight) => {
  if (!text) return;

  const words = text.split('');
  let line = '';
  let currentY = y;

  for (let i = 0; i < words.length; i++) {
    const testLine = line + words[i];
    const metrics = ctx.measureText(testLine);

    if (metrics.width > maxWidth && i > 0) {
      ctx.fillText(line, x, currentY);
      line = words[i];
      currentY += lineHeight;
    } else {
      line = testLine;
    }
  }
  ctx.fillText(line, x, currentY);
};

module.exports = {
  generateFullReport,
  buildReportContent,
  renderReportToCanvas
};
