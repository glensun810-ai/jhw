"""
豆包 AI 优先级适配器
支持多模型优先级自动选择，按优先级顺序尝试调用，使用第一个成功的模型
"""

import os
import time
from typing import Optional, List, Dict, Any
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType
from wechat_backend.logging_config import api_logger
from wechat_backend.config_manager import ConfigurationManager as PlatformConfigManager
from config import Config


class DoubaoPriorityAdapter(AIClient):
    """
    豆包 AI 优先级适配器
    按优先级顺序尝试多个模型，使用第一个成功的模型
    """
    
    def __init__(self, api_key: str, model_name: str = None, base_url: Optional[str] = None):
        # 保存 API Key
        self.api_key = api_key
        self.base_url = base_url
        
        # 获取优先级模型列表
        self.priority_models = self._get_priority_models()
        
        # 如果传入了 model_name，则添加到优先级列表最前面
        if model_name and model_name not in self.priority_models:
            self.priority_models.insert(0, model_name)
        
        # 如果没有配置任何模型，使用默认值
        if not self.priority_models:
            self.priority_models = ['ep-20260212000000-gd5tq']
        
        # 当前选中的模型和适配器
        self.selected_model: Optional[str] = None
        self.selected_adapter: Optional[DoubaoAdapter] = None
        
        # 尝试初始化适配器（选择第一个可用的模型）
        self._init_adapter()
        
        # 如果成功初始化，调用父类初始化
        if self.selected_adapter:
            super().__init__(AIPlatformType.DOUBAO, self.selected_model, api_key)
            # 复制适配器属性
            self.session = self.selected_adapter.session
            self.latency_history = self.selected_adapter.latency_history
            self.circuit_breaker = self.selected_adapter.circuit_breaker
        else:
            # 如果所有模型都不可用，使用第一个模型创建适配器（可能会失败）
            super().__init__(AIPlatformType.DOUBAO, self.priority_models[0], api_key)
    
    def _get_priority_models(self) -> List[str]:
        """
        获取优先级模型列表
        
        Returns:
            按优先级排序的模型列表
        """
        # 检查是否启用自动选择
        if not Config.is_doubao_auto_select():
            # 如果不启用自动选择，只使用第一个优先级模型
            model_id = os.getenv('DOUBAO_MODEL_PRIORITY_1', '')
            if model_id:
                return [model_id]
            return []
        
        # 收集所有优先级模型配置
        priority_models = []
        
        # 按优先级顺序添加模型（优先级 1-10）
        for i in range(1, 11):
            model_key = f'DOUBAO_MODEL_PRIORITY_{i}'
            model_id = os.getenv(model_key, '')
            if model_id and model_id.strip():
                priority_models.append(model_id.strip())
        
        return priority_models
    
    def _init_adapter(self) -> bool:
        """
        初始化适配器（选择第一个可用的模型）
        
        Returns:
            bool: 是否成功初始化
        """
        api_logger.info(f"[DoubaoPriority] 尝试初始化适配器，优先级模型列表：{self.priority_models}")
        
        for i, model_id in enumerate(self.priority_models):
            try:
                api_logger.info(f"[DoubaoPriority] 尝试模型 {i+1}/{len(self.priority_models)}: {model_id}")
                
                # 创建适配器实例
                adapter = DoubaoAdapter(
                    api_key=self.api_key,
                    model_name=model_id,
                    base_url=self.base_url
                )
                
                # 执行健康检查
                if hasattr(adapter, '_health_check'):
                    adapter._health_check()
                
                # 成功，保存适配器和模型
                self.selected_adapter = adapter
                self.selected_model = model_id
                
                api_logger.info(f"[DoubaoPriority] ✅ 模型 {model_id} 可用，已选中")
                return True
                
            except Exception as e:
                api_logger.warning(f"[DoubaoPriority] ❌ 模型 {model_id} 不可用：{str(e)}")
                # 继续尝试下一个模型
                continue
        
        # 所有模型都不可用
        api_logger.error(f"[DoubaoPriority] ❌ 所有 {len(self.priority_models)} 个模型都不可用")
        return False
    
    def _retry_with_next_model(self, failed_model: str) -> bool:
        """
        当当前模型失败时，尝试下一个优先级的模型
        
        Args:
            failed_model: 失败的模型 ID
            
        Returns:
            bool: 是否成功切换到新模型
        """
        if failed_model not in self.priority_models:
            return False
        
        # 获取失败模型的索引
        failed_index = self.priority_models.index(failed_model)
        
        # 尝试下一个优先级的模型
        for i in range(failed_index + 1, len(self.priority_models)):
            next_model = self.priority_models[i]
            
            try:
                api_logger.info(f"[DoubaoPriority] 切换到下一个优先级模型：{next_model}")
                
                # 创建新适配器
                adapter = DoubaoAdapter(
                    api_key=self.api_key,
                    model_name=next_model,
                    base_url=self.base_url
                )
                
                # 执行健康检查
                if hasattr(adapter, '_health_check'):
                    adapter._health_check()
                
                # 成功，更新适配器和模型
                self.selected_adapter = adapter
                self.selected_model = next_model
                
                # 更新父类属性
                self.model_name = next_model
                self.session = adapter.session
                self.circuit_breaker = adapter.circuit_breaker
                
                api_logger.info(f"[DoubaoPriority] ✅ 成功切换到模型 {next_model}")
                return True
                
            except Exception as e:
                api_logger.warning(f"[DoubaoPriority] ❌ 切换模型 {next_model} 失败：{str(e)}")
                continue
        
        return False
    
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示词，支持自动故障转移
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            AIResponse: AI 响应
        """
        if not self.selected_adapter:
            return AIResponse(
                success=False,
                error_message="未找到可用的豆包模型",
                error_type=AIErrorType.SERVICE_UNAVAILABLE
            )
        
        try:
            # 使用当前适配器发送请求
            response = self.selected_adapter.send_prompt(prompt, **kwargs)
            
            # 如果成功，返回响应
            if response.success:
                return response
            
            # 如果失败且错误类型是服务不可用，尝试切换模型
            if response.error_type in [AIErrorType.SERVICE_UNAVAILABLE, AIErrorType.SERVER_ERROR]:
                api_logger.warning(f"[DoubaoPriority] 模型 {self.selected_model} 调用失败，尝试切换模型")
                
                if self._retry_with_next_model(self.selected_model):
                    # 切换成功，使用新模型重试
                    api_logger.info(f"[DoubaoPriority] 使用新模型 {self.selected_model} 重试")
                    return self.selected_adapter.send_prompt(prompt, **kwargs)
            
            # 返回失败响应
            return response
            
        except Exception as e:
            api_logger.error(f"[DoubaoPriority] 发送请求异常：{str(e)}")
            
            # 尝试切换模型
            if self._retry_with_next_model(self.selected_model):
                # 切换成功，使用新模型重试
                api_logger.info(f"[DoubaoPriority] 使用新模型 {self.selected_model} 重试")
                return self.selected_adapter.send_prompt(prompt, **kwargs)
            
            # 返回错误响应
            return AIResponse(
                success=False,
                error_message=str(e),
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.selected_model,
                platform='doubao'
            )
    
    def get_selected_model(self) -> Optional[str]:
        """
        获取当前选中的模型 ID
        
        Returns:
            模型 ID
        """
        return self.selected_model
    
    def get_priority_models(self) -> List[str]:
        """
        获取优先级模型列表
        
        Returns:
            模型列表
        """
        return self.priority_models
