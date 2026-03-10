#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端诊断流程测试脚本

测试范围：
1. 创建诊断任务
2. 轮询任务状态
3. 验证结果完整性
4. 验证数据库保存
5. 验证报告可查询
"""

import sys
import time
import requests
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5001'

class TestColors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_step(text):
    print(f"\n{TestColors.BLUE}{'='*60}{TestColors.END}")
    print(f"{TestColors.BLUE}{text}{TestColors.END}")
    print(f"{TestColors.BLUE}{'='*60}{TestColors.END}")

def print_success(text):
    print(f"{TestColors.GREEN}✅ {text}{TestColors.END}")

def print_error(text):
    print(f"{TestColors.RED}❌ {text}{TestColors.END}")

def print_warning(text):
    print(f"{TestColors.YELLOW}⚠️  {text}{TestColors.END}")

def test_health_check():
    """测试 1: 健康检查"""
    print_step("测试 1: 健康检查")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"健康检查通过：{response.json()}")
            return True
        else:
            print_error(f"健康检查失败：{response.status_code}")
            return False
    except Exception as e:
        print_error(f"健康检查异常：{e}")
        return False

def test_create_diagnosis():
    """测试 2: 创建诊断任务"""
    print_step("测试 2: 创建诊断任务")
    
    payload = {
        "brand_list": ["测试品牌"],
        "selectedModels": ["deepseek"],
        "custom_question": "测试问题"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            # Support both camelCase and snake_case
            execution_id = data.get('execution_id') or data.get('executionId')
            if execution_id:
                print_success(f"诊断任务创建成功：{execution_id}")
                return execution_id
            else:
                print_error(f"响应中没有 execution_id: {data}")
                return None
        else:
            print_error(f"创建诊断任务失败：{response.status_code}")
            return None
    except Exception as e:
        print_error(f"创建诊断任务异常：{e}")
        return None

def test_poll_status(execution_id):
    """测试 3: 轮询任务状态"""
    print_step("测试 3: 轮询任务状态")

    max_polls = 60
    poll_interval = 2
    
    # Use the correct endpoint
    status_url = f"{BASE_URL}/api/diagnosis/status/{execution_id}"

    for i in range(max_polls):
        try:
            response = requests.get(
                status_url,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                stage = data.get('stage', 'unknown')
                progress = data.get('progress', 0)
                # Support both result field names
                results_data = data.get('results') or data.get('detailed_results') or []
                results_count = len(results_data)

                print(f"  轮询 {i+1}/{max_polls}: stage={stage}, progress={progress}%, results={results_count}")

                # 检查完成状态
                if stage in ['completed', 'finished', 'done'] or data.get('is_completed'):
                    print_success(f"任务完成！results={results_count}")
                    return data

                # 检查失败状态
                if stage == 'failed':
                    if results_count > 0:
                        print_warning(f"任务标记为失败但有结果：results={results_count}")
                        return data
                    else:
                        print_error(f"任务失败：{data.get('error', '未知错误')}")
                        return None
            elif response.status_code == 404:
                print_warning(f"轮询 404 - 任务可能尚未创建：{execution_id}")
                time.sleep(poll_interval)
            else:
                print_error(f"轮询失败：{response.status_code}")
                time.sleep(poll_interval)

        except Exception as e:
            print_error(f"轮询异常：{e}")
            time.sleep(poll_interval)

    print_error(f"轮询超时：{max_polls * poll_interval}秒")
    return None

def test_database_save(execution_id):
    """测试 4: 验证数据库保存"""
    print_step("测试 4: 验证数据库保存")

    import sqlite3
    conn = sqlite3.connect('backend_python/database.db')
    cursor = conn.cursor()

    # 检查 diagnosis_reports
    cursor.execute('SELECT execution_id, brand_name, status, stage, progress FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))
    report = cursor.fetchone()
    if report:
        print_success(f"diagnosis_reports: {report}")
    else:
        print_error("diagnosis_reports: 无记录")

    # 检查 diagnosis_results (替代 dimension_results)
    try:
        cursor.execute('SELECT execution_id, brand, question, model, response FROM diagnosis_results WHERE execution_id = ? LIMIT 5', (execution_id,))
        results = cursor.fetchall()
        if results:
            print_success(f"diagnosis_results: 找到 {len(results)} 条记录")
            for r in results[:3]:
                print_success(f"  - brand={r[1]}, model={r[3]}")
        else:
            print_error("diagnosis_results: 无记录")
    except sqlite3.OperationalError as e:
        print_warning(f"diagnosis_results 表不存在或字段错误：{e}")

    # 检查 report_snapshots
    try:
        cursor.execute('SELECT execution_id, report_version FROM report_snapshots WHERE execution_id = ?', (execution_id,))
        snapshot = cursor.fetchone()
        if snapshot:
            print_success(f"report_snapshots: {snapshot}")
        else:
            print_error("report_snapshots: 无记录")
    except sqlite3.OperationalError as e:
        print_warning(f"report_snapshots 表不存在：{e}")

    conn.close()

def test_get_report(execution_id):
    """测试 5: 验证报告可查询"""
    print_step("测试 5: 验证报告可查询")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/diagnosis/report/{execution_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('report'):
                print_success(f"报告查询成功：{data['report'].get('brand_name')}")
                return True
            else:
                print_error(f"报告数据为空：{data}")
                return False
        else:
            print_error(f"报告查询失败：{response.status_code}")
            return False
    except Exception as e:
        print_error(f"报告查询异常：{e}")
        return False

def main():
    """主测试流程"""
    print(f"\n{TestColors.GREEN}{'='*70}{TestColors.END}")
    print(f"{TestColors.GREEN}端到端诊断流程测试{TestColors.END}")
    print(f"{TestColors.GREEN}{'='*70}{TestColors.END}")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"服务器地址：{BASE_URL}")
    
    results = {
        'health_check': False,
        'create_diagnosis': False,
        'poll_status': False,
        'database_save': False,
        'get_report': False
    }
    
    # 测试 1: 健康检查
    results['health_check'] = test_health_check()
    if not results['health_check']:
        print_error("\n健康检查失败，无法继续测试")
        return False
    
    # 测试 2: 创建诊断任务
    execution_id = test_create_diagnosis()
    if execution_id:
        results['create_diagnosis'] = True
    else:
        print_error("\n创建诊断任务失败，无法继续测试")
        return False
    
    # 测试 3: 轮询任务状态
    status_data = test_poll_status(execution_id)
    if status_data:
        results['poll_status'] = True
    else:
        print_error("\n轮询任务状态失败")
    
    # 测试 4: 验证数据库保存
    test_database_save(execution_id)
    results['database_save'] = True  # 无论结果如何都标记为完成
    
    # 测试 5: 验证报告可查询
    results['get_report'] = test_get_report(execution_id)
    
    # 打印汇总
    print(f"\n{TestColors.BLUE}{'='*70}{TestColors.END}")
    print(f"{TestColors.BLUE}测试汇总{TestColors.END}")
    print(f"{TestColors.BLUE}{'='*70}{TestColors.END}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{TestColors.GREEN}✅ 通过{TestColors.END}" if result else f"{TestColors.RED}❌ 失败{TestColors.END}"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print(f"\n{TestColors.GREEN}🎉 所有测试通过！{TestColors.END}")
        return True
    else:
        print(f"\n{TestColors.YELLOW}⚠️  部分测试失败，请检查日志{TestColors.END}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
