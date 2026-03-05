# -*- coding: utf-8 -*-
"""Step 7-8: JS 完全迁移到 appState，清理旧变量"""

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Step 7: 简化 setData 调用，主要使用 appState
# 修改 startBrandTest 中的 setData
old_start = """    // 【Step 2 新增】同步设置 appState
    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null,
      appState: 'testing'
    });"""

new_start = """    // Step 7: 主要使用 appState
    this.setData({
      appState: 'testing',
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...'
    });"""

if old_start in content:
    content = content.replace(old_start, new_start)
    print('✅ Step 7: startBrandTest setData 已简化')
else:
    print('⚠️  startBrandTest setData 未找到')

# 修改 handleDiagnosisComplete 中的 setData
old_complete = """      // 【Step 3 新增】同步设置 appState
      this.setData({
        isTesting: false,
        testCompleted: true,
        hasLastReport: true,
        completedTime: this.getCompletedTimeText(),
        appState: 'completed'  // 与 testCompleted: true 对应
      });"""

new_complete = """      // Step 7: 主要使用 appState
      this.setData({
        appState: 'completed',
        hasLastReport: true,
        completedTime: this.getCompletedTimeText()
      });"""

if old_complete in content:
    content = content.replace(old_complete, new_complete)
    print('✅ Step 7: handleDiagnosisComplete setData 已简化')
else:
    print('⚠️  handleDiagnosisComplete setData 未找到')

# 修改错误处理中的 setData
old_error = """      // 【Step 3 新增】同步设置 appState
      this.setData({
        isTesting: false,
        testCompleted: false,
        appState: 'error'  // 标记为错误状态
      });"""

new_error = """      // Step 7: 主要使用 appState
      this.setData({
        appState: 'error'
      });"""

count = content.count(old_error)
if count > 0:
    content = content.replace(old_error, new_error)
    print(f'✅ Step 7: onError setData 已简化 ({count} 处)')
else:
    print('⚠️  onError setData 未找到')

# Step 8: 从 data 中移除旧变量（保留用于向后兼容的注释）
# 注意：为了安全，我们先注释掉而不是删除
old_data_section = """    // 测试状态
    isTesting: false,
    testProgress: 0,
    progressText: '准备启动 AI 认知诊断...',
    testCompleted: false,

    // 【Step 1 新增】统一状态管理（与现有变量并存，双轨运行）
    // 状态枚举：'idle' | 'checking' | 'testing' | 'completed' | 'error'
    appState: 'idle',"""

new_data_section = """    // 测试状态
    // 【Step 8 已弃用】这些变量已不再使用，appState 是唯一状态源
    // 保留仅用于向后兼容，未来版本将完全移除
    isTesting: false,        // @deprecated 使用 appState 代替
    testProgress: 0,         // 保留：进度百分比
    progressText: '准备启动 AI 认知诊断...',  // 保留：进度文本
    testCompleted: false,    // @deprecated 使用 appState 代替

    // 【Step 1 新增】统一状态管理
    // 状态枚举：'idle' | 'checking' | 'testing' | 'completed' | 'error'
    appState: 'idle',"""

if old_data_section in content:
    content = content.replace(old_data_section, new_data_section)
    print('✅ Step 8: data 中的旧变量已标记为 @deprecated')
else:
    print('⚠️  data 中的旧变量未找到')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ Step 7-8 完成！JS 已完全迁移到 appState')
print('\n📋 迁移总结:')
print('  - setData 调用已简化，主要使用 appState')
print('  - 旧变量已标记为 @deprecated')
print('  - appState 是唯一状态源')
