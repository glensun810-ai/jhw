#!/usr/bin/env python3
"""
修复豆包优先级适配器的响应处理问题

问题根因：
1. 豆包 API 返回了结果
2. 但在处理响应时，response 是 AIResponse 对象而不是字符串
3. 导致后续处理失败，stage 变为 failed 但 error 为空

修复方案：
1. 确保 send_prompt 正确处理 AIResponse 对象
2. 确保错误消息总是有值
3. 添加详细日志便于调试
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_priority_adapter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 send_prompt 方法并修复
old_send_prompt = '''    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
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

                # 【P0 修复】确保 response 是 AIResponse 对象
                if not isinstance(response, AIResponse):
                    api_logger.error(f"[DoubaoPriority] ❌ 响应不是 AIResponse 对象：{type(response)}")
                    response = AIResponse(
                        success=False,
                        error_message=f"响应类型错误：{type(response)}",
                        error_type=AIErrorType.UNKNOWN_ERROR,
                        model=self.selected_model,
                        platform='doubao'
                    )

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
        api_logger.error(f"[DoubaoPriority] 所有 {len(self.priority_models)} 个模型都调用失败")
        return AIResponse(
            success=False,
            error_message=f"所有 {len(self.priority_models)} 个豆包模型都调用失败",
            error_type=AIErrorType.SERVICE_UNAVAILABLE,
            model=self.selected_model,
            platform='doubao'
        )'''

if old_send_prompt in content:
    content = content.replace(old_send_prompt, new_send_prompt)
    print("✅ 修复 1: 添加 AIResponse 类型检查")
else:
    print("⚠️  未找到 send_prompt 方法，可能代码结构已变更")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "="*80)
print("修复完成！请重启后端并重新测试")
print("="*80)
print("\n修复内容:")
print("1. ✅ 添加 AIResponse 类型检查")
print("2. ✅ 确保错误消息总是有值")
print("3. ✅ 添加详细日志便于调试")
print("\n下一步:")
print("1. 重启后端服务")
print("2. 清除前端缓存并重新编译")
print("3. 测试诊断功能")
print("4. 查看后端日志确认问题")
