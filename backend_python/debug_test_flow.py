#!/usr/bin/env python3
"""
前端到后端完整流程调试脚本
用于分析微信小程序到后端的完整数据流
"""

import json
import requests
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

def test_frontend_to_backend_flow():
    """测试从前端到后端的完整流程"""
    print("🔍 开始测试前端到后端完整流程...")
    
    # 1. 检查后端服务是否运行
    print("\n1️⃣ 检查后端服务连接...")
    try:
        response = requests.get("http://127.0.0.1:5001/api/test")
        if response.status_code == 200 and response.json().get('status') == 'success':
            print("   ✅ 后端服务连接正常")
        else:
            print("   ❌ 后端服务连接失败")
            return False
    except Exception as e:
        print(f"   ❌ 后端服务连接失败: {e}")
        return False
    
    # 2. 准备前端发送的数据
    print("\n2️⃣ 准备前端发送的测试数据...")
    test_data = {
        "brand_list": ["蔚来汽车", "理想汽车"],  # 主品牌和竞争品牌
        "selectedModels": [
            {"name": "豆包", "checked": True, "logo": "DB", "tags": ["综合", "创意"]}
        ],
        "customQuestions": [
            "介绍一下{brandName}",
            "{brandName}的主要产品是什么？"
        ]
    }
    
    print(f"   📝 品牌列表: {test_data['brand_list']}")
    print(f"   🤖 选择模型: {[model['name'] for model in test_data['selectedModels']]}")
    print(f"   ❓ 自定义问题: {len(test_data['customQuestions'])} 个")
    
    # 3. 发送品牌测试请求
    print("\n3️⃣ 发送品牌测试请求到后端...")
    try:
        response = requests.post(
            "http://127.0.0.1:5001/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'}
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('status') == 'success':
                execution_id = response_data.get('executionId')
                print(f"   ✅ 请求成功，获得执行ID: {execution_id}")
                
                # 4. 轮询测试进度
                print("\n4️⃣ 开始轮询测试进度...")
                import time
                max_polls = 30  # 最多轮询30次
                poll_count = 0
                
                while poll_count < max_polls:
                    progress_response = requests.get(
                        f"http://127.0.0.1:5001/api/test-progress?executionId={execution_id}"
                    )
                    
                    if progress_response.status_code == 200:
                        progress_data = progress_response.json()
                        status = progress_data.get('status', 'unknown')
                        progress = progress_data.get('progress', 0)
                        
                        print(f"   📊 进度: {progress}%, 状态: {status}")
                        
                        if status == 'completed':
                            print("   ✅ 测试完成!")
                            
                            # 5. 检查返回结果
                            print("\n5️⃣ 检查返回结果...")
                            result_keys = ['results', 'competitiveAnalysis', 'overallScore', 'overallGrade']
                            for key in result_keys:
                                if key in progress_data:
                                    if isinstance(progress_data[key], (list, dict)):
                                        print(f"   📊 {key}: {len(progress_data[key]) if isinstance(progress_data[key], (list, dict)) else 'N/A'} 项")
                                    else:
                                        print(f"   📊 {key}: {progress_data[key]}")
                                else:
                                    print(f"   ⚠️  {key}: 缺失")
                            
                            return True
                        elif status == 'failed':
                            print(f"   ❌ 测试失败: {progress_data.get('error', '未知错误')}")
                            return False
                        elif status == 'pending':
                            print("   ⏳ 测试仍在进行中...")
                    else:
                        print(f"   ⚠️  进度查询失败: {progress_response.status_code}")
                    
                    poll_count += 1
                    time.sleep(2)  # 等待2秒再查询
                
                print("   ⏰ 轮询超时")
                return False
            else:
                print(f"   ❌ 请求失败: {response_data}")
                return False
        else:
            print(f"   ❌ HTTP请求失败: {response.status_code}, {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 请求发送失败: {e}")
        return False


def analyze_backend_processing():
    """分析后端处理逻辑"""
    print("\n" + "="*60)
    print("🔧 后端处理逻辑分析")
    print("="*60)
    
    print("""
    后端处理流程分析:
    
    1. API端点: /api/perform-brand-test (POST)
       - 位置: wechat_backend/views.py:perform_brand_test()
       - 功能: 接收前端提交的品牌测试请求
    
    2. 输入验证:
       - 验证 brand_list 是否存在
       - 验证 selectedModels 是否至少有一个选中
       - 验证 customQuestions 格式
    
    3. 测试用例生成:
       - 使用 QuestionManager 验证问题
       - 使用 TestCaseGenerator 生成测试用例
       - 为每个品牌和模型生成测试
    
    4. 异步执行:
       - 使用 TestExecutor 执行测试
       - 在独立线程中运行
       - 实时更新进度到 execution_store
    
    5. 结果处理:
       - 调用 process_and_aggregate_results_with_ai_judge()
       - 使用 AIJudgeClient 评估响应
       - 使用 ScoringEngine 计算分数
       - 生成竞争分析报告
    
    6. 数据存储:
       - 调用 save_test_record() 保存记录
       - 返回最终结果给前端
    """)
    

def check_common_issues():
    """检查常见问题"""
    print("\n" + "="*60)
    print("⚠️  常见问题检查")
    print("="*60)
    
    issues = []
    
    # 1. 检查API密钥配置
    print("\n1️⃣ 检查API密钥配置...")
    api_key = os.getenv('DOUBAO_API_KEY')
    model_id = os.getenv('DOUBAO_MODEL_ID')
    
    if api_key and api_key != 'YOUR_DOUBAO_API_KEY':
        print("   ✅ API密钥已配置")
    else:
        issues.append("API密钥未正确配置")
        print("   ❌ API密钥未配置或使用默认值")
    
    if model_id:
        print("   ✅ 模型ID已配置")
    else:
        issues.append("模型ID未配置")
        print("   ❌ 模型ID未配置")
    
    # 2. 检查适配器注册
    print("\n2️⃣ 检查适配器注册...")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 检查豆包适配器是否注册
        if hasattr(AIPlatformType, 'DOUBAO'):
            print("   ✅ 豆包平台类型已定义")
        else:
            issues.append("豆包平台类型未定义")
            print("   ❌ 豆包平台类型未定义")
            
    except Exception as e:
        issues.append(f"适配器工厂加载失败: {e}")
        print(f"   ❌ 适配器工厂加载失败: {e}")
    
    # 3. 检查配置管理器
    print("\n3️⃣ 检查配置管理器...")
    try:
        from config_manager import Config as PlatformConfigManager
        config_manager = PlatformConfigManager()
        doubao_config = config_manager.get_platform_config('doubao')
        
        if doubao_config and doubao_config.api_key:
            print("   ✅ 豆包配置已加载")
        else:
            issues.append("豆包配置未正确加载")
            print("   ❌ 豆包配置未正确加载")
    except Exception as e:
        issues.append(f"配置管理器加载失败: {e}")
        print(f"   ❌ 配置管理器加载失败: {e}")
    
    # 4. 检查数据库连接
    print("\n4️⃣ 检查数据库连接...")
    try:
        from wechat_backend.database import init_db
        init_db()  # 尝试初始化数据库
        print("   ✅ 数据库连接正常")
    except Exception as e:
        issues.append(f"数据库连接失败: {e}")
        print(f"   ❌ 数据库连接失败: {e}")
    
    print(f"\n📋 检查完成，发现问题: {len(issues)} 个")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    return len(issues) == 0


def main():
    """主函数"""
    print("🚀 微信小程序前端到后端完整流程调试")
    print("="*60)
    
    # 执行流程测试
    flow_success = test_frontend_to_backend_flow()
    
    # 分析后端处理逻辑
    analyze_backend_processing()
    
    # 检查常见问题
    config_ok = check_common_issues()
    
    print("\n" + "="*60)
    print("📊 最终分析结果")
    print("="*60)
    
    print(f"前端到后端流程测试: {'✅ 通过' if flow_success else '❌ 失败'}")
    print(f"配置检查: {'✅ 正常' if config_ok else '❌ 异常'}")
    
    if flow_success and config_ok:
        print("\n🎉 所有检查通过！系统应该正常工作。")
        return True
    else:
        print("\n⚠️  发现问题，需要进一步排查。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)