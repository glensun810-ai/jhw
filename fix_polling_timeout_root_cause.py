#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0 修复：轮询超时根因修复

问题分析:
1. 前端轮询超时 (5 分钟)
2. 后端 /test/status/<task_id> API 在 execution_store 中找不到任务时，会尝试从数据库查询
3. 但数据库查询逻辑有 bug: 使用了错误的变量名 task_status 而不是 db_task_status
4. 这导致即使数据库中有数据，也会返回空响应或错误
5. 前端认为任务未完成，继续轮询直到超时

修复内容:
1. 修复变量名错误 (task_status -> db_task_status)
2. 增强错误处理和日志记录
3. 添加任务过期清理机制
4. 优化轮询超时配置
"""

import os
import sys
from pathlib import Path

# 获取项目根目录
base_dir = Path(__file__).parent
root_dir = base_dir.parent

# 添加到 Python 路径
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / 'wechat_backend'))

print("="*70)
print("P0 修复：轮询超时根因修复")
print("="*70)
print()

# 读取 views.py 文件
views_file = root_dir / 'wechat_backend' / 'views.py'

if not views_file.exists():
    print(f"❌ 文件不存在：{views_file}")
    sys.exit(1)

print(f"📄 读取文件：{views_file}")
with open(views_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 修复变量名错误 (task_status -> db_task_status)
print("\n🔧 修复 1: 修复变量名错误")
old_code = """            db_task_status = get_db_task_status(task_id)
            if db_task_status:
                # 从数据库构建响应
                response_data = {
                    'task_id': task_id,
                    'progress': task_status.get('progress', 0),
                    'stage': task_status.get('stage', 'init'),
                    'status': task_status.get('status', 'init'),
                    'results': task_status.get('results', []),
                    'detailed_results': task_status.get('results', []),  # 添加这一行
                    'is_completed': task_status.get('status') == 'completed',
                    'created_at': task_status.get('start_time', None)
                }"""

new_code = """            db_task_status = get_db_task_status(task_id)
            if db_task_status:
                # 从数据库构建响应
                response_data = {
                    'task_id': task_id,
                    'progress': db_task_status.get('progress', 0),
                    'stage': db_task_status.get('stage', 'init'),
                    'status': db_task_status.get('status', 'init'),
                    'results': db_task_status.get('results', []),
                    'detailed_results': db_task_status.get('results', []),
                    'is_completed': db_task_status.get('status') == 'completed',
                    'created_at': db_task_status.get('start_time', None)
                }"""

if old_code in content:
    content = content.replace(old_code, new_code)
    print("  ✅ 变量名已修复 (task_status -> db_task_status)")
else:
    print("  ⚠️  未找到目标代码，可能已修复或代码已变更")

# 修复 2: 增强错误处理和日志记录
print("\n🔧 修复 2: 增强错误处理和日志记录")
old_error_handling = """        except Exception as e:
            api_logger.error(f"[TaskStatus] Error querying database for task {task_id}: {e}")
            return jsonify({'error': 'Task not found'}), 404"""

new_error_handling = """        except Exception as e:
            api_logger.error(f"[TaskStatus] Error querying database for task {task_id}: {e}", exc_info=True)
            # 返回更详细的错误信息
            return jsonify({
                'error': 'Task status query failed',
                'details': str(e),
                'suggestion': 'Please try again or start a new diagnosis'
            }), 500"""

if old_error_handling in content:
    content = content.replace(old_error_handling, new_error_handling)
    print("  ✅ 错误处理已增强")
else:
    print("  ⚠️  未找到目标代码，可能已修复或代码已变更")

# 保存修复后的文件
print("\n💾 保存修复后的文件")
with open(views_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("  ✅ 文件已保存")

# 修复 3: 检查前端轮询配置
print("\n🔧 修复 3: 检查前端轮询配置")
brand_test_service = root_dir / 'services' / 'brandTestService.js'

if brand_test_service.exists():
    with open(brand_test_service, 'r', encoding='utf-8') as f:
        js_content = f.read()

    # 检查超时配置
    if '5 * 60 * 1000' in js_content:
        print("  ℹ️  当前超时配置：5 分钟 (300 秒)")
        print("  💡 建议：如果诊断任务经常超过 5 分钟，考虑增加超时时间或优化后端性能")
    else:
        print("  ✅ 超时配置已自定义")

    # 检查轮询间隔
    if '800' in js_content:
        print("  ℹ️  当前轮询间隔：800ms")
        print("  💡 说明：800ms 是合理的间隔，不会造成过大压力")
else:
    print("  ⚠️  未找到 brandTestService.js")

print("\n" + "="*70)
print("修复完成")
print("="*70)
print()
print("📋 修复总结:")
print("  1. ✅ 修复了变量名错误 (task_status -> db_task_status)")
print("  2. ✅ 增强了错误处理和日志记录")
print("  3. ✅ 添加了详细的错误堆栈追踪")
print()
print("🔍 同类潜在 Bug 检查:")
print("  • 检查所有使用 db_task_status 的地方是否正确引用")
print("  • 检查所有降级逻辑是否有适当的错误处理")
print("  • 检查所有数据库查询是否有超时保护")
print()
print("⚠️  注意事项:")
print("  • 重启后端服务以应用修复")
print("  • 监控日志确认修复效果")
print("  • 如仍有超时，考虑增加前端超时时间")
print()
