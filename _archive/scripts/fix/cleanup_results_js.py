#!/usr/bin/env python3
"""
清理 results.js 中的旧代码
P1-011: 删除已迁移到 dataLoaderService 的旧函数
"""

import re

# 读取文件
with open('pages/results/results.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 删除 fetchResultsFromServer 函数
start_marker = "  /**\n   * 【新增】从后端 API 拉取结果数据"
end_marker = "  /**\n   * 【新增】显示认证失败提示"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    # 保留注释说明
    new_content = content[:start_idx] + "  // P1-011 已删除：fetchResultsFromServer 函数（已迁移到 dataLoaderService）\n\n  " + content[end_idx:]
    
    # 写回文件
    with open('pages/results/results.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 已删除 fetchResultsFromServer 函数 ({end_idx - start_idx} 行)")
else:
    print("⚠️ 未找到 fetchResultsFromServer 函数")

# 删除 calculateBrandScoresFromResults 函数（残留部分）
start_marker2 = "  /**\n   * 从 results 计算品牌评分（备用方案）\n   */\n    const app = getApp();"
start_idx2 = new_content.find(start_marker2)

if start_idx2 != -1:
    # 找到下一个函数定义
    next_func = new_content.find("  /**\n   * 【新增】显示认证失败提示", start_idx2)
    if next_func != -1:
        final_content = new_content[:start_idx2] + "  // P1-011 已删除：calculateBrandScoresFromResults 函数（已不再使用）\n\n  " + new_content[next_func:]
        
        with open('pages/results/results.js', 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"✅ 已删除 calculateBrandScoresFromResults 函数残留")
    else:
        print("⚠️ 未找到下一个函数定义")
else:
    print("⚠️ 未找到 calculateBrandScoresFromResults 函数残留")

print("✅ 清理完成")
