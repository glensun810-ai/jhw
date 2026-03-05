# -*- coding: utf-8 -*-
"""修复 index.js 中的 appState 同步设置"""

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 startBrandTest 中的 setData
old_code = """    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null
    });

    this.callBackendBrandTest(brand_list, selectedModels, customQuestions);
  },

  async callBackendBrandTest"""

new_code = """    // 【Step 2 新增】同步设置 appState
    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null,
      appState: 'testing'  // 与 isTesting: true 对应
    });

    this.callBackendBrandTest(brand_list, selectedModels, customQuestions);
  },

  async callBackendBrandTest"""

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ Fixed startBrandTest')
else:
    print('❌ startBrandTest code not found')

# 替换 onComplete 中的 setData
old_complete = """      this.setData({
        isTesting: false,
        testCompleted: true,
        completedTime: this.getCompletedTimeText()
      });"""

new_complete = """      // 【Step 3 新增】同步设置 appState
      this.setData({
        isTesting: false,
        testCompleted: true,
        hasLastReport: true,
        completedTime: this.getCompletedTimeText(),
        appState: 'completed'  // 与 testCompleted: true 对应
      });"""

if old_complete in content:
    content = content.replace(old_complete, new_complete)
    print('✅ Fixed onComplete')
else:
    print('❌ onComplete code not found')

# 替换 onError 中的 setData
old_error = """      this.setData({
        isTesting: false,
        testCompleted: false
      });"""

new_error = """      // 【Step 3 新增】同步设置 appState
      this.setData({
        isTesting: false,
        testCompleted: false,
        appState: 'error'  // 标记为错误状态
      });"""

count = content.count(old_error)
if count > 0:
    content = content.replace(old_error, new_error)
    print(f'✅ Fixed onError ({count} occurrences)')
else:
    print('❌ onError code not found')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ All fixes applied!')
