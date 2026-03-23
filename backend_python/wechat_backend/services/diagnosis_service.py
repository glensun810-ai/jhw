"""
诊断业务服务

功能：
- 品牌诊断执行
- 诊断进度管理
- 诊断结果处理
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.nxm_execution_engine import execute_nxm_test
from wechat_backend.question_system import QuestionManager


class DiagnosisService:
    """
    诊断业务服务类
    
    功能：
    - 品牌诊断执行
    - 诊断进度管理
    - 诊断结果处理
    """
    
    @staticmethod
    async def start_diagnosis(
        brand_list: List[str],
        selected_models: List[Dict[str, Any]],
        custom_questions: List[str],
        user_id: str,
        user_level: str
    ) -> Dict[str, Any]:
        """
        启动品牌诊断

        参数：
        - brand_list: 品牌列表
        - selected_models: 选中的 AI 模型列表
        - custom_questions: 自定义问题列表
        - user_id: 用户 ID
        - user_level: 用户等级

        返回：
        - execution_id: 执行 ID
        - status: 状态
        - message: 消息
        
        【P0 修复 - 2026-03-20】增强验证，确保诊断结果数量充足
        """
        try:
            # 生成执行 ID
            execution_id = str(uuid.uuid4())

            # 验证输入
            if not brand_list or len(brand_list) == 0:
                return {
                    'success': False,
                    'error': '品牌列表不能为空'
                }

            # 【P0 修复 - 2026-03-20】验证最少模型数
            if not selected_models or len(selected_models) == 0:
                return {
                    'success': False,
                    'error': '至少选择一个 AI 模型'
                }
            
            if len(selected_models) < 2:
                return {
                    'success': False,
                    'error': '建议选择至少 2 个 AI 模型，获得更全面的分析结果（当前已默认勾选 4 个主流模型）'
                }

            # 【P0 修复 - 2026-03-20】验证最少问题数
            questions = custom_questions or []
            if len(questions) < 2:
                return {
                    'success': False,
                    'error': '建议输入至少 2 个问题，获得更丰富的分析结果（当前已默认填充 3 个标准问题）'
                }
            
            # 提取主品牌和竞品
            main_brand = brand_list[0]
            competitor_brands = brand_list[1:] if len(brand_list) > 1 else []
            
            api_logger.info(f'[DiagnosisService] 启动诊断：{main_brand}, 模型数：{len(selected_models)}, 问题数：{len(questions)}')
            
            # 执行 NxM 测试
            result = execute_nxm_test(
                execution_id=execution_id,
                main_brand=main_brand,
                competitor_brands=competitor_brands,
                selected_models=selected_models,
                raw_questions=questions,
                user_id=user_id or 'anonymous',
                user_level=user_level or 'Free',
                execution_store={}
            )
            
            return {
                'success': True,
                'execution_id': execution_id,
                'formula': result.get('formula', ''),
                'total_tasks': result.get('total_tasks', 0)
            }
            
        except Exception as e:
            api_logger.error(f'[DiagnosisService] 启动诊断失败：{e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_diagnosis_status(execution_id: str, execution_store: Dict) -> Dict[str, Any]:
        """
        获取诊断状态
        
        参数：
        - execution_id: 执行 ID
        - execution_store: 执行状态存储
        
        返回：
        - status: 状态
        - progress: 进度
        - stage: 阶段
        """
        if execution_id not in execution_store:
            return {
                'status': 'not_found',
                'error': '执行 ID 不存在'
            }
        
        store = execution_store[execution_id]
        
        return {
            'status': store.get('status', 'unknown'),
            'progress': store.get('progress', 0),
            'stage': store.get('stage', 'init'),
            'completed': store.get('completed', 0),
            'total': store.get('total', 0),
            'results': store.get('results', []),
            'start_time': store.get('start_time', ''),
            'error': store.get('error')
        }
    
    @staticmethod
    def get_diagnosis_result(execution_id: str, execution_store: Dict) -> Optional[Dict[str, Any]]:
        """
        获取诊断结果
        
        参数：
        - execution_id: 执行 ID
        - execution_store: 执行状态存储
        
        返回：
        - result: 诊断结果
        """
        if execution_id not in execution_store:
            return None
        
        store = execution_store[execution_id]
        
        if store.get('status') != 'completed':
            return None
        
        return {
            'execution_id': execution_id,
            'results': store.get('results', []),
            'completed_at': store.get('end_time', '')
        }
    
    @staticmethod
    def validate_brand_list(brand_list: List[str]) -> Dict[str, Any]:
        """
        验证品牌列表
        
        参数：
        - brand_list: 品牌列表
        
        返回：
        - valid: 是否有效
        - error: 错误信息
        """
        if not brand_list:
            return {'valid': False, 'error': '品牌列表不能为空'}
        
        if not isinstance(brand_list, list):
            return {'valid': False, 'error': '品牌列表必须是数组'}
        
        if len(brand_list) == 0:
            return {'valid': False, 'error': '品牌列表不能为空'}
        
        for brand in brand_list:
            if not isinstance(brand, str):
                return {'valid': False, 'error': f'品牌必须是字符串：{brand}'}
            if len(brand) == 0 or len(brand) > 100:
                return {'valid': False, 'error': f'品牌名称长度必须在 1-100 字符：{brand}'}
        
        return {'valid': True, 'error': None}
    
    @staticmethod
    def validate_models(selected_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证 AI 模型列表
        
        参数：
        - selected_models: 模型列表
        
        返回：
        - valid: 是否有效
        - error: 错误信息
        """
        if not selected_models:
            return {'valid': False, 'error': '模型列表不能为空'}
        
        if not isinstance(selected_models, list):
            return {'valid': False, 'error': '模型列表必须是数组'}
        
        if len(selected_models) == 0:
            return {'valid': False, 'error': '至少选择一个 AI 模型'}
        
        return {'valid': True, 'error': None}


# 导出服务实例
diagnosis_service = DiagnosisService()
