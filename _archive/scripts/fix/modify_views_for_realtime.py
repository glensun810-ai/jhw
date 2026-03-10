#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修改 views.py 返回实时统计

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加实时分析器引用
old_imports = '''from .models import TaskStatus, TaskStage, get_task_status, save_task_status, get_deep_intelligence_result, save_deep_intelligence_result, update_task_stage'''

new_imports = '''from .models import TaskStatus, TaskStage, get_task_status, save_task_status, get_deep_intelligence_result, save_deep_intelligence_result, update_task_stage
from .realtime_analyzer import get_analyzer'''

content = content.replace(old_imports, new_imports)

# 2. 修改 get_task_status_api 返回实时统计
old_status_api = '''    # 按照 API 契约返回任务状态信息
    response_data = {
        'task_id': task_id,
        'progress': task_status.get('progress', 0),
        'stage': task_status.get('stage', 'init'),  # 【任务 C：前端同步】确保返回当前的 stage 描述
        'status': task_status.get('status', 'init'),
        'results': task_status.get('results', []),
        'is_completed': task_status.get('status') == 'completed',
        'created_at': task_status.get('start_time', None)
    }

    # 返回任务状态信息
    return jsonify(response_data), 200'''

new_status_api = '''    # 按照 API 契约返回任务状态信息
    response_data = {
        'task_id': task_id,
        'progress': task_status.get('progress', 0),
        'stage': task_status.get('stage', 'init'),
        'status': task_status.get('status', 'init'),
        'results': task_status.get('results', []),
        'is_completed': task_status.get('status') == 'completed',
        'created_at': task_status.get('start_time', None)
    }
    
    #【P0 新增】添加实时统计信息
    analyzer = get_analyzer(task_id)
    if analyzer:
        realtime_progress = analyzer.get_realtime_progress()
        response_data['realtimeStats'] = realtime_progress
        response_data['completedTasks'] = realtime_progress['completed']
        response_data['totalTasks'] = realtime_progress['total']
        response_data['brandRankings'] = realtime_progress['brand_rankings']
        response_data['sov'] = realtime_progress['sov']
        response_data['avgSentiment'] = realtime_progress['avg_sentiment']
        
        api_logger.info(f"Returning realtime stats for task {task_id}: completed={realtime_progress['completed']}, sov={realtime_progress['sov']}%")

    # 返回任务状态信息
    return jsonify(response_data), 200'''

content = content.replace(old_status_api, new_status_api)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ views.py 已修改：返回实时统计')
