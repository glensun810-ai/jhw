#!/usr/bin/env python3
"""
清理 results.js 中的语法错误
删除 P1-011 残留的旧代码
"""

import re

# 读取文件
with open('pages/results/results.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到残留代码的起始和结束位置
start_marker = "  /**\n   * 从 results 计算品牌评分（备用方案）\n   */\n    const app = getApp();"
end_marker = "  /**\n   * 【新增】显示认证失败提示\n   */"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    # 删除残留代码
    new_content = content[:start_idx] + "  // P1-011 已删除：fetchResultsFromServer 函数（已迁移到 dataLoaderService）\n\n  " + content[end_idx:]
    
    # 写回文件
    with open('pages/results/results.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 已删除残留代码 ({end_idx - start_idx} 字符)")
else:
    print(f"⚠️ 未找到残留代码标记")
    print(f"start_idx: {start_idx}")
    print(f"end_idx: {end_idx}")

print("✅ 清理完成")
