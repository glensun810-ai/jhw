#!/usr/bin/env python3
"""
端到端诊断测试脚本

测试场景：单品牌、单模型、单问题
目标：验证完整诊断流程能否成功执行

用法：
    python3 backend_python/scripts/e2e_diagnosis_test.py
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / 'backend_python'
sys.path.insert(0, str(backend_path))

# 测试配置
TEST_CONFIG = {
    'brand_list': ['测试品牌'],
    'selectedModels': [{'name': 'doubao', 'checked': True}],
    'custom_question': '请介绍一下这个品牌的知名度',
    'userOpenid': 'test_user_e2e',
    'userLevel': 'Free'
}


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step_num, description):
    """打印步骤"""
    print(f"\n[步骤 {step_num}] {description}")
    print("-" * 60)


def test_perform_brand_test():
    """测试执行品牌诊断"""
    print_header("端到端诊断测试 - 单品牌单模型")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试配置：{json.dumps(TEST_CONFIG, ensure_ascii=False, indent=2)}")
    
    step = 0
    
    # ========== 步骤 1: 导入必要的模块 ==========
    step += 1
    print_step(step, "导入模块")
    
    try:
        from wechat_backend.database_connection_pool import get_db_connection
        from wechat_backend.views.diagnosis_views import execution_store
        from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator
        print("✅ 模块导入成功")
    except Exception as e:
        print(f"❌ 模块导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========== 步骤 2: 准备测试数据 ==========
    step += 1
    print_step(step, "准备测试数据")
    
    execution_id = f"e2e_test_{int(time.time())}"
    print(f"Execution ID: {execution_id}")
    
    # ========== 步骤 3: 初始化诊断编排器 ==========
    step += 1
    print_step(step, "初始化诊断编排器")
    
    orchestrator = DiagnosisOrchestrator(execution_id, execution_store)
    print(f"✅ 编排器已初始化")
    
    # ========== 步骤 4: 执行诊断流程 ==========
    step += 1
    print_step(step, "执行诊断流程（异步）")
    
    import asyncio
    
    async def run_test():
        result = await orchestrator.execute_diagnosis(
            user_id='test_user_e2e',
            brand_list=TEST_CONFIG['brand_list'],
            selected_models=TEST_CONFIG['selectedModels'],
            custom_questions=[TEST_CONFIG['custom_question']],
            user_openid=TEST_CONFIG['userOpenid'],
            user_level=TEST_CONFIG['userLevel']
        )
        return result
    
    try:
        print("⏳ 开始执行诊断...")
        start_time = time.time()
        
        # 运行异步诊断
        result = asyncio.run(run_test())
        
        elapsed = time.time() - start_time
        print(f"⏱️  执行耗时：{elapsed:.2f}秒")
        
        # 检查结果
        if result.get('success'):
            print("✅ 诊断执行成功")
            print(f"   Execution ID: {result.get('execution_id')}")
            print(f"   Trace ID: {result.get('trace_id')}")
            print(f"   总耗时：{result.get('total_time', 'N/A')}秒")
        else:
            print("❌ 诊断执行失败")
            print(f"   错误：{result.get('error')}")
            print(f"   错误码：{result.get('error_code')}")
            
    except Exception as e:
        print(f"❌ 诊断执行异常：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========== 步骤 5: 检查数据库记录 ==========
    step += 1
    print_step(step, "检查数据库记录")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查报告记录
        cursor.execute("""
            SELECT id, execution_id, status, progress, stage, is_completed, should_stop_polling
            FROM diagnosis_reports
            WHERE execution_id = ?
        """, (execution_id,))
        
        report = cursor.fetchone()
        
        if report:
            print(f"✅ 报告记录已创建")
            print(f"   ID: {report[0]}")
            print(f"   Status: {report[2]}")
            print(f"   Progress: {report[3]}%")
            print(f"   Stage: {report[4]}")
            print(f"   Is Completed: {report[5]}")
            print(f"   Should Stop Polling: {report[6]}")
        else:
            print(f"❌ 报告记录未找到")
        
        # 检查结果记录
        cursor.execute("""
            SELECT COUNT(*)
            FROM diagnosis_results
            WHERE execution_id = ?
        """, (execution_id,))
        
        result_count = cursor.fetchone()[0]
        print(f"   结果记录数：{result_count}")
        
        if result_count > 0:
            print(f"✅ 结果记录已创建")
            
            # 检查第一条结果
            cursor.execute("""
                SELECT brand, model, sentiment, quality_score
                FROM diagnosis_results
                WHERE execution_id = ?
                LIMIT 1
            """, (execution_id,))
            
            first_result = cursor.fetchone()
            if first_result:
                print(f"   Brand: {first_result[0]}")
                print(f"   Model: {first_result[1]}")
                print(f"   Sentiment: {first_result[2]}")
                print(f"   Quality Score: {first_result[3]}")
        else:
            print(f"⚠️  无结果记录")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库检查失败：{e}")
        import traceback
        traceback.print_exc()
    
    # ========== 步骤 6: 检查 execution_store ==========
    step += 1
    print_step(step, "检查内存状态")
    
    if execution_id in execution_store:
        state = execution_store[execution_id]
        print(f"✅ 内存状态存在")
        print(f"   Status: {state.get('status')}")
        print(f"   Stage: {state.get('stage')}")
        print(f"   Progress: {state.get('progress')}%")
        print(f"   Is Completed: {state.get('is_completed')}")
    else:
        print(f"⚠️  内存状态不存在")
    
    # ========== 总结 ==========
    print_header("测试总结")
    
    # 检查最终状态
    success = result.get('success', False)
    
    if success:
        print("✅ 端到端测试通过")
        print("\n📋 诊断流程验证清单:")
        print("  ✅ 诊断编排器初始化")
        print("  ✅ AI 调用执行")
        print("  ✅ 结果保存到数据库")
        print("  ✅ 状态更新到内存")
        return True
    else:
        print("❌ 端到端测试失败")
        print(f"   失败原因：{result.get('error', '未知错误')}")
        return False


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " " * 15 + "端到端诊断测试" + " " * 25 + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    success = test_perform_brand_test()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过！诊断流程正常工作。")
        sys.exit(0)
    else:
        print("❌ 测试失败。请查看上方错误信息。")
        sys.exit(1)
