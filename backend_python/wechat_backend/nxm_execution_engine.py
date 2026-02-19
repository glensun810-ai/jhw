"""
NxM Test Execution Engine

This module implements the NxM matrix execution strategy:
- Outer loop: iterates through questions
- Inner loop: iterates through models

品牌说明：
- main_brand: 用户自己的品牌（需要测试的品牌）
- competitor_brands: 竞品品牌列表（仅用于对比分析，不参与 API 请求）

每个执行包括 GEO analysis with self-audit instructions.
"""
import time
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime

from .ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE, parse_geo_json
from .ai_adapters.factory import AIAdapterFactory
from .config_manager import config_manager
from .logging_config import api_logger
from .database import save_test_record


def execute_nxm_test(
    execution_id: str,
    main_brand: str,              # 用户自己的品牌（主品牌）
    competitor_brands: List[str],  # 竞品品牌列表（仅用于对比分析）
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str = "anonymous",
    user_level: str = "Free",
    execution_store: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    重构后的 NxM 执行逻辑
    外层循环遍历问题，内层循环遍历模型
    
    请求次数 = 问题数 × 模型数（只针对用户自己的品牌）
    
    Args:
        execution_id: 执行 ID
        main_brand: 用户自己的品牌（主品牌）
        competitor_brands: 竞品品牌列表（仅用于对比分析，不参与 API 请求）
        selected_models: 选定的模型列表
        raw_questions: 问题列表
        user_id: 用户 ID
        user_level: 用户等级
        execution_store: 执行状态存储
        
    Returns:
        包含所有测试结果的字典
    """
    try:
        # 准备结果存储
        all_results = []
        total_executions = 0
        
        # 更新状态为 AI 获取阶段
        if execution_store:
            execution_store[execution_id].update({
                'status': 'ai_fetching',
                'stage': 'ai_fetching',
                'progress': 10,
                'total': 0,
                'results': []
            })

        api_logger.info(
            f"Starting NxM async brand test '{execution_id}' for main brand: {main_brand}, "
            f"competitors: {competitor_brands}, (User: {user_id}, Level: {user_level})"
        )

        # NxM 循环：外层遍历问题，内层遍历模型
        # 注意：只针对用户自己的品牌进行请求，竞品品牌不参与循环
        for q_idx, base_question in enumerate(raw_questions):
            # 替换问题中的品牌占位符为用户自己的品牌
            question_text = base_question.replace('{brandName}', main_brand)
            
            # 替换竞品占位符
            if competitor_brands:
                question_text = question_text.replace('{competitorBrand}', competitor_brands[0])
            else:
                question_text = question_text.replace('{competitorBrand}', '')
            
            # 遍历选定的每个模型
            for model_idx, model_info in enumerate(selected_models):
                model_name = model_info['name'] if isinstance(model_info, dict) else model_info
                total_executions += 1
                
                # 更新总数
                if execution_store and execution_id in execution_store:
                    execution_store[execution_id]['total'] = total_executions
                
                debug_log_msg = f"Executing [Q:{q_idx+1}] [MainBrand:{main_brand}] on [Model:{model_name}]"
                api_logger.info(debug_log_msg)
                
                result_item = {
                    "question_id": q_idx,
                    "question_text": question_text,
                    "main_brand": main_brand,
                    "competitor_brands": competitor_brands,
                    "model": model_name,
                    "content": "",
                    "geo_data": None,
                    "status": "pending",
                    "error": None
                }
                
                try:
                    # 1. 获取 AI 客户端
                    normalized_model_name = AIAdapterFactory.get_normalized_model_name(model_name)
                    
                    # 检查平台是否可用
                    if not AIAdapterFactory.is_platform_available(normalized_model_name):
                        raise ValueError(
                            f"Model {model_name} (normalized to {normalized_model_name}) "
                            "not registered or not configured"
                        )
                    
                    # 获取 API Key
                    api_key_value = config_manager.get_api_key(normalized_model_name)
                    if not api_key_value:
                        raise ValueError(f"API key not configured for model {model_name}")
                    
                    # 获取实际模型 ID
                    model_id = config_manager.get_platform_model(normalized_model_name) or normalized_model_name
                    
                    # 创建 AI 客户端
                    adapter = AIAdapterFactory.create(normalized_model_name, api_key_value, model_id)
                    
                    # 2. 构建带有 GEO 分析要求的 Prompt
                    # 竞品品牌用于 Prompt 中的对比分析
                    competitors_str = ", ".join(competitor_brands) if competitor_brands else "无"
                    geo_prompt = GEO_PROMPT_TEMPLATE.format(
                        brand_name=main_brand,
                        competitors=competitors_str,
                        question=question_text
                    )
                    
                    # 3. 调用适配器获取回答
                    start_time = time.time()
                    ai_response = adapter.send_prompt(
                        geo_prompt,
                        brand_name=main_brand,
                        competitors=competitor_brands,
                        execution_id=execution_id,
                        question_index=q_idx + 1,
                        total_questions=len(raw_questions) * len(selected_models)
                    )
                    latency = time.time() - start_time
                    
                    # 4. 归因解析 (Attribution Parsing) - 从文本中提取 JSON 块
                    if ai_response.success:
                        response_text = ai_response.content or ""

                        # 记录 AI 响应的前 200 个字符用于调试
                        api_logger.info(
                            f"AI Response preview [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}]: "
                            f"{response_text[:200]}..."
                        )

                        # 先解析 GEO 分析结果
                        analysis = parse_geo_json(response_text)

                        # 记录解析结果
                        api_logger.info(
                            f"GEO Analysis Result [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}]: "
                            f"rank={analysis.get('rank', -1)}, "
                            f"sentiment={analysis.get('sentiment', 0)}, "
                            f"brand_mentioned={analysis.get('brand_mentioned', False)}, "
                            f"sources_count={len(analysis.get('cited_sources', []))}"
                        )

                        # 记录到 ai_responses.jsonl 文件
                        try:
                            from utils.ai_response_logger_v2 import log_ai_response
                            log_ai_response(
                                question=geo_prompt,
                                response=response_text,
                                platform=normalized_model_name,
                                model=model_id,
                                brand=main_brand,
                                competitor=", ".join(competitor_brands) if competitor_brands else None,
                                industry="家居定制",
                                question_category="品牌搜索",
                                latency_ms=int(latency * 1000),
                                tokens_used=getattr(ai_response, 'tokens_used', 0),
                                success=True,
                                execution_id=execution_id,
                                question_index=q_idx + 1,
                                total_questions=len(raw_questions) * len(selected_models),
                                metadata={
                                    "source": "nxm_execution_engine",
                                    "geo_analysis": analysis
                                }
                            )
                            api_logger.info(f"[AIResponseLogger] Task [Q:{q_idx+1}] [Model:{model_name}] logged successfully")
                        except Exception as log_error:
                            api_logger.warning(f"[AIResponseLogger] Failed to log: {log_error}")

                        # 5. 构造结构化结果
                        result_item.update({
                            "content": response_text,
                            "geo_data": analysis,  # 包含 rank, sentiment, sources
                            "status": "success",
                            "latency": latency,
                            "tokens_used": getattr(ai_response, 'tokens_used', 0),
                            "platform": normalized_model_name
                        })

                        api_logger.info(
                            f"Success: [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}] - "
                            f"GEO: rank={analysis.get('rank', -1)}, sentiment={analysis.get('sentiment', 0)}"
                        )
                    else:
                        result_item.update({
                            "status": "failed",
                            "error": ai_response.error_message or "Unknown AI error",
                            "latency": latency
                        })
                        api_logger.warning(
                            f"AI Error: [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}] - "
                            f"{ai_response.error_message}"
                        )

                        # 记录失败的调用到日志文件
                        try:
                            from utils.ai_response_logger_v2 import log_ai_response
                            log_ai_response(
                                question=geo_prompt,
                                response="",
                                platform=normalized_model_name,
                                model=model_id,
                                brand=main_brand,
                                latency_ms=int(latency * 1000),
                                success=False,
                                error_message=ai_response.error_message,
                                error_type=getattr(ai_response, 'error_type', 'unknown'),
                                execution_id=execution_id,
                                question_index=q_idx + 1,
                                total_questions=len(raw_questions) * len(selected_models),
                                metadata={"source": "nxm_execution_engine", "error_phase": "api_call"}
                            )
                        except Exception as log_error:
                            api_logger.warning(f"[AIResponseLogger] Failed to log error: {log_error}")
                    
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    api_logger.error(
                        f"Error on [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}]: "
                        f"{str(e)}\n{error_traceback}"
                    )
                    result_item.update({
                        "status": "failed",
                        "error": str(e)
                    })
                    
                    # 记录异常调用到日志文件（确保所有平台包括豆包都被记录）
                    try:
                        from utils.ai_response_logger_v2 import log_ai_response
                        log_ai_response(
                            question=geo_prompt,
                            response="",
                            platform=normalized_model_name,
                            model=model_id,
                            brand=main_brand,
                            latency_ms=int((time.time() - start_time) * 1000),
                            success=False,
                            error_message=str(e),
                            error_type="exception",
                            execution_id=execution_id,
                            question_index=q_idx + 1,
                            total_questions=len(raw_questions) * len(selected_models),
                            metadata={"source": "nxm_execution_engine", "error_phase": "adapter_call"}
                        )
                        api_logger.info(f"[AIResponseLogger] Exception logged for [Q:{q_idx+1}] [Model:{model_name}]")
                    except Exception as log_error:
                        api_logger.warning(f"[AIResponseLogger] Failed to log exception: {log_error}")
                
                # 6. 实时保存结果（防止崩溃丢失）
                all_results.append(result_item)
                
                # 更新进度
                completed_count = len(all_results)
                if execution_store and execution_id in execution_store:
                    execution_store[execution_id].update({
                        'progress': int((completed_count / max(total_executions, 1)) * 100),
                        'completed': completed_count,
                        'results': all_results
                    })

        # 7. 更新任务最终状态
        api_logger.info(
            f"NxM test execution completed for '{execution_id}'. "
            f"Total: {total_executions}, Results: {len(all_results)}, "
            f"Formula: {len(raw_questions)} questions × {len(selected_models)} models = {total_executions}"
        )
        
        if execution_store and execution_id in execution_store:
            execution_store[execution_id].update({
                'status': 'completed',
                'stage': 'completed',
                'progress': 100,
                'results': all_results,
                'total': total_executions,
                'completed': len(all_results)
            })

        # 将结果保存到数据库
        try:
            record_id = save_test_record(
                user_openid=user_id or "anonymous",
                brand_name=main_brand,
                ai_models_used=[m['name'] if isinstance(m, dict) else m for m in selected_models],
                questions_used=raw_questions,
                overall_score=0,
                total_tests=len(all_results),
                results_summary={
                    'execution_id': execution_id,
                    'total_tests': len(all_results),
                    'successful_tests': len([r for r in all_results if r.get('status') == 'success']),
                    'nxm_execution': True,
                    'competitor_brands': competitor_brands,
                    'formula': f"{len(raw_questions)} questions × {len(selected_models)} models = {total_executions}"
                },
                detailed_results=all_results
            )
            api_logger.info(f"Saved test record with ID: {record_id}")
        except Exception as e:
            api_logger.error(f"Error saving test records to database: {e}")
        
        return {
            'success': True,
            'execution_id': execution_id,
            'total_executions': total_executions,
            'results': all_results,
            'formula': f"{len(raw_questions)} questions × {len(selected_models)} models = {total_executions}"
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        api_logger.error(f"NxM test execution failed for execution_id {execution_id}: {e}\nTraceback: {error_traceback}")
        
        if execution_store and execution_id in execution_store:
            execution_store[execution_id].update({
                'status': 'failed',
                'error': f"{str(e)}\nTraceback: {error_traceback}"
            })
        
        return {
            'success': False,
            'execution_id': execution_id,
            'error': str(e),
            'traceback': error_traceback
        }


def verify_nxm_execution(
    execution_store: Dict[str, Any],
    execution_id: str,
    expected_questions: int,
    expected_models: int,
    expected_main_brand: str
) -> Dict[str, Any]:
    """
    验证 NxM 执行是否正确
    
    Args:
        execution_store: 执行状态存储
        execution_id: 执行 ID
        expected_questions: 期望的问题数
        expected_models: 期望的模型数
        expected_main_brand: 期望的主品牌
        
    Returns:
        验证结果字典
    """
    expected_total = expected_questions * expected_models
    
    if execution_id not in execution_store:
        return {
            'valid': False,
            'error': f"Execution ID {execution_id} not found in store"
        }
    
    execution = execution_store[execution_id]
    actual_total = execution.get('total', 0)
    results = execution.get('results', [])
    
    # 检查总执行次数
    if actual_total != expected_total:
        return {
            'valid': False,
            'error': f"Expected {expected_total} executions, got {actual_total}",
            'details': {
                'expected': expected_total,
                'actual': actual_total,
                'formula': f"{expected_questions} questions × {expected_models} models"
            }
        }
    
    # 检查结果数量
    if len(results) != actual_total:
        return {
            'valid': False,
            'error': f"Results count mismatch: expected {actual_total}, got {len(results)}"
        }
    
    # 检查每个结果是否包含 geo_data
    results_with_geo = [r for r in results if r.get('geo_data') is not None]
    geo_data_percentage = (len(results_with_geo) / len(results) * 100) if results else 0
    
    # 检查成功结果是否都有 geo_data
    success_results = [r for r in results if r.get('status') == 'success']
    success_with_geo = [r for r in success_results if r.get('geo_data') is not None]
    
    verification = {
        'valid': True,
        'total_executions': actual_total,
        'total_results': len(results),
        'successful_results': len(success_results),
        'failed_results': len(results) - len(success_results),
        'results_with_geo_data': len(results_with_geo),
        'geo_data_percentage': geo_data_percentage,
        'success_results_with_geo': len(success_with_geo),
        'success_geo_data_percentage': (len(success_with_geo) / len(success_results) * 100) if success_results else 0,
        'nxm_pattern': f"{expected_questions} questions × {expected_models} models = {expected_total}",
        'main_brand': expected_main_brand
    }
    
    return verification
