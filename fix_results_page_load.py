#!/usr/bin/env python3
"""
修复首页跳转逻辑，保存完整数据并传递到结果页
"""

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到要替换的行（1124-1131 行）
new_lines = []
skip_until = 0

for i, line in enumerate(lines, 1):
    if i < skip_until:
        continue
    
    if i == 1124:
        # 替换 1124-1131 行
        new_lines.append("            wx.showToast({ title: '诊断完成', icon: 'success' });\n")
        new_lines.append("            this.renderReport();\n")
        new_lines.append("            \n")
        new_lines.append("            // 【P0 修复】保存完整数据并跳转到结果页\n")
        new_lines.append("            const resultsToSave = parsedStatus.detailed_results || parsedStatus.results || [];\n")
        new_lines.append("            const competitiveAnalysisToSave = parsedStatus.competitive_analysis || this.data.latestCompetitiveAnalysis || {};\n")
        new_lines.append("            const brandScoresToSave = parsedStatus.brand_scores || (competitiveAnalysisToSave && competitiveAnalysisToSave.brandScores) || {};\n")
        new_lines.append("            \n")
        new_lines.append("            wx.setStorageSync('latestTestResults_' + executionId, resultsToSave);\n")
        new_lines.append("            wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, competitiveAnalysisToSave);\n")
        new_lines.append("            wx.setStorageSync('latestBrandScores_' + executionId, brandScoresToSave);\n")
        new_lines.append("            wx.setStorageSync('latestTargetBrand', this.data.brandName);\n")
        new_lines.append("            \n")
        new_lines.append("            console.log('✅ 数据已保存到本地存储:', {\n")
        new_lines.append("              resultsCount: resultsToSave.length,\n")
        new_lines.append("              hasCompetitiveAnalysis: Object.keys(competitiveAnalysisToSave).length > 0,\n")
        new_lines.append("              hasBrandScores: Object.keys(brandScoresToSave).length > 0\n")
        new_lines.append("            });\n")
        new_lines.append("            \n")
        new_lines.append("            wx.navigateTo({\n")
        new_lines.append("              url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}&results=${encodeURIComponent(JSON.stringify(resultsToSave))}&competitiveAnalysis=${encodeURIComponent(JSON.stringify(competitiveAnalysisToSave))}`\n")
        new_lines.append("            });\n")
        skip_until = 1132  # 跳过原来的 1124-1131 行
    else:
        new_lines.append(line)

# 保存文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ 修复成功：首页跳转传递完整数据')
