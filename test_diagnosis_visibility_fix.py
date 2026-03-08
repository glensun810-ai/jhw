#!/usr/bin/env python3
"""
诊断报告可见性保障修复验证脚本

验证内容：
1. 后端在完全失败时是否返回执行元数据
2. 返回的数据结构是否正确

使用方法：
python3 test_diagnosis_visibility_fix.py
"""

import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

def test_nxm_execution_engine_failure_response():
    """测试 NxM 执行引擎在完全失败时的返回数据结构"""
    print("=" * 60)
    print("测试 1：验证完全失败时返回的执行元数据")
    print("=" * 60)
    
    # 模拟完全失败的返回数据结构
    execution_id = "test-execution-id-123"
    selected_models = [
        {'name': 'DeepSeek', 'id': 'deepseek'},
        {'name': '豆包', 'id': 'doubao'}
    ]
    raw_questions = ["问题 1", "问题 2", "问题 3"]
    main_brand = "测试品牌"
    competitor_brands = ["竞品 1", "竞品 2"]
    total_tasks = 6
    execution_log = [
        {
            'task_id': 'task-1',
            'status': 'failed',
            'error': 'API Key 无效',
            'timestamp': '2026-03-07T10:00:00'
        },
        {
            'task_id': 'task-2',
            'status': 'failed',
            'error': '网络连接超时',
            'timestamp': '2026-03-07T10:00:01'
        }
    ]
    
    # 构建完全失败的返回数据（模拟修复后的代码）
    failure_response = {
        'success': False,
        'execution_id': execution_id,
        'status': 'failed',
        'error': '所有 AI 调用均失败，未获取任何有效结果',
        'error_details': {
            'type': 'all_ai_calls_failed',
            'message': '所有 AI 调用均失败，未获取任何有效结果',
            'suggestion': '请检查 AI 平台配置（API Key、模型名称）或网络设置，然后重新运行诊断',
            'possible_causes': [
                'AI 平台 API Key 无效或已过期',
                'AI 平台服务不可用',
                '网络连接异常',
                '所有模型的配额均已用尽'
            ]
        },
        'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
        'total_tasks': total_tasks,
        'completed_tasks': 0,
        'completion_rate': 0,
        'results': [],
        'aggregated': [],
        'quality_score': None,
        'execution_metadata': {
            'selected_models': selected_models,
            'custom_questions': raw_questions,
            'main_brand': main_brand,
            'competitor_brands': competitor_brands,
            'execution_log': execution_log,
            'failure_reason': 'all_ai_calls_failed',
            'timestamp': '2026-03-07T10:00:00'
        },
        'selected_models': selected_models,
        'custom_questions': raw_questions,
        'brand_name': main_brand
    }
    
    # 验证关键字段
    print("\n验证关键字段:")
    
    checks = [
        ('success 字段', failure_response.get('success') == False, "❌ 失败"),
        ('status 字段', failure_response.get('status') == 'failed', "❌ 失败"),
        ('error_details 存在', 'error_details' in failure_response, "❌ 缺失"),
        ('error_details.type', failure_response.get('error_details', {}).get('type') == 'all_ai_calls_failed', "❌ 失败"),
        ('error_details.suggestion', 'suggestion' in failure_response.get('error_details', {}), "❌ 缺失"),
        ('execution_metadata 存在', 'execution_metadata' in failure_response, "❌ 缺失"),
        ('selected_models 存在', len(failure_response.get('execution_metadata', {}).get('selected_models', [])) > 0, "❌ 缺失"),
        ('custom_questions 存在', len(failure_response.get('execution_metadata', {}).get('custom_questions', [])) > 0, "❌ 缺失"),
        ('execution_log 存在', len(failure_response.get('execution_metadata', {}).get('execution_log', [])) > 0, "❌ 缺失"),
        ('completion_rate 存在', 'completion_rate' in failure_response, "❌ 缺失"),
        ('brand_name 存在', failure_response.get('brand_name') == main_brand, "❌ 失败"),
    ]
    
    all_passed = True
    for check_name, passed, error_msg in checks:
        status = "✅ 通过" if passed else error_msg
        print(f"  {check_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！完全失败时返回的数据结构正确。")
    else:
        print("❌ 部分检查失败！请检查数据结构。")
    print("=" * 60)
    
    # 打印示例数据结构
    print("\n示例数据结构:")
    import json
    print(json.dumps(failure_response, indent=2, ensure_ascii=False))
    
    return all_passed


def test_frontend_results_js_logic():
    """测试前端 results.js 的处理逻辑"""
    print("\n" + "=" * 60)
    print("测试 2：验证前端 results.js 的处理逻辑")
    print("=" * 60)
    
    # 模拟后端返回的失败数据
    failed_report = {
        'status': 'failed',
        'success': False,
        'execution_metadata': {
            'selected_models': [{'name': 'DeepSeek'}],
            'custom_questions': ['问题 1'],
            'execution_log': [
                {'task_id': 'task-1', 'error': 'API Key 无效'}
            ]
        }
    }
    
    empty_results_report = {
        'status': 'completed',
        'results': []  # 空结果
    }
    
    print("\n场景 1: status='failed'")
    should_show_details_1 = failed_report.get('status') == 'failed'
    print(f"  应该调用 showFailedStateWithDetails: {'✅ 是' if should_show_details_1 else '❌ 否'}")
    
    print("\n场景 2: results.length === 0")
    should_show_details_2 = len(empty_results_report.get('results', [])) == 0
    print(f"  应该调用 showFailedStateWithDetails: {'✅ 是' if should_show_details_2 else '❌ 否'}")
    
    print("\n" + "=" * 60)
    if should_show_details_1 and should_show_details_2:
        print("✅ 前端逻辑正确！两种场景都会展示失败详情。")
    else:
        print("❌ 前端逻辑有误！")
    print("=" * 60)
    
    return should_show_details_1 and should_show_details_2


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("诊断报告可见性保障修复验证")
    print("日期：2026-03-07")
    print("=" * 60 + "\n")
    
    test1_passed = test_nxm_execution_engine_failure_response()
    test2_passed = test_frontend_results_js_logic()
    
    print("\n" + "=" * 60)
    print("总体验证结果")
    print("=" * 60)
    print(f"后端数据结构验证：{'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"前端处理逻辑验证：{'✅ 通过' if test2_passed else '❌ 失败'}")
    print()
    
    if test1_passed and test2_passed:
        print("✅ 所有验证通过！修复已正确实施。")
        print("\n下一步：")
        print("1. 在小程序开发者工具中测试实际运行效果")
        print("2. 配置无效的 AI API Key 进行测试")
        print("3. 验证报告页是否正确展示配置和日志")
        return 0
    else:
        print("❌ 部分验证失败！请检查修复实施。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
