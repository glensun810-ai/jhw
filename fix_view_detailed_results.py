#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the function
new_lines = []
skip_until_close = False
brace_count = 0

for i, line in enumerate(lines):
    if 'viewDetailedResults: function()' in line:
        # Add new function
        new_lines.append('  viewDetailedResults: function() {\n')
        new_lines.append('    // 优先使用新的 reportData，如果不存在则使用旧的 latestTestResults\n')
        new_lines.append('    const resultsToUse = this.data.reportData || this.data.latestTestResults;\n')
        new_lines.append('\n')
        new_lines.append('    if (resultsToUse) {\n')
        new_lines.append('      // 【关键修复】使用 Storage 传递大数据，避免 URL 编码 2KB 限制\n')
        new_lines.append('      const executionId = wx.getStorageSync(\'latestExecutionId\') || Date.now().toString();\n')
        new_lines.append('      wx.setStorageSync(\'last_diagnostic_results\', {\n')
        new_lines.append('        results: resultsToUse,\n')
        new_lines.append('        competitiveAnalysis: this.data.latestCompetitiveAnalysis || {},\n')
        new_lines.append('        brandScores: this.data.latestBrandScores || {},\n')
        new_lines.append('        targetBrand: this.data.brandName,\n')
        new_lines.append('        executionId: executionId,\n')
        new_lines.append('        timestamp: Date.now()\n')
        new_lines.append('      });\n')
        new_lines.append('\n')
        new_lines.append('      // 【优化】只传递 executionId 和 brandName\n')
        new_lines.append('      wx.navigateTo({\n')
        new_lines.append('        url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}`\n')
        new_lines.append('      });\n')
        new_lines.append('    } else {\n')
        new_lines.append('      wx.showToast({ title: \'暂无诊断结果\', icon: \'none\' });\n')
        new_lines.append('    }\n')
        new_lines.append('  },\n')
        skip_until_close = True
        brace_count = 1
        continue
    
    if skip_until_close:
        brace_count += line.count('{') - line.count('}')
        if brace_count <= 0:
            skip_until_close = False
        continue
    
    new_lines.append(line)

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ viewDetailedResults function updated successfully')
