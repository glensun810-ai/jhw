#!/usr/bin/env python3
"""
Doubao API Key 配置验证脚本
验证三项功能：
1. AI 调用功能
2. 结果保存功能
3. 后台分析功能
"""

import os
import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_backend'))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入配置和适配器
from src.config import Config
from wechat_backend.ai_adapters.doubao_priority_adapter import DoubaoPriorityAdapter
from wechat_backend.logging_config import api_logger


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_api_key_config():
    """检查 API Key 配置"""
    print_section("1. API Key 配置检查")
    
    # 检查环境变量
    ark_key = os.environ.get('ARK_API_KEY')
    doubao_key = os.environ.get('DOUBAO_API_KEY')
    
    print(f"ARK_API_KEY: {'✅ 已配置' if ark_key else '❌ 未配置'}")
    if ark_key:
        print(f"  值：{ark_key[:8]}...{ark_key[-4:]}")
    
    print(f"DOUBAO_API_KEY: {'✅ 已配置' if doubao_key else '❌ 未配置'}")
    if doubao_key:
        print(f"  值：{doubao_key[:8]}...{doubao_key[-4:]}")
    
    # 检查 Config 类加载
    config_key = Config.get_doubao_api_key()
    print(f"\nConfig.get_doubao_api_key(): {'✅ 成功' if config_key else '❌ 失败'}")
    if config_key:
        print(f"  值：{config_key[:8]}...{config_key[-4:]}")
    
    # 检查模型配置
    print_section("模型配置检查")
    models = Config.get_doubao_models()
    print(f"可用模型数量：{len(models)}")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    
    # 检查优先级模型
    priority_models = Config.get_doubao_priority_models()
    if priority_models:
        print(f"\n优先级模型 ({len(priority_models)} 个):")
        for i, model in enumerate(priority_models, 1):
            print(f"  优先级{i}: {model}")
    
    auto_select = Config.is_doubao_auto_select()
    print(f"\n自动选择模式：{'✅ 启用' if auto_select else '❌ 禁用'}")
    
    # 检查平台配置状态
    is_configured = Config.is_api_key_configured('doubao')
    print(f"\nConfig.is_api_key_configured('doubao'): {'✅ True' if is_configured else '❌ False'}")
    
    return config_key is not None and is_configured


def test_ai_call():
    """测试 AI 调用功能"""
    print_section("2. AI 调用功能测试")
    
    api_key = Config.get_doubao_api_key()
    if not api_key:
        print("❌ API Key 未配置，跳过调用测试")
        return False
    
    try:
        print("正在初始化 DoubaoPriorityAdapter...")
        adapter = DoubaoPriorityAdapter(api_key=api_key)
        
        print(f"✅ 适配器初始化成功")
        print(f"  选中模型：{adapter.selected_model}")
        print(f"  优先级模型列表：{adapter.priority_models}")
        
        # 测试调用
        test_prompt = "请用一句话回答：1+1 等于几？"
        print(f"\n正在发送测试请求：{test_prompt}")
        print("这可能需要 5-30 秒...")
        
        start_time = datetime.now()
        response = adapter.send_prompt(test_prompt)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ 调用成功！耗时：{duration:.2f}秒")
        print(f"响应内容：{response.content[:200] if response.content else 'None'}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 调用失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_result_save():
    """测试结果保存功能"""
    print_section("3. 结果保存功能测试")
    
    # 检查日志配置
    try:
        from wechat_backend.logging_config import api_logger
        print("✅ 日志系统已加载")
        print(f"  日志处理器：{api_logger.handlers}")
        
        # 测试日志记录
        test_msg = f"[测试] 结果保存功能测试 - {datetime.now().isoformat()}"
        api_logger.info(test_msg)
        print(f"✅ 日志记录成功：{test_msg}")
        
        return True
    except Exception as e:
        print(f"❌ 日志系统加载失败：{str(e)}")
        return False


def test_backend_analysis():
    """测试后台分析功能"""
    print_section("4. 后台分析功能测试")
    
    # 检查 Judge 模型配置
    print("检查 Judge 模型配置...")
    judge_platform = os.environ.get('JUDGE_LLM_PLATFORM', 'deepseek')
    judge_model = os.environ.get('JUDGE_LLM_MODEL', 'deepseek-chat')
    judge_key = os.environ.get('JUDGE_LLM_API_KEY')
    
    print(f"Judge 平台：{judge_platform}")
    print(f"Judge 模型：{judge_model}")
    print(f"Judge API Key: {'✅ 已配置' if judge_key else '❌ 未配置'}")
    
    # 检查分析模块
    try:
        from ai_judge_module import AIJudgeClient, JudgePromptBuilder, JudgeResultParser
        print("\n✅ Judge 模块可导入")
        print(f"  可用类：AIJudgeClient, JudgePromptBuilder, JudgeResultParser")
        
        # 尝试初始化（不实际调用）
        print("Judge 模块组件检查...")
        prompt_builder = JudgePromptBuilder()
        result_parser = JudgeResultParser()
        print("✅ Judge 模块基本检查通过")
        
        return True
    except ImportError as e:
        print(f"⚠️  Judge 模块导入失败：{str(e)}")
        return False
    except Exception as e:
        print(f"⚠️  Judge 模块检查异常：{str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("  Doubao API Key 配置与功能验证报告")
    print(f"  时间：{datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {
        'api_key_config': False,
        'ai_call': False,
        'result_save': False,
        'backend_analysis': False
    }
    
    # 1. 检查 API Key 配置
    results['api_key_config'] = check_api_key_config()
    
    # 2. 测试 AI 调用
    results['ai_call'] = test_ai_call()
    
    # 3. 测试结果保存
    results['result_save'] = test_result_save()
    
    # 4. 测试后台分析
    results['backend_analysis'] = test_backend_analysis()
    
    # 总结
    print_section("验证总结")
    
    items = [
        ("API Key 配置", results['api_key_config']),
        ("AI 调用功能", results['ai_call']),
        ("结果保存功能", results['result_save']),
        ("后台分析功能", results['backend_analysis'])
    ]
    
    for name, passed in items:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    total = sum(1 for _, v in items if v)
    print(f"\n总计：{total}/{len(items)} 项通过")
    
    if total == len(items):
        print("\n🎉 所有功能验证通过！")
    else:
        print("\n⚠️  部分功能验证失败，请检查上述错误信息。")
    
    return total == len(items)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
