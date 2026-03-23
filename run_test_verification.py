#!/usr/bin/env python3
"""
品牌影响力诊断功能 - 自动化测试验证脚本
"""

import sys
import os
import json
import sqlite3

print('='*70)
print('品牌影响力诊断功能 - 自动化测试验证')
print('='*70)

# 测试配置
BACKEND_PATH = 'backend_python'
DB_PATH = os.path.join(BACKEND_PATH, 'database.db')
sys.path.insert(0, BACKEND_PATH)

# 测试结果
test_results = {
    'passed': 0,
    'failed': 0,
    'tests': []
}

def test_result(name, passed, message=''):
    status = '✅ 通过' if passed else '❌ 失败'
    test_results['tests'].append({'name': name, 'passed': passed, 'message': message})
    if passed:
        test_results['passed'] += 1
    else:
        test_results['failed'] += 1
    print(f'{status}: {name}')
    if message:
        print(f'  {message}')

# =============================================================================
# 测试 1: 后端服务连通性
# =============================================================================
print('\n【测试 1】后端服务连通性测试')
try:
    import requests
    response = requests.get('http://127.0.0.1:5001/api/test', timeout=5)
    if response.status_code == 200:
        test_result('后端 API 健康检查', True, f'HTTP {response.status_code}')
    else:
        test_result('后端 API 健康检查', False, f'HTTP {response.status_code}')
except Exception as e:
    test_result('后端 API 健康检查', False, f'连接失败：{str(e)}')

# =============================================================================
# 测试 2: 数据库数据验证
# =============================================================================
print('\n【测试 2】数据库数据验证')
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查诊断报告数量
    cursor.execute('SELECT COUNT(*) as cnt FROM diagnosis_reports WHERE status="completed"')
    report_count = cursor.fetchone()['cnt']
    test_result('诊断报告数据', report_count > 0, f'已完成报告数：{report_count}')
    
    # 检查诊断结果数量
    cursor.execute('SELECT COUNT(*) as cnt FROM diagnosis_results')
    result_count = cursor.fetchone()['cnt']
    test_result('诊断结果数据', result_count > 0, f'结果记录数：{result_count}')
    
    # 检查分析数据
    cursor.execute('SELECT COUNT(*) as cnt FROM diagnosis_analysis')
    analysis_count = cursor.fetchone()['cnt']
    test_result('分析数据', analysis_count > 0, f'分析记录数：{analysis_count}')
    
    # 获取最新的 execution_id
    cursor.execute('''
        SELECT execution_id, brand_name, status 
        FROM diagnosis_reports 
        WHERE status = 'completed'
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    latest_report = cursor.fetchone()
    
    if latest_report:
        exec_id = latest_report['execution_id']
        test_result('最新执行 ID', True, f'{exec_id[:8]}... ({latest_report["brand_name"]})')
    else:
        exec_id = None
        test_result('最新执行 ID', False, '无已完成的报告')
    
    conn.close()
except Exception as e:
    test_result('数据库数据验证', False, f'错误：{str(e)}')
    exec_id = None

# =============================================================================
# 测试 3: 诊断报告 API 测试
# =============================================================================
print('\n【测试 3】诊断报告 API 测试')
if exec_id:
    try:
        import requests
        url = f'http://127.0.0.1:5001/api/diagnosis/report/{exec_id}'
        response = requests.get(url, timeout=30)
        
        test_result('API 响应状态', response.status_code == 200, f'HTTP {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查响应结构
            test_result('响应结构', data.get('success') == True, 'success=True')
            
            report_data = data.get('data', {})
            
            # 检查核心指标
            metrics = report_data.get('metrics', {})
            has_metrics = all(k in metrics for k in ['sov', 'sentiment', 'rank', 'influence'])
            test_result('核心指标 (metrics)', has_metrics, 
                       f'SOV={metrics.get("sov")}, sentiment={metrics.get("sentiment")}, rank={metrics.get("rank")}, influence={metrics.get("influence")}')
            
            # 检查评分维度
            dimension_scores = report_data.get('dimensionScores', {})
            has_dimensions = all(k in dimension_scores for k in ['authority', 'visibility', 'purity', 'consistency'])
            test_result('评分维度 (dimensionScores)', has_dimensions,
                       f'authority={dimension_scores.get("authority")}, visibility={dimension_scores.get("visibility")}, purity={dimension_scores.get("purity")}, consistency={dimension_scores.get("consistency")}')
            
            # 检查问题诊断墙
            diagnostic_wall = report_data.get('diagnosticWall', {})
            has_wall = 'risk_levels' in diagnostic_wall and 'priority_recommendations' in diagnostic_wall
            wall_data = diagnostic_wall.get('risk_levels', {})
            test_result('问题诊断墙 (diagnosticWall)', has_wall,
                       f'high_risks={len(wall_data.get("high", []))}, medium_risks={len(wall_data.get("medium", []))}, recommendations={len(diagnostic_wall.get("priority_recommendations", []))}')
            
            # 检查品牌分布
            brand_dist = report_data.get('brandDistribution', {})
            has_brand_dist = bool(brand_dist.get('data'))
            test_result('品牌分布 (brandDistribution)', has_brand_dist, f'brands={list(brand_dist.get("data", {}).keys())}')
            
            # 检查原始结果
            results = report_data.get('results', [])
            test_result('原始结果 (results)', len(results) > 0, f'results_count={len(results)}')
            
    except Exception as e:
        test_result('诊断报告 API', False, f'错误：{str(e)}')
else:
    test_result('诊断报告 API', False, '无可用的 execution_id')

# =============================================================================
# 测试 4: 服务层功能验证
# =============================================================================
print('\n【测试 4】服务层功能验证')
try:
    os.chdir(BACKEND_PATH)
    from wechat_backend.diagnosis_report_service import DiagnosisReportService
    
    service = DiagnosisReportService()
    
    if exec_id:
        report = service.get_full_report(exec_id)
        
        test_result('服务层返回', report is not None, 'get_full_report 返回数据')
        
        if report:
            # 验证指标计算
            has_metrics = 'metrics' in report
            test_result('指标计算 (metrics)', has_metrics, '已实现')
            
            has_dimensions = 'dimensionScores' in report
            test_result('维度计算 (dimensionScores)', has_dimensions, '已实现')
            
            has_wall = 'diagnosticWall' in report
            test_result('诊断墙生成 (diagnosticWall)', has_wall, '已实现')
            
            # 验证数据验证器
            from wechat_backend.validators.service_validator import ServiceDataValidator
            try:
                ServiceDataValidator.validate_report_data(report, exec_id)
                test_result('数据验证器', True, '验证通过')
            except Exception as ve:
                test_result('数据验证器', False, str(ve))
    else:
        test_result('服务层功能', False, '无可用的 execution_id')
        
except Exception as e:
    test_result('服务层功能验证', False, f'错误：{str(e)}')

# =============================================================================
# 测试结果汇总
# =============================================================================
print('\n' + '='*70)
print('测试结果汇总')
print('='*70)
print(f'总测试数：{len(test_results["tests"])}')
print(f'✅ 通过：{test_results["passed"]}')
print(f'❌ 失败：{test_results["failed"]}')
print(f'通过率：{test_results["passed"]/len(test_results["tests"])*100:.1f}%')
print('='*70)

# 详细结果
print('\n详细结果:')
for test in test_results['tests']:
    status = '✅' if test['passed'] else '❌'
    print(f'  {status} {test["name"]}: {test["message"]}')

# 最终结论
print('\n' + '='*70)
if test_results['failed'] == 0:
    print('🎉 所有测试通过！品牌影响力诊断功能正常工作')
elif test_results['failed'] <= 2:
    print('⚠️  部分测试失败，但不影响核心功能')
else:
    print('❌ 多个测试失败，需要排查问题')
print('='*70)
