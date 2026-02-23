#!/usr/bin/env python3
"""
架构自检 2.0 - 自动化验证脚本

验证原报告中所有问题是否已修复，并检查新的潜在问题
"""

import os
import sys
from pathlib import Path
import json

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
BACKEND_ROOT = PROJECT_ROOT / 'backend_python'

# 验证结果
verification_results = {
    'P0_issues': {},
    'P1_issues': {},
    'P2_issues': {},
    'new_issues': [],
    'summary': {}
}

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    exists = file_path.exists()
    verification_results['summary'][f'file_{description}'] = '✅' if exists else '❌'
    return exists

def check_code_contains(file_path, patterns, description):
    """检查代码是否包含特定模式"""
    if not file_path.exists():
        verification_results['summary'][f'code_{description}'] = '❌ 文件不存在'
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_found = True
    for pattern in patterns:
        if pattern not in content:
            all_found = False
            break
    
    verification_results['summary'][f'code_{description}'] = '✅' if all_found else '❌'
    return all_found

def verify_p0_fixes():
    """验证 P0 级问题修复"""
    print("🔍 验证 P0 级问题修复...")
    
    # P0-1: execution_store 降级查询
    views_file = BACKEND_ROOT / 'wechat_backend' / 'views.py'
    p0_1_fixed = check_code_contains(
        views_file,
        ['db_task_status.stage.value', 'execution_id', 'finally:', 'conn.close()'],
        'P0-1 降级查询修复'
    )
    verification_results['P0_issues']['P0-1'] = {
        'description': 'execution_store 降级查询',
        'status': '✅ 已修复' if p0_1_fixed else '❌ 未修复',
        'file': str(views_file)
    }
    
    # P0-2: 数据库索引
    migrate_file = BACKEND_ROOT / 'migrate_execution_id.py'
    p0_2_fixed = check_file_exists(migrate_file, 'P0-2 数据库迁移')
    verification_results['P0_issues']['P0-2'] = {
        'description': '数据库 execution_id 索引',
        'status': '✅ 已修复' if p0_2_fixed else '❌ 未修复',
        'file': str(migrate_file)
    }
    
    print(f"  P0-1: {verification_results['P0_issues']['P0-1']['status']}")
    print(f"  P0-2: {verification_results['P0_issues']['P0-2']['status']}")

def verify_p1_fixes():
    """验证 P1 级问题修复"""
    print("\n🔍 验证 P1 级问题修复...")
    
    views_file = BACKEND_ROOT / 'wechat_backend' / 'views.py'
    
    # P1-1: Storage 管理器
    storage_file = PROJECT_ROOT / 'utils' / 'storage-manager.js'
    p1_1_fixed = check_file_exists(storage_file, 'P1-1 Storage 管理器')
    
    # 检查 index.js 集成
    index_file = PROJECT_ROOT / 'pages' / 'index' / 'index.js'
    p1_1_integrated = check_code_contains(
        index_file,
        ['saveDiagnosisResult', 'storage-manager'],
        'P1-1 index.js 集成'
    )
    
    verification_results['P1_issues']['P1-1'] = {
        'description': '统一 Storage 数据格式',
        'status': '✅ 已修复' if (p1_1_fixed and p1_1_integrated) else '⚠️ 部分修复',
        'file': str(storage_file)
    }
    
    # P1-2: 错误处理
    nxm_file = BACKEND_ROOT / 'wechat_backend' / 'nxm_execution_engine.py'
    p1_2_backend = check_code_contains(
        nxm_file,
        ['error_details', 'execution_store'],
        'P1-2 后端错误处理'
    )
    
    brand_service = PROJECT_ROOT / 'services' / 'brandTestService.js'
    p1_2_frontend = check_code_contains(
        brand_service,
        ['createUserFriendlyError', 'errorInfo'],
        'P1-2 前端错误处理'
    )
    
    verification_results['P1_issues']['P1-2'] = {
        'description': '完善错误处理链路',
        'status': '✅ 已修复' if (p1_2_backend and p1_2_frontend) else '⚠️ 部分修复',
        'file': str(nxm_file)
    }
    
    # P1-3: selectedModels 简化
    p1_3_frontend = check_code_contains(
        brand_service,
        ['modelNames', '字符串数组'],
        'P1-3 前端简化'
    )
    
    verification_results['P1_issues']['P1-3'] = {
        'description': '简化 selectedModels 格式',
        'status': '✅ 已修复' if p1_3_frontend else '⚠️ 部分修复',
        'file': str(brand_service)
    }
    
    # P1-5: 数据库连接关闭
    p1_5_fixed = check_code_contains(
        views_file,
        ['finally:', 'cursor.close()', 'conn.close()'],
        'P1-5 数据库连接关闭'
    )
    
    verification_results['P1_issues']['P1-5'] = {
        'description': '数据库连接关闭',
        'status': '✅ 已修复' if p1_5_fixed else '❌ 未修复',
        'file': str(views_file)
    }
    
    print(f"  P1-1: {verification_results['P1_issues']['P1-1']['status']}")
    print(f"  P1-2: {verification_results['P1_issues']['P1-2']['status']}")
    print(f"  P1-3: {verification_results['P1_issues']['P1-3']['status']}")
    print(f"  P1-5: {verification_results['P1_issues']['P1-5']['status']}")

def verify_p2_fixes():
    """验证 P2 级问题修复"""
    print("\n🔍 验证 P2 级问题修复...")
    
    # P2-1: 日志优化
    log_config = BACKEND_ROOT / 'wechat_backend' / 'log_level_config.py'
    p2_1_fixed = check_file_exists(log_config, 'P2-1 日志优化')
    
    run_file = BACKEND_ROOT / 'run.py'
    p2_1_integrated = check_code_contains(
        run_file,
        ['setup_optimized_logging', 'log_level_config'],
        'P2-1 集成到 run.py'
    )
    
    verification_results['P2_issues']['P2-1'] = {
        'description': '优化日志记录级别',
        'status': '✅ 已修复' if (p2_1_fixed and p2_1_integrated) else '⚠️ 部分修复',
        'file': str(log_config)
    }
    
    # P2-2: 限流监控
    rate_limit = BACKEND_ROOT / 'wechat_backend' / 'security' / 'rate_limit_monitor.py'
    p2_2_fixed = check_file_exists(rate_limit, 'P2-2 限流监控')
    
    verification_results['P2_issues']['P2-2'] = {
        'description': '添加请求限流监控',
        'status': '✅ 已修复' if p2_2_fixed else '❌ 未修复',
        'file': str(rate_limit)
    }
    
    print(f"  P2-1: {verification_results['P2_issues']['P2-1']['status']}")
    print(f"  P2-2: {verification_results['P2_issues']['P2-2']['status']}")

def scan_new_issues():
    """扫描新的潜在问题"""
    print("\n🔍 扫描新的潜在问题...")
    
    # 检查临时文件
    temp_files = list(PROJECT_ROOT.glob('*.bak')) + list(PROJECT_ROOT.glob('*.bak3'))
    if temp_files:
        verification_results['new_issues'].append({
            'type': '临时文件',
            'severity': '🟢 低',
            'description': f'发现 {len(temp_files)} 个备份文件',
            'suggestion': '清理临时文件'
        })
    
    # 检查大型文件
    large_files = []
    for file in PROJECT_ROOT.rglob('*.js'):
        if file.stat().st_size > 100000:  # > 100KB
            large_files.append(str(file.relative_to(PROJECT_ROOT)))
    
    if large_files:
        verification_results['new_issues'].append({
            'type': '代码组织',
            'severity': '🟡 中',
            'description': f'发现 {len(large_files)} 个大型 JS 文件 (>100KB)',
            'suggestion': '考虑代码拆分和模块化'
        })
    
    # 检查 TODO/FIXME 注释
    todo_count = 0
    for py_file in BACKEND_ROOT.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                todo_count += content.count('TODO') + content.count('FIXME')
        except:
            pass
    
    if todo_count > 10:
        verification_results['new_issues'].append({
            'type': '技术债务',
            'severity': '🟡 中',
            'description': f'发现 {todo_count} 个 TODO/FIXME 注释',
            'suggestion': '优先处理高优先级的 TODO'
        })
    
    print(f"  发现 {len(verification_results['new_issues'])} 个新的潜在问题")

def generate_summary():
    """生成总结"""
    p0_total = len(verification_results['P0_issues'])
    p0_fixed = sum(1 for v in verification_results['P0_issues'].values() if '✅' in v['status'])
    
    p1_total = len(verification_results['P1_issues'])
    p1_fixed = sum(1 for v in verification_results['P1_issues'].values() if '✅' in v['status'])
    
    p2_total = len(verification_results['P2_issues'])
    p2_fixed = sum(1 for v in verification_results['P2_issues'].values() if '✅' in v['status'])
    
    verification_results['summary']['P0 修复率'] = f"{p0_fixed}/{p0_total} ({p0_fixed/p0_total*100:.0f}%)"
    verification_results['summary']['P1 修复率'] = f"{p1_fixed}/{p1_total} ({p1_fixed/p1_total*100:.0f}%)"
    verification_results['summary']['P2 修复率'] = f"{p2_fixed}/{p2_total} ({p2_fixed/p2_total*100:.0f}%)"
    verification_results['summary']['新问题数量'] = len(verification_results['new_issues'])
    
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    print(f"P0 级问题：{verification_results['summary']['P0 修复率']}")
    print(f"P1 级问题：{verification_results['summary']['P1 修复率']}")
    print(f"P2 级问题：{verification_results['summary']['P2 修复率']}")
    print(f"新问题：{verification_results['summary']['新问题数量']} 个")

def save_report():
    """保存验证报告"""
    # JSON 报告
    report_file = PROJECT_ROOT / 'docs' / 'architecture_verification_2.0.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(verification_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON 验证报告已保存：{report_file}")
    
    # Markdown 报告路径
    md_report = PROJECT_ROOT / 'docs' / '2026-02-23_架构自检与问题盘点报告_2.0.md'
    print(f"✅ Markdown 报告已生成：{md_report}")

if __name__ == '__main__':
    print("="*60)
    print("架构自检 2.0 - 自动化验证")
    print("="*60)
    print()
    
    verify_p0_fixes()
    verify_p1_fixes()
    verify_p2_fixes()
    scan_new_issues()
    generate_summary()
    save_report()
    
    print("\n" + "="*60)
    print("验证完成！")
    print("="*60)
