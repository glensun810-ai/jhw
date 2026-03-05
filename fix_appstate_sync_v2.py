# -*- coding: utf-8 -*-
"""修复 index.js 中的 appState 同步设置 - 版本 2"""

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 startBrandTest 中的 setData (版本 2 - 不带空格)
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

# 尝试不带空格的版本
old_code2 = """    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      completedTime: null
    });

    this.callBackendBrandTest(brand_list, selectedModels, customQuestions);
  },

  async callBackendBrandTest"""

if old_code in content or old_code2 in content:
    content = content.replace(old_code, new_code).replace(old_code2, new_code)
    print('✅ Fixed startBrandTest')
else:
    print('❌ startBrandTest code not found, trying alternative...')
    # 尝试更简单的匹配
    alt_old = """      completedTime: null
    });

    this.callBackendBrandTest"""
    alt_new = """      completedTime: null,
      appState: 'testing'
    });

    this.callBackendBrandTest"""
    if alt_old in content:
        content = content.replace(alt_old, alt_new)
        print('✅ Fixed startBrandTest (alternative)')
    else:
        print('❌ Alternative not found')

with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nDone!')
