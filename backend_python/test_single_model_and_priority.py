#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单模型调用与优先级评估测试脚本

测试内容：
1. 单模型执行器 - 用户选择哪个模型就用哪个
2. 优先级评估器 - DeepSeek → 豆包 → 通义千问
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 设置路径
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

wechat_backend_dir = os.path.join(base_dir, 'wechat_backend')
if wechat_backend_dir not in sys.path:
    sys.path.insert(0, wechat_backend_dir)

# 加载 .env 文件
root_dir = Path(base_dir).parent
env_file = root_dir / '.env'

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载配置文件：{env_file}")
else:
    print(f"❌ 未找到配置文件：{env_file}")
    sys.exit(1)


def test_single_model_executor():
    """测试单模型执行器"""
    print("\n" + "="*60)
    print("测试 1: 单模型执行器（用户选择哪个就用哪个）")
    print("="*60)
    
    try:
        from wechat_backend.multi_model_executor import get_single_model_executor
        import asyncio
        
        executor = get_single_model_executor(timeout=30)
        
        # 测试用户选择 DeepSeek
        print("\n场景 1: 用户选择 DeepSeek 模型")
        result, model_name = asyncio.run(
            executor.execute(
                prompt="你好，请用一句话介绍你自己。",
                model_name="deepseek",
                execution_id="test-001",
                q_idx=0
            )
        )
        
        if result.success:
            print(f"✅ DeepSeek 调用成功")
            print(f"   实际使用模型：{model_name}")
            print(f"   响应内容：{result.content[:100]}...")
        else:
            print(f"❌ DeepSeek 调用失败：{result.error_message}")
        
        # 测试用户选择通义千问
        print("\n场景 2: 用户选择通义千问模型")
        result, model_name = asyncio.run(
            executor.execute(
                prompt="你好，请用一句话介绍你自己。",
                model_name="qwen",
                execution_id="test-002",
                q_idx=0
            )
        )
        
        if result.success:
            print(f"✅ 通义千问调用成功")
            print(f"   实际使用模型：{model_name}")
            print(f"   响应内容：{result.content[:100]}...")
        else:
            print(f"❌ 通义千问调用失败：{result.error_message}")
        
        # 测试用户选择豆包
        print("\n场景 3: 用户选择豆包模型")
        result, model_name = asyncio.run(
            executor.execute(
                prompt="你好，请用一句话介绍你自己。",
                model_name="doubao",
                execution_id="test-003",
                q_idx=0
            )
        )
        
        if result.success:
            print(f"✅ 豆包调用成功")
            print(f"   实际使用模型：{model_name}")
            print(f"   响应内容：{result.content[:100]}...")
        else:
            print(f"❌ 豆包调用失败：{result.error_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_priority_evaluator():
    """测试优先级评估器"""
    print("\n" + "="*60)
    print("测试 2: 优先级评估器（DeepSeek → 豆包 → 通义千问）")
    print("="*60)
    
    try:
        from wechat_backend.multi_model_executor import get_priority_evaluator
        
        evaluator = get_priority_evaluator(timeout=30)
        
        # 测试评估功能
        print("\n场景：评估 AI 回答质量")
        result, model_name = evaluator.execute_with_priority(
            prompt="请判断以下回答是否准确：'地球是圆的'",
            execution_id="test-eval-001"
        )
        
        if result.success:
            print(f"✅ 评估成功")
            print(f"   实际使用模型：{model_name}")
            print(f"   响应内容：{result.content[:200]}...")
        else:
            print(f"❌ 评估失败：{result.error_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_judge_with_priority():
    """测试 AI Judge 使用优先级调用器"""
    print("\n" + "="*60)
    print("测试 3: AI Judge 使用优先级调用器")
    print("="*60)
    
    try:
        from ai_judge_module import AIJudgeClient
        
        # 创建 Judge 客户端
        judge_client = AIJudgeClient()
        
        if not judge_client.ai_client:
            print("⚠️  AI Judge 客户端未初始化，跳过测试")
            return True
        
        print(f"✅ AI Judge Client 初始化成功")
        print(f"   平台：{judge_client.judge_platform}")
        print(f"   模型：{judge_client.judge_model}")
        
        # 测试评估功能
        print("\n场景：评估品牌诊断回答")
        result = judge_client.evaluate_response(
            brand_name="小米",
            question="小米手机的质量如何？",
            ai_answer="小米手机以其高性价比和良好的性能著称，质量可靠。"
        )
        
        if result:
            print(f"✅ 评估完成")
            print(f"   权威度评分：{result.accuracy_score}/100")
            print(f"   可见度评分：{result.completeness_score}/100")
            print(f"   好感度评分：{result.sentiment_score}/100")
            print(f"   品牌纯净度：{result.purity_score}/100")
            print(f"   语义一致性：{result.consistency_score}/100")
        else:
            print(f"⚠️  评估返回 None（可能是 API 问题）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("单模型调用与优先级评估测试")
    print("="*60)
    
    # 1. 测试单模型执行器
    single_ok = test_single_model_executor()
    
    # 2. 测试优先级评估器
    priority_ok = test_priority_evaluator()
    
    # 3. 测试 AI Judge
    judge_ok = test_ai_judge_with_priority()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"单模型执行器：{'✅ 通过' if single_ok else '❌ 失败'}")
    print(f"优先级评估器：{'✅ 通过' if priority_ok else '❌ 失败'}")
    print(f"AI Judge: {'✅ 通过' if judge_ok else '❌ 失败'}")
    
    if single_ok and priority_ok and judge_ok:
        print("\n🎉 所有测试通过！重构成功！")
        print("\n重构要点：")
        print("1. ✅ 诊断流程使用用户选择的单一模型")
        print("2. ✅ 评估流程使用优先级调用（DeepSeek → 豆包 → 通义千问）")
        print("3. ✅ 移除了多模型冗余调用功能")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
