#!/usr/bin/env python3
"""
删除 detail 页后修复首页引用
"""

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 1: 删除 navigateToDetail 调用，改为直接显示进度
old_call = """if (executionId) {
        logger.debug('✅ 战局指令下达成功，执行 ID:', executionId);
        wx.hideLoading(); // 确保配对关闭
        this.navigateToDetail(executionId, brand_list, selectedModels, custom_question); // 调用跳转
      } else {"""

new_call = """if (executionId) {
        logger.debug('✅ 战局指令下达成功，执行 ID:', executionId);
        wx.hideLoading(); // 确保配对关闭
        
        // 【P0 修复】删除 detail 页后，直接在首页显示进度
        this.setData({
          isTesting: true,
          executionId: executionId,
          testProgress: 0,
          progressText: '正在启动 AI 认知诊断...'
        });
        
        // 启动进度轮询
        this.startProgressPolling(executionId);
      } else {"""

if old_call in content:
    content = content.replace(old_call, new_call)
    print('✅ 替换 1 成功：修改 startBrandTest 函数')
else:
    print('❌ 替换 1 失败：未找到匹配内容')

# 替换 2: 删除 navigateToDetail 函数
old_func_start = content.find('  /**\n   * 强制清理并跳转\n   */\n  navigateToDetail: function')
if old_func_start != -1:
    # 找到函数结束位置
    old_func_end = content.find('  },\n\n  /**', old_func_start)
    if old_func_end != -1:
        old_func_end = content.find('\n', old_func_end)
        content = content[:old_func_start] + content[old_func_end:]
        print('✅ 替换 2 成功：删除 navigateToDetail 函数')
    else:
        print('❌ 替换 2 失败：未找到函数结束位置')
else:
    print('❌ 替换 2 失败：未找到 navigateToDetail 函数')

# 替换 3: 删除 startProgressPolling 中对 detail 页的引用
old_polling = 'const url = `/pages/detail/index?executionId=${encodeURIComponent(executionId)}`;'
new_polling = '// 【P0 修复】删除 detail 页后，进度轮询在首页进行'

if old_polling in content:
    content = content.replace(old_polling, new_polling)
    print('✅ 替换 3 成功：修改 startProgressPolling 函数')
else:
    print('❌ 替换 3 失败：未找到匹配内容')

# 保存文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 文件保存成功')
