#!/usr/bin/env python3
"""
AI 平台显示 Bug 修复脚本
彻底修复 AI 平台刷新后不可见的问题
"""

import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 在 data 中添加注释，强调默认值的重要性
old_data_comment = '''    // AI 模型选择'''
new_data_comment = '''    // AI 模型选择 - 【P0 关键修复】在 data 中定义默认值，确保页面渲染时有数据'''

if old_data_comment in content:
    content = content.replace(old_data_comment, new_data_comment)
    print("✅ 修复 1: 已更新 data 注释")
else:
    print("⚠️ 修复 1: 未找到目标注释")

# 修复 2: 在 onLoad 中添加 AI 平台初始化调用
old_onload_code = '''      // 3. 加载用户 AI 平台偏好（使用服务）
      loadUserPlatformPreferences(this);
      this.updateSelectedModelCount();
      this.updateSelectedQuestionCount();'''

new_onload_code = '''      // 3. 【P0 关键修复】初始化 AI 平台数据（同步，确保页面渲染时有数据）
      this.initDomesticAiModels();
      this.initOverseasAiModels();
      
      // 4. 加载用户 AI 平台偏好（使用服务，异步）
      loadUserPlatformPreferences(this);
      this.updateSelectedModelCount();
      this.updateSelectedQuestionCount();'''

if old_onload_code in content:
    content = content.replace(old_onload_code, new_onload_code)
    print("✅ 修复 2: 已在 onLoad 中添加 AI 平台初始化")
else:
    print("⚠️ 修复 2: 未找到 onLoad 代码")

# 修复 3: 更新后续步骤编号
old_step_4 = '''      // 4. 【新增】从 Storage 读取高级设置展开/折叠状态'''
new_step_4 = '''      // 5. 【新增】从 Storage 读取高级设置展开/折叠状态'''

if old_step_4 in content:
    content = content.replace(old_step_4, new_step_4)
    print("✅ 修复 3: 已更新步骤编号")
    
old_step_5 = '''      // 5. 防御性读取 config.estimate'''
new_step_5 = '''      // 6. 防御性读取 config.estimate'''

if old_step_5 in content:
    content = content.replace(old_step_5, new_step_5)
    print("✅ 修复 4: 已更新步骤编号")

old_step_6 = '''      // 6. 检查是否需要立即启动快速搜索'''
new_step_6 = '''      // 7. 检查是否需要立即启动快速搜索'''

if old_step_6 in content:
    content = content.replace(old_step_6, new_step_6)
    print("✅ 修复 5: 已更新步骤编号")

old_step_7 = '''      // 7. 应用页面进入动画'''
new_step_7 = '''      // 8. 应用页面进入动画'''

if old_step_7 in content:
    content = content.replace(old_step_7, new_step_7)
    print("✅ 修复 6: 已更新步骤编号")

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ AI 平台显示 Bug 修复完成！")
print("\n修复内容:")
print("1. 在 data 中定义 AI 平台默认值（已有）")
print("2. 在 onLoad 中同步初始化 AI 平台数据")
print("3. onShow 中 refreshAiPlatforms() 作为双重保障")
print("\n请重新编译小程序验证修复效果。")
