"""
豆包 AI 优先级适配器
支持多模型优先级自动选择，使用第一个成功的模型

P0-DOUBAO-2 修复：配额耗尽模型缓存
- 使用类级别缓存 exhausted_models_cache 在内存中缓存 429 状态
- 当前执行批次内不再反复尝试已欠费的模型
- 缓存自动过期（10 分钟），避免长期影响
"""

import os
import time
from typing import Optional, List, Dict, Any, Set
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from wechat_backend.logging_config import api_logger
from wechat_backend.config_manager import ConfigurationManager as PlatformConfigManager
from legacy_config import Config


class DoubaoPriorityAdapter(AIClient):
    """
    豆包 AI 优先级适配器
    按优先级顺序尝试多个模型，使用第一个成功的模型
    
    配额耗尽模型缓存机制：
    - exhausted_models_cache: 类级别缓存，存储所有实例共享的配额耗尽模型
    - exhausted_timestamps: 记录每个模型被标记为耗尽的时间戳
    - CACHE_TTL: 缓存过期时间（秒），默认 10 分钟
    """

    # ==================== P0-DOUBAO-2 修复：配额耗尽模型缓存 ====================
    # 类级别缓存，所有实例共享
    exhausted_models_cache: Set[str] = set()  # 配额耗尽的模型集合
    exhausted_timestamps: Dict[str, float] = {}  # 模型耗尽时间戳
    CACHE_TTL: int = 600  # 缓存过期时间（秒），默认 10 分钟
    # =======================================================================
    
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

        # 【P0 修复】记录 429 错误的模型（配额耗尽）- 实例级别（向后兼容）
        self.exhausted_models: set = set()

        # 【P0-DOUBAO-2 修复】清理过期缓存
        self._cleanup_expired_cache()

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
    
    def _cleanup_expired_cache(self):
        """
        清理过期的配额耗尽缓存
        
        移除超过 CACHE_TTL 时间的记录，避免长期影响
        """
        current_time = time.time()
        expired_models = []
        
        for model_id, timestamp in self.exhausted_timestamps.items():
            if current_time - timestamp > self.CACHE_TTL:
                expired_models.append(model_id)
        
        for model_id in expired_models:
            self.exhausted_models_cache.discard(model_id)
            del self.exhausted_timestamps[model_id]
        
        if expired_models:
            api_logger.info(
                f"[DoubaoPriority] 清理过期缓存：{len(expired_models)} 个模型 "
                f"({', '.join(expired_models)})"
            )
    
    def _mark_model_exhausted(self, model_id: str):
        """
        标记模型为配额耗尽
        
        Args:
            model_id: 模型 ID
        """
        self.exhausted_models_cache.add(model_id)
        self.exhausted_timestamps[model_id] = time.time()
        self.exhausted_models.add(model_id)  # 同时更新实例缓存（向后兼容）
        api_logger.warning(
            f"[DoubaoPriority] 🔒 模型 {model_id} 配额耗尽 (429)，已加入缓存 "
            f"(TTL={self.CACHE_TTL}s)"
        )
    
    def _is_model_exhausted(self, model_id: str) -> bool:
        """
        检查模型是否已配额耗尽
        
        Args:
            model_id: 模型 ID
            
        Returns:
            bool: 是否已配额耗尽
        """
        # 先检查是否在缓存中
        if model_id not in self.exhausted_models_cache:
            return False
        
        # 检查是否过期（双重检查，防止清理遗漏）
        if model_id in self.exhausted_timestamps:
            if time.time() - self.exhausted_timestamps[model_id] > self.CACHE_TTL:
                # 已过期，从缓存中移除
                self.exhausted_models_cache.discard(model_id)
                del self.exhausted_timestamps[model_id]
                api_logger.info(f"[DoubaoPriority] 模型 {model_id} 缓存已过期，恢复可用")
                return False
        
        return True
    
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
            # P1-1 修复：跳过已配额用尽的模型（使用类级别缓存）
            if self._is_model_exhausted(model_id):
                api_logger.info(f"[DoubaoPriority] 🔒 跳过配额用尽模型：{model_id} (缓存中)")
                continue

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
                error_str = str(e)
                # P0-DOUBAO-2 修复：检测 429 配额用尽错误，加入缓存
                is_quota_exceeded = (
                    '429' in error_str or
                    'SetLimitExceeded' in error_str or
                    'Too Many Requests' in error_str or
                    'inference limit' in error_str
                )

                if is_quota_exceeded:
                    self._mark_model_exhausted(model_id)
                else:
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

            # P0-DOUBAO-2 修复：跳过已配额用尽的模型（使用类级别缓存）
            if self._is_model_exhausted(next_model):
                api_logger.info(f"[DoubaoPriority] 🔒 跳过配额用尽模型：{next_model} (缓存中)")
                continue

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
                error_str = str(e)
                # 检测 429 配额用尽错误，加入缓存
                is_quota_exceeded = (
                    '429' in error_str or
                    'SetLimitExceeded' in error_str or
                    'Too Many Requests' in error_str or
                    'inference limit' in error_str
                )

                if is_quota_exceeded:
                    self._mark_model_exhausted(next_model)
                else:
                    api_logger.warning(f"[DoubaoPriority] ❌ 切换模型 {next_model} 失败：{str(e)}")
                continue

        return False
    
    @classmethod
    def clear_exhausted_cache(cls):
        """
        清空配额耗尽缓存（用于测试或手动干预）
        
        注意：生产环境慎用，可能导致再次触发 429 错误
        """
        cls.exhausted_models_cache.clear()
        cls.exhausted_timestamps.clear()
        api_logger.info("[DoubaoPriority] 🗑️ 已清空配额耗尽缓存")
    
    @classmethod
    def get_exhausted_cache_info(cls) -> Dict[str, Any]:
        """
        获取缓存信息（用于监控和调试）
        
        Returns:
            包含缓存统计信息的字典
        """
        current_time = time.time()
        expired_count = sum(
            1 for ts in cls.exhausted_timestamps.values()
            if current_time - ts > cls.CACHE_TTL
        )
        
        return {
            'total_cached': len(cls.exhausted_models_cache),
            'expired_count': expired_count,
            'active_count': len(cls.exhausted_models_cache) - expired_count,
            'cache_ttl_seconds': cls.CACHE_TTL,
            'cached_models': list(cls.exhausted_models_cache),
            'timestamps': dict(cls.exhausted_timestamps)
        }
    
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

            # 如果失败且错误类型是可恢复错误（服务不可用、服务器错误、频率限制、配额用尽），尝试切换模型
            # P0-2 修复：添加 INSUFFICIENT_QUOTA 到故障转移触发列表
            if response.error_type in [
                AIErrorType.SERVICE_UNAVAILABLE,
                AIErrorType.SERVER_ERROR,
                AIErrorType.RATE_LIMIT_EXCEEDED,
                AIErrorType.INSUFFICIENT_QUOTA  # 新增：配额用尽时切换
            ]:
                api_logger.warning(f"[DoubaoPriority] 模型 {self.selected_model} 调用失败 ({response.error_type})，尝试切换模型")

                # 记录配额用尽的模型（使用类级别缓存）
                if response.error_type == AIErrorType.INSUFFICIENT_QUOTA:
                    self._mark_model_exhausted(self.selected_model)

                if self._retry_with_next_model(self.selected_model):
                    # 切换成功，使用新模型重试
                    api_logger.info(f"[DoubaoPriority] 使用新模型 {self.selected_model} 重试")
                    return self.selected_adapter.send_prompt(prompt, **kwargs)
                else:
                    api_logger.error(f"[DoubaoPriority] 所有模型都已尝试，无法切换")

            # 返回失败响应
            return response

        except Exception as e:
            api_logger.error(f"[DoubaoPriority] 发送请求异常：{str(e)}")

            # 检查是否是 429 错误（配额用尽）
            error_str = str(e)
            is_quota_exceeded = (
                '429' in error_str or
                'SetLimitExceeded' in error_str or
                'Too Many Requests' in error_str or
                'inference limit' in error_str
            )

            # P0-DOUBAO-2 修复：配额用尽时记录到缓存
            if is_quota_exceeded and self.selected_model:
                self._mark_model_exhausted(self.selected_model)

            # 尝试切换模型（如果是 429 错误或当前模型失败）
            if is_quota_exceeded:
                api_logger.warning(f"[DoubaoPriority] 检测到配额用尽（429），尝试切换模型")
                if self._retry_with_next_model(self.selected_model):
                    # 切换成功，使用新模型重试
                    api_logger.info(f"[DoubaoPriority] 使用新模型 {self.selected_model} 重试")
                    return self.selected_adapter.send_prompt(prompt, **kwargs)
                else:
                    api_logger.error(f"[DoubaoPriority] 所有模型都已尝试，无法切换")

            # 返回错误响应
            return AIResponse(
                success=False,
                error_message=str(e),
                error_type=AIErrorType.RATE_LIMIT_EXCEEDED if is_quota_exceeded else AIErrorType.UNKNOWN_ERROR,
                model=self.selected_model,
                platform='doubao'
            )

    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """
        生成响应（兼容 NXM 执行引擎的调用接口）
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            AIResponse: AI 响应
        """
        # 直接调用 send_prompt 方法
        return self.send_prompt(prompt, **kwargs)

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
