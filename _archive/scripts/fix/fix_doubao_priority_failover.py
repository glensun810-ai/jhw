#!/usr/bin/env python3
"""
修复豆包优先级适配器的故障转移逻辑

问题:
1. 健康检查时可能耗尽所有模型配额
2. send_prompt 只在当前模型失败后才切换，但健康检查已经试过了
3. 需要实现真正的"按需切换"：只有当前模型返回 429 时才切换到下一个

修复方案:
1. 移除健康检查中的模型尝试逻辑
2. send_prompt 方法中检测到 429 错误时自动切换到下一个模型
3. 记录每个模型的 429 错误，避免重复尝试已耗尽的模型
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_priority_adapter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================================
# 修复 1: 添加 429 错误模型记录
# ============================================================================

# 在 __init__ 方法中添加 429 错误记录
old_init = '''        # 当前选中的模型和适配器
        self.selected_model: Optional[str] = None
        self.selected_adapter: Optional[DoubaoAdapter] = None'''

new_init = '''        # 当前选中的模型和适配器
        self.selected_model: Optional[str] = None
        self.selected_adapter: Optional[DoubaoAdapter] = None
        
        # 【P0 修复】记录 429 错误的模型（配额耗尽）
        self.exhausted_models: set = set()'''

content = content.replace(old_init, new_init)

# ============================================================================
# 修复 2: 修改 _init_adapter 不进行健康检查，只选择第一个未耗尽的模型
# ============================================================================

old_init_adapter = '''    def _init_adapter(self) -> bool:
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
        return False'''

new_init_adapter = '''    def _init_adapter(self) -> bool:
        """
        初始化适配器（选择第一个未耗尽的模型，不进行健康检查）

        Returns:
            bool: 是否成功初始化
        """
        api_logger.info(f"[DoubaoPriority] 尝试初始化适配器，优先级模型列表：{self.priority_models}")
        api_logger.info(f"[DoubaoPriority] 已耗尽模型：{self.exhausted_models}")

        for i, model_id in enumerate(self.priority_models):
            # 【P0 修复】跳过已耗尽的模型
            if model_id in self.exhausted_models:
                api_logger.info(f"[DoubaoPriority] ⏭️  跳过已耗尽模型 {i+1}/{len(self.priority_models)}: {model_id}")
                continue
            
            try:
                api_logger.info(f"[DoubaoPriority] 尝试模型 {i+1}/{len(self.priority_models)}: {model_id}")

                # 创建适配器实例（不执行健康检查，避免消耗配额）
                adapter = DoubaoAdapter(
                    api_key=self.api_key,
                    model_name=model_id,
                    base_url=self.base_url
                )

                # 成功，保存适配器和模型
                self.selected_adapter = adapter
                self.selected_model = model_id

                api_logger.info(f"[DoubaoPriority] ✅ 模型 {model_id} 可用，已选中")
                return True

            except Exception as e:
                api_logger.warning(f"[DoubaoPriority] ❌ 模型 {model_id} 初始化失败：{str(e)}")
                # 继续尝试下一个模型
                continue

        # 所有模型都不可用
        api_logger.error(f"[DoubaoPriority] ❌ 所有 {len(self.priority_models)} 个模型都不可用或已耗尽")
        return False'''

content = content.replace(old_init_adapter, new_init_adapter)

# ============================================================================
# 修复 3: 修改 _retry_with_next_model 只切换一次，不循环尝试
# ============================================================================

old_retry = '''    def _retry_with_next_model(self, failed_model: str) -> bool:
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

        return False'''

new_retry = '''    def _retry_with_next_model(self, failed_model: str, is_429_error: bool = False) -> bool:
        """
        当当前模型失败时，尝试下一个优先级的模型

        Args:
            failed_model: 失败的模型 ID
            is_429_error: 是否是 429 配额耗尽错误

        Returns:
            bool: 是否成功切换到新模型
        """
        if failed_model not in self.priority_models:
            return False

        # 【P0 修复】如果是 429 错误，标记为已耗尽
        if is_429_error:
            self.exhausted_models.add(failed_model)
            api_logger.warning(f"[DoubaoPriority] 🔒 模型 {failed_model} 配额耗尽，已锁定")

        # 获取失败模型的索引
        failed_index = self.priority_models.index(failed_model)

        # 【P0 修复】只尝试下一个模型，不循环尝试所有
        for i in range(failed_index + 1, min(failed_index + 2, len(self.priority_models))):
            next_model = self.priority_models[i]
            
            # 【P0 修复】跳过已耗尽的模型
            if next_model in self.exhausted_models:
                api_logger.info(f"[DoubaoPriority] ⏭️  跳过已耗尽模型：{next_model}")
                continue

            try:
                api_logger.info(f"[DoubaoPriority] 切换到下一个优先级模型：{next_model}")

                # 创建新适配器（不执行健康检查）
                adapter = DoubaoAdapter(
                    api_key=self.api_key,
                    model_name=next_model,
                    base_url=self.base_url
                )

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
                # 【P0 修复】如果切换失败且是 429 错误，也标记为已耗尽
                if is_429_error:
                    self.exhausted_models.add(next_model)
                continue

        return False'''

content = content.replace(old_retry, new_retry)

# ============================================================================
# 修复 4: 修改 send_prompt 方法，检测 429 错误时切换模型
# ============================================================================

old_send_prompt = '''    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
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
            )'''

new_send_prompt = '''    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示词，支持自动故障转移和 429 配额耗尽处理

        Args:
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            AIResponse: AI 响应
        """
        if not self.selected_adapter:
            # 【P0 修复】尝试重新初始化
            api_logger.warning("[DoubaoPriority] 未找到可用模型，尝试重新初始化")
            if not self._init_adapter():
                return AIResponse(
                    success=False,
                    error_message="未找到可用的豆包模型",
                    error_type=AIErrorType.SERVICE_UNAVAILABLE
                )

        max_retries = len(self.priority_models)  # 最多尝试所有模型
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                api_logger.info(f"[DoubaoPriority] 使用模型 {self.selected_model} 发送请求 (尝试 {retry_count+1}/{max_retries})")
                
                # 使用当前适配器发送请求
                response = self.selected_adapter.send_prompt(prompt, **kwargs)

                # 如果成功，返回响应
                if response.success:
                    api_logger.info(f"[DoubaoPriority] ✅ 模型 {self.selected_model} 调用成功")
                    return response

                # 【P0 修复】检查是否是 429 配额耗尽错误
                is_429 = False
                if response.error_message and ('429' in str(response.error_message) or 'SetLimitExceeded' in str(response.error_message)):
                    is_429 = True
                    api_logger.warning(f"[DoubaoPriority] 🔥 模型 {self.selected_model} 配额耗尽 (429)")

                # 如果失败且错误类型是服务不可用或 429，尝试切换模型
                if is_429 or response.error_type in [AIErrorType.SERVICE_UNAVAILABLE, AIErrorType.SERVER_ERROR]:
                    api_logger.warning(f"[DoubaoPriority] 模型 {self.selected_model} 调用失败，尝试切换模型")

                    if self._retry_with_next_model(self.selected_model, is_429_error=is_429):
                        # 切换成功，使用新模型重试
                        api_logger.info(f"[DoubaoPriority] 切换成功，使用新模型 {self.selected_model} 重试")
                        retry_count += 1
                        continue
                    else:
                        api_logger.error(f"[DoubaoPriority] ❌ 无更多可用模型")
                        break

                # 其他错误，直接返回失败响应
                api_logger.warning(f"[DoubaoPriority] ⚠️  模型 {self.selected_model} 调用失败：{response.error_message}")
                return response

            except Exception as e:
                error_str = str(e)
                # 【P0 修复】检查是否是 429 配额耗尽错误
                is_429 = '429' in error_str or 'SetLimitExceeded' in error_str
                
                api_logger.error(f"[DoubaoPriority] 发送请求异常：{error_str}")

                # 尝试切换模型
                if self._retry_with_next_model(self.selected_model, is_429_error=is_429):
                    # 切换成功，使用新模型重试
                    api_logger.info(f"[DoubaoPriority] 切换成功，使用新模型 {self.selected_model} 重试")
                    retry_count += 1
                    continue
                else:
                    api_logger.error(f"[DoubaoPriority] ❌ 无更多可用模型")
                    break
        
        # 所有尝试都失败
        return AIResponse(
            success=False,
            error_message=f"所有 {len(self.priority_models)} 个豆包模型都调用失败",
            error_type=AIErrorType.SERVICE_UNAVAILABLE,
            model=self.selected_model,
            platform='doubao'
        )'''

content = content.replace(old_send_prompt, new_send_prompt)

# 写入文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 豆包优先级适配器修复完成！")
print("\n修复内容:")
print("1. ✅ 添加 exhausted_models 记录 429 错误的模型")
print("2. ✅ _init_adapter 不进行健康检查，避免消耗配额")
print("3. ✅ _retry_with_next_model 只切换下一个模型，不循环尝试")
print("4. ✅ send_prompt 检测 429 错误时自动切换模型")
print("5. ✅ 支持重试所有可用模型，直到成功或全部耗尽")
print("\n工作流程:")
print("1. 初始化时选择第一个未耗尽的模型")
print("2. 调用时如果返回 429，标记为已耗尽，切换到下一个")
print("3. 继续调用，直到成功或所有模型都耗尽")
print("\n下一步:")
print("1. 重启后端服务")
print("2. 测试诊断功能")
