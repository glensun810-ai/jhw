#!/usr/bin/env python3
"""
AI 响应日志记录增强模块
解决部分 API 返回结果未及时保存到 ai_responses.jsonl 的问题

增强功能:
1. 异步日志队列 - 避免阻塞主流程
2. 批量写入 - 提高写入效率
3. 失败重试机制 - 确保日志不丢失
4. 增强的错误处理
"""

import json
import os
import threading
import queue
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

# 导入原有的 logger
from wechat_backend.utils.ai_response_logger_v3 import AIResponseLogger, DEFAULT_LOG_FILE, _file_lock

# 日志队列配置
LOG_QUEUE_MAX_SIZE = 1000  # 队列最大容量
LOG_BATCH_SIZE = 10  # 批量写入大小
LOG_FLUSH_INTERVAL = 5  # 刷新间隔（秒）
LOG_MAX_RETRIES = 3  # 最大重试次数


class AsyncAIResponseLogger:
    """
    异步 AI 响应日志记录器
    使用队列和后台线程处理日志写入，避免阻塞主流程
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """初始化异步记录器"""
        if log_file:
            self.log_file = Path(log_file)
        else:
            self.log_file = DEFAULT_LOG_FILE
        
        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 日志队列
        self.log_queue = queue.Queue(maxsize=LOG_QUEUE_MAX_SIZE)
        
        # 后台写入线程
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._log_worker, daemon=True)
        self._worker_thread.start()
        
        # 统计信息
        self._stats = {
            'queued': 0,
            'written': 0,
            'failed': 0,
            'retried': 0
        }
        self._stats_lock = threading.Lock()
        
        print(f"[AsyncAIResponseLogger] 初始化完成，日志文件：{self.log_file}")
    
    def _log_worker(self):
        """后台日志写入线程"""
        batch = []
        last_flush_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                # 尝试从队列获取日志（超时 1 秒）
                try:
                    record = self.log_queue.get(timeout=1)
                    batch.append(record)
                except queue.Empty:
                    # 队列为空，继续等待
                    pass
                
                # 检查是否需要刷新
                should_flush = (
                    len(batch) >= LOG_BATCH_SIZE or
                    (batch and (time.time() - last_flush_time) >= LOG_FLUSH_INTERVAL) or
                    self._stop_event.is_set()
                )
                
                if should_flush and batch:
                    self._write_batch(batch)
                    self._stats['written'] += len(batch)
                    batch = []
                    last_flush_time = time.time()
                    
            except Exception as e:
                print(f"[AsyncAIResponseLogger] 工作线程错误：{e}")
                traceback.print_exc()
                
                # 尝试将批次中的日志写回队列
                if batch:
                    for record in batch:
                        try:
                            self.log_queue.put_nowait(record)
                        except queue.Full:
                            self._stats['failed'] += 1
        
        # 线程退出前，写入剩余日志
        if batch:
            self._write_batch(batch)
            self._stats['written'] += len(batch)
        
        print(f"[AsyncAIResponseLogger] 工作线程退出，统计：{self._stats}")
    
    def _write_batch(self, batch: list):
        """批量写入日志"""
        if not batch:
            return
        
        retry_count = 0
        success = False
        
        while retry_count < LOG_MAX_RETRIES and not success:
            try:
                with _file_lock:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        for record in batch:
                            f.write(json.dumps(record, ensure_ascii=False) + '\n')
                        f.flush()  # 确保写入磁盘
                
                success = True
                
                if retry_count > 0:
                    self._stats['retried'] += retry_count
                    
            except Exception as e:
                retry_count += 1
                print(f"[AsyncAIResponseLogger] 写入失败 (尝试 {retry_count}/{LOG_MAX_RETRIES}): {e}")
                
                if retry_count < LOG_MAX_RETRIES:
                    time.sleep(0.5 * retry_count)  # 递增延迟
        
        if not success:
            self._stats['failed'] += len(batch)
            print(f"[AsyncAIResponseLogger] 写入失败，丢弃 {len(batch)} 条日志")
    
    def log_response(self, **kwargs) -> Dict[str, Any]:
        """
        记录 AI 响应（异步）
        
        Returns:
            Dict: 日志记录 ID 和状态
        """
        import uuid
        
        # 构建日志记录
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        record = {
            'record_id': record_id,
            'timestamp': timestamp,
            'unix_timestamp': time.time(),
            'version': '3.0-enhanced',
            **kwargs
        }
        
        # 尝试加入队列
        try:
            self.log_queue.put_nowait(record)
            self._stats['queued'] += 1
            
            return {
                'record_id': record_id,
                'status': 'queued',
                'queue_size': self.log_queue.qsize()
            }
            
        except queue.Full:
            # 队列已满，同步写入
            print(f"[AsyncAIResponseLogger] 队列已满，同步写入 record_id={record_id}")
            
            try:
                with _file_lock:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
                        f.flush()
                
                self._stats['written'] += 1
                
                return {
                    'record_id': record_id,
                    'status': 'written_sync',
                    'queue_size': self.log_queue.qsize()
                }
                
            except Exception as e:
                self._stats['failed'] += 1
                print(f"[AsyncAIResponseLogger] 同步写入失败：{e}")
                
                return {
                    'record_id': record_id,
                    'status': 'failed',
                    'error': str(e)
                }
    
    def flush(self):
        """强制刷新队列中的所有日志"""
        print(f"[AsyncAIResponseLogger] 强制刷新队列，当前队列大小：{self.log_queue.qsize()}")
        
        # 等待工作线程处理
        wait_time = 0
        while not self.log_queue.empty() and wait_time < 10:
            time.sleep(1)
            wait_time += 1
        
        print(f"[AsyncAIResponseLogger] 刷新完成，剩余队列大小：{self.log_queue.qsize()}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            return {
                **self._stats,
                'queue_size': self.log_queue.qsize(),
                'worker_alive': self._worker_thread.is_alive()
            }
    
    def close(self):
        """关闭记录器"""
        print("[AsyncAIResponseLogger] 正在关闭...")
        self._stop_event.set()
        self.flush()
        self._worker_thread.join(timeout=5)
        print("[AsyncAIResponseLogger] 已关闭")


# 全局异步记录器实例
_async_logger: Optional[AsyncAIResponseLogger] = None
_async_logger_lock = threading.Lock()


def get_async_logger(log_file: Optional[str] = None) -> AsyncAIResponseLogger:
    """获取全局异步记录器实例"""
    global _async_logger
    
    with _async_logger_lock:
        if _async_logger is None:
            _async_logger = AsyncAIResponseLogger(log_file)
        return _async_logger


def log_ai_response_async(**kwargs) -> Dict[str, Any]:
    """
    异步记录 AI 响应（便捷函数）
    
    用法:
        result = log_ai_response_async(
            question="...",
            response="...",
            platform="deepseek",
            model="deepseek-chat",
            success=True
        )
        print(f"日志已加入队列：{result['record_id']}")
    """
    logger = get_async_logger()
    return logger.log_response(**kwargs)


# 增强的同步日志记录（带重试）
def log_ai_response_enhanced(**kwargs) -> Dict[str, Any]:
    """
    增强的同步日志记录（带重试机制）
    
    如果异步记录器可用，使用异步；否则使用同步
    """
    try:
        # 优先使用异步
        async_logger = get_async_logger()
        result = async_logger.log_response(**kwargs)
        
        if result['status'] == 'queued':
            return result
        # 如果队列满导致同步写入，也返回结果
        
    except Exception as e:
        print(f"[log_ai_response_enhanced] 异步记录失败，降级为同步：{e}")
    
    # 降级为同步记录（带重试）
    import uuid
    
    record_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    record = {
        'record_id': record_id,
        'timestamp': timestamp,
        'unix_timestamp': time.time(),
        'version': '3.0-enhanced-sync',
        **kwargs
    }
    
    retry_count = 0
    success = False
    
    while retry_count < LOG_MAX_RETRIES and not success:
        try:
            with _file_lock:
                with open(DEFAULT_LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    f.flush()
            
            success = True
            
        except Exception as e:
            retry_count += 1
            print(f"[log_ai_response_enhanced] 写入失败 (尝试 {retry_count}/{LOG_MAX_RETRIES}): {e}")
            
            if retry_count < LOG_MAX_RETRIES:
                time.sleep(0.5 * retry_count)
    
    if success:
        return {
            'record_id': record_id,
            'status': 'written',
            'retries': retry_count
        }
    else:
        return {
            'record_id': record_id,
            'status': 'failed',
            'error': '写入失败，已达最大重试次数'
        }
