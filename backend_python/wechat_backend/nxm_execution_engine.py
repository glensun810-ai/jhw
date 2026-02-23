"""
NxM 执行引擎 - 主入口

重构版本：模块化
- 熔断器 → nxm_circuit_breaker.py
- 任务调度 → nxm_scheduler.py
- 结果聚合 → nxm_result_aggregator.py

输入：NxM 执行参数
输出：执行结果
"""

import time
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
# P0 修复：延迟导入 config_manager，避免循环依赖
# from wechat_backend.config_manager import config_manager
from wechat_backend.logging_config import api_logger
from wechat_backend.database import save_test_record

# 导入模块
from wechat_backend.nxm_circuit_breaker import get_circuit_breaker
from wechat_backend.nxm_scheduler import NxMScheduler, create_scheduler
from wechat_backend.nxm_result_aggregator import (
    parse_geo_with_validation,
    verify_completion,
    deduplicate_results,
    aggregate_results_by_brand
)


def execute_nxm_test(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    execution_store: Dict[str, Any],
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    执行 NxM 测试
    
    参数:
    - execution_id: 执行 ID
    - main_brand: 主品牌
    - competitor_brands: 竞品品牌列表
    - selected_models: 选中的 AI 模型列表
    - raw_questions: 原始问题列表
    - user_id: 用户 ID
    - user_level: 用户等级
    - execution_store: 执行状态存储
    - timeout_seconds: 超时时间（秒）
    
    返回:
    - success: 是否成功
    - execution_id: 执行 ID
    - formula: 执行公式描述
    """
    
    # 创建调度器
    scheduler = create_scheduler(execution_id, execution_store)
    
    # 计算总任务数
    total_tasks = len(raw_questions) * len(selected_models)
    scheduler.initialize_execution(total_tasks)
    
    # 启动超时计时器
    def on_timeout():
        scheduler.fail_execution(f"执行超时 ({timeout_seconds}秒)")
    
    scheduler.start_timeout_timer(timeout_seconds, on_timeout)
    
    # 在后台线程中执行
    def run_execution():
        try:
            results = []
            completed = 0
            
            # 外层循环：遍历问题
            for q_idx, question in enumerate(raw_questions):
                # 内层循环：遍历模型
                for model_info in selected_models:
                    model_name = model_info.get('name', '')
                    
                    # 检查模型是否可用（熔断器）
                    if not scheduler.is_model_available(model_name):
                        api_logger.warning(f"[NxM] 模型 {model_name} 已熔断，跳过")
                        completed += 1
                        scheduler.update_progress(completed, total_tasks, 'ai_fetching')
                        continue
                    
                    try:
                        # P0 修复：直接使用 Config 类获取 API Key，避免循环依赖
                        from config import Config

                        # 创建 AI 客户端
                        client = AIAdapterFactory.create(model_name)
                        api_key = Config.get_api_key(model_name)

                        if not api_key:
                            raise ValueError(f"模型 {model_name} API Key 未配置")

                        # 构建提示词
                        prompt = GEO_PROMPT_TEMPLATE.format(
                            brand=main_brand,
                            question=question
                        )

                        # 修复 3: 添加 AI 响应重试机制
                        max_retries = 2
                        retry_count = 0
                        response = None
                        geo_data = None
                        parse_error = None

                        while retry_count <= max_retries:
                            try:
                                # 调用 AI 接口
                                response = client.generate_response(
                                    prompt=prompt,
                                    api_key=api_key
                                )

                                # 解析 GEO 数据
                                geo_data, parse_error = parse_geo_with_validation(
                                    response,
                                    execution_id,
                                    q_idx,
                                    model_name
                                )

                                # 如果解析成功，跳出重试循环
                                if not parse_error and not geo_data.get('_error'):
                                    break

                                # 解析失败，记录日志并准备重试
                                api_logger.warning(f"[NxM] 解析失败，准备重试：{model_name}, Q{q_idx}, 尝试 {retry_count + 1}/{max_retries}")
                                retry_count += 1

                            except Exception as call_error:
                                api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {call_error}")
                                retry_count += 1

                        # 检查最终结果
                        if not response or not geo_data or geo_data.get('_error'):
                            api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                            scheduler.record_model_failure(model_name)
                            # 仍然添加结果，但标记为失败
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }
                            scheduler.add_result(result)
                            results.append(result)
                        else:
                            scheduler.record_model_success(model_name)

                            # 构建结果
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data,
                                'timestamp': datetime.now().isoformat()
                            }

                            scheduler.add_result(result)
                            results.append(result)

                        # 更新进度
                        completed += 1
                        scheduler.update_progress(completed, total_tasks, 'ai_fetching')

                    except Exception as e:
                        api_logger.error(f"[NxM] 执行失败：{model_name}, Q{q_idx}: {e}")
                        scheduler.record_model_failure(model_name)
                        completed += 1
                        scheduler.update_progress(completed, total_tasks, 'ai_fetching')
            
            # 验证执行完成
            verification = verify_completion(results, total_tasks)
            
            if verification['success']:
                # 去重结果
                deduplicated = deduplicate_results(results)
                
                # 完成执行
                scheduler.complete_execution()
                
                # 保存测试记录
                save_test_record(
                    execution_id=execution_id,
                    user_id=user_id,
                    brand_name=main_brand,
                    results=deduplicated,
                    user_level=user_level
                )
                
                api_logger.info(f"[NxM] 执行成功：{execution_id}, 结果数：{len(deduplicated)}")
            else:
                scheduler.fail_execution(verification['message'])
            
        except Exception as e:
            api_logger.error(f"[NxM] 执行异常：{execution_id}: {e}")
            scheduler.fail_execution(str(e))
        finally:
            scheduler.cancel_timeout_timer()
    
    # 启动后台线程
    thread = threading.Thread(target=run_execution)
    thread.daemon = True
    thread.start()
    
    return {
        'success': True,
        'execution_id': execution_id,
        'formula': f'{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求',
        'total_tasks': total_tasks
    }


def verify_nxm_execution(
    execution_id: str,
    execution_store: Dict[str, Any]
) -> Dict[str, Any]:
    """
    验证 NxM 执行结果
    
    参数:
    - execution_id: 执行 ID
    - execution_store: 执行状态存储
    
    返回:
    - verified: 是否验证通过
    - message: 消息
    """
    if execution_id not in execution_store:
        return {
            'verified': False,
            'message': f'执行 ID 不存在：{execution_id}'
        }
    
    store = execution_store[execution_id]
    results = store.get('results', [])
    total = store.get('total', 0)
    
    verification = verify_completion(results, total)
    
    return {
        'verified': verification['success'],
        'message': verification['message'],
        'results_count': len(results),
        'expected_total': total
    }
