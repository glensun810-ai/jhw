#!/usr/bin/env python3
"""
品牌诊断端到端测试脚本
测试完整的诊断流程：AI 调用 → 结果保存 → 后台分析 → 报告生成
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_backend'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from wechat_backend.logging_config import api_logger
from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator


async def test_full_diagnosis():
    """测试完整诊断流程"""
    
    print("=" * 60)
    print("  品牌诊断端到端测试")
    print(f"  时间：{datetime.now().isoformat()}")
    print("=" * 60)
    
    # 测试参数
    execution_id = f"test_{int(time.time())}"
    user_id = "test_user"
    brand_list = ["趣车良品", "车蚂蚁", "车享家"]
    selected_models = [
        {"name": "doubao", "key": os.environ.get('ARK_API_KEY')},
    ]
    custom_questions = [
        "趣车良品的产品质量怎么样？",
    ]
    
    print(f"\n测试参数:")
    print(f"  Execution ID: {execution_id}")
    print(f"  品牌列表：{brand_list}")
    print(f"  模型列表：{[m['name'] for m in selected_models]}")
    print(f"  问题列表：{custom_questions}")
    
    # 创建 execution_store（内存状态存储）
    execution_store = {}
    
    # 创建编排器
    orchestrator = DiagnosisOrchestrator(execution_id, execution_store)
    
    try:
        print(f"\n开始执行诊断...")
        start_time = time.time()
        
        # 执行诊断
        result = await orchestrator.execute_diagnosis(
            user_id=user_id,
            brand_list=brand_list,
            selected_models=selected_models,
            custom_questions=custom_questions,
            user_openid=user_id,
            user_level='Free'
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'=' * 60}")
        print(f"  诊断执行完成")
        print(f"  总耗时：{duration:.2f}秒")
        print(f"{'=' * 60}")
        
        # 检查结果
        if result.get('success'):
            print("\n✅ 诊断成功!")
            print(f"  Execution ID: {result.get('execution_id')}")
            print(f"  Trace ID: {result.get('trace_id')}")
            
            # 检查报告
            report = result.get('report')
            if report:
                print(f"\n  报告摘要:")
                print(f"    品牌名称：{report.get('brandName', 'N/A')}")
                print(f"    总体评分：{report.get('overallScore', 'N/A')}")
                print(f"    平台分析：{len(report.get('platformAnalysis', []))} 个平台")
                print(f"    竞品分析：{len(report.get('competitiveAnalysis', []))} 个竞品")
                
                # 保存报告到文件
                report_file = f"test_report_{execution_id}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"\n  报告已保存到：{report_file}")
            else:
                print("\n  ⚠️  报告数据为空")
        else:
            print("\n❌ 诊断失败!")
            print(f"  错误：{result.get('error', 'Unknown')}")
            print(f"  错误码：{result.get('error_code', 'N/A')}")
            print(f"  Trace ID: {result.get('trace_id', 'N/A')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  品牌诊断系统端到端测试")
    print("=" * 60 + "\n")
    
    # 检查 API Key 配置
    api_key = os.environ.get('ARK_API_KEY')
    if not api_key:
        print("❌ ARK_API_KEY 未配置，无法执行测试")
        return False
    
    print(f"✅ ARK_API_KEY 已配置：{api_key[:8]}...{api_key[-4:]}")
    
    # 运行异步测试
    success = asyncio.run(test_full_diagnosis())
    
    print("\n" + "=" * 60)
    print(f"  测试结果：{'✅ 通过' if success else '❌ 失败'}")
    print("=" * 60 + "\n")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
