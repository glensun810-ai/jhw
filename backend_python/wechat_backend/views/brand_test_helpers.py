"""
品牌诊断测试辅助函数

将 perform_brand_test 函数拆分为多个小的、可测试的子函数

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from wechat_backend.logging_config import api_logger
from wechat_backend.security.input_validation import validate_safe_text
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import validate_model_region_consistency
from wechat_backend.config_manager import config_manager
from wechat_backend.v2.services.timeout_service import TimeoutManager


class BrandTestValidator:
    """品牌测试输入验证器"""
    
    @staticmethod
    def validate_brand_list(data: Dict[str, Any]) -> Tuple[List[str], str]:
        """
        验证品牌列表
        
        Args:
            data: 请求数据
            
        Returns:
            (brand_list, error_message)
        """
        if 'brand_list' not in data:
            return None, 'Missing brand_list in request data'
            
        if not isinstance(data['brand_list'], list):
            return None, f'brand_list must be a list, got {type(data["brand_list"]).__name__}'
            
        brand_list = data['brand_list']
        if not brand_list:
            return None, 'brand_list cannot be empty'
            
        for brand in brand_list:
            if not isinstance(brand, str):
                return None, f'Each brand must be a string, got {type(brand).__name__}'
            if not validate_safe_text(brand, max_length=100):
                return None, f'Invalid brand name: {brand}'
                
        return brand_list, None
    
    @staticmethod
    def validate_selected_models(data: Dict[str, Any]) -> Tuple[List[Dict], str]:
        """
        验证并解析选择的模型列表
        
        Args:
            data: 请求数据
            
        Returns:
            (parsed_models, error_message)
        """
        if 'selectedModels' not in data:
            return None, 'Missing selectedModels in request data'
            
        if not isinstance(data['selectedModels'], list):
            return None, f'selectedModels must be a list, got {type(data["selectedModels"]).__name__}'
            
        selected_models = data['selectedModels']
        if not selected_models:
            return None, 'At least one AI model must be selected'
            
        # 解析模型列表（支持字典和字符串格式）
        parsed_models = []
        for model in selected_models:
            if isinstance(model, dict):
                model_name = (
                    model.get('name') or 
                    model.get('id') or 
                    model.get('value') or 
                    model.get('label')
                )
                if model_name:
                    parsed_models.append({
                        'name': model_name,
                        'checked': model.get('checked', True)
                    })
            elif isinstance(model, str):
                parsed_models.append({
                    'name': model,
                    'checked': True
                })
                
        if not parsed_models:
            return None, 'No valid AI models found after parsing'
            
        return parsed_models, None
    
    @staticmethod
    def validate_custom_questions(data: Dict[str, Any]) -> Tuple[List[str], str]:
        """
        验证并解析自定义问题
        
        Args:
            data: 请求数据
            
        Returns:
            (questions, error_message)
        """
        custom_questions = []
        
        if 'custom_question' in data:
            # 处理字符串格式（新格式）
            if not isinstance(data['custom_question'], str):
                return None, f'custom_question must be a string, got {type(data["custom_question"]).__name__}'
                
            question_text = data['custom_question'].strip()
            if question_text:
                # 智能分割多个问题
                raw_questions = re.split(r'[？?.\n\s]+', question_text)
                custom_questions = [
                    q.strip() + ('?' if not q.strip().endswith('?') else '')
                    for q in raw_questions if q.strip()
                ]
                
        elif 'customQuestions' in data:
            # 处理数组格式（旧格式）
            if not isinstance(data['customQuestions'], list):
                return None, f'customQuestions must be a list, got {type(data["customQuestions"]).__name__}'
            custom_questions = data['customQuestions']
            
        # 验证问题安全性
        for question in custom_questions:
            if not validate_safe_text(question, max_length=500):
                return None, f'Unsafe question content: {question}'
                
        return custom_questions, None
    
    @staticmethod
    def validate_models_config(selected_models: List[Dict]) -> Tuple[bool, str]:
        """
        验证模型配置（API Key 和注册状态）
        
        Args:
            selected_models: 解析后的模型列表
            
        Returns:
            (is_valid, error_message)
        """
        for model in selected_models:
            model_name = model['name']
            normalized_name = AIAdapterFactory.get_normalized_model_name(model_name)
            
            # 检查平台可用性
            if not AIAdapterFactory.is_platform_available(normalized_name):
                registered_models = [pt.value for pt in AIAdapterFactory._adapters.keys()]
                return False, (
                    f'Model {model_name} not registered or configured. '
                    f'Available: {registered_models}'
                )
                
            # 检查 API Key
            api_key = config_manager.get_api_key(normalized_name)
            if not api_key:
                return False, f'Model {model_name} not configured - missing API key'
                
        # 验证区域一致性
        model_names = [model['name'] for model in selected_models]
        normalized_names = [
            AIAdapterFactory.get_normalized_model_name(name) 
            for name in model_names
        ]
        
        is_valid, error_msg = validate_model_region_consistency(normalized_names)
        if not is_valid:
            return False, error_msg
            
        return True, None


class BrandTestInitializer:
    """品牌测试初始化器"""
    
    @staticmethod
    def generate_execution_id() -> str:
        """生成执行 ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def initialize_execution_store(
        execution_id: str,
        main_brand: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        初始化执行存储
        
        Args:
            execution_id: 执行 ID
            main_brand: 主品牌
            user_id: 用户 ID
            
        Returns:
            execution_store 初始状态
        """
        return {
            execution_id: {
                'progress': 0,
                'completed': 0,
                'total': 0,
                'status': 'initializing',
                'stage': 'init',
                'results': [],
                'start_time': datetime.now().isoformat(),
                'main_brand': main_brand,
                'user_id': user_id
            }
        }
    
    @staticmethod
    def create_initial_report_record(
        execution_id: str,
        user_id: str,
        main_brand: str,
        competitor_brands: List[str],
        selected_models: List[Dict],
        custom_questions: List[str]
    ) -> Optional[int]:
        """
        创建初始数据库记录
        
        Args:
            execution_id: 执行 ID
            user_id: 用户 ID
            main_brand: 主品牌
            competitor_brands: 竞品品牌列表
            selected_models: 模型列表
            custom_questions: 自定义问题列表
            
        Returns:
            report_id 或 None
        """
        try:
            from wechat_backend.diagnosis_report_service import get_report_service
            
            service = get_report_service()
            config = {
                'brand_name': main_brand,
                'competitor_brands': competitor_brands,
                'selected_models': selected_models,
                'custom_questions': custom_questions
            }
            
            report_id = service.create_report(execution_id, user_id, config)
            
            # 更新初始状态
            service._repo.update_status(
                execution_id=execution_id,
                status='initializing',
                progress=0,
                stage='init',
                is_completed=False
            )
            
            api_logger.info(
                f"[P0 修复] ✅ 初始数据库记录已创建：{execution_id}, report_id={report_id}"
            )
            
            return report_id
            
        except Exception as e:
            api_logger.error(f"[P0 修复] ⚠️ 创建初始记录失败：{e}")
            return None
    
    @staticmethod
    def setup_timeout_handler(
        execution_id: str,
        execution_store: Dict[str, Any],
        user_id: str,
        main_brand: str,
        competitor_brands: List[str],
        selected_models: List[Dict],
        custom_questions: List[str]
    ) -> TimeoutManager:
        """
        设置超时处理器
        
        Args:
            execution_id: 执行 ID
            execution_store: 执行存储
            user_id: 用户 ID
            main_brand: 主品牌
            competitor_brands: 竞品品牌列表
            selected_models: 模型列表
            custom_questions: 自定义问题列表
            
        Returns:
            TimeoutManager 实例
        """
        timeout_manager = TimeoutManager()
        
        def on_timeout(eid: str):
            """超时回调"""
            api_logger.error(
                "global_timeout_triggered",
                extra={
                    'event': 'global_timeout_triggered',
                    'execution_id': eid,
                    'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
                }
            )
            
            # 更新内存状态
            if eid in execution_store:
                execution_store[eid].update({
                    'status': 'timeout',
                    'stage': 'timeout',
                    'progress': 100,
                    'is_completed': True,
                    'should_stop_polling': True,
                    'error': f'诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）'
                })
            
            # 更新数据库状态
            try:
                from wechat_backend.state_manager import get_state_manager
                state_manager = get_state_manager(execution_store)
                state_manager.update_state(
                    execution_id=eid,
                    status='timeout',
                    stage='timeout',
                    progress=100,
                    is_completed=True,
                    error_message=f'诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）',
                    write_to_db=True,
                    user_id=user_id,
                    brand_name=main_brand,
                    competitor_brands=competitor_brands,
                    selected_models=selected_models,
                    custom_questions=custom_questions
                )
            except Exception as timeout_err:
                api_logger.error(f"[超时处理] 数据库状态更新失败：{timeout_err}")
        
        # 启动超时计时器
        timeout_manager.start_timer(
            execution_id=execution_id,
            on_timeout=on_timeout,
            timeout_seconds=TimeoutManager.MAX_EXECUTION_TIME
        )
        
        api_logger.info(
            "global_timeout_timer_started",
            extra={
                'event': 'global_timeout_timer_started',
                'execution_id': execution_id,
                'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
            }
        )
        
        return timeout_manager
