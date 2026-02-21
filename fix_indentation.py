#!/usr/bin/env python3
"""
修复 restoreDraft 函数的缩进问题
"""

# 读取文件
with open('pages/index/index.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 restoreDraft 函数并修复缩进
in_restore_draft = False
fixed_lines = []
brace_count = 0

for i, line in enumerate(lines):
    if 'restoreDraft: function()' in line:
        in_restore_draft = True
        fixed_lines.append(line)
        continue
    
    if in_restore_draft:
        # 修复第 371 行的缩进
        if 'if (draft.brandName || (draft.competitorBrands && draft.competitorBrands.length > 0))' in line:
            # 这行已经有正确的内容，但需要添加 {
            fixed_lines.append('      if (draft.brandName || (draft.competitorBrands && draft.competitorBrands.length > 0)) {\n')
            continue
        
        # 修复内部代码的缩进
        if line.strip().startswith('// 检查是否是 7 天内的草稿'):
            fixed_lines.append('        ' + line.lstrip())
            continue
        elif line.strip().startswith('const now = Date.now()'):
            fixed_lines.append('        ' + line.lstrip())
            continue
        elif line.strip().startswith('const draftAge = now'):
            fixed_lines.append('        ' + line.lstrip())
            continue
        elif line.strip().startswith('const sevenDays = 7'):
            fixed_lines.append('        ' + line.lstrip())
            continue
        elif line.strip().startswith('if (draftAge < sevenDays)'):
            fixed_lines.append('        ' + line.lstrip())
            continue
        elif line.strip().startswith('this.setData({'):
            fixed_lines.append('          ' + line.lstrip())
            continue
        elif line.strip().startswith('brandName: draft.brandName'):
            fixed_lines.append('            ' + line.lstrip())
            continue
        elif line.strip().startswith('currentCompetitor: draft.currentCompetitor'):
            fixed_lines.append('            ' + line.lstrip())
            continue
        elif line.strip().startswith('competitorBrands: draft.competitorBrands'):
            fixed_lines.append('            ' + line.lstrip())
            continue
        elif line.strip().startswith('});'):
            fixed_lines.append('          ' + line.lstrip())
            continue
        elif line.strip().startswith("console.log('草稿已恢复'"):
            fixed_lines.append('          ' + line.lstrip())
            continue
        elif line.strip().startswith('} else {'):
            fixed_lines.append('        ' + line.lstrip())
            continue
        elif line.strip().startswith('// 草稿过期，清除'):
            fixed_lines.append('          ' + line.lstrip())
            continue
        elif line.strip().startswith('wx.removeStorageSync'):
            fixed_lines.append('          ' + line.lstrip())
            continue
        elif line.strip().startswith("console.log('草稿已过期'"):
            fixed_lines.append('          ' + line.lstrip())
            continue
        elif line.strip() == '}':
            # 这是 if 语句的闭合括号
            fixed_lines.append('        }\n')
            continue
        elif line.strip() == '}' and 'try' not in ''.join(lines[max(0,i-10):i]):
            # try 块的闭合括号
            fixed_lines.append('    } catch (error) {\n')
            fixed_lines.append("      console.error('restoreDraft 失败', error);\n")
            fixed_lines.append('    }\n')
            fixed_lines.append('  },\n')
            in_restore_draft = False
            continue
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# 写入文件
with open('pages/index/index.js', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ restoreDraft 缩进修复完成")
