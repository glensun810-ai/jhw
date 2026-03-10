# -*- coding: utf-8 -*-
"""Step 7-8 精确修复"""

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 startBrandTest 中的 setData
old1 = """    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null,
      appState: 'testing'
    });"""

new1 = """    // Step 7: 主要使用 appState
    this.setData({
      appState: 'testing',
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...'
    });"""

if old1 in content:
    content = content.replace(old1, new1)
    print('✅ Fixed startBrandTest setData')
else:
    print('❌ startBrandTest setData not found')

# 修复 data 中的注释
old2 = """    // 测试状态
    isTesting: false,
    testProgress: 0,
    progressText: '准备启动 AI 认知诊断...',
    testCompleted: false,

    // 【Step 1 新增】统一状态管理（与现有变量并存，双轨运行）
    // 状态枚举：'idle' | 'checking' | 'testing' | 'completed' | 'error'
    appState: 'idle',"""

new2 = """    // 测试状态
    // 【Step 8 已弃用】这些变量已不再使用，appState 是唯一状态源
    isTesting: false,        // @deprecated 使用 appState 代替
    testProgress: 0,         // 保留：进度百分比
    progressText: '准备启动 AI 认知诊断...',  // 保留：进度文本
    testCompleted: false,    // @deprecated 使用 appState 代替

    // 【Step 1 新增】统一状态管理
    appState: 'idle',  // 状态枚举：'idle' | 'testing' | 'completed' | 'error'"""

if old2 in content:
    content = content.replace(old2, new2)
    print('✅ Fixed data section comments')
else:
    print('❌ data section not found')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ Step 7-8 precise fix completed!')
