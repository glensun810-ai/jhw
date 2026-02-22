#!/usr/bin/env python3
"""
index.js 重构脚本 - 阶段 2/2
重构 startBrandTest, callBackendBrandTest, pollTestProgress 等函数
"""

import re

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换 startBrandTest 函数
old_startBrandTest = r'''  startBrandTest: function\(\) \{
    const brandName = this\.data\.brandName\.trim\(\);
    if \(!brandName\) \{
      wx\.showToast\(\{ title: '请输入您的品牌名称', icon: 'error' \}\);
      return;
    \}

    const brand_list = \[brandName, \.\.\.this\.data\.competitorBrands\];
    let selectedModels = \[\.\.\.this\.data\.domesticAiModels, \.\.\.this\.data\.overseasAiModels\]\.filter\(model => model\.checked && !model\.disabled\);
    let customQuestions = this\.getValidQuestions\(\);

    if \(selectedModels\.length === 0\) \{
      wx\.showToast\(\{ title: '请选择至少一个 AI 模型', icon: 'error' \}\);
      return;
    \}
    if \(customQuestions\.length === 0\) \{
      customQuestions = \["介绍一下\{brandName\}", "\{brandName\}的主要产品是什么"\];
    \}

    this\.setData\(\{
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断\.\.\.',
      testCompleted: false,
      completedTime: null
    \}\);

    this\.callBackendBrandTest\(brand_list, selectedModels, customQuestions\);
  \},'''

new_startBrandTest = '''  startBrandTest: function() {
    const brandName = this.data.brandName.trim();
    if (!brandName) {
      wx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
      return;
    }

    let selectedModels = [...this.data.domesticAiModels, ...this.data.overseasAiModels].filter(model => model.checked && !model.disabled);
    let customQuestions = this.getValidQuestions();

    if (selectedModels.length === 0) {
      wx.showToast({ title: '请选择至少一个 AI 模型', icon: 'error' });
      return;
    }
    if (customQuestions.length === 0) {
      customQuestions = ["介绍一下{brandName}", "{brandName} 的主要产品是什么"];
    }

    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null
    });

    // 使用服务启动诊断
    this.callBackendBrandTest(brandName, selectedModels, customQuestions);
  },'''

content = re.sub(old_startBrandTest, new_startBrandTest, content)

# 写入文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ startBrandTest 重构完成")
print(f"当前文件行数：{len(content.splitlines())}")
