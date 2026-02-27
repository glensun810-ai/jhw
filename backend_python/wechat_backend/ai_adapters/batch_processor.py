"""
AI 请求批量处理模块

功能：
1. 请求合并（Batching）
2. 延迟执行（Debouncing）
3. 并发控制
4. 响应缓存

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, Future

from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIResponse, AIClient


# ==================== 配置常量 ====================

class BatchConfig:
    """批量处理配置"""
    # 最大批量大小
    MAX_BATCH_SIZE = 10
    # 批量等待时间（秒）
    BATCH_WAIT_TIME = 0.5
    # 请求超时时间（秒）
    REQUEST_TIMEOUT = 60
    # 最大并发数
    MAX_CONCURRENT_REQUESTS = 5
    # 缓存有效期（秒）
    CACHE_TTL = 300
    # 缓存最大条目数
    CACHE_MAX_SIZE = 100


# ==================== 请求批处理 ====================

class BatchRequest:
    """批量请求"""
    
    def __init__(
        self,
        prompts: List[str],
        context: List[Dict[str, Any]],
        future: Future
    ):
        self.prompts = prompts
        self.context = context
        self.future = future
        self.created_at = datetime.now()
    
    def __len__(self):
        return len(self.prompts)


class AIBatchProcessor:
    """
    AI 请求批量处理器
    
    将多个独立的 AI 请求合并为批量请求，减少 API 调用次数
    """
    
    def __init__(
        self,
        ai_client: AIClient,
        batch_size: int = BatchConfig.MAX_BATCH_SIZE,
        wait_time: float = BatchConfig.BATCH_WAIT_TIME,
        max_concurrent: int = BatchConfig.MAX_CONCURRENT_REQUESTS
    ):
        """
        初始化批量处理器
        
        Args:
            ai_client: AI 客户端实例
            batch_size: 最大批量大小
            wait_time: 批量等待时间
            max_concurrent: 最大并发数
        """
        self.ai_client = ai_client
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.max_concurrent = max_concurrent
        
        self._queue: Queue = Queue()
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._running = True
        self._lock = threading.Lock()
        
        # 启动批处理线程
        self._batch_thread = threading.Thread(target=self._batch_processor_loop, daemon=True)
        self._batch_thread.start()
        
        api_logger.info(
            f"AIBatchProcessor initialized for {ai_client.platform_type.value}/"
            f"{ai_client.model_name} (batch_size={batch_size}, max_concurrent={max_concurrent})"
        )
    
    def submit(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Future:
        """
        提交请求到批量队列
        
        Args:
            prompt: 提示文本
            context: 上下文信息
            
        Returns:
            Future: 异步结果
        """
        future = Future()
        request = BatchRequest(
            prompts=[prompt],
            context=[context or {}],
            future=future
        )
        
        self._queue.put(request)
        return future
    
    def submit_batch(
        self,
        prompts: List[str],
        contexts: Optional[List[Dict[str, Any]]] = None
    ) -> Future:
        """
        提交批量请求
        
        Args:
            prompts: 提示文本列表
            contexts: 上下文列表
            
        Returns:
            Future: 异步结果（List[AIResponse]）
        """
        future = Future()
        
        if not contexts:
            contexts = [{} for _ in prompts]
        
        request = BatchRequest(
            prompts=prompts,
            context=contexts,
            future=future
        )
        
        self._queue.put(request)
        return future
    
    def _batch_processor_loop(self):
        """批处理循环"""
        while self._running:
            try:
                # 收集一批请求
                batch_requests: List[BatchRequest] = []
                batch_start_time = time.time()
                
                # 等待第一个请求
                try:
                    first_request = self._queue.get(timeout=self.wait_time)
                    batch_requests.append(first_request)
                except Empty:
                    continue
                
                # 收集更多请求直到达到批量大小或超时
                while (
                    len(batch_requests) < self.batch_size and
                    time.time() - batch_start_time < self.wait_time
                ):
                    try:
                        request = self._queue.get(timeout=0.1)
                        batch_requests.append(request)
                    except Empty:
                        break
                
                # 合并批量请求
                all_prompts = []
                all_contexts = []
                all_futures = []
                
                for req in batch_requests:
                    all_prompts.extend(req.prompts)
                    all_contexts.extend(req.context)
                    all_futures.extend([req.future] * len(req.prompts))
                
                # 执行批量请求
                self._executor.submit(
                    self._execute_batch,
                    all_prompts,
                    all_contexts,
                    all_futures
                )
                
            except Exception as e:
                api_logger.error(f"Batch processor error: {e}")
    
    def _execute_batch(
        self,
        prompts: List[str],
        contexts: List[Dict[str, Any]],
        futures: List[Future]
    ):
        """
        执行批量请求
        
        Args:
            prompts: 提示列表
            contexts: 上下文列表
            futures: Future 列表
        """
        try:
            api_logger.info(
                f"Executing batch of {len(prompts)} requests for "
                f"{self.ai_client.platform_type.value}"
            )
            
            # 并发执行请求
            results = []
            for prompt, context in zip(prompts, contexts):
                try:
                    result = self.ai_client.send_prompt(prompt, **context)
                    results.append(result)
                except Exception as e:
                    api_logger.error(f"Batch request error: {e}")
                    results.append(
                        AIResponse(
                            success=False,
                            error_message=str(e),
                            model=self.ai_client.model_name,
                            platform=self.ai_client.platform_type.value
                        )
                    )
            
            # 设置结果
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
            
            api_logger.info(
                f"Batch completed: {len(prompts)} requests, "
                f"{sum(1 for r in results if r.success)} successful"
            )
            
        except Exception as e:
            api_logger.error(f"Batch execution error: {e}")
            
            # 设置异常
            for future in futures:
                if not future.done():
                    future.set_exception(e)
    
    def shutdown(self, wait: bool = True):
        """
        关闭处理器
        
        Args:
            wait: 是否等待完成
        """
        self._running = False
        self._executor.shutdown(wait=wait)
        
        # 设置未完成请求的异常
        while not self._queue.empty():
            try:
                request = self._queue.get_nowait()
                for future in request.future:
                    if not future.done():
                        future.set_exception(
                            Exception("Batch processor shutdown")
                        )
            except Empty:
                break


# ==================== 响应缓存 ====================

class AICacheEntry:
    """AI 响应缓存条目"""
    
    def __init__(self, response: AIResponse, created_at: datetime):
        self.response = response
        self.created_at = created_at
        self.expires_at = created_at + timedelta(seconds=BatchConfig.CACHE_TTL)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at


class AIResponseCache:
    """
    AI 响应缓存
    
    缓存相同的请求，避免重复调用
    """
    
    def __init__(self, max_size: int = BatchConfig.CACHE_MAX_SIZE):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self._cache: Dict[str, AICacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        
        api_logger.info(f"AIResponseCache initialized (max_size={max_size})")
    
    def _generate_key(self, prompt: str, **kwargs) -> str:
        """生成缓存键"""
        # 简化键生成，只使用 prompt
        # 可以扩展为包含 kwargs
        return f"{prompt.strip()}"
    
    def get(self, prompt: str, **kwargs) -> Optional[AIResponse]:
        """
        获取缓存响应
        
        Args:
            prompt: 提示文本
            **kwargs: 额外参数
            
        Returns:
            AIResponse 或 None
        """
        key = self._generate_key(prompt, **kwargs)
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                if entry.is_expired():
                    # 删除过期条目
                    del self._cache[key]
                    self._misses += 1
                    return None
                
                self._hits += 1
                return entry.response
            
            self._misses += 1
            return None
    
    def set(self, prompt: str, response: AIResponse, **kwargs):
        """
        设置缓存响应
        
        Args:
            prompt: 提示文本
            response: AI 响应
            **kwargs: 额外参数
        """
        # 只缓存成功的响应
        if not response.success:
            return
        
        key = self._generate_key(prompt, **kwargs)
        
        with self._lock:
            # 如果缓存已满，删除最旧的条目
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at
                )
                del self._cache[oldest_key]
            
            self._cache[key] = AICacheEntry(
                response=response,
                created_at=datetime.now()
            )
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            api_logger.info("AIResponseCache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': f"{hit_rate:.2f}%",
                'size': len(self._cache),
                'max_size': self.max_size
            }


# ==================== 带缓存和批处理的 AI 客户端包装器 ====================

class CachedBatchedAIClient:
    """
    带缓存和批处理的 AI 客户端包装器
    
    组合缓存和批处理功能，提供优化的 AI 调用接口
    """
    
    def __init__(
        self,
        ai_client: AIClient,
        enable_cache: bool = True,
        enable_batch: bool = True,
        batch_size: int = BatchConfig.MAX_BATCH_SIZE,
        batch_wait_time: float = BatchConfig.BATCH_WAIT_TIME
    ):
        """
        初始化包装器
        
        Args:
            ai_client: 原始 AI 客户端
            enable_cache: 是否启用缓存
            enable_batch: 是否启用批处理
            batch_size: 批量大小
            batch_wait_time: 批量等待时间
        """
        self.ai_client = ai_client
        self.enable_cache = enable_cache
        self.enable_batch = enable_batch
        
        # 初始化缓存
        self.cache = AIResponseCache() if enable_cache else None
        
        # 初始化批处理器
        self.batch_processor = AIBatchProcessor(
            ai_client=ai_client,
            batch_size=batch_size,
            wait_time=batch_wait_time
        ) if enable_batch else None
        
        api_logger.info(
            f"CachedBatchedAIClient initialized for "
            f"{ai_client.platform_type.value}/{ai_client.model_name} "
            f"(cache={enable_cache}, batch={enable_batch})"
        )
    
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示（带缓存和批处理优化）
        
        Args:
            prompt: 提示文本
            **kwargs: 额外参数
            
        Returns:
            AIResponse: AI 响应
        """
        # 1. 尝试从缓存获取
        if self.cache:
            cached_response = self.cache.get(prompt, **kwargs)
            if cached_response:
                api_logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cached_response
        
        # 2. 使用批处理器提交请求
        if self.batch_processor:
            future = self.batch_processor.submit(prompt, kwargs)
            response = future.result(timeout=BatchConfig.REQUEST_TIMEOUT)
        else:
            # 直接调用原始客户端
            response = self.ai_client.send_prompt(prompt, **kwargs)
        
        # 3. 缓存响应
        if self.cache and response.success:
            self.cache.set(prompt, response, **kwargs)
        
        return response
    
    def send_batch(
        self,
        prompts: List[str],
        contexts: Optional[List[Dict[str, Any]]] = None
    ) -> List[AIResponse]:
        """
        批量发送提示
        
        Args:
            prompts: 提示列表
            contexts: 上下文列表
            
        Returns:
            List[AIResponse]: AI 响应列表
        """
        if not self.batch_processor:
            # 如果没有批处理器，逐个发送
            return [
                self.send_prompt(prompt, **(contexts[i] if contexts else {}))
                for i, prompt in enumerate(prompts)
            ]
        
        # 提交批量请求
        future = self.batch_processor.submit_batch(prompts, contexts)
        return future.result(timeout=BatchConfig.REQUEST_TIMEOUT * len(prompts))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            'platform': self.ai_client.platform_type.value,
            'model': self.ai_client.model_name,
            'cache_enabled': self.enable_cache,
            'batch_enabled': self.enable_batch
        }
        
        if self.cache:
            stats['cache'] = self.cache.get_stats()
        
        if self.batch_processor:
            stats['batch'] = {
                'queue_size': self.batch_processor._queue.qsize(),
                'batch_size': self.batch_processor.batch_size,
                'max_concurrent': self.batch_processor.max_concurrent
            }
        
        return stats
    
    def shutdown(self):
        """关闭包装器"""
        if self.batch_processor:
            self.batch_processor.shutdown()
        
        if self.cache:
            self.cache.clear()
        
        api_logger.info(
            f"CachedBatchedAIClient shutdown for "
            f"{self.ai_client.platform_type.value}/{self.ai_client.model_name}"
        )


# ==================== 便捷函数 ====================

_ai_clients: Dict[str, CachedBatchedAIClient] = {}

def get_optimized_ai_client(
    ai_client: AIClient,
    enable_cache: bool = True,
    enable_batch: bool = True
) -> CachedBatchedAIClient:
    """
    获取优化的 AI 客户端
    
    Args:
        ai_client: 原始 AI 客户端
        enable_cache: 是否启用缓存
        enable_batch: 是否启用批处理
        
    Returns:
        CachedBatchedAIClient: 优化的客户端
    """
    key = f"{ai_client.platform_type.value}:{ai_client.model_name}"
    
    if key not in _ai_clients:
        _ai_clients[key] = CachedBatchedAIClient(
            ai_client=ai_client,
            enable_cache=enable_cache,
            enable_batch=enable_batch
        )
    
    return _ai_clients[key]

def cleanup_ai_clients():
    """清理所有 AI 客户端"""
    for client in _ai_clients.values():
        client.shutdown()
    _ai_clients.clear()
    api_logger.info("All AI clients cleaned up")
