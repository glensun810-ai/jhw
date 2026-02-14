import requests
import time
from typing import Dict, Any, Optional
from ai_client import AIClient, AIResponse


class DeepSeekAdapter(AIClient):
    """
    DeepSeek AI 平台适配器
    用于将 DeepSeek API 接入 GEO 内容质量验证系统
    支持两种模式：普通对话模式（deepseek-chat）和搜索/推理模式（deepseek-reasoner）
    包含内部 Prompt 约束逻辑，可配置是否启用中文回答及事实性约束
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.deepseek.com/v1",
        enable_chinese_constraint: bool = True  # 新增参数：是否启用中文约束
    ):
        """
        初始化 DeepSeek 适配器

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-chat"
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示搜索/推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_chinese_constraint: 是否启用中文回答约束，默认为 True
        """
        self.api_key = api_key
        self.model_name = model_name
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_chinese_constraint = enable_chinese_constraint  # 存储中文约束开关
    
    def send_prompt(self, prompt: str) -> AIResponse:
        """
        发送提示到 DeepSeek 并返回标准化响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含 DeepSeek 响应的统一数据结构
        """
        # 记录请求开始时间以计算延迟
        start_time = time.time()

        try:
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 如果启用了中文约束，在原始 prompt 基础上添加约束指令
            # 这样做不会影响上层传入的原始 prompt，仅在发送给 AI 时附加约束
            processed_prompt = prompt
            if self.enable_chinese_constraint:
                constraint_instruction = (
                    "请严格按照以下要求作答：\n"
                    "1. 必须使用中文回答\n"
                    "2. 基于事实和公开信息作答\n"
                    "3. 避免在不确定时胡编乱造\n"
                    "4. 输出结构清晰（分点或分段）\n\n"
                )
                processed_prompt = constraint_instruction + prompt

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 根据模式构建不同的请求体
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 搜索/推理模式 (reasoner): 适用于需要深度分析和推理的问题
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": processed_prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # 如果是推理模式，添加额外参数
            if self.mode == "reasoner":
                payload["reasoner"] = "search"  # 启用搜索推理能力
            
            # 发送请求到 DeepSeek API
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30  # 设置请求超时时间为30秒
            )
            
            # 计算请求延迟
            latency = time.time() - start_time
            
            # 检查响应状态码
            if response.status_code != 200:
                error_message = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                return AIResponse(
                    platform="DeepSeek",
                    model=self.model_name,
                    content="",
                    usage={},
                    latency=latency,
                    success=False,
                    error_message=error_message,
                    mode=self.mode  # 添加模式信息
                )
            
            # 解析响应数据
            response_data = response.json()
            
            # 提取所需信息
            content = ""
            usage = {}
            
            # 从响应中提取实际回答文本
            choices = response_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
            
            # 从响应中提取使用情况信息
            usage = response_data.get("usage", {})
            
            # 返回成功的 AIResponse，包含模式信息
            return AIResponse(
                platform="DeepSeek",
                model=response_data.get("model", self.model_name),
                content=content,
                usage=usage,
                latency=latency,
                success=True,
                error_message=None,
                mode=self.mode  # 添加模式信息
            )
            
        except requests.exceptions.Timeout:
            # 处理请求超时异常
            latency = time.time() - start_time
            return AIResponse(
                platform="DeepSeek",
                model=self.model_name,
                content="",
                usage={},
                latency=latency,
                success=False,
                error_message="请求超时",
                mode=self.mode  # 添加模式信息
            )
        
        except requests.exceptions.RequestException as e:
            # 处理其他请求相关异常
            latency = time.time() - start_time
            return AIResponse(
                platform="DeepSeek",
                model=self.model_name,
                content="",
                usage={},
                latency=latency,
                success=False,
                error_message=f"请求异常: {str(e)}",
                mode=self.mode  # 添加模式信息
            )
        
        except ValueError as e:
            # 处理 API Key 验证等值错误
            latency = time.time() - start_time
            return AIResponse(
                platform="DeepSeek",
                model=self.model_name,
                content="",
                usage={},
                latency=latency,
                success=False,
                error_message=str(e),
                mode=self.mode  # 添加模式信息
            )
        
        except Exception as e:
            # 处理其他未预期的异常
            latency = time.time() - start_time
            return AIResponse(
                platform="DeepSeek",
                model=self.model_name,
                content="",
                usage={},
                latency=latency,
                success=False,
                error_message=f"未知错误: {str(e)}",
                mode=self.mode  # 添加模式信息
            )
    
    def health_check(self) -> bool:
        """
        检查 DeepSeek 客户端的健康状态
        通过发送一个简单的测试请求来验证连接
        
        Returns:
            bool: 客户端是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.send_prompt("你好，请回复'正常'。")
            return test_response.success
        except Exception:
            return False